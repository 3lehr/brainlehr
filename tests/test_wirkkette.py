"""J2 -- Haken- und Prozessabgleich (melder/wirkkette.py).

Wiederholt die Positivkontrolle und die beiden Negativfaelle des eigenen
--selftest per pytest, damit die Suite sie ohne Subprozess-Umweg mitfaehrt.
Der ausfuehrliche Beleg (Grenzwerte, alle sechs Fixtures, die Sanity-Probe
gegen Mehrheitsfunde) steht in melder/wirkkette.py::_selftest und wird von
tests/test_alle_selftests.py separat aufgerufen -- diese Datei doppelt das
NICHT, sondern prueft die drei fuer J2 zentralen Aussagen direkt gegen den
importierten Code, ohne Subprozess-Kosten."""
from __future__ import annotations

import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "melder"), str(_w / "haken")]

import wirkkette  # noqa: E402


def test_positivkontrolle_vektorstand_vor_reparatur(tmp_path):
    """Nachbau des Zustands von melder/vektorstand.py VOR Commit 591149ef
    (git show 591149ef^:melder/vektorstand.py): kein settings.json-Eintrag,
    kein Import durch einen Pruefer -- Kopie in einem tmp-Baum, kein Eingriff
    in die echte Datei. Muss als Stufe-1-Fund auftauchen."""
    root = tmp_path
    (root / "schema.sql").write_text("--\n")
    for ordner in ("melder", "haken", "berichte"):
        (root / ordner).mkdir()
    (root / "melder" / "vektorstand_vor_reparatur.py").write_text(
        '"""Nachbau vor Reparatur -- kein Ereignis, kein Import."""\n'
        "def melden(conn=None):\n    return None\n"
    )
    settings_pfad = root / "settings.json"
    settings_pfad.write_text('{"hooks": {}}')

    funde = wirkkette.bericht(root, [settings_pfad, None])
    namen_s1 = {f["name"] for f in funde["stufe1"]}
    assert "melder/vektorstand_vor_reparatur.py" in namen_s1


def test_negativfall_sauber_verdrahteter_mechanismus_bleibt_unerwaehnt(tmp_path):
    """Ein Mechanismus an PreToolUse (feuert auch im Subagenten) mit einer
    ganz gewoehnlichen print-Meldung darf auf KEINER der drei Stufen
    auftauchen."""
    import json

    root = tmp_path
    (root / "schema.sql").write_text("--\n")
    for ordner in ("melder", "haken", "berichte"):
        (root / ordner).mkdir()
    (root / "melder" / "sauber.py").write_text('"""tut etwas, meldet alles."""\nprint("ok")\n')
    settings_pfad = root / "settings.json"
    settings_pfad.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [
        {"type": "command", "command": "python3 melder/sauber.py"}]}]}}))

    funde = wirkkette.bericht(root, [settings_pfad, None])
    assert "melder/sauber.py" not in {f["name"] for f in funde["stufe1"]}
    assert "melder/sauber.py" not in {f["name"] for f in funde["stufe2"]}
    assert "melder/sauber.py" not in {f["name"] for f in funde["stufe3"]}


def test_stufe2_reales_beispiel_haken_mcp_veraltet():
    """haken/mcp_veraltet.py haengt seit L-b3eb79 ausschliesslich an
    UserPromptSubmit -- der belegte Blindgaenger-Fall dieser Aufgabe. Nur
    LESEND geprueft (haken/ ist fuer diesen Auftrag tabu). Existiert die
    Datei nicht oder ist ~/.claude/settings.json nicht vorhanden (fremde
    Maschine), wird der Test uebersprungen statt falsch rot zu laufen."""
    import pytest

    einstellungen = Path.home() / ".claude" / "settings.json"
    ziel = wirkkette.ort.WURZEL / "haken" / "mcp_veraltet.py"
    if not einstellungen.exists() or not ziel.exists():
        pytest.skip("fremde Maschine ohne Klient-Einstellungen oder Datei fehlt")

    quellen = wirkkette.ausloeserlos.alle_quellen(wirkkette.ort.WURZEL)
    event_map = wirkkette._event_map(wirkkette._settings_pfade())
    events = wirkkette.ereignisse_von(ziel, quellen, event_map)
    assert wirkkette.blind_im_selbstlauf(events), (
        f"erwartet: nur UserPromptSubmit, gemessen: {events} -- entweder "
        "inzwischen zusaetzlich verdrahtet (Befund, kein Testfehler) oder "
        "die Einstufung ist kaputt")


def test_stufe3_spezifischer_fehlertyp_mit_pass_wird_gefunden(tmp_path):
    """Direkter Aufruf von meldung_verschluckt() gegen eine synthetische
    Datei -- die Positivkontrolle fuer Stufe 3 (kein realer Fall im
    heutigen Bestand von melder/haken/berichte, siehe Modulkopf)."""
    datei = tmp_path / "verschluckt.py"
    datei.write_text(
        '"""tut etwas."""\n'
        "import sqlite3\n"
        "def schreiben(conn):\n"
        "    try:\n"
        "        conn.execute('INSERT INTO t VALUES (1)')\n"
        "    except sqlite3.IntegrityError:\n"
        "        pass\n"
    )
    assert wirkkette.meldung_verschluckt(datei)


def test_stufe3_testidiom_erwarteter_wurf_wird_nicht_gemeldet(tmp_path):
    """Gegenprobe zur Verschaerfung vom 2026-08-15: 'assert False, ...' im
    try-Rumpf ist ein Testidiom (erwarteter Wurf), kein verschluckter
    Befund -- ohne diese Ausnahme waeren alle 6 Rohtreffer am echten Bestand
    genau dieses Muster gewesen."""
    datei = tmp_path / "testidiom.py"
    datei.write_text(
        '"""selftest-artiger Code."""\n'
        "def demo():\n"
        "    try:\n"
        "        pruefe(None)\n"
        "        assert False, 'muss werfen'\n"
        "    except ValueError:\n"
        "        pass\n"
    )
    assert wirkkette.meldung_verschluckt(datei) == []
