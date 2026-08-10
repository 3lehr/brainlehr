"""Vollstaendigkeits-Test fuer lessons_ai/lessons_ad/lessons_au (schema.sql,
Auftrag 2026-08-07). Lehre L-636a44: ein Trigger-Satz, der nach einem
Neustart nur zur Haelfte stand, blieb unbemerkt, weil kein Test JEDEN
Trigger und JEDEN Zweig einzeln gegen JEDE indizierte Spalte pruefte. Hier
deshalb: Anlegen, Aendern (je Spalte einzeln), Loeschen -- je ein Test, der
bei einem halben Trigger-Satz rot wird. "Pfadwechsel" hat bei Lehren keine
Entsprechung (kein path-Feld) -- stattdessen wird jede der drei indizierten
Spalten (description, root_cause, prevention) einzeln per UPDATE geaendert,
das ist die naheliegende Analogie zum Pfadwechsel-Test bei Knoten
(test_fts_pfad_tags.py::test_path_change_updates_index): ein Trigger, der
nur EINE Spalte im DELETE/INSERT-Zweig mitfuehrt, waere sonst unentdeckt.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))


def _fresh_db(tmp_path) -> sqlite3.Connection:
    db_path = tmp_path / "lessons_fts_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    return conn


def _insert_lesson(conn, lesson_id, description="d", root_cause="r", prevention="p"):
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, root_cause, prevention, "
        "status, first_seen, last_seen) VALUES (?, 'insight', ?, ?, ?, 'active', "
        "datetime('now'), datetime('now'))",
        (lesson_id, description, root_cause, prevention),
    )


def _hits(conn, word: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM lessons_fts WHERE lessons_fts MATCH ?", (word,)
    ).fetchone()[0]


# --- lessons_ai (INSERT) -- alle drei Spalten einzeln auffindbar ------------

def test_insert_indexes_description(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t1", description="beschreibungswortxyz")
    conn.commit()
    assert _hits(conn, "beschreibungswortxyz") == 1


def test_insert_indexes_root_cause(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t2", root_cause="ursachewortxyz")
    conn.commit()
    assert _hits(conn, "ursachewortxyz") == 1


def test_insert_indexes_prevention(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t3", prevention="vorbeugungswortxyz")
    conn.commit()
    assert _hits(conn, "vorbeugungswortxyz") == 1


# --- lessons_ad (DELETE) -----------------------------------------------------

def test_delete_removes_all_three_columns(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t4", description="loeschbeschreibungxyz",
                    root_cause="loeschursachexyz", prevention="loeschvorbeugungxyz")
    conn.commit()
    assert _hits(conn, "loeschbeschreibungxyz") == 1
    assert _hits(conn, "loeschursachexyz") == 1
    assert _hits(conn, "loeschvorbeugungxyz") == 1
    conn.execute("DELETE FROM lessons_learned WHERE id = 'L-t4'")
    conn.commit()
    assert _hits(conn, "loeschbeschreibungxyz") == 0
    assert _hits(conn, "loeschursachexyz") == 0
    assert _hits(conn, "loeschvorbeugungxyz") == 0


# --- lessons_au (UPDATE, zwei Zweige: alten Eintrag loeschen + neuen einfuegen) --
# Je Spalte einzeln, sonst bleibt ein Trigger, der nur EINE Spalte im
# DELETE-Zweig mitfuehrt, unentdeckt (exakt der Fehler bei Knoten, den
# test_fts_pfad_tags.py::test_path_change_updates_index bereits einmal fand).

def test_update_description_swaps_index_entry(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t5", description="altebeschreibungxyz")
    conn.commit()
    assert _hits(conn, "altebeschreibungxyz") == 1
    conn.execute("UPDATE lessons_learned SET description = 'neuebeschreibungxyz' WHERE id = 'L-t5'")
    conn.commit()
    assert _hits(conn, "altebeschreibungxyz") == 0
    assert _hits(conn, "neuebeschreibungxyz") == 1


def test_update_root_cause_swaps_index_entry(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t6", root_cause="alteursachexyz")
    conn.commit()
    assert _hits(conn, "alteursachexyz") == 1
    conn.execute("UPDATE lessons_learned SET root_cause = 'neueursachexyz' WHERE id = 'L-t6'")
    conn.commit()
    assert _hits(conn, "alteursachexyz") == 0
    assert _hits(conn, "neueursachexyz") == 1


def test_update_prevention_swaps_index_entry(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t7", prevention="altevorbeugungxyz")
    conn.commit()
    assert _hits(conn, "altevorbeugungxyz") == 1
    conn.execute("UPDATE lessons_learned SET prevention = 'neuevorbeugungxyz' WHERE id = 'L-t7'")
    conn.commit()
    assert _hits(conn, "altevorbeugungxyz") == 0
    assert _hits(conn, "neuevorbeugungxyz") == 1


def test_update_touching_all_three_columns_at_once(tmp_path):
    """Regressionsfall fuer den unvollstaendigen Trigger-Satz (L-636a44):
    ein UPDATE, das alle drei Spalten gleichzeitig aendert, darf keine davon
    zuruecklassen."""
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t8", description="dbeschraltxyz", root_cause="rursachaltxyz", prevention="pvorbaltxyz")
    conn.commit()
    conn.execute(
        "UPDATE lessons_learned SET description = 'dbeschrneuxyz', root_cause = 'rursachneuxyz', "
        "prevention = 'pvorbneuxyz' WHERE id = 'L-t8'"
    )
    conn.commit()
    for alt in ("dbeschraltxyz", "rursachaltxyz", "pvorbaltxyz"):
        assert _hits(conn, alt) == 0, f"{alt} haette aus dem Index verschwinden muessen"
    for neu in ("dbeschrneuxyz", "rursachneuxyz", "pvorbneuxyz"):
        assert _hits(conn, neu) == 1, f"{neu} haette im Index stehen muessen"


# --- Umlaut-Faltung (Auftrag Abnahme d) --------------------------------------

def test_umlaut_folding_matches_without_umlaut(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_lesson(conn, "L-t9", description="Existenzgründer-Broschüre für Käufer")
    conn.commit()
    assert _hits(conn, "existenzgruender") == 1
    assert _hits(conn, "broschuere") == 1
    assert _hits(conn, "kaeufer") == 1
