#!/usr/bin/env python3
"""ausloeser.py -- INT-ACT-001: ein Auslöser ohne Sitzung handelt ohne
Zuschauer, darum braucht er dieselben vier Stopp-Punkte wie ein Mensch am
Werkzeug (keine Kennwörter, keine Außenwirkung, nichts Unumkehrbares, kein
Geld) plus Ausweis, Protokoll und einen Ausschalter, der ohne ihn selbst
erreichbar ist (docs/REQUIREMENTS_INTERFACE_KOMPAT.md, "Wirkung: der Teil,
den das Wissen nicht leisten kann").

NAMENSFALLE, bewusst vermieden: kern/wirkung.py existiert bereits und meint
die Wirkung des ABRUFS (ADR-018 -- ob eine Norm den Bestand erreicht). Dieses
Modul hier heißt ausloeser.py und meint etwas anderes: ob und wie ein
geplanter Vorgang OHNE Sitzung ausgeführt werden darf. Nicht verwechseln.

ZWEI SCHRITTE, GETRENNT:
  plane()     erklärt einen Auslöser (Name, Takt, Aktion) und sagt, WIE er
              beglaubigt, protokolliert und abgeschaltet wird. Führt nichts
              aus -- ein erklärter, nie ausgeführter Auslöser hinterlässt
              keinen Protokolleintrag.
  fuehre_aus()  führt einen erklärten Auslöser aus, nur wenn ein gültiger
              Ausweis vorliegt, der Auslöser erklärt ist, und der Ausschalter
              NICHT gesetzt ist. Jeder Aufruf schreibt einen Protokolleintrag
              -- auch eine Abweisung, sonst wäre ein Angriff auf den
              Ausschalter selbst unsichtbar.

BAUFORM AUSSCHALTER -- DATEI, nicht Umgebungsvariable, und das ist begründet:
Dieser Auslöser soll später von launchd angestoßen werden (de.brainlehr.dienst
ist heute der einzige LaunchAgent, und der antwortet nur). Die Umgebung eines
launchd-Prozesses steht in seinem plist und ändert sich nicht, ohne den Agenten
neu zu laden -- ein Umgebungsschalter wäre also *nicht* ohne den Auslöser
selbst erreichbar, weil ihn nur ändert, wer die Plist anfasst. Eine Datei kann
jeder Prozess unter demselben Nutzer jederzeit anlegen oder löschen, auch von
Hand im Finder ("Datei ausschalter-an anlegen"). BRAINLEHR_AUSLOESER_AUS bleibt
als Override für Tests und um den Ort zu verlegen, ist aber nicht die Sperre
selbst -- die Sperre ist die Existenz der Datei.

BAUFORM PROTOKOLL -- eigene JSONL-Datei, keine Datenbank-Tabelle: Diese Datei
ist tabu (kern/domaene.py, knowledge_mcp_server.py). Eine neue Tabelle bräuchte
eine Migration, die niemand angefordert hat, und der Auslöser darf laut Auftrag
keine Schemaänderung mitbringen. Eine Zeile je Aufruf ist genug, um rot vor
grün zu belegen (siehe tests/test_ausloeser.py).

BAUFORM PLAN-ABLAGE -- eigene JSON-Datei: plane() und fuehre_aus() laufen in
der Regel in VERSCHIEDENEN Prozessen (ein Aufruf erklärt, launchd führt später
aus) -- ein In-Memory-Register wäre beim zweiten Prozess leer. Die Datei liegt
neben der Ausweisdatei (kern.ausweis.ausweisdatei().parent), weil beide zum
selben Vorgang "wer darf hier was ohne Aufsicht" gehören.

ERSTER ZULÄSSIGER AKTIONSTYP: 'bericht' -- ausschließlich lesend und lokal.
Jeder weitere Typ (Netzaufruf, Versand, Veröffentlichung, Push, Geld,
Kennwörter, Unumkehrbares) wird von plane() abgewiesen, nicht nur dokumentiert
-- ERLAUBTE_AKTIONEN ist eine Vorgabe-deny-Liste, kein Verbotskatalog.

NICHT GEBAUT, bewusst: kein LaunchAgent, kein crontab-Eintrag, keine Änderung
an ~/Library -- das Einschalten ist die Entscheidung des Betreibers. Keine
Wiederholungslogik für 'takt' (der Text wird nur gespeichert, nicht
ausgewertet) -- das ist Aufgabe des Schedulers (launchd/cron), nicht dieses
Moduls. Keine Rollenprüfung über 'beglaubigt' hinaus -- der Auftrag verlangt
"ein gültiger Ausweis", keine bestimmte Rolle; wer eine Rolle braucht, prüft
das in der Aktion selbst.

Aufruf:
    python3 ausloeser.py --liste
    python3 ausloeser.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen --
# siehe kern/ausweis.py fuer die Begruendung, hier wortgleich uebernommen.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import ausweis  # noqa: E402
import ort  # noqa: E402  -- WURZEL/runs, gleiches Muster wie melder/rasterblick.py
import speicher  # noqa: E402  -- Naht zur DB, nur speicher.lesen() (mode=ro)

ENV_AUSSCHALTER = "BRAINLEHR_AUSLOESER_AUS"
ENV_PROTOKOLL = "BRAINLEHR_AUSLOESER_PROTOKOLL"
ENV_PLAENE = "BRAINLEHR_AUSLOESER_PLAENE"
ENV_KENNZAHLEN = "BRAINLEHR_AUSLOESER_KENNZAHLEN"

_DATEINAME_AUSSCHALTER = "ausloeser-aus"
_DATEINAME_PROTOKOLL = "ausloeser-protokoll.jsonl"
_DATEINAME_PLAENE = "ausloeser-plaene.json"
# Unter runs/, nicht neben Ausweis/Protokoll: die anderen drei sind
# Betriebszustand des Auslösers selbst (Ausweisordner, oft 0700, nicht zum
# Ansehen gedacht). Diese Datei ist eine Zeitreihe zum Nachsehen -- runs/ ist
# genau dafuer da (siehe runs/messlauf_*.json, runs/ausgangsmessung_*.json).
_DATEINAME_KENNZAHLEN = "ausloeser_kennzahlen.jsonl"


def _basisordner() -> Path:
    """Derselbe Ordner wie die Ausweisdatei -- nicht bei Modulimport
    ausgewertet (das wuerde Testueberschreibungen der Umgebung verpassen),
    sondern bei jedem Aufruf frisch."""
    return ausweis.ausweisdatei().parent


def ausschalterdatei() -> Path:
    roh = os.environ.get(ENV_AUSSCHALTER)
    return Path(roh) if roh else _basisordner() / _DATEINAME_AUSSCHALTER


def protokolldatei() -> Path:
    roh = os.environ.get(ENV_PROTOKOLL)
    return Path(roh) if roh else _basisordner() / _DATEINAME_PROTOKOLL


def plaenedatei() -> Path:
    roh = os.environ.get(ENV_PLAENE)
    return Path(roh) if roh else _basisordner() / _DATEINAME_PLAENE


def kennzahlendatei() -> Path:
    roh = os.environ.get(ENV_KENNZAHLEN)
    return Path(roh) if roh else ort.WURZEL / "runs" / _DATEINAME_KENNZAHLEN


def ausgeschaltet(pfad: Path | None = None) -> bool:
    return (pfad or ausschalterdatei()).exists()


# --- Aktionstypen ------------------------------------------------------------
# Vorgabe DENY, wie bei werkzeugrechte.RECHTE: ein Aktionstyp ohne Eintrag
# hier ist gesperrt, nicht frei. Jede Funktion bekommt nur den Namen -- keine
# Aktion braucht mehr, solange 'lesend und lokal' die Grenze ist.

def _kennzahlen(db: Path | None = None) -> dict:
    """Fuenf billige COUNT-Abfragen ueber speicher.lesen() (mode=ro) -- rein
    lesend, kein Schreibversuch moeglich. Bewusst NICHT dabei, aus S22-Vorschlag:
      - 'Melder ohne Ausloeser' (melder/ausloeserlos.py): gemessen ueber 2s fuer
        einen vollstaendigen Dateibaum-Scan -- allein schon ueber dem Budget
        dieses Berichts.
      - 'Pruefstein-Kandidaten' (kern/umschrift_pruefstein.py): vergleicht
        Textpaare, keine billige Zaehlung, kein Kandidat ohne teuren Lauf.
    Beide sind aus dem Bericht gestrichen, nicht vergessen."""
    with speicher.lesen(db) as conn:
        return {
            "knoten_gesamt": conn.execute(
                "SELECT COUNT(*) n FROM knowledge_nodes WHERE zurueckgezogen = 0"
            ).fetchone()["n"],
            "knoten_arbeitsbestand": conn.execute(
                "SELECT COUNT(*) n FROM knowledge_nodes "
                "WHERE zurueckgezogen = 0 AND gattung = 'arbeitsbestand'"
            ).fetchone()["n"],
            "lehren_aktiv": conn.execute(
                "SELECT COUNT(*) n FROM lessons_learned WHERE status = 'active'"
            ).fetchone()["n"],
            "access_log_zeilen": conn.execute(
                "SELECT COUNT(*) n FROM access_log"
            ).fetchone()["n"],
            "access_log_mit_tokens": conn.execute(
                "SELECT COUNT(*) n FROM access_log WHERE tokens_input IS NOT NULL"
            ).fetchone()["n"],
        }


def _zeile_anhaengen(pfad: Path, zeile: dict) -> None:
    """Haengt an -- ueberschreibt nie. Zwei Ausfuehrungen erzeugen zwei
    Zeilen, das ist der ganze Punkt einer Zeitreihe (S22)."""
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(pfad, "a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def _aktion_bericht(name: str) -> dict:
    """Der einzige heute zugelassene Aktionstyp: liest nur lesend (mode=ro)
    aus dem Bestand, schreibt ausschließlich eine Zeile an die eigene
    Zeitreihe (kennzahlendatei()) an -- keine andere Datei, kein Netz, kein
    Modellaufruf."""
    kennzahlen = _kennzahlen()
    zeile = {"zeit": _jetzt().isoformat(), "name": name, **kennzahlen}
    ziel = kennzahlendatei()
    _zeile_anhaengen(ziel, zeile)
    return {"typ": "bericht", "name": name, "datei": str(ziel), "kennzahlen": kennzahlen}


def _aktion_rundruf(name: str) -> dict:
    """Fragt die laufenden Sitzungen, wo der Betreiber sie zuletzt korrigieren
    musste -- und legt die Frage als Datei ab, statt sie selbst zu verschicken.

    ANLASS, gemessen: Am 2026-08-18 wurden sieben laufende Sitzungen dieses
    Rechners von Hand befragt. Vier antworteten, fuenf Befunde kamen zurueck,
    KEIN EINZIGER stammte aus eigener Arbeit; drei waren am selben Tag baubar
    (Knoten 58da4895). Drei Zuege nach ihrer Antwort begann eine Sitzung eine
    neue Abhaengigkeitsaenderung, die niemand gemeldet haette -- weil niemand
    mehr fragte. Genau das macht den Rundruf zu einem Takt und nicht zu einem
    Ereignis.

    WARUM DIESE AKTION NICHT SELBST VERSCHICKT: Ein Auslaeser laeuft ohne
    Sitzung; er hat kein SendMessage und darf keins bekommen. Eine Aktion, die
    von sich aus andere Sitzungen anschreibt, waere Aussenwirkung aus einem
    Hintergrundlauf heraus -- der dritte der vier Stopp-Punkte. Sie legt
    deshalb nur den AUFTRAG ab; die naechste Sitzung, die ihn liest,
    verschickt ihn. Das ist derselbe Bau wie beim Bericht: schreiben, nicht
    handeln.

    DIE FRAGE IST DIE BERICHTIGTE FASSUNG des Betreibers, woertlich:
    "ich meinte eher welche entscheidung musste den betreiber wiedersprechen,
    wo musst er dich korregieren". Nicht die Selbsteinschaetzung ("was
    braeuchte Widerspruch") -- die ist nach L-79ec88 in beide Richtungen
    unzuverlaessig. Gefragt wird nach dem, was im Verlauf nachlesbar ist."""
    frage = (
        "RUNDRUF (Auslöser {name}, {zeit}). Drei Fragen, je höchstens zwei Sätze. "
        "Kein Auftrag — laufende Arbeit nicht unterbrechen.\n"
        "1. Wer bist du (Repo, Zweig, woran gerade) und welche Dateien hältst du?\n"
        "2. Wo hat der Betreiber dich seit dem letzten Rundruf tatsächlich korrigiert "
        "oder zurückgepfiffen? Je Vorfall: was du getan hattest, was er WÖRTLICH sagte, "
        "und was in brainlehr hätte anschlagen müssen, damit er es nicht selbst sagen musste. "
        "Der dritte Punkt ist der Ertrag.\n"
        "3. Hast du eine Abhängigkeit geändert, auf die eine andere Sitzung baut "
        "(Pfad, Name, Feld, Format, Schema)? Oder brauchst du eine unverändert?"
    ).format(name=name, zeit=_jetzt().isoformat())

    zeile = {"zeit": _jetzt().isoformat(), "name": name, "typ": "rundruf",
             "zustellung": "offen", "frage": frage}
    ziel = kennzahlendatei().with_name("rundruf-auftraege.jsonl")
    _zeile_anhaengen(ziel, zeile)
    return {"typ": "rundruf", "name": name, "datei": str(ziel),
            "hinweis": "Auftrag abgelegt. Verschickt wird er von der naechsten Sitzung, "
                       "die ihn liest -- ein Hintergrundlauf schreibt keine Nachrichten."}


ERLAUBTE_AKTIONEN = {"bericht": _aktion_bericht, "rundruf": _aktion_rundruf}


_MENSCHTEXT = {
    "kein_ausweis": "Dieser Auslöser braucht einen gültigen Ausweis -- keiner liegt vor.",
    "nicht_erklaert": "Dieser Auslöser ist nicht erklärt -- zuerst plane() aufrufen.",
    "ausschalter_gesetzt": "Der Ausschalter ist gesetzt -- dieser Auslöser ist abgeschaltet.",
    "aktionstyp_nicht_erlaubt": "Dieser Aktionstyp ist nicht zugelassen.",
}


# --- Plan --------------------------------------------------------------------

def _lies_plaene(pfad: Path) -> dict:
    if not pfad.exists():
        return {}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    plaene = daten.get("plaene") if isinstance(daten, dict) else None
    return plaene if isinstance(plaene, dict) else {}


def _schreibe_plaene(pfad: Path, plaene: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "plaene": plaene}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(pfad, 0o600)


def plane(name: str, takt: str, aktion: str, *, plaene_pfad: Path | None = None,
          jetzt: datetime | None = None) -> dict:
    """Erklärt einen Auslöser. Führt NICHTS aus -- siehe fuehre_aus().

    Gibt zurück, WIE dieser Auslöser (und jeder andere) beglaubigt,
    protokolliert und abgeschaltet wird. Diese drei Werte hängen nicht am
    einzelnen Namen, sie sind fürs ganze Modul gleich -- die Rückgabe macht
    sie trotzdem an jedem Plan sichtbar, weil genau das der Beleg ist, den
    tests/test_interface_kompat_katalog.py verlangt."""
    if not name or not name.strip():
        raise ValueError("name darf nicht leer sein")
    if not takt or not takt.strip():
        raise ValueError("takt darf nicht leer sein")
    if aktion not in ERLAUBTE_AKTIONEN:
        raise ValueError(
            f"Aktionstyp {aktion!r} ist nicht zugelassen. Ein Auslöser ohne "
            "Sitzung darf nichts mit Außenwirkung tun (Netzaufruf, Versand, "
            "Veröffentlichung, Push), kein Geld bewegen, keine Kennwörter "
            "lesen und nichts Unumkehrbares tun. Zugelassen ist ausschließlich: "
            f"{sorted(ERLAUBTE_AKTIONEN)}.")

    pfad = plaene_pfad or plaenedatei()
    plaene = _lies_plaene(pfad)
    plaene[name] = {"takt": takt, "aktion": aktion,
                    "erklaert_am": (jetzt or _jetzt()).isoformat()}
    _schreibe_plaene(pfad, plaene)

    return {
        "name": name, "takt": takt, "aktion": aktion,
        "ausweis": "gültiger, beglaubigter Ausweis (kern.ausweis.loese_auf) "
                   "wird vor jeder Ausführung geprüft",
        "protokoll": str(protokolldatei()),
        "ausschalter": str(ausschalterdatei()),
    }


# --- Protokoll -----------------------------------------------------------

def _protokolliere(pfad: Path, *, name: str, ergebnis: str,
                   ausw: "ausweis.Ausweis", jetzt: datetime) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    zeile = json.dumps({
        "zeit": jetzt.isoformat(), "name": name, "ergebnis": ergebnis,
        "ausweis": ausw.protokollname,
    }, ensure_ascii=False)
    with open(pfad, "a", encoding="utf-8") as f:
        f.write(zeile + "\n")


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


# --- Ausführung ------------------------------------------------------------

def fuehre_aus(name: str, *, ausw: "ausweis.Ausweis | None" = None,
              jetzt: datetime | None = None,
              plaene_pfad: Path | None = None,
              protokoll_pfad: Path | None = None,
              ausschalter_pfad: Path | None = None) -> dict:
    """Führt einen erklärten Auslöser aus -- nur wenn Ausweis, Erklärung und
    Ausschalter es zulassen, in dieser Reihenfolge. JEDER Aufruf schreibt
    einen Protokolleintrag, auch eine Abweisung -- sonst bliebe ein Angriff
    auf den Ausschalter selbst unsichtbar."""
    jetzt = jetzt or _jetzt()
    ausw = ausw if ausw is not None else ausweis.loese_auf()
    protokoll_pfad = protokoll_pfad or protokolldatei()
    plaene_pfad = plaene_pfad or plaenedatei()
    ausschalter_pfad = ausschalter_pfad or ausschalterdatei()

    def _abweisen(grund: str, cls: type = PermissionError):
        _protokolliere(protokoll_pfad, name=name, ergebnis=f"abgewiesen:{grund}",
                       ausw=ausw, jetzt=jetzt)
        raise cls(_MENSCHTEXT[grund])

    if not ausw.beglaubigt:
        _abweisen("kein_ausweis")

    plan = _lies_plaene(plaene_pfad).get(name)
    if plan is None:
        _abweisen("nicht_erklaert", ValueError)

    if ausgeschaltet(ausschalter_pfad):
        _abweisen("ausschalter_gesetzt")

    ausfuehren = ERLAUBTE_AKTIONEN.get(plan["aktion"])
    if ausfuehren is None:
        # Verteidigung in der Tiefe: plane() weist unbekannte Aktionstypen
        # schon beim Erklären ab, aber die Plandatei laesst sich auch von
        # Hand editieren.
        _abweisen("aktionstyp_nicht_erlaubt", ValueError)

    ergebnis = ausfuehren(name)
    _protokolliere(protokoll_pfad, name=name, ergebnis="ausgefuehrt",
                   ausw=ausw, jetzt=jetzt)
    return {"name": name, "ausgefuehrt": True, "ergebnis": ergebnis}


# --- Selbsttest --------------------------------------------------------------

def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        plaene_pfad = Path(tmp) / "plaene.json"
        protokoll_pfad = Path(tmp) / "protokoll.jsonl"
        ausschalter_pfad = Path(tmp) / "aus"
        kennzahlen_pfad = Path(tmp) / "kennzahlen.jsonl"
        # _aktion_bericht() liest kennzahlendatei() ohne Parameter (feste
        # ERLAUBTE_AKTIONEN-Signatur ausfuehren(name)) -- Umleitung nur ueber
        # die Umgebungsvariable moeglich, sonst schriebe der Selbsttest in
        # die echte runs/-Datei.
        _alter_kennzahlen_env = os.environ.get(ENV_KENNZAHLEN)
        os.environ[ENV_KENNZAHLEN] = str(kennzahlen_pfad)

        try:
            beglaubigt = ausweis.Ausweis(name="probe", rollen=("leser",), beglaubigt=True)
            unbeglaubigt = ausweis.Ausweis(name="wer", rollen=(), beglaubigt=False)

            # --- plane() fuehrt nichts aus: kein Protokolleintrag -----------
            plan = plane("t1", "taeglich 06:30", "bericht", plaene_pfad=plaene_pfad)
            assert plan["ausweis"] and plan["protokoll"] and plan["ausschalter"]
            assert not protokoll_pfad.exists()

            # --- Aktionstyp mit Aussenwirkung wird beim Erklaeren abgewiesen -
            try:
                plane("t2", "taeglich", "versand", plaene_pfad=plaene_pfad)
                raise AssertionError("Aktionstyp 'versand' haette abgewiesen werden muessen")
            except ValueError:
                pass

            # --- fehlender Ausweis verhindert die Ausfuehrung, protokolliert -
            try:
                fuehre_aus("t1", ausw=unbeglaubigt, plaene_pfad=plaene_pfad,
                          protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
                raise AssertionError("unbeglaubigt haette abgewiesen werden muessen")
            except PermissionError:
                pass
            zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
            assert len(zeilen) == 1 and "abgewiesen:kein_ausweis" in zeilen[0]

            # --- gesetzter Ausschalter verhindert die Ausfuehrung ------------
            ausschalter_pfad.touch()
            try:
                fuehre_aus("t1", ausw=beglaubigt, plaene_pfad=plaene_pfad,
                          protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
                raise AssertionError("gesetzter Ausschalter haette abgewiesen werden muessen")
            except PermissionError:
                pass
            zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
            assert len(zeilen) == 2 and "abgewiesen:ausschalter_gesetzt" in zeilen[1]
            assert not kennzahlen_pfad.exists()
            ausschalter_pfad.unlink()

            # --- unerklaerter Name wird abgewiesen ---------------------------
            try:
                fuehre_aus("unbekannt-x", ausw=beglaubigt, plaene_pfad=plaene_pfad,
                          protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
                raise AssertionError("unerklaerter Name haette abgewiesen werden muessen")
            except ValueError:
                pass

            # --- gueltiger Lauf: erlaubt, protokolliert, EINE Kennzahlzeile --
            ergebnis = fuehre_aus("t1", ausw=beglaubigt, plaene_pfad=plaene_pfad,
                                  protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
            assert ergebnis["ausgefuehrt"]
            zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
            assert len(zeilen) == 4 and "ausgefuehrt" in zeilen[-1]
            k_zeilen = kennzahlen_pfad.read_text(encoding="utf-8").splitlines()
            assert len(k_zeilen) == 1
            eintrag = json.loads(k_zeilen[0])
            assert eintrag["name"] == "t1" and "knoten_gesamt" in eintrag

            # --- zweiter gueltiger Lauf: ZWEITE Zeile, keine Ueberschreibung -
            fuehre_aus("t1", ausw=beglaubigt, plaene_pfad=plaene_pfad,
                      protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
            k_zeilen = kennzahlen_pfad.read_text(encoding="utf-8").splitlines()
            assert len(k_zeilen) == 2
        finally:
            if _alter_kennzahlen_env is None:
                os.environ.pop(ENV_KENNZAHLEN, None)
            else:
                os.environ[ENV_KENNZAHLEN] = _alter_kennzahlen_env

    print("ausloeser.py: Selbsttest gruen")


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--liste", action="store_true",
                   help="zeigt erklaerte Auslöser aus der Plandatei")
    p.add_argument("--fuehre-aus", metavar="NAME",
                   help="fuehrt einen erklaerten Auslöser aus -- fuer launchd/cron, "
                        "siehe dienst/de.brainlehr.dienst-kennzahlen.plist")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return 0
    if a.liste:
        for name, plan in _lies_plaene(plaenedatei()).items():
            print(f"{name}: takt={plan.get('takt')!r} aktion={plan.get('aktion')!r} "
                  f"erklaert_am={plan.get('erklaert_am')!r}")
        return 0
    if a.fuehre_aus:
        try:
            fuehre_aus(a.fuehre_aus)
        except (PermissionError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
