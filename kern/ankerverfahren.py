#!/usr/bin/env python3
"""Ankerverfahren -- austauschbare Verfahren, die eine Merkle-Wurzel aus
auditanker.py in einen unabhaengig nachpruefbaren Anker-Beleg verwandeln.
(Auftrag 2026-08-06, Anschluss an auditanker.py.)

WARUM ES DAS GIBT: auditanker.format_anchor() gibt eine Commit-Nachricht
aus -- eine Form, die git voraussetzt. Der Betreiber hat ausdruecklich
gesagt, dass ein Nutzer im Steuer-/Unternehmenskontext nicht gezwungen sein
soll, git zu benutzen. Dieses Modul liefert Verfahren, die ohne git
auskommen, plus den Rahmen, der sie austauschbar macht.

DER KERN, AN DEM SICH JEDES VERFAHREN UNTERSCHEIDET: ein Anker beantwortet
nicht "ist der Bestand unveraendert" -- das leistet die Kette/der Merkle-
Baum selbst. Er beantwortet "wem gegenueber ist das beweisbar". Eine
selbstgehaltene Kette beweist nichts gegen den, der sie haelt. Darum traegt
jedes Verfahren hier eine VerfahrenInfo: was es beweist, wem gegenueber,
was es voraussetzt, und -- am wichtigsten -- was es NICHT beweist.

ZWEI VERFAHREN:

1. RFC 3161 (Zeitstempeldienst). Reichweite: gegenueber jedem, der dem
   TSA-Betreiber traut -- auch gegen den Eigentuemer der Kette selbst.
   Setzt Netz + einen TSA voraus. Dieses Modul baut die Anfrage (DER,
   handgerollt -- kein asn1crypto/rfc3161ng im Bestand, siehe Ladder unten)
   und kann sie auf Wunsch senden; die KRYPTOGRAFISCHE Pruefung der
   TSA-Signatur gegen deren Zertifikatskette macht dieses Modul NICHT
   selbst (das ist eine vollstaendige CMS/X.509-Implementierung wert und
   genau das Rad, das `openssl ts -verify` bereits korrekt dreht). Was
   dieses Modul lokal prueft: dass ein Beleg tatsaechlich zu DIESER Wurzel
   gehoert (Messimprint-Vergleich) -- die Gegenprobe aus Abnahme Punkt 2.
   Die Signatur selbst zu pruefen bleibt Aufgabe eines externen Werkzeugs
   gegen die TSA-Antwort, die der Beleg unveraendert mitfuehrt.

2. Gegenzeichnung (zweiter Schluessel signiert). Gewaehlt statt Versand an
   eine fremde Stelle oder WORM, weil es das einzige Verfahren ist, das
   OHNE Netz, OHNE Konto und OHNE Aussenwirkung auskommt -- passend zu der
   Grenze "kein Netzaufruf im Selbsttest, keiner ohne ausdruecklichen
   Schalter" und zum Ponytail-Grundsatz (Ed25519 liegt mit `cryptography`
   bereits im Bestand, keine neue Abhaengigkeit). Reichweite: gegenueber
   der Gegenpartei, die den oeffentlichen Schluessel kennt -- kein Dritter
   noetig, passt in einen Unternehmenskontext (Pruefer, zweite Abteilung).

RAHMEN: jedes Verfahren hat `<name>_beleg(wurzel, bereich, zeitstempel,
..., senden=False|signieren=False)` -> dict und `<name>_pruefe(beleg, ...)`
-> bool. `baue_beleg()`/`pruefe_beleg()` sind die generischen Einstiege,
die anhand `beleg["verfahren"]` weiterreichen.

TROCKEN IST VOREINSTELLUNG: beide Bau-Funktionen haben einen Schalter
(`senden` bzw. `signieren`), der auf False steht. Ohne ihn wird nichts
gesendet, nichts signiert, kein Schluessel angefasst -- die Funktion baut
nur, was gesendet/signiert WUERDE, und sagt das im Beleg (`modus:
"trocken"`).

LADDER-ENTSCHEIDUNG (RFC-3161-DER-Bau): kein asn1crypto/rfc3161ng im
Bestand (siehe requirements -- pip list zeigt weder das eine noch das
andere), und ein neues Paket fuer eine sieben Felder lange, seit RFC 3161
(2001) fixe ASN.1-Struktur ist unverhaeltnismaessig. Die Bytes sind daher
von Hand gebaut und gegen `openssl ts -query` (im System vorhanden)
Byte-fuer-Byte verifiziert -- siehe test_ankerverfahren.py.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)


class TrockenlaufVerletzung(RuntimeError):
    """Wird erwartet und darf nie tatsaechlich geworfen werden -- Wachhund
    im Selbsttest, falls ein Verfahren doch mal ohne Schalter aktiv wuerde."""


# ─── DER-Bau fuer RFC 3161 (handgerollt, siehe Modul-Docstring) ─────────

SHA256_OID = "2.16.840.1.101.3.4.2.1"


def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    b = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(b)]) + b


def _der_tlv(tag: int, value: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(value)) + value


def _der_oid(dotted: str) -> bytes:
    arcs = [int(a) for a in dotted.split(".")]
    out = bytearray([arcs[0] * 40 + arcs[1]])
    for arc in arcs[2:]:
        if arc == 0:
            out.append(0)
            continue
        chunk: list[int] = []
        while arc:
            chunk.insert(0, arc & 0x7F)
            arc >>= 7
        for i in range(len(chunk) - 1):
            chunk[i] |= 0x80
        out.extend(chunk)
    return _der_tlv(0x06, bytes(out))


def _der_integer(n: int) -> bytes:
    if n == 0:
        return _der_tlv(0x02, b"\x00")
    b = n.to_bytes((n.bit_length() + 7) // 8 + 1, "big")
    while len(b) > 1 and b[0] == 0 and b[1] < 0x80:
        b = b[1:]
    return _der_tlv(0x02, b)


def _der_octet_string(b: bytes) -> bytes:
    return _der_tlv(0x04, b)


def _der_boolean(v: bool) -> bytes:
    return _der_tlv(0x01, b"\xff" if v else b"\x00")


def _der_sequence(*parts: bytes) -> bytes:
    return _der_tlv(0x30, b"".join(parts))


def _der_null() -> bytes:
    return b"\x05\x00"


def rfc3161_messageimprint_der(hashed: bytes) -> bytes:
    """MessageImprint ::= SEQUENCE { AlgorithmIdentifier(sha256), hashedMessage }."""
    alg_id = _der_sequence(_der_oid(SHA256_OID), _der_null())
    return _der_sequence(alg_id, _der_octet_string(hashed))


def rfc3161_anfrage_der(hashed: bytes, *, cert_req: bool = True) -> bytes:
    """TimeStampReq ::= SEQUENCE { version=1, messageImprint, certReq }.
    reqPolicy und nonce bewusst weggelassen (beide OPTIONAL) -- damit
    dieselbe Wurzel immer dieselbe Anfrage ergibt (reproduzierbar
    pruefbar, kein Zufall im Selbsttest)."""
    if len(hashed) != 32:
        raise ValueError("hashed_message muss SHA-256 sein (32 Byte)")
    parts = [_der_integer(1), rfc3161_messageimprint_der(hashed)]
    if cert_req:
        parts.append(_der_boolean(True))
    return _der_sequence(*parts)


# ─── Rahmen: Verfahren-Metadaten ────────────────────────────────────────

@dataclass(frozen=True)
class VerfahrenInfo:
    name: str
    beweist: str
    wem_gegenueber: str
    voraussetzt: list[str]
    beweist_nicht: list[str]
    kosten: str


RFC3161_INFO = VerfahrenInfo(
    name="rfc3161",
    beweist="Wurzel+Bereich existierten spaetestens zum TSA-Zeitstempel",
    wem_gegenueber="jedem, der dem TSA-Betreiber traut -- auch gegen den Eigentuemer der Kette",
    voraussetzt=["Netzzugang", "erreichbarer TSA (z.B. freetsa.org)", "kein Konto noetig"],
    beweist_nicht=[
        "dass der Kettenbestand selbst intakt ist (das leistet auditanker.merkle_root)",
        "WER die Anfrage gestellt hat (kein Identitaetsnachweis des Antragstellers)",
        "die Signatur der TSA-Antwort -- das prueft ein externes Werkzeug (openssl ts -verify) gegen deren Zertifikat, nicht dieses Modul",
    ],
    kosten="kostenlos bei oeffentlichen TSA (z.B. freetsa.org, DigiCert-Testdienste)",
)

GEGENZEICHNUNG_INFO = VerfahrenInfo(
    name="gegenzeichnung",
    beweist="ein zweiter Schluesselinhaber hat Wurzel+Bereich+Zeitpunkt gesehen und bestaetigt",
    wem_gegenueber="der Gegenpartei, die den oeffentlichen Schluessel kennt -- kein Dritter noetig",
    voraussetzt=["ein zweites Schluesselpaar (Ed25519)", "der oeffentliche Schluessel muss der pruefenden Seite bekannt sein"],
    beweist_nicht=[
        "irgendetwas gegen den Inhaber des zweiten Schluessels selbst -- er koennte kollusiv mitwirken",
        "dass der Zeitstempel im Beleg von einer unabhaengigen Uhr stammt (es ist die lokale Uhr des Signierenden, kein Trust-Anker fuer Zeit)",
        "die Identitaet hinter dem Schluessel, wenn kein Zertifikat/Ausweis dazu vorliegt",
    ],
    kosten="keine (kein Netz, kein Konto)",
)

VERGLEICHSTABELLE: list[dict[str, str]] = [
    {
        "verfahren": "RFC 3161",
        "reichweite": "gegen jeden, auch gegen Eigentuemer",
        "voraussetzung": "Netz + TSA",
        "kosten": "kostenlos (oeffentliche TSA)",
        "beweist_nicht": "die TSA-Signatur selbst -- extern pruefen (openssl ts -verify)",
    },
    {
        "verfahren": "Gegenzeichnung",
        "reichweite": "gegen die Gegenpartei, kein Dritter",
        "voraussetzung": "zweites Schluesselpaar, Pruefer kennt Public Key",
        "kosten": "keine",
        "beweist_nicht": "nichts gegen den Gegenzeichner selbst (Kollusion moeglich)",
    },
    {
        "verfahren": "Offline/WORM (nicht umgesetzt, siehe Auftrag)",
        "reichweite": "gegen niemanden extern -- nur gegen spaetere Selbsttaeuschung",
        "voraussetzung": "einmal beschreibbares Medium ohne eigenen Schreibzugriff",
        "kosten": "Hardware",
        "beweist_nicht": "alles, was ein Dritter braucht -- rein intern",
    },
]


def vergleichstabelle_text() -> str:
    """Text-Tabelle fuer CLI/Doku, keine Bibliothek noetig fuer 3 Zeilen."""
    cols = ["verfahren", "reichweite", "voraussetzung", "kosten", "beweist_nicht"]
    widths = {c: max(len(c), *(len(row[c]) for row in VERGLEICHSTABELLE)) for c in cols}
    lines = ["  ".join(c.ljust(widths[c]) for c in cols)]
    lines.append("  ".join("-" * widths[c] for c in cols))
    for row in VERGLEICHSTABELLE:
        lines.append("  ".join(row[c].ljust(widths[c]) for c in cols))
    return "\n".join(lines)


# ─── Kanonische Nachricht (gemeinsam fuer beide Verfahren) ──────────────

def _daten_ohne_zeit(wurzel: str, bereich: dict) -> bytes:
    """Wurzel + Bereich, OHNE Zeitstempel -- fuer RFC 3161: der
    Zeitstempel ist genau das, was die TSA beisteuert, ihn vorab
    einzubetten waere zirkulaer."""
    return f"{wurzel}|{bereich['von']}-{bereich['bis']}".encode("utf-8")


def _daten_mit_zeit(wurzel: str, bereich: dict, zeitstempel: str) -> bytes:
    """Fuer Gegenzeichnung: hier gibt es keine externe Uhr, die lokale
    Zeit ist Teil der Behauptung, die signiert wird."""
    return _daten_ohne_zeit(wurzel, bereich) + f"|{zeitstempel}".encode("utf-8")


# ─── Verfahren 1: RFC 3161 ───────────────────────────────────────────────

DEFAULT_TSA_URL = "https://freetsa.org/tsr"


def rfc3161_beleg(
    wurzel: str,
    bereich: dict,
    zeitstempel: str,
    *,
    senden: bool = False,
    tsa_url: str = DEFAULT_TSA_URL,
    timeout: float = 10.0,
) -> dict:
    """Baut die TimeStampReq-Anfrage. Trocken (Voreinstellung): nichts
    wird gesendet, der Beleg zeigt nur, was gesendet WUERDE. Mit
    `senden=True`: sendet an `tsa_url`, Antwort (roh, DER) landet
    unveraendert im Beleg -- deren Signatur prueft dieses Modul nicht
    selbst, siehe Modul-Docstring."""
    hashed = hashlib.sha256(_daten_ohne_zeit(wurzel, bereich)).digest()
    anfrage = rfc3161_anfrage_der(hashed)
    beleg = {
        "verfahren": "rfc3161",
        "modus": "trocken",
        "wurzel": wurzel,
        "bereich": bereich,
        "zeitstempel_lokal": zeitstempel,
        "hashed_message_hex": hashed.hex(),
        "anfrage_der_hex": anfrage.hex(),
        "antwort_der_hex": None,
        "tsa_url": tsa_url,
    }
    if not senden:
        return beleg
    req = urllib.request.Request(
        tsa_url,
        data=anfrage,
        headers={"Content-Type": "application/timestamp-query"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            antwort = resp.read()
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"RFC-3161-Anfrage an {tsa_url} fehlgeschlagen: {e}") from e
    beleg["modus"] = "gesendet"
    beleg["antwort_der_hex"] = antwort.hex()
    return beleg


def rfc3161_pruefe(beleg: dict, wurzel: str, bereich: dict) -> bool:
    """Gegenrichtung: gehoert dieser Beleg zu DIESER Wurzel+Bereich?
    Reine Messimprint-Gegenprobe -- die TSA-Signaturkette bleibt Sache
    eines externen Werkzeugs (siehe Modul-Docstring)."""
    hashed = hashlib.sha256(_daten_ohne_zeit(wurzel, bereich)).digest()
    return beleg.get("verfahren") == "rfc3161" and beleg.get("hashed_message_hex") == hashed.hex()


# ─── Verfahren 2: Gegenzeichnung ────────────────────────────────────────

def gegenzeichnung_beleg(
    wurzel: str,
    bereich: dict,
    zeitstempel: str,
    *,
    private_key_pem: bytes | None = None,
    signieren: bool = False,
) -> dict:
    """Trocken (Voreinstellung): zeigt die Nachricht, die signiert
    WUERDE, ruehrt keinen Schluessel an. Mit `signieren=True` muss
    `private_key_pem` mitgegeben werden (PEM, unverschluesselt) --
    dieses Modul erzeugt und beruehrt keine Schluessel des Betreibers,
    siehe Grenzen im Auftrag; fehlt der Schluessel, klare Fehlermeldung."""
    nachricht = _daten_mit_zeit(wurzel, bereich, zeitstempel)
    beleg = {
        "verfahren": "gegenzeichnung",
        "modus": "trocken",
        "wurzel": wurzel,
        "bereich": bereich,
        "zeitstempel": zeitstempel,
        "nachricht_hex": nachricht.hex(),
        "signatur_hex": None,
        "public_key_hex": None,
    }
    if not signieren:
        return beleg
    if private_key_pem is None:
        raise ValueError("signieren=True verlangt private_key_pem -- kein Schluessel im Modul erzeugt oder gespeichert")
    schluessel = load_pem_private_key(private_key_pem, password=None)
    if not isinstance(schluessel, Ed25519PrivateKey):
        raise ValueError("private_key_pem muss ein Ed25519-Schluessel sein")
    signatur = schluessel.sign(nachricht)
    public_key = schluessel.public_key().public_bytes_raw()
    beleg["modus"] = "signiert"
    beleg["signatur_hex"] = signatur.hex()
    beleg["public_key_hex"] = public_key.hex()
    return beleg


def gegenzeichnung_pruefe(beleg: dict, wurzel: str, bereich: dict, zeitstempel: str) -> bool:
    """Gegenrichtung: Signatur gegen neu gebaute Nachricht + im Beleg
    mitgefuehrten oeffentlichen Schluessel pruefen."""
    if beleg.get("verfahren") != "gegenzeichnung":
        return False
    sig_hex = beleg.get("signatur_hex")
    pub_hex = beleg.get("public_key_hex")
    if not sig_hex or not pub_hex:
        return False
    nachricht = _daten_mit_zeit(wurzel, bereich, zeitstempel)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(
            bytes.fromhex(sig_hex), nachricht
        )
        return True
    except InvalidSignature:
        return False


# ─── generischer Einstieg ────────────────────────────────────────────────

def baue_beleg(verfahren: str, wurzel: str, bereich: dict, zeitstempel: str, **kwargs: Any) -> dict:
    if verfahren == "rfc3161":
        return rfc3161_beleg(wurzel, bereich, zeitstempel, **kwargs)
    if verfahren == "gegenzeichnung":
        return gegenzeichnung_beleg(wurzel, bereich, zeitstempel, **kwargs)
    raise ValueError(f"unbekanntes Verfahren: {verfahren}")


def pruefe_beleg(beleg: dict, wurzel: str, bereich: dict, zeitstempel: str) -> bool:
    verfahren = beleg.get("verfahren")
    if verfahren == "rfc3161":
        return rfc3161_pruefe(beleg, wurzel, bereich)
    if verfahren == "gegenzeichnung":
        return gegenzeichnung_pruefe(beleg, wurzel, bereich, zeitstempel)
    raise ValueError(f"unbekanntes Verfahren im Beleg: {verfahren}")


# ─── Warteschlange (Auftrag 2026-08-06: "darf nie blockieren") ─────────
#
# Ein Zeitstempeldienst darf nicht darueber entscheiden, ob ein Abschluss
# durchlaeuft. versuche_anker() faengt darum JEDE Ausnahme aus baue_beleg()
# ab -- Netz, Zeitueberschreitung, Dienstablehnung, fehlender Schluessel --
# und legt einen Eintrag in einer eigenen Datei ab, statt hochzureichen.
#
# ABLAGEORT: eigene JSON-Datei neben knowledge.db, NICHT eine Tabelle darin.
# Begruendung: die Warteschlange muss lesbar bleiben, waehrend die DB
# gerade gesichert/wiederhergestellt wird (Auftrag) -- eine eigene Datei
# hat dabei keine Sperre/Transaktion mit der DB gemeinsam. Read-modify-write
# per json.load/json.dump ist fuer die erwartete Groessenordnung (Ausfaelle
# sind die Ausnahme, nicht die Regel) die einfachste tragende Loesung
# (Ladder), keine Bibliothek noetig.
#
# GEHEIMNISSE NIE IN DIE DATEI: private_key_pem wird vor dem Schreiben
# herausgefiltert (BSI DEV.2.5 -- keine Credentials in Dateien). Beim
# Nachholen einer Gegenzeichnung muss der Schluessel darum erneut
# mitgegeben werden, er wird nie persistiert.

ANKER_QUEUE_PATH = _w / "anker_warteschlange.json"

# ponytail: feste Zahl statt Backoff-Politik. Genug Abstand fuer
# voruebergehende Ausfaelle (TSA-Wartung, DNS-Hickup), ohne dass ein
# dauerhaft falscher Schluessel/URL endlos im Kreis laeuft. Hochziehen ist
# eine Zahl aendern, kein Umbau -- Erhoehung bei Bedarf hier vornehmen.
MAX_VERSUCHE = 5


def _jetzt_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _kategorisiere_fehler(exc: BaseException) -> tuple[str, str]:
    """Ordnet eine gescheiterte Anfrage einer von vier Lagen zu (Auftrag
    Punkt 4: 'haelt fest WARUM'). rfc3161_beleg() verpackt Netz-/Zeit-
    fehler in ein RuntimeError (`raise ... from e`) -- der Ursprung haengt
    am __cause__, deshalb wird der zuerst geprueft."""
    ursprung = exc.__cause__ or exc
    if isinstance(ursprung, TimeoutError):
        return "zeitueberschreitung", str(exc)
    if isinstance(ursprung, urllib.error.HTTPError):
        return "abgelehnt", str(exc)
    if isinstance(ursprung, urllib.error.URLError):
        return "netz", str(exc)
    if isinstance(exc, ValueError) and "schluessel" in str(exc).lower():
        return "schluessel_fehlt", str(exc)
    return "unbekannt", str(exc)


def _queue_laden(path: Path | str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _queue_speichern(entries: list[dict], path: Path | str) -> None:
    Path(path).write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def versuche_anker(
    verfahren: str,
    wurzel: str,
    bereich: dict,
    zeitstempel: str,
    *,
    queue_path: Path | str = ANKER_QUEUE_PATH,
    **kwargs: Any,
) -> dict:
    """Wie `baue_beleg()`, aber Auflage 1 aus dem Auftrag: eine Ausnahme
    wird NIE hochgereicht. Gelingt der Versuch, kommt der fertige Beleg
    zurueck (und NICHTS landet in der Warteschlange -- Gegenprobe Abnahme
    3). Scheitert er, wandert Wurzel+Bereich+Zeitstempel in die
    Warteschlange und die Rueckgabe zeigt modus='aufgeschoben'."""
    try:
        return baue_beleg(verfahren, wurzel, bereich, zeitstempel, **kwargs)
    except Exception as e:  # bewusst breit -- siehe Modul-Docstring dieses Abschnitts
        fehlerart, text = _kategorisiere_fehler(e)
        kwargs_sicher = {k: v for k, v in kwargs.items() if k != "private_key_pem"}
        jetzt = _jetzt_iso()
        eintrag = {
            "id": uuid.uuid4().hex,
            "verfahren": verfahren,
            "wurzel": wurzel,
            "bereich": bereich,
            "zeitstempel": zeitstempel,
            "kwargs_sicher": kwargs_sicher,
            "fehlerart": fehlerart,
            "fehler_text": text,
            "versuche": 1,
            "status": "offen",
            "erstellt_am": jetzt,
            "letzter_versuch_am": jetzt,
            "erledigt_am": None,
            "beleg": None,
        }
        entries = _queue_laden(queue_path)
        entries.append(eintrag)
        _queue_speichern(entries, queue_path)
        return {
            "verfahren": verfahren,
            "modus": "aufgeschoben",
            "wurzel": wurzel,
            "bereich": bereich,
            "fehlerart": fehlerart,
            "warteschlangen_id": eintrag["id"],
        }


def nachholen(
    *,
    queue_path: Path | str = ANKER_QUEUE_PATH,
    ausfuehren: bool = False,
    private_key_pem: bytes | None = None,
    now: datetime | None = None,
) -> dict:
    """Arbeitet offene Warteschlangeneintraege ab. Trocken per Vorgabe
    (Grenze: kein Netzaufruf ohne ausdruecklichen Schalter, gilt auch
    hier) -- ohne `ausfuehren=True` wird nur gezaehlt, was faellig waere,
    kein baue_beleg()-Aufruf, keine Datei angefasst. Mit `ausfuehren=True`:
    erfolgreiche Eintraege werden 'erledigt' MIT dem Beleg daneben
    (Auftrag Punkt 2); scheitert ein Versuch erneut, steigt der Zaehler,
    ab MAX_VERSUCHE kippt der Eintrag auf 'braucht_aufmerksamkeit' statt
    endlos weiterzulaufen (Punkt 5). Gegenzeichnungs-Eintraege ohne
    mitgegebenen `private_key_pem` werden uebersprungen (kein Zaehler-
    Aufschlag -- es wurde ja gar nicht versucht)."""
    now = now or datetime.now(timezone.utc)
    entries = _queue_laden(queue_path)
    offene = [e for e in entries if e["status"] == "offen"]
    if not ausfuehren:
        return {"modus": "trocken", "faellig": len(offene), "erledigt": 0,
                "weiter_offen": len(offene), "braucht_aufmerksamkeit": 0, "uebersprungen": 0}

    ergebnis = {"modus": "ausgefuehrt", "erledigt": 0, "weiter_offen": 0,
                "braucht_aufmerksamkeit": 0, "uebersprungen": 0}
    for eintrag in entries:
        if eintrag["status"] != "offen":
            continue
        kwargs = dict(eintrag["kwargs_sicher"])
        if eintrag["verfahren"] == "gegenzeichnung" and kwargs.get("signieren"):
            if private_key_pem is None:
                ergebnis["uebersprungen"] += 1
                continue
            kwargs["private_key_pem"] = private_key_pem
        try:
            beleg = baue_beleg(eintrag["verfahren"], eintrag["wurzel"], eintrag["bereich"],
                                eintrag["zeitstempel"], **kwargs)
        except Exception as e:
            fehlerart, text = _kategorisiere_fehler(e)
            eintrag["versuche"] += 1
            eintrag["fehlerart"] = fehlerart
            eintrag["fehler_text"] = text
            eintrag["letzter_versuch_am"] = now.isoformat()
            if eintrag["versuche"] >= MAX_VERSUCHE:
                eintrag["status"] = "braucht_aufmerksamkeit"
                ergebnis["braucht_aufmerksamkeit"] += 1
            else:
                ergebnis["weiter_offen"] += 1
            continue
        eintrag["status"] = "erledigt"
        eintrag["erledigt_am"] = now.isoformat()
        eintrag["beleg"] = beleg
        ergebnis["erledigt"] += 1
    _queue_speichern(entries, queue_path)
    return ergebnis


def rueckstand(queue_path: Path | str = ANKER_QUEUE_PATH, now: datetime | None = None) -> dict:
    """Zeigt den Rueckstand, ohne etwas zu veraendern (Auftrag Punkt 3:
    eine Warteschlange, in die niemand sieht, ist schlimmer als keine)."""
    now = now or datetime.now(timezone.utc)
    entries = [e for e in _queue_laden(queue_path) if e["status"] != "erledigt"]
    if not entries:
        return {"anzahl": 0, "aeltester_seit": None, "alter_tage": 0, "eintraege": []}
    aeltester = min(entries, key=lambda e: e["erstellt_am"])
    alter_tage = (now - datetime.fromisoformat(aeltester["erstellt_am"])).days
    return {
        "anzahl": len(entries),
        "aeltester_seit": aeltester["erstellt_am"],
        "alter_tage": alter_tage,
        "eintraege": [
            {"id": e["id"], "verfahren": e["verfahren"], "status": e["status"],
             "fehlerart": e["fehlerart"], "versuche": e["versuche"]}
            for e in entries
        ],
    }


# ─── Selbsttest (kein Netz, keine Schluessel des Betreibers) ────────────

def _selftest() -> None:
    # Referenzbytes unabhaengig von diesem Modul erzeugt:
    #   echo "testroot123" > /tmp/x; openssl ts -query -data /tmp/x -sha256 -no_nonce -cert -out /tmp/x.tsq
    # (openssl 3.6.3, im System vorhanden -- siehe Modul-Docstring "Ladder-Entscheidung").
    referenz_hex = (
        "3039020101303130 0d0609608648016503040201050004207ec49d976353"
        "0f5bea688883d86c5cdcc31d36bf4b4cb81b9cdec066eb4a2ff10101ff"
    ).replace(" ", "")
    hashed = hashlib.sha256(b"testroot123\n").digest()
    anfrage = rfc3161_anfrage_der(hashed)
    assert anfrage.hex() == referenz_hex, f"{anfrage.hex()} != {referenz_hex}"

    # Trockenlauf ist Voreinstellung: kein senden-Parameter -> nichts gesendet.
    bereich = {"von": 1, "bis": 4, "n": 4}
    beleg_a = rfc3161_beleg("aaaa", bereich, "2026-08-06T00:00:00+02:00")
    assert beleg_a["modus"] == "trocken"
    assert beleg_a["antwort_der_hex"] is None

    # Pruefrichtung: Beleg passt zur eigenen Wurzel...
    assert rfc3161_pruefe(beleg_a, "aaaa", bereich)
    # ...aber NICHT zu einer anderen Wurzel (Gegenprobe, Abnahme Punkt 2).
    assert not rfc3161_pruefe(beleg_a, "bbbb", bereich)
    # ...und NICHT zu einem anderen Bereich derselben Wurzel.
    assert not rfc3161_pruefe(beleg_a, "aaaa", {"von": 5, "bis": 8, "n": 4})

    # Ein Aufruf ohne `senden=True` darf niemals eine Netzfunktion beruehren --
    # strukturell garantiert (Codepfad returnt vor jedem urllib-Aufruf),
    # hier zusaetzlich am Ergebnis bestaetigt.
    if beleg_a["modus"] != "trocken":
        raise TrockenlaufVerletzung("rfc3161_beleg sendete ohne senden=True")

    # Gegenzeichnung: trocken zuerst.
    beleg_b = gegenzeichnung_beleg("cccc", bereich, "2026-08-06T00:00:00+02:00")
    assert beleg_b["modus"] == "trocken"
    assert beleg_b["signatur_hex"] is None
    if beleg_b["modus"] != "trocken":
        raise TrockenlaufVerletzung("gegenzeichnung_beleg signierte ohne signieren=True")

    # Fehlender Schluessel bei signieren=True -> saubere Meldung, kein Absturz anderswo.
    try:
        gegenzeichnung_beleg("cccc", bereich, "2026-08-06T00:00:00+02:00", signieren=True)
        raise AssertionError("haette ohne private_key_pem werfen muessen")
    except ValueError:
        pass

    # Signiert, mit einem NUR fuer diesen Test erzeugten Schluessel --
    # niemals ein Schluessel des Betreibers (siehe Grenzen im Auftrag).
    test_schluessel = Ed25519PrivateKey.generate()
    test_pem = test_schluessel.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    zeitstempel = "2026-08-06T00:00:00+02:00"
    beleg_signiert = gegenzeichnung_beleg(
        "cccc", bereich, zeitstempel, private_key_pem=test_pem, signieren=True
    )
    assert beleg_signiert["modus"] == "signiert"
    assert beleg_signiert["signatur_hex"] is not None

    # Pruefrichtung passt...
    assert gegenzeichnung_pruefe(beleg_signiert, "cccc", bereich, zeitstempel)
    # ...Gegenprobe: anderer Wurzel-Text verifiziert NICHT.
    assert not gegenzeichnung_pruefe(beleg_signiert, "dddd", bereich, zeitstempel)
    # ...Gegenprobe: anderer Zeitstempel verifiziert NICHT (Nachricht bindet die Zeit ein).
    assert not gegenzeichnung_pruefe(beleg_signiert, "cccc", bereich, "2099-01-01T00:00:00+02:00")
    # ...Gegenprobe: manipulierte Signatur verifiziert NICHT.
    manipuliert = dict(beleg_signiert)
    manipuliert["signatur_hex"] = "00" * 64
    assert not gegenzeichnung_pruefe(manipuliert, "cccc", bereich, zeitstempel)

    # generischer Einstieg spiegelt dasselbe.
    assert pruefe_beleg(beleg_signiert, "cccc", bereich, zeitstempel)
    assert not pruefe_beleg(beleg_signiert, "andere-wurzel", bereich, zeitstempel)

    print("ankerverfahren --selftest: alle Faelle bestanden")


# ─── CLI ─────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--selftest", action="store_true")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("vergleich", help="Vergleichstabelle ausgeben")

    p_rfc = sub.add_parser("rfc3161", help="RFC-3161-Beleg bauen (trocken, ausser --senden)")
    p_rfc.add_argument("wurzel")
    p_rfc.add_argument("--von", type=int, required=True)
    p_rfc.add_argument("--bis", type=int, required=True)
    p_rfc.add_argument("--zeitstempel", required=True)
    p_rfc.add_argument("--senden", action="store_true", help="tatsaechlich an die TSA senden (sonst Trockenlauf)")
    p_rfc.add_argument("--tsa-url", default=DEFAULT_TSA_URL)

    p_gz = sub.add_parser("gegenzeichnung", help="Gegenzeichnungs-Beleg bauen (trocken, ausser --signieren)")
    p_gz.add_argument("wurzel")
    p_gz.add_argument("--von", type=int, required=True)
    p_gz.add_argument("--bis", type=int, required=True)
    p_gz.add_argument("--zeitstempel", required=True)
    p_gz.add_argument("--signieren", action="store_true")
    p_gz.add_argument("--schluessel", type=Path, help="PEM-Datei mit Ed25519-Privatschluessel (nur mit --signieren)")

    p_nach = sub.add_parser("nachholen", help="Warteschlange abarbeiten (trocken ausser --ausfuehren)")
    p_nach.add_argument("--ausfuehren", action="store_true", help="tatsaechlich erneut versuchen (sonst nur Vorschau)")
    p_nach.add_argument("--schluessel", type=Path, help="PEM-Datei fuer faellige Gegenzeichnungs-Eintraege")

    sub.add_parser("rueckstand", help="Rueckstand der Warteschlange anzeigen")

    args = parser.parse_args(argv)

    if args.selftest:
        _selftest()
        return 0

    if args.cmd == "vergleich":
        print(vergleichstabelle_text())
        return 0

    if args.cmd == "rfc3161":
        bereich = {"von": args.von, "bis": args.bis}
        beleg = rfc3161_beleg(
            args.wurzel, bereich, args.zeitstempel, senden=args.senden, tsa_url=args.tsa_url
        )
        print(json.dumps(beleg, indent=2))
        return 0

    if args.cmd == "gegenzeichnung":
        bereich = {"von": args.von, "bis": args.bis}
        pem = args.schluessel.read_bytes() if args.schluessel else None
        beleg = gegenzeichnung_beleg(
            args.wurzel, bereich, args.zeitstempel, private_key_pem=pem, signieren=args.signieren
        )
        print(json.dumps(beleg, indent=2))
        return 0

    if args.cmd == "nachholen":
        pem = args.schluessel.read_bytes() if args.schluessel else None
        ergebnis = nachholen(ausfuehren=args.ausfuehren, private_key_pem=pem)
        print(json.dumps(ergebnis, indent=2))
        return 0

    if args.cmd == "rueckstand":
        print(json.dumps(rueckstand(), indent=2))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
