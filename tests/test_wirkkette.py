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


def test_stufe2_faehigkeit_konstruierter_blindgaenger():
    """Faehigkeitstest statt Ankerung an einem realen Fall (Ersatz fuer die
    vormalige Positivkontrolle gegen haken/mcp_veraltet.py -- die brach genau
    dann, als der reale Blindgaenger in Commit d6ab2505 erfolgreich
    zusaetzlich an SubagentStart verdrahtet wurde: der Erfolgsfall, nicht der
    Fehlerfall dieses Tests). ereignisse_von() nimmt pfad/quellen/event_map
    als reine Parameter entgegen -- ein konstruierter Eingabestand genuegt,
    kein Griff ins Dateisystem, kein Bruch bei der naechsten Reparatur eines
    echten Mechanismus."""
    kandidat = Path("/nicht/vorhanden/blindgaenger.py")
    event_map = {"UserPromptSubmit": kandidat.name}
    events = wirkkette.ereignisse_von(kandidat, {}, event_map)
    assert wirkkette.blind_im_selbstlauf(events)


def test_stufe2_faehigkeit_zusaetzliches_ereignis_rettet():
    """Gegenprobe: haengt derselbe konstruierte Kandidat zusaetzlich an einem
    Ereignis, das auch im Selbstlauf feuert, gilt er nicht mehr als blind."""
    kandidat = Path("/nicht/vorhanden/blindgaenger.py")
    event_map = {"UserPromptSubmit": kandidat.name, "PreToolUse": kandidat.name}
    events = wirkkette.ereignisse_von(kandidat, {}, event_map)
    assert not wirkkette.blind_im_selbstlauf(events)


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


def test_selbstlauf_vermerkt_gegenprobe_beide_richtungen(tmp_path):
    """Widerspruch aufgeloest (2026-08-15): tests/test_haken_verdrahtung.py
    liess einen begruendeten SELBSTLAUF-VERMERK schon als Entlastung gelten,
    melder/wirkkette.py meldete die drei betroffenen Dateien (u.a.
    haken/knowledge_recall_hook.py) trotzdem weiter als Stufe-2-Blindfleck.
    Gegenprobe in beide Richtungen, wie von der Aufgabe verlangt: ein
    tragfaehig begruendeter Vermerk rettet (a), ein leerer/fehlender Vermerk
    faellt weiterhin durch (b)+(c)."""
    lang = "SELBSTLAUF-VERMERK: " + ("Begruendung " * 10)  # deutlich ueber Mindestlaenge
    (tmp_path / "mit_begruendung.py").write_text(f'"""{lang}"""\n')
    (tmp_path / "nur_stichwort.py").write_text('"""SELBSTLAUF-VERMERK"""\n')
    (tmp_path / "ohne_vermerk.py").write_text('"""tut etwas."""\n')

    assert wirkkette.selbstlauf_vermerkt(tmp_path / "mit_begruendung.py") is True
    assert wirkkette.selbstlauf_vermerkt(tmp_path / "nur_stichwort.py") is False, (
        "das nackte Stichwort ohne Begruendung ist ein Freibrief -- muss "
        "weiterhin als unbelegt gelten")
    assert wirkkette.selbstlauf_vermerkt(tmp_path / "ohne_vermerk.py") is False


def test_stufe2_vermerkt_wechselt_rubrik_statt_zu_verschwinden(tmp_path):
    """Ein begruendeter Vermerk darf den Fund nicht aus dem Bericht tilgen
    (das waere ein Abschaltknopf, L-ed0b73) -- er wechselt nur die Rubrik.
    Direkt gegen bericht() geprueft, synthetischer Root wie in _selftest()."""
    import json

    root = tmp_path
    (root / "schema.sql").write_text("--\n")
    for ordner in ("melder", "haken", "berichte"):
        (root / ordner).mkdir()

    (root / "haken" / "begruendet.py").write_text(
        '"""tut etwas.\n\nSELBSTLAUF-VERMERK: ' + ("Begruendung " * 10) + '"""\n'
        "print(\"x\")\n"
    )
    settings_pfad = root / "settings.json"
    settings_pfad.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
        {"type": "command", "command": "python3 haken/begruendet.py"}]}]}}))

    funde = wirkkette.bericht(root, [settings_pfad, None])
    assert "haken/begruendet.py" not in {f["name"] for f in funde["stufe2"]}
    assert "haken/begruendet.py" in {f["name"] for f in funde["stufe2_vermerkt"]}

    text = wirkkette.render(funde)
    assert "bewusst nur fuer Menschen" in text
    assert "haken/begruendet.py" in text


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
