"""Rot-vor-gruen fuer den Befund 2026-08-06: ein roher INSERT am
knowledge_mcp_server.py-Werkzeug vorbei erzeugte 17 Knoten ohne source, mit
freiem parent_path und beliebigem anlass -- die Python-seitigen Pruefungen
(source-Leercheck in knowledge_add, _validate_anlass) schuetzen nur den Weg
ueber das Werkzeug, nicht die Datei selbst (PRAGMA foreign_keys steht auf 0).
Fix: sechs BEFORE-Trigger an knowledge_nodes (schema.sql fuer neue Dateien,
knowledge_mcp_server.py::_ensure_node_constraint_triggers als Nachzug fuer
Bestands-DBs, migrate_source_constraints.py als manueller/CI-Weg).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

NEEDED_TRIGGERS = (
    "knowledge_nodes_source_check_bi", "knowledge_nodes_source_check_bu",
    "knowledge_nodes_parent_check_bi", "knowledge_nodes_parent_check_bu",
    "knowledge_nodes_anlass_check_bi", "knowledge_nodes_anlass_check_bu",
)


def _insert_raw(conn: sqlite3.Connection, *, id_: str, path: str,
                parent_path: str | None = None, source: str = "test",
                anlass: str = "unbekannt") -> None:
    """Roher INSERT ueber das Werkzeug hinweg -- genau der Weg, der den
    Befund erzeugte."""
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, "
        "summary, content, level, tags, source, created_at, updated_at, anlass, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (id_, path, parent_path, "shared", "Titel", "Summary", "Inhalt", 0,
         "[]", source, "2026-08-06T00:00:00+02:00", "2026-08-06T00:00:00+02:00", anlass, "keine_norm",
         "skript:test", "Testvorrichtung"),
    )
    conn.commit()


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische DB aus dem aktuellen schema.sql -- Trigger sind hier bereits
    aktiv (das ist der Zustand NACH dem Fix)."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


@pytest.fixture()
def old_db_without_triggers(tmp_path):
    """Simuliert den Zustand VOR diesem Auftrag: gleiches Schema, aber ohne
    die sechs Zusicherungs-Trigger (wie eine Bestands-DB, die schema.sql
    noch nicht kannte)."""
    db_path = tmp_path / "alt_ohne_trigger.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    for t in NEEDED_TRIGGERS:
        conn.execute(f"DROP TRIGGER IF EXISTS {t}")
    conn.commit()
    conn.close()
    return db_path


# --- a) Rot vor gruen ------------------------------------------------------

def test_rot_vor_fix_roher_insert_ohne_source_gelingt(old_db_without_triggers):
    """VOR der Aenderung: ein roher INSERT ohne source geht klaglos durch --
    genau der Befund (17 Knoten ohne source)."""
    conn = sqlite3.connect(str(old_db_without_triggers))
    _insert_raw(conn, id_="n1", path="/x", source="")
    row = conn.execute("SELECT source FROM knowledge_nodes WHERE id='n1'").fetchone()
    conn.close()
    assert row == ("",)  # kein Fehler, leere source landet klaglos in der DB


def test_gruen_nach_fix_roher_insert_ohne_source_wird_abgewiesen(temp_db):
    """NACH der Aenderung: derselbe rohe INSERT wird abgewiesen."""
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError, match="source darf nicht leer sein"):
        _insert_raw(conn, id_="n1", path="/x", source="")
    conn.close()


# --- b) Je Regel ein roher Negativfall -------------------------------------

def test_negativ_source_leer_insert(temp_db):
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError, match="source darf nicht leer sein"):
        _insert_raw(conn, id_="n1", path="/x", source="   ")
    conn.close()


def test_negativ_source_leer_update(temp_db):
    """Gilt auch fuer UPDATE, nicht nur INSERT."""
    conn = sqlite3.connect(str(temp_db))
    _insert_raw(conn, id_="n1", path="/x", source="echt")
    with pytest.raises(sqlite3.IntegrityError, match="source darf nicht leer sein"):
        conn.execute("UPDATE knowledge_nodes SET source = '' WHERE id='n1'")
    conn.close()


def test_negativ_parent_path_zeigt_ins_leere(temp_db):
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError, match="parent_path zeigt auf keinen vorhandenen Knoten"):
        _insert_raw(conn, id_="n1", path="/x/y", parent_path="/x")  # /x existiert nicht
    conn.close()


def test_negativ_anlass_unzulaessig(temp_db):
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError, match="anlass unzulaessig"):
        _insert_raw(conn, id_="n1", path="/x", anlass="erfunden")
    conn.close()


# --- c) Gegenprobe: gueltiger roher INSERT geht weiter durch ---------------

def test_gegenprobe_gueltiger_insert_geht_durch(temp_db):
    conn = sqlite3.connect(str(temp_db))
    _insert_raw(conn, id_="n1", path="/x", parent_path=None, source="echte Quelle", anlass="skript")
    row = conn.execute("SELECT id, source, anlass FROM knowledge_nodes WHERE id='n1'").fetchone()
    conn.close()
    assert row == ("n1", "echte Quelle", "skript")


def test_gegenprobe_parent_path_slash_und_vorhandener_knoten_erlaubt(temp_db):
    conn = sqlite3.connect(str(temp_db))
    _insert_raw(conn, id_="root", path="/x", parent_path="/", source="s")
    _insert_raw(conn, id_="child", path="/x/y", parent_path="/x", source="s")
    count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert count == 2


# --- d) Suche nach der Aenderung: FTS-Trigger unbeschaedigt ----------------

def test_suche_findet_neuen_knoten_nach_insert(temp_db):
    conn = sqlite3.connect(str(temp_db))
    _insert_raw(conn, id_="n1", path="/suchtest", source="s")
    conn.close()

    import knowledge_mcp_server as kms_reloaded  # gleiche Modulinstanz, DB_PATH gepatcht
    res = kms_reloaded.knowledge_search("Titel")
    ids = [r["id"] for r in res.get("results", [])]
    assert "n1" in ids, res


def test_suche_findet_knoten_nach_update_unveraendert(temp_db):
    """Zweiter FTS-Trigger-Zweig (knowledge_au hat zwei Zweige) -- Update auf
    einem gueltigen Knoten darf die Suche nicht kaputt machen."""
    conn = sqlite3.connect(str(temp_db))
    _insert_raw(conn, id_="n1", path="/suchtest2", source="s")
    conn.execute("UPDATE knowledge_nodes SET summary = 'Geaenderte Zusammenfassung Einzigartig' WHERE id='n1'")
    conn.commit()
    conn.close()

    res = kms.knowledge_search("Einzigartig")
    ids = [r["id"] for r in res.get("results", [])]
    assert "n1" in ids, res


# --- Selbstheilung fuer Bestands-DBs (ensure_schema) -----------------------

def test_ensure_schema_heilt_alte_db_nach_und_traegt_source_nach(old_db_without_triggers, monkeypatch):
    conn = sqlite3.connect(str(old_db_without_triggers))
    _insert_raw(conn, id_="n1", path="/alt", source="")
    conn.close()

    monkeypatch.setattr(kms, "DB_PATH", old_db_without_triggers)
    conn = kms.get_db()  # ruft ensure_schema()
    row = conn.execute("SELECT source FROM knowledge_nodes WHERE id='n1'").fetchone()
    assert row[0] == kms.SOURCE_BACKFILL_PLACEHOLDER

    with pytest.raises(sqlite3.IntegrityError, match="source darf nicht leer sein"):
        _insert_raw(conn, id_="n2", path="/neu", source="")
    conn.close()
