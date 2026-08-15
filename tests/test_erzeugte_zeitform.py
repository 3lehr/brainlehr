"""Ratsche fuer die ERZEUGER, nicht den Bestand -- Nachtrag zu Aufgabe 111.

tests/test_zeitform_utc.py prueft die Datenbank und wurde Minuten nach
Commit ac4e1a0 (Schritt 3, 37873 umgerechnete Werte) wieder ROT: acht
Fundstellen in sieben Dateien bauten ihren Zeitstempel weiterhin selbst
(`datetime.now(timezone.utc).isoformat()` -- UTC mit Mikrosekunden und
'+00:00' statt 'Z'), obwohl Schritt 2 (docs/PLAN_UTC_2026-08-14.md) 46
andere Erzeuger schon auf kern/zeitmarke.jetzt() umgestellt hatte. Ein Test,
der nur den Bestand liest, waere nach einem Aufraeumen auch OHNE Reparatur
gruen -- das ist der Grund, warum diese Datei die ERZEUGER direkt aufruft.

ROT VOR GRUEN (2026-08-14, vor dieser Reparatur), einzeln belegt:
    kern/ankerverfahren.py:439                  _jetzt_iso()
    kern/kanten_aus_lehren.py:152                create_edges()
    kern/kanten_aus_bedeutung.py:326             schreibe_kanten()
    kern/kanten_herkunft_rueckwirkend.py:227      _knoten() (schreibe() an
                                                   Zeile 145 nutzte schon
                                                   strftime -- dieselbe
                                                   Datei widersprach sich)
    kern/meisterschaft.py:93                      _now()
    melder/foederation.py:143 und 217             _erzeuge() und vertraue()

NICHT HIER GEPRUEFT, weil kein Leser dafuer im Bestand nachweisbar ist
(siehe Bericht): haken/antwort_abruf.py:360 (_eskalieren, schreibt "ts" in
eilmeldung_eskalation.jsonl -- der einzige bekannte Leser eilmeldung_hook.py
existiert in diesem Repo nicht, ein Formwechsel bliebe unverifiziert).
"""
from __future__ import annotations

import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import zeitmarke  # noqa: E402


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()


def test_negativfall_alte_form_wird_abgelehnt():
    """Gegenprobe zur Pruefung selbst: eine Zeitangabe in der alten Form
    (Mikrosekunden + '+00:00') muss durchfallen -- sonst misst der Test
    nichts, egal was die Erzeuger liefern."""
    from datetime import datetime, timezone
    alt = datetime.now(timezone.utc).isoformat()  # z.B. '...901235+00:00'
    assert not zeitmarke.UTC_MUSTER.match(alt), (
        f"die Pruefung selbst ist stumpf -- {alt!r} muesste abgelehnt werden")


def test_ankerverfahren_jetzt_iso():
    import ankerverfahren
    wert = ankerverfahren._jetzt_iso()
    assert zeitmarke.UTC_MUSTER.match(wert), wert


def test_meisterschaft_now():
    import meisterschaft
    wert = meisterschaft._now()
    assert zeitmarke.UTC_MUSTER.match(wert), wert


def test_kanten_aus_lehren_create_edges():
    import kanten_aus_lehren as m
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE knowledge_relations (
        id TEXT, source_path TEXT, target_path TEXT, relation_type TEXT,
        confidence REAL, weight REAL, evidence TEXT, source TEXT,
        creator TEXT, model TEXT, session TEXT, created_at TEXT, updated_at TEXT)""")
    ref = m.FileReference(path="kern/zeitmarke.py", exists=True,
                           lesson_id="L-000001", field="description")
    created, skipped = m.create_edges(conn, [ref])
    assert created == 1, (created, skipped)
    wert = conn.execute(
        "SELECT created_at FROM knowledge_relations LIMIT 1").fetchone()[0]
    assert zeitmarke.UTC_MUSTER.match(wert), wert


def test_kanten_aus_bedeutung_schreibe_kanten():
    import kanten_aus_bedeutung as m
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE knowledge_relations (
        id TEXT, source_path TEXT, target_path TEXT, relation_type TEXT,
        confidence REAL, weight REAL, evidence TEXT, source TEXT,
        creator TEXT, model TEXT, session TEXT, created_at TEXT, updated_at TEXT,
        hinsicht TEXT)""")
    kd = m.Kandidat(a_path="knoten/a", a_title="A", b_path="knoten/b",
                     b_title="B", similarity=0.9)
    created, skipped = m.schreibe_kanten(conn, [kd])
    assert created == 1, (created, skipped)
    wert = conn.execute(
        "SELECT created_at FROM knowledge_relations LIMIT 1").fetchone()[0]
    assert zeitmarke.UTC_MUSTER.match(wert), wert


def test_kanten_herkunft_rueckwirkend_knoten_und_schreibe():
    import kanten_herkunft_rueckwirkend as m
    conn = sqlite3.connect(":memory:")
    _schema(conn)
    m._knoten(conn, "aaaaaaaa", "pfad/a", "Titel A")
    wert = conn.execute(
        "SELECT created_at FROM knowledge_nodes WHERE id='aaaaaaaa'").fetchone()[0]
    assert zeitmarke.UTC_MUSTER.match(wert), wert

    m._knoten(conn, "bbbbbbbb", "pfad/b", "Titel B")
    kandidat = m.Kandidat(source_path="pfad/a", target="pfad/b",
                           ziel_art="knoten", roh="bbbbbbbb")
    neu = m.schreibe(conn, [kandidat])
    assert neu == 1
    wert2 = conn.execute(
        "SELECT created_at FROM knowledge_relations WHERE source_path='pfad/a'"
    ).fetchone()[0]
    assert zeitmarke.UTC_MUSTER.match(wert2), wert2


def test_foederation_erzeuge_und_vertraue(tmp_path, monkeypatch):
    import foederation as m
    pfad = tmp_path / "brainlehr.db"
    conn = sqlite3.connect(str(pfad))
    conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()

    kennung, _name = m._erzeuge(pfad, grund="testaufbau")
    assert kennung
    conn = sqlite3.connect(str(pfad))
    wert = conn.execute(
        "SELECT updated_at FROM knowledge_config WHERE key=?",
        (m.SCHLUESSEL_KENNUNG,)).fetchone()[0]
    conn.close()
    assert zeitmarke.UTC_MUSTER.match(wert), wert

    vertrauensdatei = tmp_path / "vertrauen.json"
    m.vertraue("deadbeef", name="testinstanz", hoechstens="leser",
               pfad=vertrauensdatei, eigene="")
    eintraege = m._lies_vertrauen(vertrauensdatei)
    assert eintraege and zeitmarke.UTC_MUSTER.match(eintraege[0]["seit"]), eintraege
