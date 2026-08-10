"""Rot-vor-gruen fuer die Modellsperre Stufe 2 (Auftrag 2026-08-07): drei
knowledge_mcp_server.py-Prozesse liefen ueber Tage mit einem veralteten
Einbettungsmodell im Speicher weiter und schrieben Vektoren mit dem alten
Modell in die gemeinsame knowledge_embeddings, nachdem das Vorgabe-Modell
laengst auf bge-m3 umgestellt war. Fix: BEFORE-Trigger an knowledge_embeddings
(knowledge_embeddings_model_check_bi/_bu in schema.sql), die einen INSERT/
UPDATE mit einem anderen als dem in knowledge_config hinterlegten Modell mit
RAISE(ABORT) ablehnen -- gleiches Idiom wie die sechs bestehenden
knowledge_nodes_*_check-Trigger (siehe test_source_constraints.py).

Negativfall (verbindlich laut Auftrag): eine abgelehnte Einbettung darf den
Knoten-/Lesson-Schreibvorgang selbst NICHT verhindern -- geprueft ueber
knowledge_add() mit gemocktem embed_text() und einem absichtlich falschen
knowledge_config-Wert.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


def _insert_embedding(conn: sqlite3.Connection, *, model: str, ref_id: str = "n1") -> None:
    conn.execute(
        "INSERT INTO knowledge_embeddings (kind, ref_id, project_id, model, dim, vector, updated_at) "
        "VALUES ('node', ?, 'shared', ?, 4, X'00000000', '2026-08-07T00:00:00+02:00')",
        (ref_id, model),
    )
    conn.commit()


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische DB aus dem aktuellen schema.sql -- Trigger + Config-Seed
    ('embed_model' = 'bge-m3') sind hier bereits aktiv."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


@pytest.fixture()
def old_db_without_lock(tmp_path):
    """Simuliert den Zustand VOR diesem Auftrag: gleiches Schema, aber ohne
    die beiden Modell-Trigger (wie eine Bestands-DB vor dem naechsten
    Server-Neustart, der ensure_schema() erneut laufen laesst)."""
    db_path = tmp_path / "alt_ohne_sperre.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.execute("DROP TRIGGER IF EXISTS knowledge_embeddings_model_check_bi")
    conn.execute("DROP TRIGGER IF EXISTS knowledge_embeddings_model_check_bu")
    conn.commit()
    conn.close()
    return db_path


# --- a) Rot vor gruen -------------------------------------------------------

def test_rot_vor_fix_fremdes_modell_geht_klaglos_durch(old_db_without_lock):
    conn = sqlite3.connect(str(old_db_without_lock))
    _insert_embedding(conn, model="nomic-embed-text")
    row = conn.execute("SELECT model FROM knowledge_embeddings WHERE ref_id='n1'").fetchone()
    conn.close()
    assert row == ("nomic-embed-text",)  # kein Fehler -- genau der Befund


def test_gruen_nach_fix_fremdes_modell_wird_abgewiesen(temp_db):
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError, match="weicht vom gueltigen Modell"):
        _insert_embedding(conn, model="nomic-embed-text")
    conn.close()


def test_gueltiges_modell_gelingt(temp_db):
    conn = sqlite3.connect(str(temp_db))
    _insert_embedding(conn, model="bge-m3")
    row = conn.execute("SELECT model FROM knowledge_embeddings WHERE ref_id='n1'").fetchone()
    conn.close()
    assert row == ("bge-m3",)


def test_negativ_update_auf_fremdes_modell_abgewiesen(temp_db):
    conn = sqlite3.connect(str(temp_db))
    _insert_embedding(conn, model="bge-m3")
    with pytest.raises(sqlite3.IntegrityError, match="weicht vom gueltigen Modell"):
        conn.execute("UPDATE knowledge_embeddings SET model='nomic-embed-text' WHERE ref_id='n1'")
    conn.close()


# --- b) Negativfall (verbindlich): Knoten wird trotzdem geschrieben --------

def test_negativfall_knoten_wird_trotz_abgelehnter_einbettung_geschrieben(temp_db, monkeypatch):
    """Config traegt absichtlich ein falsches Modell -- _rebuild_node_embedding
    baut einen echten Vektor (embed_text gemockt), der INSERT dafuer scheitert
    am Trigger. Der Knoten selbst muss trotzdem entstehen (kein
    sqlite3.IntegrityError aus knowledge_add nach aussen)."""
    conn = sqlite3.connect(str(temp_db))
    conn.execute("UPDATE knowledge_config SET value='ein-anderes-modell' WHERE key='embed_model'")
    conn.commit()
    conn.close()

    monkeypatch.setattr(kms.embeddings, "embed_text", lambda text, **kw: [0.1, 0.2, 0.3])
    # embeddings.DEFAULT_EMBED_MODEL bleibt 'bge-m3' (oder ENV-Wert) -- ungleich
    # dem eben gesetzten Config-Wert, damit der Trigger sicher greift.
    assert kms.embeddings.DEFAULT_EMBED_MODEL != "ein-anderes-modell"

    res = kms.knowledge_add("/", "Trotzdem geschrieben", "Zusammenfassung", source="test")
    assert res.get("status") == "created", res

    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT id FROM knowledge_nodes WHERE id=?", (res["id"],)).fetchone()
    emb = conn.execute(
        "SELECT 1 FROM knowledge_embeddings WHERE kind='node' AND ref_id=?", (res["id"],)
    ).fetchone()
    conn.close()
    assert row is not None, "Knoten fehlt -- die abgelehnte Einbettung haette ihn nicht mitreissen duerfen"
    assert emb is None, "Einbettung haette abgelehnt werden muessen, ist aber da"


def test_gegenprobe_knoten_bekommt_einbettung_bei_gueltigem_modell(temp_db, monkeypatch):
    """Gegenprobe zum Negativfall: stimmt das Modell, landet die Einbettung
    tatsaechlich mit -- der Trigger blockt nicht pauschal."""
    monkeypatch.setattr(kms.embeddings, "embed_text", lambda text, **kw: [0.1, 0.2, 0.3])

    res = kms.knowledge_add("/", "Mit Einbettung", "Zusammenfassung", source="test")
    assert res.get("status") == "created", res

    conn = sqlite3.connect(str(temp_db))
    emb = conn.execute(
        "SELECT model FROM knowledge_embeddings WHERE kind='node' AND ref_id=?", (res["id"],)
    ).fetchone()
    conn.close()
    assert emb == (kms.embeddings.DEFAULT_EMBED_MODEL,), emb
