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


@dataclass(frozen=True)
class Ausweis:
    """Aufgeloeste Identitaet. `beglaubigt` ist die einzige Angabe, die
    zaehlt -- `name` allein sagt nichts, weil ein unbeglaubigter Name frei
    gewaehlt sein kann."""
    name: str
    rollen: tuple[str, ...]
    beglaubigt: bool
    art: str = "maschine"

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
            art: str = "maschine", pfad: Path | None = None) -> str:
    """Legt einen Ausweis an und gibt das Geheimnis EINMAL zurueck. Danach
    steht in der Datei nur noch sein Hash -- ein verlorenes Geheimnis wird
    ersetzt, nie wiederhergestellt."""
    unbekannte = [r for r in rollen if r not in ROLLEN]
    if unbekannte:
        raise ValueError(f"unbekannte Rolle(n): {unbekannte}. "
                         f"Bekannt: {sorted(ROLLEN)}")
    if not name or ":" in name:
        raise ValueError("Name darf nicht leer sein und keinen Doppelpunkt "
                         "tragen (das Praefix 'unbeglaubigt:' braucht ihn).")
    if art not in ARTEN:
        raise ValueError(f"art muss eine von {ARTEN} sein, nicht {art!r}")
    pfad = pfad or ausweisdatei()
    geheimnis = geheimnis or secrets.token_urlsafe(32)
    salz = secrets.token_bytes(16)
    eintraege = [e for e in _lies_datei(pfad) if e.get("name") != name]
    eintraege.append({
        "name": name,
        "art": art,
        "rollen": list(rollen),
        "salz": salz.hex(),
        "hash": _ableiten(geheimnis, salz).hex(),
        "kdf": {"art": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
    })
    _schreibe_datei(pfad, eintraege)
    return geheimnis


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
            _stand_schluessel: tuple[int, int, int, int]
            ) -> tuple[str, tuple[str, ...], str] | None:
    """scrypt kostet je Pruefung rund 16 MiB und einige Millisekunden. Das ist
    fuer eine Anmeldung richtig und fuer einen Protokolleintrag falsch --
    _identity() laeuft bei JEDEM log_access(). Darum einmal je (Geheimnis,
    Dateistand) rechnen. Der Dateistand im Schluessel sorgt dafuer, dass ein
    neu angelegter Ausweis sofort greift, ohne Neustart."""
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
            # Fehlende Art -> 'maschine'. Ein Altbestand-Eintrag ohne Angabe
            # wird nie zum Menschen befoerdert, nur weil das Feld fehlt.
            art = eintrag.get("art", "maschine")
            return (eintrag["name"], tuple(eintrag.get("rollen", ())),
                    art if art in ARTEN else "maschine")
    return None


def loese_auf(argument: str | None = None, *,
              geheimnis: str | None = None,
              pfad: Path | None = None) -> Ausweis:
    """DIE Umkehrung: Ausweis gewinnt, Argument ist danach stumm.

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
        treffer = _pruefe(geheimnis, str(datei), _stand(datei))
        if treffer is not None:
            return Ausweis(name=treffer[0], rollen=treffer[1],
                           beglaubigt=True, art=treffer[2])

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

    print("ausweis.py: Selbsttest gruen")


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
