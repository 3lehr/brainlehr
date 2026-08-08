"""Tests fuer das anlass-Feld (Auftrag 2026-08-06): was hat einen Eintrag
ausgeloest -- selbst/betreiber (selbstberichtet) vs. hook/skript (objektiv)
vs. unbekannt (Vorgabe, Altbestand). Rot-vor-gruen: vor diesem Auftrag hatte
weder knowledge_nodes noch lessons_learned diese Spalte, jeder Aufruf mit
anlass= schlug mit TypeError fehl und schema.sql kannte die Spalte nicht.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _source():
    return "erzeugt aus /pfad/datei.md (Stand 2026-08-06T12:00:00+02:00)"


# --- knowledge_add ----------------------------------------------------

def test_knowledge_add_vorgabe_ist_unbekannt(temp_db):
    res = kms.knowledge_add("/", "Ohne Anlass", "Zusammenfassung", source=_source())
    assert res.get("status") == "created", res
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT anlass FROM knowledge_nodes WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("unbekannt",), row


def test_knowledge_add_gueltiger_anlass_wird_gesetzt(temp_db):
    res = kms.knowledge_add("/", "Mit Anlass", "Zusammenfassung", source=_source(), anlass="betreiber")
    assert res.get("status") == "created", res
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT anlass FROM knowledge_nodes WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("betreiber",), row


def test_knowledge_add_unbekannter_anlass_wird_abgelehnt(temp_db):
    res = kms.knowledge_add("/", "Quatsch-Anlass", "Zusammenfassung", source=_source(), anlass="quatsch")
    assert "error" in res, res
    for wert in kms.ALLOWED_ANLASS:
        assert wert in res["error"], res["error"]
    conn = sqlite3.connect(str(temp_db))
    assert conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE title = 'Quatsch-Anlass'"
    ).fetchone()[0] == 0, "Knoten wurde trotz unbekanntem anlass geschrieben"
    conn.close()


# --- lesson_record ------------------------------------------------------

def test_lesson_record_vorgabe_ist_unbekannt(temp_db):
    res = kms.lesson_record("insight", "Ein Test-Fund ohne anlass")
    assert res.get("status") == "recorded", res
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT anlass FROM lessons_learned WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("unbekannt",), row


def test_lesson_record_gueltiger_anlass_wird_gesetzt(temp_db):
    res = kms.lesson_record("insight", "Ein Test-Fund mit anlass", anlass="skript")
    assert res.get("status") == "recorded", res
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT anlass FROM lessons_learned WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("skript",), row


def test_lesson_record_unbekannter_anlass_wird_abgelehnt(temp_db):
    res = kms.lesson_record("insight", "Quatsch-Anlass-Fund", anlass="quatsch")
    assert res.get("status") == "rejected", res
    for wert in kms.ALLOWED_ANLASS:
        assert wert in res["error"], res["error"]
    conn = sqlite3.connect(str(temp_db))
    assert conn.execute(
        "SELECT COUNT(*) FROM lessons_learned WHERE description = 'Quatsch-Anlass-Fund'"
    ).fetchone()[0] == 0, "Lesson wurde trotz unbekanntem anlass geschrieben"
    conn.close()


def test_lesson_record_bump_laesst_anlass_der_bestehenden_zeile_unveraendert(temp_db):
    """Negativfall auf der anderen Seite: same_as/Dublette darf den anlass
    der ERSTEN Zeile nicht ueberschreiben, egal was der zweite Aufruf uebergibt."""
    first = kms.lesson_record("insight", "Wiederholter Fund", anlass="selbst")
    assert first["status"] == "recorded", first
    second = kms.lesson_record("insight", "Wiederholter Fund", anlass="skript")
    assert second["status"] == "incremented", second
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT anlass FROM lessons_learned WHERE id = ?", (first["id"],)).fetchone()
    conn.close()
    assert row == ("selbst",), row


# --- Altbestand / Migration ---------------------------------------------

def test_schema_default_deckt_ohne_migration_geschriebene_altzeilen_ab(temp_db):
    """Eine Zeile, roh per SQL ohne anlass eingefuegt (so wie migrate_anlass.py
    eine echte Alt-DB vorfindet), bekommt automatisch 'unbekannt' -- das ist
    der DEFAULT-Mechanismus, den migrate_anlass.py fuer die Rueckfuellung nutzt."""
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, norm_entscheidung) "
        "VALUES ('alt1', '/alt', 'shared', 'Alt', 'x', 'x', 0, 'x', 'keine_norm')"
    )
    conn.execute("INSERT INTO lessons_learned (id, type, description) VALUES ('L-alt', 'insight', 'Alt-Fund')")
    conn.commit()
    row_n = conn.execute("SELECT anlass FROM knowledge_nodes WHERE id = 'alt1'").fetchone()
    row_l = conn.execute("SELECT anlass FROM lessons_learned WHERE id = 'L-alt'").fetchone()
    conn.close()
    assert row_n == ("unbekannt",), row_n
    assert row_l == ("unbekannt",), row_l


# --- knowledge_stats ------------------------------------------------------

def test_knowledge_stats_zeigt_anlass_verteilung_getrennt(temp_db):
    kms.knowledge_add("/", "Knoten selbst", "x", source=_source(), anlass="selbst")
    kms.knowledge_add("/", "Knoten unbekannt", "x", source=_source())
    kms.lesson_record("insight", "Lehre betreiber", anlass="betreiber")
    kms.lesson_record("insight", "Lehre unbekannt")

    stats = kms.knowledge_stats()
    assert stats["nodes_by_anlass"].get("selbst") == 1, stats["nodes_by_anlass"]
    assert stats["nodes_by_anlass"].get("unbekannt") == 1, stats["nodes_by_anlass"]
    assert stats["lessons_by_anlass"].get("betreiber") == 1, stats["lessons_by_anlass"]
    assert stats["lessons_by_anlass"].get("unbekannt") == 1, stats["lessons_by_anlass"]
