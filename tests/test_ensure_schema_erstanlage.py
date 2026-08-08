"""Rot-vor-gruen fuer den Befund 2026-08-06 (fremder Ort, leere Datenbank):
ensure_schema() zog bisher nur Spalten nach (ALTER TABLE access_log ...) und
setzte voraus, dass die Kerntabellen schon existieren -- eine leere Datei als
Datenbank scheiterte mit `sqlite3.OperationalError: no such table:
access_log`. Fix: _ensure_core_schema() spielt schema.sql (einzige
Schemaquelle) VOR den additiven Schritten ein.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


def test_leere_datenbank_bekommt_kerntabellen(tmp_path):
    db = tmp_path / "leer.db"
    conn = sqlite3.connect(db)
    try:
        kms.ensure_schema(conn)
        tabellen = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for kern in ("knowledge_nodes", "lessons_learned", "access_log",
                     "knowledge_relations"):
            assert kern in tabellen, f"{kern} fehlt nach ensure_schema auf leerer DB"
    finally:
        conn.close()


def test_vorhandene_datenbank_bleibt_unveraendert(tmp_path):
    """Wichtigster Fall: eine bereits vollstaendige DB darf ensure_schema
    kein zweites Mal antasten (alle Anweisungen in schema.sql stehen unter
    IF NOT EXISTS, die additiven Spalten sind bereits da)."""
    db = tmp_path / "voll.db"
    conn = sqlite3.connect(db)
    kms.ensure_schema(conn)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, "
        "summary, source, updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('n1', '/x', NULL, 0, 't', 's', 'test', 'jetzt', 'keine_norm', 'skript:test', 'Testvorrichtung')"
    )
    conn.commit()
    vor = conn.execute("SELECT * FROM knowledge_nodes WHERE id='n1'").fetchone()

    kms.ensure_schema(conn)  # zweiter Lauf, muss No-op fuer Bestandsdaten sein

    nach = conn.execute("SELECT * FROM knowledge_nodes WHERE id='n1'").fetchone()
    assert vor == nach
    conn.close()


def test_fehlende_schema_sql_wirft_sprechenden_fehler(tmp_path, monkeypatch):
    monkeypatch.setattr(kms, "__file__", str(tmp_path / "nirgendwo" / "knowledge_mcp_server.py"))
    conn = sqlite3.connect(tmp_path / "x.db")
    try:
        with pytest.raises(RuntimeError, match="schema.sql fehlt"):
            kms.ensure_schema(conn)
    finally:
        conn.close()


def test_erstanlage_traegt_die_herkunftsschranke(tmp_path):
    """Befund 2026-08-08: eine Erstanlage bekam 29 Trigger, der Betrieb hatte
    31 -- die beiden fehlenden waren knowledge_nodes_herkunft_bu und
    lessons_herkunft_bu. Eine frisch installierte brainlehr lief also ohne die
    Regel, die sie ausmacht: Herkunft nachtragen ja, umschreiben nie.

    ROT VOR GRUEN: gegen den Stand vor der Aenderung fehlen beide Trigger,
    und das UPDATE unten geht anstandslos durch.

    Geprueft wird beides -- dass die Trigger da sind UND dass sie greifen.
    Ein vorhandener Trigger, der nichts abweist, waere kein Beleg.
    """
    db = tmp_path / "erstanlage.db"
    conn = sqlite3.connect(db)
    try:
        kms.ensure_schema(conn)
        trigger = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        assert "knowledge_nodes_herkunft_bu" in trigger
        assert "lessons_herkunft_bu" in trigger

        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, level, title, "
            "summary, source, updated_at, actor, norm_entscheidung, "
            "norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('t1', '/t1', NULL, 0, 't', 's', 'test', 'jetzt', 'actor-A', "
            "'keine_norm', 'actor-A', 'Testvorrichtung')"
        )
        with pytest.raises(sqlite3.IntegrityError, match="Herkunftsfeld unveraenderlich"):
            conn.execute("UPDATE knowledge_nodes SET actor = 'actor-B' WHERE id = 't1'")
    finally:
        conn.close()
