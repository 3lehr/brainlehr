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

ENV_AUSSCHALTER = "BRAINLEHR_AUSLOESER_AUS"
ENV_PROTOKOLL = "BRAINLEHR_AUSLOESER_PROTOKOLL"
ENV_PLAENE = "BRAINLEHR_AUSLOESER_PLAENE"

_DATEINAME_AUSSCHALTER = "ausloeser-aus"
_DATEINAME_PROTOKOLL = "ausloeser-protokoll.jsonl"
_DATEINAME_PLAENE = "ausloeser-plaene.json"


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


def ausgeschaltet(pfad: Path | None = None) -> bool:
    return (pfad or ausschalterdatei()).exists()


# --- Aktionstypen ------------------------------------------------------------
# Vorgabe DENY, wie bei werkzeugrechte.RECHTE: ein Aktionstyp ohne Eintrag
# hier ist gesperrt, nicht frei. Jede Funktion bekommt nur den Namen -- keine
# Aktion braucht mehr, solange 'lesend und lokal' die Grenze ist.

def _aktion_bericht(name: str) -> dict:
    """Der einzige heute zugelassene Aktionstyp: liest nichts Fremdes, schreibt
    nichts außer der eigenen Rückgabe, hat keine Außenwirkung."""
    return {"typ": "bericht", "name": name,
            "hinweis": "Platzhalter -- erzeugt keinen Bericht, nur den Beleg, "
                       "dass ein lesender lokaler Aktionstyp ausgeführt wurde."}


ERLAUBTE_AKTIONEN = {"bericht": _aktion_bericht}


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

        beglaubigt = ausweis.Ausweis(name="probe", rollen=("leser",), beglaubigt=True)
        unbeglaubigt = ausweis.Ausweis(name="wer", rollen=(), beglaubigt=False)

        # --- plane() fuehrt nichts aus: kein Protokolleintrag ---------------
        plan = plane("t1", "taeglich 06:30", "bericht", plaene_pfad=plaene_pfad)
        assert plan["ausweis"] and plan["protokoll"] and plan["ausschalter"]
        assert not protokoll_pfad.exists()

        # --- Aktionstyp mit Aussenwirkung wird beim Erklaeren abgewiesen ----
        try:
            plane("t2", "taeglich", "versand", plaene_pfad=plaene_pfad)
            raise AssertionError("Aktionstyp 'versand' haette abgewiesen werden muessen")
        except ValueError:
            pass

        # --- fehlender Ausweis verhindert die Ausfuehrung, protokolliert ----
        try:
            fuehre_aus("t1", ausw=unbeglaubigt, plaene_pfad=plaene_pfad,
                      protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
            raise AssertionError("unbeglaubigt haette abgewiesen werden muessen")
        except PermissionError:
            pass
        zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
        assert len(zeilen) == 1 and "abgewiesen:kein_ausweis" in zeilen[0]

        # --- gesetzter Ausschalter verhindert die Ausfuehrung ---------------
        ausschalter_pfad.touch()
        try:
            fuehre_aus("t1", ausw=beglaubigt, plaene_pfad=plaene_pfad,
                      protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
            raise AssertionError("gesetzter Ausschalter haette abgewiesen werden muessen")
        except PermissionError:
            pass
        zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
        assert len(zeilen) == 2 and "abgewiesen:ausschalter_gesetzt" in zeilen[1]
        ausschalter_pfad.unlink()

        # --- unerklaerter Name wird abgewiesen -------------------------------
        try:
            fuehre_aus("unbekannt-x", ausw=beglaubigt, plaene_pfad=plaene_pfad,
                      protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
            raise AssertionError("unerklaerter Name haette abgewiesen werden muessen")
        except ValueError:
            pass

        # --- gueltiger Lauf: erlaubt, protokolliert --------------------------
        ergebnis = fuehre_aus("t1", ausw=beglaubigt, plaene_pfad=plaene_pfad,
                              protokoll_pfad=protokoll_pfad, ausschalter_pfad=ausschalter_pfad)
        assert ergebnis["ausgefuehrt"]
        zeilen = protokoll_pfad.read_text(encoding="utf-8").splitlines()
        assert len(zeilen) == 4 and "ausgefuehrt" in zeilen[-1]

    print("ausloeser.py: Selbsttest gruen")


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--liste", action="store_true",
                   help="zeigt erklaerte Auslöser aus der Plandatei")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return 0
    if a.liste:
        for name, plan in _lies_plaene(plaenedatei()).items():
            print(f"{name}: takt={plan.get('takt')!r} aktion={plan.get('aktion')!r} "
                  f"erklaert_am={plan.get('erklaert_am')!r}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
