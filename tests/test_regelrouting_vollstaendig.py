"""Eine ausgelagerte Regel muss wieder erreichbar sein -- sonst ist sie weg.

DER ANLASS (Betreiberweisung 2026-08-20): "wollten wir die claude.md und wie
sie auch immer bei hermes usw heisst nicht schmal halten und dafuer routen?"

GEMESSEN vor dem Umbau: ~/.claude/CLAUDE.md hat 705 Zeilen (~17 000 Token bei
JEDEM Prompt). 272 davon (39 %) haengen an einer Dateiart und gelten nur dort
-- rund 6 200 Token, die eine reine Wissensfrage mitschleppt, ohne sie je zu
brauchen.

DIE GEFAHR DABEI, und sie ist groesser als der Gewinn: Wer eine Regel aus dem
Systemprompt nimmt und das Routing vergisst, hat sie ABGESCHAFFT, nicht
ausgelagert -- und merkt es nie, weil eine fehlende Regel sich nicht meldet.
Deshalb prueft diese Datei beide Richtungen: die Regel ist NICHT mehr im
Systemprompt UND sie kommt ueber das Routing zurueck.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HAKEN = REPO / "haken" / "regelrouting.py"
REGELN = Path.home() / ".claude" / "regeln"
CLAUDE = Path.home() / ".claude" / "CLAUDE.md"


def _route(datei: str, werkzeug: str = "Edit", sitzung: str | None = None) -> str:
    """Den Haken so aufrufen, wie Claude Code es tut.

    MIT EIGENER SITZUNGSKENNUNG, und das ist keine Feinheit: Der Haken spielt
    jede Regel pro Sitzung nur EINMAL ein (~/.brainlehr-regelrouting.json).
    Ohne eigene Kennung liefen alle Testzeilen unter "unbekannt" -- der erste
    Lauf war gruen, jeder weitere rot, und beim ersten Mal sah es aus, als
    funktioniere alles. Ein Test, dessen Ergebnis vom vorherigen Lauf abhaengt,
    misst den Zustand, nicht die Sache."""
    import uuid
    eingabe = json.dumps({"hook_event_name": "PreToolUse", "tool_name": werkzeug,
                          "session_id": sitzung or f"test-{uuid.uuid4()}",
                          "tool_input": {"file_path": datei}})
    r = subprocess.run([sys.executable, str(HAKEN)], input=eingabe,
                       capture_output=True, text=True, timeout=30)
    return r.stdout


def test_oberflaechenregeln_kommen_bei_einer_oberflaechendatei():
    raus = _route("/tmp/probe/ansicht.swift")
    assert "WCAG" in raus, "die Oberflaechenregeln werden nicht geroutet"


def test_reine_wissensfrage_bekommt_nichts():
    """DER PUNKT DES GANZEN: Wer nur etwas wissen will, faesst keine Datei an
    -- PreToolUse greift nicht, und die themengebundenen Regeln bleiben weg.
    Genau die Frage des Betreibers: 'wenn nur jemand echte wissenfragen hat
    braucht er auch kein bsi'."""
    raus = _route("/tmp/probe/notiz.txt")
    assert "WCAG" not in raus


def test_jede_ausgelagerte_datei_ist_im_haken_verdrahtet():
    """Eine Regeldatei ohne Eintrag im Routing ist eine abgeschaffte Regel.
    Dieselbe Klasse wie 'ein Melder ohne Ausloeser zaehlt als keiner'."""
    quelle = HAKEN.read_text(encoding="utf-8")
    for datei in sorted(REGELN.glob("*.md")):
        assert datei.stem in quelle, (
            f"{datei.name} liegt ausgelagert da, wird aber von keinem "
            f"Ausloeser eingespielt -- die Regel ist damit weg, nicht geroutet")


def test_ausgelagertes_hinterlaesst_eine_spur_in_claude_md():
    """NEGATIVFALL gegen das spurlose Verschwinden: Wer die Regel nicht mehr
    im Systemprompt sieht, muss wenigstens WISSEN, dass es sie gibt. Sonst
    kann niemand sie nachschlagen, aendern oder abschaffen -- und sie wirkt
    nur noch als Ueberraschung, wenn ein Waechter sie vorhaelt."""
    text = CLAUDE.read_text(encoding="utf-8")
    for datei in sorted(REGELN.glob("*.md")):
        assert datei.name in text or datei.stem in text.lower(), (
            f"{datei.name} ist aus CLAUDE.md verschwunden, ohne einen "
            f"Verweis zu hinterlassen")


def test_agentenregeln_kommen_beim_agentenaufruf():
    """Regeln fuer Agentenauftraege haengen an einem WERKZEUG, nicht an einer
    Dateiart -- ein Agentenaufruf hat keinen Dateipfad. Ein reiner
    Endungsvergleich haette diese Gruppe nie eingespielt, und sie waere beim
    Auslagern still verschwunden."""
    raus = _route("", werkzeug="Agent")
    assert "Agentenauftrag" in raus or "Schnappschuss" in raus or "Schnappsch" in raus


def test_codebauregeln_kommen_bei_einer_codedatei():
    raus = _route("/tmp/probe/modul.py")
    assert "BSI" in raus or "Walkthrough" in raus


def test_zweiter_aufruf_derselben_sitzung_wiederholt_nicht():
    """Gegenprobe zum Zustand: Dieselbe Regel kommt pro Sitzung genau einmal.
    Sonst stuende sie bei jedem Werkzeugaufruf erneut im Kontext -- und das
    Routing haette den Systemprompt nicht verkleinert, sondern vervielfacht."""
    sitzung = "test-wiederholung-fest"
    erst = _route("/tmp/a.swift", sitzung=sitzung)
    zweit = _route("/tmp/b.swift", sitzung=sitzung)
    assert "WCAG" in erst and "WCAG" not in zweit
