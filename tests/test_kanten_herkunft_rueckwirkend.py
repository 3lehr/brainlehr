"""Tests fuer kern/kanten_herkunft_rueckwirkend.py -- Herkunftskanten aus
woertlichen Verweisen im Knotentext (Auftrag 73 Schritt 1).

Rot-vor-Gruen: vor der Implementierung schlagen alle Tests hier beim Import
fehl (ModuleNotFoundError), danach bestehen sie. Die Vorrichtung ist eine
temporaere Datei (tmp_path) -- nie die echte Datenbank, sonst schlaegt
tests/test_naht_ratsche.py an.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
from datetime import datetime, timezone

import pytest

import kanten_herkunft_rueckwirkend as khr  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    pfad = tmp_path / "herkunft_test.db"
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(pfad))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return pfad


def _knoten(conn, id_, path, title, summary="", content=None):
    jetzt = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, source,
            anlass, norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
            norm_entschieden_grund, created_at, updated_at)
           VALUES (?, ?, NULL, 'shared', ?, ?, ?, 'test', 'skript',
                   'keine_norm', 'test', ?, 'Testvorrichtung, keine echte Norm-Pruefung',
                   ?, ?)""",
        (id_, path, title, summary, content, jetzt, jetzt, jetzt))


def _lehre(conn, id_, description):
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description) VALUES (?, 'insight', ?)",
        (id_, description))


def test_positivfall_lehre_und_knoten(db):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    _lehre(conn, "L-abc123", "Testlehre")
    _knoten(conn, "aaaaaaaa", "/test/vorgaenger", "Vorgaenger", "Ausgangsknoten")
    _knoten(conn, "bbbbbbbb", "/test/nachfolger", "Nachfolger",
            "Baut auf L-abc123 und Knoten aaaaaaaa auf")
    conn.commit()

    kandidaten, erfunden = khr.sammle(conn)
    ziele = {(k.target, k.ziel_art) for k in kandidaten if k.source_path == "/test/nachfolger"}
    assert ziele == {("L-abc123", "lehre"), ("/test/vorgaenger", "knoten")}
    assert erfunden == []
    conn.close()


def test_negativfall_ohne_verweis_keine_kante(db):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    _knoten(conn, "dddddddd", "/test/ohne_verweis", "Ohne Verweis",
            "Ganz normaler Text ohne jede Kennung")
    conn.commit()

    kandidaten, erfunden = khr.sammle(conn)
    assert kandidaten == [], "ein Verfahren, das ueberall etwas findet, findet nichts"
    assert erfunden == []
    conn.close()


def test_grenzwert_erfundene_lehre_wird_gemeldet_nicht_verschluckt(db):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    _knoten(conn, "eeeeeeee", "/test/erfunden", "Erfunden",
            "Beruft sich auf L-ffffff, die es im Bestand nicht gibt")
    conn.commit()

    kandidaten, erfunden = khr.sammle(conn)
    assert kandidaten == [], "eine erfundene Lehre darf keine Kante erzeugen"
    assert len(erfunden) == 1
    assert erfunden[0]["kennung"] == "L-ffffff"
    assert erfunden[0]["knoten_path"] == "/test/erfunden"
    conn.close()


def test_selbstbezug_erzeugt_keine_kante_auf_sich_selbst(db):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    _knoten(conn, "cccccccc", "/test/selbstbezug", "Selbstbezug",
            "Verweist versehentlich auf die eigene Kennung cccccccc")
    conn.commit()

    kandidaten, erfunden = khr.sammle(conn)
    assert kandidaten == [], "ein Knoten darf keine Kante auf sich selbst erzeugen"
    conn.close()


def test_schreiben_ist_idempotent(db):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    _lehre(conn, "L-abc123", "Testlehre")
    _knoten(conn, "aaaaaaaa", "/test/vorgaenger", "Vorgaenger", "Ausgangsknoten")
    _knoten(conn, "bbbbbbbb", "/test/nachfolger", "Nachfolger",
            "Baut auf L-abc123 und Knoten aaaaaaaa auf")
    conn.commit()

    kandidaten, _ = khr.sammle(conn)
    vorher = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = 'abgeleitet_von'"
    ).fetchone()[0]
    assert vorher == 0

    neu = khr.schreibe(conn, kandidaten)
    assert neu == 2
    nachher = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = 'abgeleitet_von'"
    ).fetchone()[0]
    assert nachher == 2

    # zweiter Lauf: UNIQUE(source,target,typ) haelt die Zahl fest
    neu2 = khr.schreibe(conn, kandidaten)
    assert neu2 == 0
    nachher2 = conn.execute(
        "SELECT COUNT(*) FROM knowledge_relations WHERE relation_type = 'abgeleitet_von'"
    ).fetchone()[0]
    assert nachher2 == 2
    conn.close()


def test_modul_selbsttest_gruen():
    khr._selftest()
