#!/usr/bin/env python3
"""ausweis.py -- B4.1/B4.2: wer etwas tut, wird gemessen statt behauptet.

Plan: docs/PLAN_B4_AUSWEIS_2026-08-09.md

DIE FEHLKLASSE, die dieses Modul schliesst: `_identity()` in
knowledge_mcp_server.py loeste bis heute so auf --

    actor or os.environ.get("BEGOD_KNOWLEDGE_ACTOR") or UNBEKANNTER_SCHREIBER

Das ARGUMENT steht vor der Umgebung. Wer `actor="betreiber"` mitschickt, IST
Betreiber; es gibt kein if und kein Abweisen. Bauartgleich mit L-8487fb
(openlehr): ein Endpunkt liess die Kennung frei waehlen und stellte dafuer
einen Grant aus.

WARUM NICHT IM GESPRAECH GEFRAGT WIRD ("wer bist du?"): Das Geheimnis stuende
dann im Verlauf, im Transkript auf der Platte, in jedem Kontextfenster und in
jeder Verdichtung. Ein Modell koennte es weitertragen -- absichtlich oder durch
eingeschleusten Text (siehe einschleusung.py). Und vor allem: wer im Gespraech
antwortet, BEHAUPTET seine Identitaet. Das ist der heutige Zustand mit mehr
Zeremonie. Die Identitaet kommt darum von dort, wo das Modell nicht hinreicht:
aus dem Prozessstart (Umgebungsvariable, vom Klienten gesetzt) bzw. spaeter aus
dem Bearer-Token (ADR-001). Das Modell erfaehrt seinen NAMEN, nie sein
GEHEIMNIS.

KEIN ABWEISEN OHNE AUSWEIS -- bewusst. 3.998 Protokollzeilen, mehrere lokale
Skripte (normbestand.py, hebb_kanten.py) und der ChatGPT-Zugang schreiben heute
ohne Ausweis. Ein hartes Abweisen waere ein Bruch ohne Gegenwert, solange keine
Ausweise existieren. Stattdessen traegt ein unbeglaubigter Name das Praefix
`unbeglaubigt:` -- damit ist im Protokoll dauerhaft und rueckwirkend
unterscheidbar, ob eine Zuschreibung geprueft war oder nur behauptet. Sobald
ein Ausweis vorliegt, ist das Argument stumm.

SCRYPT STATT ARGON2/BCRYPT: Der BSI-Hardstop nennt bcrypt/argon2; beide sind
auf diesem Rechner nicht installiert. hashlib.scrypt ist Standardbibliothek,
ebenfalls memory-hard und in BSI TR-02102-1 als Passwort-Ableitung zugelassen.
Die Abweichung ist damit benannt, nicht stillschweigend.

FEHLKLASSE DIESES MODULS: eine Identitaet wird beglaubigt, die es nicht ist.
PREIS EINES FEHLALARMS: Ein gueltiger Ausweis wird nicht erkannt -> der
Aufrufer faellt auf `unbeglaubigt:` zurueck und verliert Rechte. Laut, nicht
still -- und nie andersherum.

Aufruf:
    python3 ausweis.py --anlegen hausmeister --rollen readonly
    python3 ausweis.py --liste
    python3 ausweis.py --selftest
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

# --- Ablageort -------------------------------------------------------------
# AUSSERHALB des Repos und ausserhalb jeder Datenbank: wer die knowledge.db
# oeffnen kann, koennte sonst die Rechtetabelle aendern (L-bd1562). Rechte
# gehoeren dorthin, wo der Zugang entschieden wird, nicht dorthin, wo er wirkt.
#
# SICHTBAR STATT VERSTECKT (Betreiber, 2026-08-09: "kannst du mir die ausweise
# auf den desktop legen, das ich sie auf jedenfall wieder finde"). Ein Ordner
# auf dem Schreibtisch statt ~/.brainlehr. Was das kostet und was nicht:
#   - In der Datei stehen NUR scrypt-Hashes, Namen und Rollen. Kein Geheimnis
#     im Klartext, an keiner Stelle. Wer die Datei sieht, kann nichts damit.
#   - Die Rechte (0600) tragen den Schutz, nicht die Verborgenheit. Ein
#     Punktordner im Heimatverzeichnis ist nicht sicherer, nur unauffindbarer.
#   - Bezahlt wird: liegt der Schreibtisch in einer Cloud-Synchronisierung,
#     wandern die Hashes mit. Bei 32 Byte Zufallsgeheimnis ist ein
#     scrypt-Hash nicht zurueckrechenbar -- aber es ist eine Kopie mehr.
# Uebersteuerbar bleibt der Ort ueber BRAINLEHR_AUSWEISE.
VORGABE_AUSWEISORDNER = Path.home() / "Desktop" / "brainlehr-ausweise"
VORGABE_AUSWEISDATEI = VORGABE_AUSWEISORDNER / "ausweise.json"

# Liegt neben der Datei, damit der Ordner sich selbst erklaert, wenn ihn
# jemand in einem halben Jahr wiederfindet.
LIESMICH = """brainlehr — Ausweise

Diese Datei sagt, WER jemand ist. Sie enthaelt KEINE Geheimnisse im Klartext,
nur deren Pruefsummen (scrypt) — wer sie liest, kann sich damit nicht anmelden.

Das Geheimnis selbst steht genau zweimal:
  1. einmalig auf dem Bildschirm, als der Ausweis angelegt wurde
  2. in der Konfiguration des Klienten, der damit arbeitet
     (~/.claude.json, unter mcpServers.knowledge.env)
Bewahre es in deinem Passwortmanager auf. Es wird nie wiederhergestellt,
sondern ersetzt:  python3 ausweis.py --anlegen <name> --rollen <rollen>

Die Dateirechte sind 600 (nur du). Wird das aufgeweicht, ignoriert brainlehr
die Datei und beglaubigt niemanden mehr — lieber alle unbeglaubigt als falsch
beglaubigt.

ART: 'maschine' ist die Vorgabe. Nur ein Ausweis mit art=mensch gilt als
menschlicher Entscheider (z.B. fuer Hausnormen im Rang 1/2). Ein Geheimnis,
das in einer Klientenkonfiguration liegt, gehoert einer Maschine — auch wenn
es deinen Namen traegt.

Ordner verlegen:  Umgebungsvariable BRAINLEHR_AUSWEISE auf den neuen Pfad.
Alles rueckgaengig machen:  diesen Ordner loeschen und BRAINLEHR_GEHEIMNIS aus
der Klientenkonfiguration nehmen. Danach ist der Zustand wie vorher.
"""

# Umgebungsvariablen. GEHEIMNIS traegt das Geheimnis selbst -- es wird nie
# protokolliert, nie zurueckgegeben und nie in eine Fehlermeldung geschrieben.
ENV_GEHEIMNIS = "BRAINLEHR_GEHEIMNIS"
ENV_AUSWEISDATEI = "BRAINLEHR_AUSWEISE"

UNBEGLAUBIGT = "unbeglaubigt:"
UNBEKANNT = "unbekannt"

# scrypt-Parameter. n=2**14 ist der von RFC 7914 fuer interaktive Anmeldung
# genannte Wert; er kostet rund 16 MiB und einige Millisekunden je Pruefung.
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_LEN = 32

# --- Rollenmodell ----------------------------------------------------------
# Uebernommen aus AKA2026 (Knoten /brainlehr/was-brainlehr-fuer-b4-fehlt-liegt-in,
# belegt in konsil-akamy-webclient-2026-03-09.json). Muster: modul:aktion:bezug.
#
# Die DRITTE Stelle ist der Grund, warum dieses Modell und nicht ein eigenes:
# `own` und `published` machen Sichtbarkeit vom BEZUG zum Objekt abhaengig, nicht
# nur von der Rolle. Ohne sie gibt es nur ganz-oder-gar-nicht -- und genau daran
# scheitert jede Trennung innerhalb EINES gemeinsamen Bestands.
#
# Im Code statt in der Ausweisdatei: die Datei sagt, WER jemand ist. Was eine
# Rolle darf, ist eine Entscheidung und gehoert versioniert. Sonst kann, wer
# eine Ausweiszeile schreiben darf, sich auch Rechte erfinden.
ROLLEN: dict[str, tuple[str, ...]] = {
    "betreiber":   ("*",),
    "schreiber":   ("wissen:lesen", "wissen:schreiben",
                    "lehre:lesen", "lehre:schreiben",
                    "kante:lesen", "kante:schreiben",
                    "annahme:lesen", "annahme:schreiben",
                    "verwaltung:lesen"),
    "fachkundig":  ("wissen:lesen", "wissen:schreiben:own",
                    "lehre:lesen", "lehre:schreiben:own",
                    "kante:lesen", "annahme:lesen", "annahme:schreiben:own"),
    "leser":       ("wissen:lesen", "lehre:lesen", "kante:lesen",
                    "annahme:lesen"),
    "gast":        ("wissen:lesen:published", "lehre:lesen:published"),
}

# Bezugsstufen, absteigend nach Weite. Wird gebraucht, damit zwei Rollen mit
# unterschiedlichem Bezug auf dasselbe Recht die WEITERE gewinnen lassen --
# sonst haengt das Ergebnis an der Reihenfolge der Rollenliste.
_BEZUG_WEITE = {"alle": 3, "own": 2, "published": 1}


# Art des Ausweistraegers. VORGABE IST 'maschine', und das ist der Kern:
#
# Ein Ausweis wird brauchbar, indem sein Geheimnis in eine Klientenkonfiguration
# wandert (~/.claude.json). Wer das tut, gibt das Geheimnis einer MASCHINE --
# ab da handelt ein Modell unter diesem Namen. Hiesse der Ausweis dann
# 'betreiber', waere aus dem Modell per Konfigurationseintrag ein Mensch
# geworden.
#
# Das ist keine Theorie: der Trigger knowledge_nodes_normrang_herkunft_bi
# verweigert Hausnormen mit Rang 1/2, wenn norm_entschieden_von auf ein Modell
# zeigt (LIKE '%claude%', '%gpt%', ...) -- und norm_entschieden_von wird aus
# actor gesetzt. Ein menschlich benannter Maschinenausweis haette genau diese
# Sperre lautlos ausgehebelt. Gefunden beim Nachsehen auf die Frage des
# Betreibers "nicht dass wir uns nun selbst aussperren!" -- die Gefahr lag in
# der Gegenrichtung.
ARTEN = ("maschine", "mensch")

# Rechte, die ein Mandat NIE weitergeben kann -- nicht aus Misstrauen gegen den
# Delegierten, sondern wegen der Art der Frage. Das Vorbild ist die
# Urabstimmung: bei Grundsatzfragen entscheidet die Basis selbst, weil eine
# Stellvertretung den Sinn der Frage aufhebt.
# Ein Mandat, das eines davon zu uebertragen versucht, wird beim Anlegen
# abgewiesen statt stillschweigend beschnitten -- sonst entstuende ein Ausweis,
# der aussieht, als koennte er etwas.
NICHT_DELEGIERBAR = frozenset({"*", "verwaltung:schreiben", "norm:setzen",
                               "veto:sperren"})


@dataclass(frozen=True)
class Ausweis:
    """Aufgeloeste Identitaet. `beglaubigt` ist die einzige Angabe, die
    zaehlt -- `name` allein sagt nichts, weil ein unbeglaubigter Name frei
    gewaehlt sein kann."""
    name: str
    rollen: tuple[str, ...]
    beglaubigt: bool
    art: str = "maschine"
    # Wessen Vollmacht in `rollen` mit eingegangen ist -- None heisst: alles
    # daran ist eigenes Recht. Gehoert ins Protokoll, sonst ist hinterher nicht
    # unterscheidbar, ob jemand aus eigenem Recht oder als Delegierter handelte.
    mandat_von: str | None = None

    @property
    def ist_mensch(self) -> bool:
        """Nur ein beglaubigter, ausdruecklich menschlicher Ausweis. Ein
        unbeglaubigter Ausweis ist NIE ein Mensch, egal wie er heisst --
        sonst genuegte ein Argument, um einer zu werden."""
        return self.beglaubigt and self.art == "mensch"

    @property
    def protokollname(self) -> str:
        """Was in access_log.actor landet. Unbeglaubigte Namen tragen das
        Praefix dauerhaft mit -- die Unterscheidung geprueft/behauptet bleibt
        so rueckwirkend auswertbar.

        AUSNAHME 'unbekannt': dort gibt es keine Behauptung, die man als
        unbeglaubigt kennzeichnen koennte -- niemand hat etwas behauptet.
        'unbeglaubigt:unbekannt' waere nicht nur doppelt gemoppelt, es haette
        auch den bestehenden Wert UNBEKANNTER_SCHREIBER veraendert, auf den
        anderer Code vergleicht. Vom eigenen Test gefunden."""
        if self.beglaubigt or self.name == UNBEKANNT:
            return self.name
        return f"{UNBEGLAUBIGT}{self.name}"


# --- Ausweisdatei ----------------------------------------------------------

def ausweisdatei() -> Path:
    roh = os.environ.get(ENV_AUSWEISDATEI)
    return Path(roh) if roh else VORGABE_AUSWEISDATEI


def _lies_datei(pfad: Path) -> list[dict]:
    """Leere Liste, wenn es keine Datei gibt -- das ist der Normalfall vor der
    Erstausstattung und kein Fehler.

    RECHTEPRUEFUNG: eine Ausweisdatei, die andere lesen duerfen, ist keine.
    Bei zu weiten Rechten wird sie ignoriert (mit Meldung nach stderr) statt
    stillschweigend verwendet -- lieber alle unbeglaubigt als falsch
    beglaubigt."""
    if not pfad.exists():
        return []
    modus = pfad.stat().st_mode
    if modus & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"ausweis: {pfad} ist fuer Gruppe/Andere zugaenglich "
              f"(0{modus & 0o777:o}) -- ignoriert. Beheben: chmod 600 {pfad}",
              file=sys.stderr)
        return []
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as fehler:
        print(f"ausweis: {pfad} nicht lesbar ({fehler}) -- ignoriert.",
              file=sys.stderr)
        return []
    eintraege = daten.get("ausweise") if isinstance(daten, dict) else None
    return eintraege if isinstance(eintraege, list) else []


def _schreibe_datei(pfad: Path, eintraege: list[dict]) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    liesmich = pfad.parent / "LIESMICH.txt"
    if not liesmich.exists():
        liesmich.write_text(LIESMICH, encoding="utf-8")
    # Rechte VOR dem Schreiben setzen: zwischen open() und chmod() laege sonst
    # ein Fenster, in dem die Datei mit den Vorgaberechten der umask existiert.
    fd = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "ausweise": eintraege}, f,
                  ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(pfad, 0o600)


def _ableiten(geheimnis: str, salz: bytes) -> bytes:
    return hashlib.scrypt(geheimnis.encode("utf-8"), salt=salz,
                          n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_LEN)


def anlegen(name: str, rollen: list[str], *, geheimnis: str | None = None,
            art: str = "maschine", gilt_bis: str | None = None,
            mandat: dict | None = None, pfad: Path | None = None) -> str:
    """Legt einen Ausweis an und gibt das Geheimnis EINMAL zurueck. Danach
    steht in der Datei nur noch sein Hash -- ein verlorenes Geheimnis wird
    ersetzt, nie wiederhergestellt.

    `mandat` = {"von": <name>, "rollen": [...], "gegenstand": [...],
                "gilt_bis": <iso>}. Der Gegenstand ist PFLICHT: ein Mandat
    ohne ihn waere ein freies Mandat, und ein freies Mandat fuer ein Modell
    heisst, es entscheidet im Namen eines Menschen ueber Dinge, die dieser nie
    gesehen hat (docs/DURCHSPIEL_BEZUGSGRUPPEN_2026-08-09.md, 8.1)."""
    unbekannte = [r for r in rollen if r not in ROLLEN]
    if unbekannte:
        raise ValueError(f"unbekannte Rolle(n): {unbekannte}. "
                         f"Bekannt: {sorted(ROLLEN)}")
    if not name or ":" in name:
        raise ValueError("Name darf nicht leer sein und keinen Doppelpunkt "
                         "tragen (das Praefix 'unbeglaubigt:' braucht ihn).")
    if art not in ARTEN:
        raise ValueError(f"art muss eine von {ARTEN} sein, nicht {art!r}")
    _pruefe_datum(gilt_bis, "gilt_bis")

    pfad = pfad or ausweisdatei()
    eintraege = [e for e in _lies_datei(pfad) if e.get("name") != name]

    if mandat is not None:
        mandat = _pruefe_mandat(mandat, eintraege)

    geheimnis = geheimnis or secrets.token_urlsafe(32)
    salz = secrets.token_bytes(16)
    eintrag = {
        "name": name,
        "art": art,
        "rollen": list(rollen),
        "salz": salz.hex(),
        "hash": _ableiten(geheimnis, salz).hex(),
        "kdf": {"art": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
    }
    if gilt_bis:
        eintrag["gilt_bis"] = gilt_bis
    if mandat:
        eintrag["mandat"] = mandat
    eintraege.append(eintrag)
    _schreibe_datei(pfad, eintraege)
    return geheimnis


def _pruefe_datum(wert: str | None, feld: str) -> None:
    if wert is None:
        return
    try:
        datetime.fromisoformat(wert)
    except ValueError:
        raise ValueError(f"{feld} muss ISO-8601 sein, nicht {wert!r}") from None


def _pruefe_mandat(mandat: dict, eintraege: list[dict]) -> dict:
    """Alle Schranken beim ANLEGEN, damit kein Ausweis entsteht, der aussieht,
    als koennte er etwas. Die Laufzeitpruefung in _mandatsrollen() bleibt
    trotzdem -- die Datei kann auch von Hand geschrieben werden."""
    if not isinstance(mandat, dict):
        raise ValueError("mandat muss ein Objekt sein")
    von = mandat.get("von")
    mandant = _finde(eintraege, von) if von else None
    if mandant is None:
        raise ValueError(f"mandat.von: kein Ausweis namens {von!r} vorhanden")
    # Keine Weiterdelegation: eine Kette ist nicht mehr pruefbar, und bei einem
    # Menschen als Mandant braucht sie niemand.
    if isinstance(mandant.get("mandat"), dict):
        raise ValueError(f"{von!r} handelt selbst im Mandat -- "
                         "Weiterdelegation ist nicht vorgesehen")
    gegenstand = mandat.get("gegenstand") or []
    if not gegenstand:
        raise ValueError(
            "mandat.gegenstand fehlt. Ein Mandat ohne Gegenstand ist ein "
            "FREIES Mandat -- der Traeger entschiede dann im Namen eines "
            "anderen ueber Dinge, die dieser nie gesehen hat.")
    gewollt = set(mandat.get("rollen") or ())
    if not gewollt:
        raise ValueError("mandat.rollen fehlt")
    unbekannte = sorted(gewollt - set(ROLLEN))
    if unbekannte:
        raise ValueError(f"mandat.rollen unbekannt: {unbekannte}")
    # Nicht-delegierbare Rechte: manche Befugnisse sind es nicht wegen
    # Misstrauen gegen den Delegierten, sondern wegen der Art der Frage
    # (Urabstimmung, 8.2). Abweisen statt stillschweigend beschneiden.
    verboten = sorted(r for r in gewollt
                      if any(x in NICHT_DELEGIERBAR for x in ROLLEN.get(r, ())))
    if verboten:
        raise ValueError(
            f"nicht delegierbar: {verboten} -- diese Rolle traegt ein Recht "
            f"aus {sorted(NICHT_DELEGIERBAR)}, das bei seinem Traeger bleibt.")
    zuviel = sorted(gewollt - set(mandant.get("rollen", ())))
    if zuviel:
        raise ValueError(
            f"{von!r} hat selbst nicht: {zuviel}. Ein Mandat kann nur eine "
            "Teilmenge weitergeben, nie mehr als der Mandant hat.")
    _pruefe_datum(mandat.get("gilt_bis"), "mandat.gilt_bis")
    return {"von": von, "rollen": sorted(gewollt),
            "gegenstand": sorted(gegenstand),
            **({"gilt_bis": mandat["gilt_bis"]} if mandat.get("gilt_bis") else {})}


# --- Aufloesung ------------------------------------------------------------

def _stand(pfad: Path) -> tuple[int, int, int, int]:
    """Fingerabdruck der Ausweisdatei fuer den Cache-Schluessel. Aendert sie
    sich, faellt der Cache von selbst.

    st_ctime_ns und st_mode gehoeren dazu, nicht nur mtime und Groesse: ein
    `chmod` aendert den Inhalt NICHT, aber sehr wohl, ob die Datei jemanden
    beglaubigen darf (_lies_datei weist zu weite Rechte ab). Ohne beide blieb
    eine reparierte Datei im Cache als 'ignoriert' stehen -- vom eigenen
    Selbsttest gefunden, nicht vermutet."""
    try:
        s = pfad.stat()
        return (s.st_mtime_ns, s.st_ctime_ns, s.st_size, s.st_mode)
    except OSError:
        return (0, 0, 0, 0)


@lru_cache(maxsize=8)
def _pruefe(geheimnis: str, pfad_str: str,
            _stand_schluessel: tuple[int, int, int, int]) -> str | None:
    """Gibt nur den NAMEN zurueck, nicht den Eintrag.

    scrypt kostet je Pruefung rund 16 MiB und einige Millisekunden. Das ist
    fuer eine Anmeldung richtig und fuer einen Protokolleintrag falsch --
    _identity() laeuft bei JEDEM log_access(). Darum einmal je (Geheimnis,
    Dateistand) rechnen. Der Dateistand im Schluessel sorgt dafuer, dass ein
    neu angelegter Ausweis sofort greift, ohne Neustart.

    Warum nur der Name: alles Weitere (Ablauf, Mandat) haengt an der ZEIT und
    darf darum nicht mitgecacht werden -- ein zwischenzeitlich abgelaufenes
    Mandat wuerde sonst weitergelten. Den Eintrag frisch nachzuschlagen kostet
    nichts; die teure Rechnung ist die scrypt-Ableitung, und die bleibt
    gecacht."""
    for eintrag in _lies_datei(Path(pfad_str)):
        try:
            salz = bytes.fromhex(eintrag["salz"])
            erwartet = bytes.fromhex(eintrag["hash"])
            kdf = eintrag.get("kdf", {})
            gerechnet = hashlib.scrypt(
                geheimnis.encode("utf-8"), salt=salz,
                n=kdf.get("n", SCRYPT_N), r=kdf.get("r", SCRYPT_R),
                p=kdf.get("p", SCRYPT_P), dklen=len(erwartet))
        except (KeyError, ValueError, TypeError):
            continue  # kaputter Eintrag beglaubigt niemanden
        # Zeitkonstant: sonst verraet die Laufzeit, wie weit ein geratenes
        # Geheimnis stimmte.
        if hmac.compare_digest(gerechnet, erwartet):
            return eintrag["name"]
    return None


# --- Ablauf und Mandat -----------------------------------------------------

def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _abgelaufen(gilt_bis: str | None, jetzt: datetime) -> bool:
    """Ein unlesbares Datum gilt als abgelaufen, nicht als unbefristet. Ein
    Tippfehler im Ablaufdatum darf keinen unbegrenzten Zugang erzeugen."""
    if not gilt_bis:
        return False
    try:
        ende = datetime.fromisoformat(gilt_bis)
    except ValueError:
        return True
    if ende.tzinfo is None:
        ende = ende.replace(tzinfo=timezone.utc)
    return jetzt >= ende


def _art_von(eintrag: dict) -> str:
    """Fehlende Art -> 'maschine'. Ein Altbestand-Eintrag ohne Angabe wird nie
    zum Menschen befoerdert, nur weil das Feld fehlt."""
    art = eintrag.get("art", "maschine")
    return art if art in ARTEN else "maschine"


def _finde(eintraege: list[dict], name: str) -> dict | None:
    for e in eintraege:
        if e.get("name") == name:
            return e
    return None


def _mandatsrollen(eintrag: dict, eintraege: list[dict],
                   jetzt: datetime, gegenstand: str | None
                   ) -> tuple[tuple[str, ...], str | None]:
    """Der Schnitt wird ZUR LAUFZEIT gebildet, nicht beim Ausstellen.

    Delegation ist der klassische Weg zur Rechteausweitung: A darf X,
    delegiert an B, und B kann ploetzlich X+Y. Dagegen hilft nur, bei JEDEM
    Aufruf neu zu schneiden -- verliert der Mandant ein Recht, verliert es der
    Delegierte im selben Moment. Ein beim Ausstellen eingefrorener Schnitt
    ueberlebt den Mandanten.

    IMPERATIVES MANDAT (siehe docs/DURCHSPIEL_BEZUGSGRUPPEN_2026-08-09.md,
    8.1): Fuer ein Modell ist nur das weisungsgebundene Mandat zulaessig. Ein
    freies Mandat hiesse, es entscheidet im Namen eines Menschen ueber Dinge,
    die dieser nie gesehen hat. Darum ist der Gegenstand Pflicht, und
    ausserhalb davon faellt die Vollmacht weg -- ohne Abbruch, das ist das
    'zurueck in die Gruppe'.
    """
    mandat = eintrag.get("mandat")
    if not isinstance(mandat, dict):
        return (), None
    if _abgelaufen(mandat.get("gilt_bis"), jetzt):
        return (), None

    # Gegenstandsbindung: ausserhalb gilt die Vollmacht nicht. Kein Fehler --
    # der Delegierte behaelt seine eigenen Rechte und muss zurueckfragen.
    gegenstaende = mandat.get("gegenstand") or ()
    if gegenstand is None or gegenstand not in gegenstaende:
        return (), None

    mandant = _finde(eintraege, mandat.get("von", ""))
    if mandant is None or _abgelaufen(mandant.get("gilt_bis"), jetzt):
        return (), None
    # Keine Weiterdelegation: ein Mandat aus einem Mandat waere nicht mehr
    # pruefbar. anlegen() weist es bereits ab; hier steht die zweite Schranke,
    # weil die Datei auch von Hand geschrieben werden kann.
    if isinstance(mandant.get("mandat"), dict):
        return (), None

    hat_der_mandant = set(mandant.get("rollen", ()))
    gewollt = set(mandat.get("rollen", ()))
    return tuple(sorted(gewollt & hat_der_mandant)), mandat.get("von")


def loese_auf(argument: str | None = None, *,
              geheimnis: str | None = None,
              pfad: Path | None = None,
              gegenstand: str | None = None,
              jetzt: datetime | None = None) -> Ausweis:
    """DIE Umkehrung: Ausweis gewinnt, Argument ist danach stumm.

    `gegenstand` entscheidet, ob ein Mandat greift (imperatives Mandat, siehe
    _mandatsrollen). `jetzt` wird hereingereicht statt intern geholt -- ohne
    injizierbare Zeit laesst sich kein Ablauf pruefen, ohne die Uhr zu stellen.

    Reihenfolge:
      1. Geheimnis (Umgebung oder Parameter) trifft einen Eintrag -> beglaubigt.
      2. Sonst: Argument, dann BEGOD_KNOWLEDGE_ACTOR, dann 'unbekannt' --
         jeweils UNbeglaubigt.

    Ein Geheimnis, das keinen Eintrag trifft, fuehrt NICHT zu einem Fehler und
    NICHT zu einer stillen Beglaubigung: der Aufrufer faellt auf den
    unbeglaubigten Zweig zurueck. Ein falsches Geheimnis darf nie mehr Rechte
    ergeben als gar keines."""
    geheimnis = geheimnis if geheimnis is not None else os.environ.get(ENV_GEHEIMNIS)
    if geheimnis:
        datei = pfad or ausweisdatei()
        name = _pruefe(geheimnis, str(datei), _stand(datei))
        if name is not None:
            jetzt = jetzt or _jetzt()
            eintraege = _lies_datei(datei)
            eintrag = _finde(eintraege, name)
            # Ein abgelaufener Ausweis beglaubigt nicht mehr -- er wirft aber
            # auch keinen Fehler, sondern faellt in den unbeglaubigten Zweig.
            # Dieselbe Bauform wie beim falschen Geheimnis: nie mehr Rechte
            # als gar keiner, nie ein Abbruch, der Arbeit unmoeglich macht.
            if eintrag is not None and not _abgelaufen(eintrag.get("gilt_bis"), jetzt):
                geliehen, von = _mandatsrollen(eintrag, eintraege, jetzt, gegenstand)
                return Ausweis(
                    name=name,
                    rollen=tuple(sorted(set(eintrag.get("rollen", ())) | set(geliehen))),
                    beglaubigt=True,
                    # Ein Mandat hebt die Art NIE an: ein Maschinenausweis mit
                    # dem Mandat eines Menschen bleibt Maschine. Sonst waere
                    # das Mandat der Umweg zur Menschwerdung -- genau die
                    # Luecke, die `art` gerade geschlossen hat.
                    art=_art_von(eintrag),
                    mandat_von=von,
                )

    name = argument or os.environ.get("BEGOD_KNOWLEDGE_ACTOR") or UNBEKANNT
    # Ein Argument, das das Praefix selbst mitbringt, darf es nicht doppelt
    # tragen -- und vor allem nicht so aussehen, als sei es echt geprueft.
    if name.startswith(UNBEGLAUBIGT):
        name = name[len(UNBEGLAUBIGT):] or UNBEKANNT
    return Ausweis(name=name, rollen=(), beglaubigt=False)


# --- Rechte ----------------------------------------------------------------

def bezug_fuer(ausweis: Ausweis, recht: str) -> str | None:
    """Gibt den Bezug zurueck, in dem `recht` gilt: 'alle', 'own',
    'published' -- oder None, wenn es gar nicht gilt.

    None statt False, weil der Aufrufer den Bezug BRAUCHT: 'darf lesen' ohne
    'welche' ist die halbe Antwort, und genau die Haelfte, an der ganz-oder-
    gar-nicht scheitert.

    Vorgabe ist DENY: wer keine Rolle hat, darf nichts. Ein unbeglaubigter
    Ausweis traegt nie Rollen."""
    modul, _, aktion = recht.partition(":")
    if not modul or not aktion:
        raise ValueError(f"Recht braucht die Form modul:aktion -- {recht!r}")
    bestes: str | None = None
    for rolle in ausweis.rollen:
        for eintrag in ROLLEN.get(rolle, ()):
            if eintrag == "*":
                gefunden = "alle"
            else:
                e_modul, _, rest = eintrag.partition(":")
                e_aktion, _, e_bezug = rest.partition(":")
                if e_modul != modul:
                    continue
                if e_aktion != "*" and e_aktion != aktion:
                    continue
                gefunden = e_bezug or "alle"
            if bestes is None or _BEZUG_WEITE[gefunden] > _BEZUG_WEITE[bestes]:
                bestes = gefunden
            if bestes == "alle":
                return "alle"
    return bestes


def darf(ausweis: Ausweis, recht: str) -> bool:
    """Kurzform fuer Faelle ohne Bezug (z.B. ein Werkzeug ganz sperren)."""
    return bezug_fuer(ausweis, recht) is not None


# --- Selbsttest ------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ausweise.json"

        # --- P1: kein Ausweis -> Argument gilt, aber unbeglaubigt ----------
        a = loese_auf("betreiber", geheimnis=None, pfad=pfad)
        assert a.name == "betreiber" and not a.beglaubigt
        assert a.protokollname == "unbeglaubigt:betreiber"
        assert a.rollen == () and not darf(a, "wissen:schreiben"), \
            "unbeglaubigt darf nichts"

        # --- P2: DER Kern. Ausweis gewinnt, Argument ist stumm -------------
        g = anlegen("hausmeister", ["leser"], pfad=pfad)
        a = loese_auf("betreiber", geheimnis=g, pfad=pfad)
        assert a.name == "hausmeister", \
            f"Argument hat den Ausweis ueberstimmt: {a.name}"
        assert a.beglaubigt and a.protokollname == "hausmeister"

        # --- falsches Geheimnis gibt nie mehr als gar keines ---------------
        a = loese_auf("betreiber", geheimnis=g + "x", pfad=pfad)
        assert not a.beglaubigt and a.name == "betreiber"

        # --- Untergrabung: Praefix im Argument mitgeliefert -----------------
        a = loese_auf("unbeglaubigt:betreiber", geheimnis=None, pfad=pfad)
        assert a.protokollname == "unbeglaubigt:betreiber", a.protokollname
        a = loese_auf(UNBEGLAUBIGT, geheimnis=None, pfad=pfad)
        assert a.name == UNBEKANNT

        # --- Grenzwerte der Aufloesung -------------------------------------
        assert loese_auf(None, geheimnis=None, pfad=pfad).name == UNBEKANNT
        assert loese_auf("", geheimnis=None, pfad=pfad).name == UNBEKANNT
        # 'unbekannt' bekommt KEIN Praefix -- es gibt keine Behauptung, die
        # man als unbeglaubigt kennzeichnen koennte, und der Wert wird
        # anderswo verglichen (UNBEKANNTER_SCHREIBER).
        assert loese_auf(None, geheimnis=None, pfad=pfad).protokollname == UNBEKANNT
        assert loese_auf(UNBEKANNT, geheimnis=None, pfad=pfad).protokollname == UNBEKANNT
        assert loese_auf("x", geheimnis="", pfad=pfad).name == "x"

        # --- Env-Kette: Argument vor BEGOD_KNOWLEDGE_ACTOR, beide unbegl. ---
        alt = os.environ.get("BEGOD_KNOWLEDGE_ACTOR")
        os.environ["BEGOD_KNOWLEDGE_ACTOR"] = "aus-env"
        try:
            assert loese_auf(None, geheimnis=None, pfad=pfad).name == "aus-env"
            assert loese_auf("arg", geheimnis=None, pfad=pfad).name == "arg"
            # und auch die Env verliert gegen einen echten Ausweis
            assert loese_auf(None, geheimnis=g, pfad=pfad).name == "hausmeister"
        finally:
            if alt is None:
                del os.environ["BEGOD_KNOWLEDGE_ACTOR"]
            else:
                os.environ["BEGOD_KNOWLEDGE_ACTOR"] = alt

        # --- P4/P5/P6: Bezug ------------------------------------------------
        leser = loese_auf(geheimnis=g, pfad=pfad)
        assert bezug_fuer(leser, "wissen:lesen") == "alle"
        assert bezug_fuer(leser, "wissen:schreiben") is None, "Vorgabe ist deny"

        g2 = anlegen("gastnutzer", ["gast"], pfad=pfad)
        gast = loese_auf(geheimnis=g2, pfad=pfad)
        assert bezug_fuer(gast, "wissen:lesen") == "published"
        assert bezug_fuer(gast, "kante:lesen") is None

        g3 = anlegen("fachmann", ["fachkundig"], pfad=pfad)
        fach = loese_auf(geheimnis=g3, pfad=pfad)
        assert bezug_fuer(fach, "wissen:schreiben") == "own"
        assert bezug_fuer(fach, "wissen:lesen") == "alle"

        g4 = anlegen("chef", ["betreiber"], pfad=pfad)
        chef = loese_auf(geheimnis=g4, pfad=pfad)
        assert bezug_fuer(chef, "was:auch:immer".partition(":")[0] + ":lesen") == "alle"

        # --- Reihenfolge der Rollen darf das Ergebnis nicht aendern ---------
        g5 = anlegen("beides", ["gast", "leser"], pfad=pfad)
        g6 = anlegen("beides2", ["leser", "gast"], pfad=pfad)
        assert (bezug_fuer(loese_auf(geheimnis=g5, pfad=pfad), "wissen:lesen")
                == bezug_fuer(loese_auf(geheimnis=g6, pfad=pfad), "wissen:lesen")
                == "alle"), "weiterer Bezug muss gewinnen, unabhaengig von der Reihenfolge"

        # --- Art: Vorgabe maschine, Mensch nur ausdruecklich ---------------
        assert loese_auf(geheimnis=g, pfad=pfad).art == "maschine", \
            "Vorgabe muss maschine sein -- ein Ausweis landet in einer " \
            "Klientenkonfiguration, also bei einem Modell"
        assert not loese_auf(geheimnis=g, pfad=pfad).ist_mensch

        g7 = anlegen("markus", ["betreiber"], art="mensch", pfad=pfad)
        mensch = loese_auf(geheimnis=g7, pfad=pfad)
        assert mensch.ist_mensch and mensch.art == "mensch"

        # Ein UNbeglaubigter ist nie Mensch, egal wie er heisst -- sonst
        # genuegte ein Argument, um einer zu werden.
        assert not loese_auf("markus", geheimnis=None, pfad=pfad).ist_mensch

        # Altbestand ohne Feld 'art' wird nicht befoerdert.
        eintraege = _lies_datei(pfad)
        for e in eintraege:
            e.pop("art", None)
        _schreibe_datei(pfad, eintraege)
        assert loese_auf(geheimnis=g7, pfad=pfad).art == "maschine", \
            "fehlendes Feld darf niemanden zum Menschen machen"
        assert not loese_auf(geheimnis=g7, pfad=pfad).ist_mensch
        g7 = anlegen("markus", ["betreiber"], art="mensch", pfad=pfad)

        try:
            anlegen("x", ["leser"], art="halbgott", pfad=pfad)
        except ValueError:
            pass
        else:
            raise AssertionError("unbekannte Art haette abweisen muessen")

        # --- P7: Geheimnis steht nirgends im Klartext -----------------------
        roh = pfad.read_text(encoding="utf-8")
        for k in (g, g2, g3, g4):
            assert k not in roh, "Geheimnis im Klartext in der Ausweisdatei"

        # --- Dateirechte: zu weit -> ignoriert, nicht stillschweigend genutzt
        assert pfad.stat().st_mode & 0o777 == 0o600
        os.chmod(pfad, 0o644)
        assert not loese_auf(geheimnis=g, pfad=pfad).beglaubigt, \
            "weltlesbare Ausweisdatei darf niemanden beglaubigen"
        os.chmod(pfad, 0o600)
        assert loese_auf(geheimnis=g, pfad=pfad).beglaubigt

        # --- kaputte Datei beglaubigt niemanden -----------------------------
        kaputt = Path(tmp) / "kaputt.json"
        fd = os.open(kaputt, os.O_WRONLY | os.O_CREAT, 0o600)
        os.write(fd, b"{nicht json")
        os.close(fd)
        assert not loese_auf(geheimnis=g, pfad=kaputt).beglaubigt

        # --- fehlerhafte Anlage --------------------------------------------
        for name, rollen in (("x", ["gibtsnicht"]), ("", ["leser"]),
                             ("mit:doppelpunkt", ["leser"])):
            try:
                anlegen(name, rollen, pfad=pfad)
            except ValueError:
                pass
            else:
                raise AssertionError(f"haette abweisen muessen: {name} {rollen}")

        try:
            bezug_fuer(leser, "ohne-doppelpunkt")
        except ValueError:
            pass
        else:
            raise AssertionError("Recht ohne Aktion haette abweisen muessen")

    _selftest_mandat()
    print("ausweis.py: Selbsttest gruen")


def _selftest_mandat() -> None:
    """M1-M10 aus docs/DURCHSPIEL_BEZUGSGRUPPEN_2026-08-09.md, 8.6."""
    import tempfile

    T0 = datetime(2026, 8, 9, 12, 0, 0, tzinfo=timezone.utc)
    iso = lambda d: d.isoformat()  # noqa: E731

    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "ausweise.json"

        g_chef = anlegen("chefin", ["schreiber"], art="mensch", pfad=pfad)
        g_bote = anlegen("bote", ["leser"], pfad=pfad,
                         mandat={"von": "chefin", "rollen": ["schreiber"],
                                 "gegenstand": ["abfallwirtschaft"]})

        # --- M5: ausserhalb des Gegenstands nur eigene Rechte, kein Abbruch --
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0)
        assert a.rollen == ("leser",) and a.mandat_von is None
        assert bezug_fuer(a, "wissen:schreiben") is None

        # --- innerhalb: geliehenes Recht greift, Herkunft ist vermerkt -------
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert set(a.rollen) == {"leser", "schreiber"}, a.rollen
        assert a.mandat_von == "chefin"
        assert bezug_fuer(a, "wissen:schreiben") == "alle"

        # --- M3: ein Mandat hebt die Art NIE an ------------------------------
        assert a.art == "maschine" and not a.ist_mensch, \
            "Mandat eines Menschen darf keine Maschine befoerdern"

        # --- M2: Mandant verliert das Recht -> Delegierter sofort auch -------
        anlegen("chefin", ["leser"], art="mensch", geheimnis=g_chef, pfad=pfad)
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert a.rollen == ("leser",), \
            f"Schnitt wurde eingefroren statt zur Laufzeit gebildet: {a.rollen}"
        anlegen("chefin", ["schreiber"], art="mensch", geheimnis=g_chef, pfad=pfad)

        # --- M1: Mandat ueber ein Recht, das der Mandant nie hatte -----------
        try:
            anlegen("bote2", ["leser"], pfad=pfad,
                    mandat={"von": "chefin", "rollen": ["betreiber"],
                            "gegenstand": ["x"]})
        except ValueError as f:
            assert "nicht delegierbar" in str(f) or "hat selbst nicht" in str(f), f
        else:
            raise AssertionError("M1: haette abweisen muessen")

        # --- M4: Mandat ohne Gegenstand ist ein freies Mandat ----------------
        for kaputt in ({"von": "chefin", "rollen": ["schreiber"]},
                       {"von": "chefin", "rollen": ["schreiber"], "gegenstand": []}):
            try:
                anlegen("bote3", ["leser"], pfad=pfad, mandat=kaputt)
            except ValueError as f:
                assert "gegenstand" in str(f).lower(), f
            else:
                raise AssertionError("M4: freies Mandat haette abweisen muessen")

        # --- M8: nicht-delegierbares Recht ----------------------------------
        anlegen("gott", ["betreiber"], art="mensch", pfad=pfad)
        try:
            anlegen("statthalter", ["leser"], pfad=pfad,
                    mandat={"von": "gott", "rollen": ["betreiber"],
                            "gegenstand": ["alles"]})
        except ValueError as f:
            assert "nicht delegierbar" in str(f), f
        else:
            raise AssertionError("M8: haette abweisen muessen")

        # --- M9: Mandant gibt es gar nicht ----------------------------------
        try:
            anlegen("bote4", ["leser"], pfad=pfad,
                    mandat={"von": "niemand", "rollen": ["leser"],
                            "gegenstand": ["x"]})
        except ValueError as f:
            assert "kein Ausweis" in str(f), f
        else:
            raise AssertionError("M9: haette abweisen muessen")

        # --- M7: keine Weiterdelegation --------------------------------------
        try:
            anlegen("unterbote", ["leser"], pfad=pfad,
                    mandat={"von": "bote", "rollen": ["leser"],
                            "gegenstand": ["abfallwirtschaft"]})
        except ValueError as f:
            assert "Weiterdelegation" in str(f), f
        else:
            raise AssertionError("M7: haette abweisen muessen")

        # --- M6 + Grenzwerte am Ablauf ---------------------------------------
        ende = T0 + timedelta(hours=1)
        g_kurz = anlegen("zeitweise", ["leser"], pfad=pfad, gilt_bis=iso(ende))
        eine_sek = timedelta(seconds=1)
        assert loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=ende - eine_sek).beglaubigt
        # genau auf der Schwelle: abgelaufen. Ein Ablauf, der die Sekunde des
        # Endes noch gelten laesst, ist kein Ablauf, sondern eine Verlaengerung.
        assert not loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=ende).beglaubigt
        assert not loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=ende + eine_sek).beglaubigt
        # abgelaufen heisst unbeglaubigt, nicht Abbruch -- Arbeit bleibt moeglich
        a = loese_auf("zeitweise", geheimnis=g_kurz, pfad=pfad, jetzt=ende)
        assert a.protokollname == "unbeglaubigt:zeitweise" and a.rollen == ()

        # abgelaufenes MANDAT: Ausweis gilt weiter, Vollmacht nicht
        g_frist = anlegen("fristbote", ["leser"], pfad=pfad,
                          mandat={"von": "chefin", "rollen": ["schreiber"],
                                  "gegenstand": ["abfallwirtschaft"],
                                  "gilt_bis": iso(ende)})
        a = loese_auf(geheimnis=g_frist, pfad=pfad, jetzt=ende,
                      gegenstand="abfallwirtschaft")
        assert a.beglaubigt and a.rollen == ("leser",) and a.mandat_von is None

        # M9 zur Laufzeit: Mandant laeuft ab -> Vollmacht faellt mit ihm
        anlegen("chefin", ["schreiber"], art="mensch", geheimnis=g_chef,
                pfad=pfad, gilt_bis=iso(ende))
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=ende,
                      gegenstand="abfallwirtschaft")
        assert a.rollen == ("leser",), \
            "abgelaufener Mandant darf keine Vollmacht mehr tragen"

        # kaputtes Datum gilt als abgelaufen, nicht als unbefristet
        eintraege = _lies_datei(pfad)
        _finde(eintraege, "zeitweise")["gilt_bis"] = "morgen frueh"
        _schreibe_datei(pfad, eintraege)
        assert not loese_auf(geheimnis=g_kurz, pfad=pfad, jetzt=T0).beglaubigt, \
            "unlesbares Ablaufdatum darf keinen unbegrenzten Zugang erzeugen"

        # --- M10: Rotation -- der alte Ausweis muss scheitern -----------------
        g_alt = anlegen("sprecher", ["schreiber"], pfad=pfad)
        g_neu = anlegen("sprecher", ["schreiber"], pfad=pfad)
        assert loese_auf(geheimnis=g_neu, pfad=pfad, jetzt=T0).beglaubigt
        assert not loese_auf(geheimnis=g_alt, pfad=pfad, jetzt=T0).beglaubigt, \
            "M10: nach der Rotation gilt das alte Geheimnis weiter"

        # --- von Hand geschriebene Datei: die Laufzeitschranke haelt ----------
        eintraege = _lies_datei(pfad)
        eintraege.append({**_finde(eintraege, "bote"), "name": "schlaubi",
                          "mandat": {"von": "chefin", "rollen": ["betreiber"],
                                     "gegenstand": ["abfallwirtschaft"]}})
        _schreibe_datei(pfad, eintraege)
        a = loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert "betreiber" not in a.rollen, \
            "handgeschriebenes Mandat umging den Laufzeitschnitt"

        # ... und die KETTE von Hand. anlegen() weist sie ab, aber die Datei
        # kann jemand von Hand schreiben -- die Laufzeitschranke muss halten.
        #
        # WICHTIG fuer die Konstruktion dieser Probe: unterbote muss ein Recht
        # wollen, das bote SELBST hat ('leser'), nicht eines, das bote nur
        # geliehen hat ('schreiber'). Geliehenes faengt schon der Schnitt gegen
        # die eigenen Rollen des Mandanten ab -- eine Probe darauf ist blind
        # und war es auch: die erste Fassung blieb unter Mutation gruen
        # (Mutationsprobe 2026-08-09, einzige von sechs). Erst am eigenen Recht
        # des Delegierten wird die Kettenschranke ueberhaupt beobachtbar.
        eintraege = _lies_datei(pfad)
        g_unter = "geheimnis-unterbote"
        salz = secrets.token_bytes(16)
        eintraege.append({
            "name": "unterbote", "art": "maschine", "rollen": [],
            "salz": salz.hex(), "hash": _ableiten(g_unter, salz).hex(),
            "kdf": {"art": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
            "mandat": {"von": "bote", "rollen": ["leser"],
                       "gegenstand": ["abfallwirtschaft"]},
        })
        _schreibe_datei(pfad, eintraege)
        a = loese_auf(geheimnis=g_unter, pfad=pfad, jetzt=T0,
                      gegenstand="abfallwirtschaft")
        assert a.beglaubigt and a.rollen == (), \
            f"Weiterdelegation ueber zwei Stufen ging durch: {a.rollen}"


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--anlegen", metavar="NAME")
    p.add_argument("--rollen", default="leser",
                   help=f"kommagetrennt, bekannt: {','.join(sorted(ROLLEN))}")
    p.add_argument("--liste", action="store_true")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--datei", type=Path, default=None)
    args = p.parse_args()

    if args.selftest:
        _selftest()
        return 0

    pfad = args.datei or ausweisdatei()

    if args.anlegen:
        geheimnis = anlegen(args.anlegen, args.rollen.split(","), pfad=pfad)
        print(f"Ausweis '{args.anlegen}' angelegt in {pfad} (Rechte 600).")
        print("\nDas Geheimnis steht genau EINMAL hier. Es wird nicht "
              "gespeichert, nur sein Hash:\n")
        print(f"    {geheimnis}\n")
        print("Eintragen beim Klienten, nicht im Gespraech -- in ~/.claude.json "
              "unter mcpServers.knowledge.env:")
        print(f'    "{ENV_GEHEIMNIS}": "{geheimnis}"')
        return 0

    if args.liste:
        eintraege = _lies_datei(pfad)
        if not eintraege:
            print(f"Keine Ausweise in {pfad}.")
        for e in eintraege:
            print(f"{e['name']:20s} {','.join(e.get('rollen', []))}")
        return 0

    aktuell = loese_auf()
    print(f"Aufgeloest: {aktuell.protokollname}  Rollen: "
          f"{','.join(aktuell.rollen) or '-'}  "
          f"beglaubigt: {'ja' if aktuell.beglaubigt else 'nein'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
