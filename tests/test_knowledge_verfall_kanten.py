"""Tests fuer P4 (Vektor-Verfall) und P5 (Wikilink-Kanten), Plan 2026-08-05.

P4: ein veralteter Vektor ist schlechter als gar keiner -- die Hybridsuche
gewichtet ihn gutgläubig mit (siehe test_knowledge_hybrid_search.py), waehrend
sie einen fehlenden sauber verkraftet. Deshalb loescht knowledge_update()/
lesson_update() die zugehoerige knowledge_embeddings-Zeile bei jeder
Textaenderung -- Gegenprobe: ein reiner tags/resolution-Wechsel laesst den
Vektor unberuehrt, sonst waere das nur "immer loeschen".

P5: [[wikilink]]-Verweise im content werden beim Schreiben zu echten
knowledge_relations-Kanten aufgeloest. Ein unaufgeloester Verweis ist kein
Fehler (Hinweis auf einen noch zu schreibenden Knoten), wird aber im
Rueckgabewert gemeldet statt verschluckt.
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
    # /shared muss als echter Knoten existieren, sonst lehnt knowledge_add()
    # seit P1 den Elternpfad ab (unbekannter parent_path).
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, level, updated_at, source) "
        "VALUES ('root', '/shared', NULL, 'shared', 'Shared', 'Wurzel', 0, ?, 'test')",
        (kms.now_iso(),),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _insert_node(db_path, node_id, path, title, content="", parent_path="/shared"):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, content, level, updated_at, source) "
        "VALUES (?, ?, ?, 'shared', ?, 'Zusammenfassung', ?, 1, ?, 'test')",
        (node_id, path, parent_path, title, content, kms.now_iso()),
    )
    conn.commit()
    conn.close()


def _insert_vector(db_path, kind, ref_id):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_embeddings (kind, ref_id, model, vector, updated_at) VALUES (?,?,?,?,?)",
        (kind, ref_id, "test-model", b"\x00\x00\x80?" * 4, kms.now_iso()),
    )
    conn.commit()
    conn.close()


def _vector_exists(db_path, kind, ref_id) -> bool:
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT 1 FROM knowledge_embeddings WHERE kind = ? AND ref_id = ?", (kind, ref_id)
    ).fetchone()
    conn.close()
    return row is not None


def _relations_from(db_path, source_path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM knowledge_relations WHERE source_path = ?", (source_path,)
    ).fetchall()
    conn.close()
    return rows


# --- P4: content/summary geaendert loescht Vektor, tags nicht ---------------

def test_content_change_deletes_node_vector(temp_db):
    _insert_node(temp_db, "n1", "/shared/knoten", "Knoten")
    _insert_vector(temp_db, "node", "n1")
    kms.knowledge_update("n1", content="Neuer Text")
    assert not _vector_exists(temp_db, "node", "n1")


def test_summary_change_deletes_node_vector(temp_db):
    _insert_node(temp_db, "n1", "/shared/knoten", "Knoten")
    _insert_vector(temp_db, "node", "n1")
    kms.knowledge_update("n1", summary="Neue Zusammenfassung")
    assert not _vector_exists(temp_db, "node", "n1")


def test_tags_only_change_keeps_node_vector(temp_db):
    """Gegenprobe: ohne diese wuerde ein Test, der bei JEDER Aenderung
    loescht, unbemerkt durchgehen."""
    _insert_node(temp_db, "n1", "/shared/knoten", "Knoten")
    _insert_vector(temp_db, "node", "n1")
    result = kms.knowledge_update("n1", tags=["a", "b"])
    assert result["status"] == "updated"
    assert _vector_exists(temp_db, "node", "n1")


def test_lesson_text_change_deletes_lesson_vector(temp_db):
    rec = kms.lesson_record("error", "Urspruengliche Beschreibung.")
    lesson_id = rec["id"]
    _insert_vector(temp_db, "lesson", lesson_id)
    kms.lesson_update(lesson_id, description="Korrigierte Beschreibung.")
    assert not _vector_exists(temp_db, "lesson", lesson_id)


def test_lesson_resolution_only_change_keeps_vector(temp_db):
    """Gegenprobe: resolution fliesst laut build_embeddings.py nicht in den
    Embedding-Text ein (nur description+root_cause+prevention)."""
    rec = kms.lesson_record("error", "Beschreibung bleibt gleich.")
    lesson_id = rec["id"]
    _insert_vector(temp_db, "lesson", lesson_id)
    result = kms.lesson_update(lesson_id, resolution="So wurde es geloest.")
    assert result["status"] == "updated"
    assert _vector_exists(temp_db, "lesson", lesson_id)


# --- P5: Wikilinks -> Kanten -------------------------------------------------

def test_known_wikilink_creates_one_relation(temp_db):
    _insert_node(temp_db, "target", "/shared/ziel", "Zielknoten")
    result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                               content="siehe [[Zielknoten]]", source="test")
    assert result["relations_created"] == ["/shared/ziel"]
    rows = _relations_from(temp_db, result["path"])
    assert len(rows) == 1
    assert rows[0]["target_path"] == "/shared/ziel"


def test_unknown_wikilink_creates_no_relation_but_is_reported(temp_db):
    result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                               content="siehe [[gibt-es-nicht]]", source="test")
    assert result["relations_created"] == []
    assert "gibt-es-nicht" in result["unresolved_links"]
    assert _relations_from(temp_db, result["path"]) == []


def test_update_removing_link_drops_old_edge(temp_db):
    _insert_node(temp_db, "target", "/shared/ziel", "Zielknoten")
    add_result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                                   content="siehe [[Zielknoten]]", source="test")
    assert len(_relations_from(temp_db, add_result["path"])) == 1

    kms.knowledge_update(add_result["id"], content="kein Verweis mehr")
    assert _relations_from(temp_db, add_result["path"]) == []


def test_duplicate_wikilink_creates_only_one_relation(temp_db):
    _insert_node(temp_db, "target", "/shared/ziel", "Zielknoten")
    result = kms.knowledge_add("/shared", "Quellknoten", "Zsf",
                               content="[[Zielknoten]] und nochmal [[Zielknoten]]", source="test")
    assert result["relations_created"] == ["/shared/ziel"]
    assert len(_relations_from(temp_db, result["path"])) == 1


def test_self_link_creates_no_relation(temp_db):
    _insert_node(temp_db, "self", "/shared/selbstbezug", "Selbstbezug")
    result = kms.knowledge_update("self", content="siehe [[Selbstbezug]]")
    assert result["relations_created"] == []
    assert _relations_from(temp_db, "/shared/selbstbezug") == []
