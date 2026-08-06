"""Tests fuer P8 (Nachtrag): `project_id` in knowledge_fts (schema.sql).

Belegt, dass ein Suchwort, das nur in `project_id` steht, trotzdem gefunden
wird -- und dass ein Bereichswechsel (UPDATE project_id) den alten Bereich
aus dem Index nimmt und den neuen einfuegt. Genau hier ist der Trigger
knowledge_au am 2026-08-05 schon einmal gerissen (siehe test_fts_pfad_tags.py
::test_path_change_updates_index): er schrieb zu wenige Spalten, warf keinen
Fehler und bestand integrity-check trotzdem.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))


def _fresh_db(tmp_path) -> sqlite3.Connection:
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    return conn


def _insert_node(conn, node_id, path, project_id="shared", title="x", summary="y", content=""):
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, 'test')",
        (node_id, path, project_id, title, summary, content),
    )


def _hits(conn, word: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM knowledge_fts WHERE knowledge_fts MATCH ?", (word,)
    ).fetchone()[0]


def test_word_only_in_project_id_matches(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_node(conn, "n1", "/apps/irgendwas", project_id="fahrtenbuch",
                  title="Titel ohne Bezug", summary="Zusammenfassung ohne Bezug")
    conn.commit()
    assert _hits(conn, "fahrtenbuch") == 1


def test_project_id_change_updates_index(tmp_path):
    """Der Regressionsfall aus dem Auftrag: knowledge_au muss project_id mitfuehren."""
    conn = _fresh_db(tmp_path)
    _insert_node(conn, "n1", "/apps/irgendwas", project_id="altprojekt",
                  title="Titel ohne Bezug", summary="Zusammenfassung ohne Bezug")
    conn.commit()
    assert _hits(conn, "altprojekt") == 1
    assert _hits(conn, "neuprojekt") == 0

    conn.execute("UPDATE knowledge_nodes SET project_id = 'neuprojekt' WHERE id = 'n1'")
    conn.commit()

    assert _hits(conn, "neuprojekt") == 1
    assert _hits(conn, "altprojekt") == 0


def test_other_project_not_found_when_scoped(tmp_path):
    """Gegenprobe: bereichsgebundene Suche (project_id-Filter im MATCH) sieht
    einen Knoten aus einem anderen Bereich nicht."""
    conn = _fresh_db(tmp_path)
    _insert_node(conn, "n1", "/apps/fahrtenbuch/x", project_id="fahrtenbuch",
                  title="Kilometerstand", summary="Kandidat")
    _insert_node(conn, "n2", "/apps/openlehr/x", project_id="openlehr",
                  title="Kilometerstand", summary="Kandidat")
    conn.commit()

    rows = conn.execute(
        "SELECT rowid FROM knowledge_fts WHERE knowledge_fts MATCH 'kilometerstand'"
    ).fetchall()
    assert len(rows) == 2  # ungefiltert: beide

    scoped = conn.execute(
        "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        "WHERE knowledge_fts MATCH 'kilometerstand' AND n.project_id = 'openlehr'"
    ).fetchall()
    assert [r[0] for r in scoped] == ["n2"]


def test_every_trigger_writes_every_fts_column(tmp_path):
    """Trigger-Selbstschutz (Auftrag: 'jeder Trigger schreibt genau so viele
    Spalten wie knowledge_fts hat'). Diese Fehlerklasse wirft keinen Fehler
    und besteht integrity-check -- sie muss strukturell gefangen werden, nicht
    durch Sorgfalt: knowledge_au riss am 2026-08-05 genau hier, unbemerkt."""
    import re

    conn = _fresh_db(tmp_path)
    fts_cols = [r[1] for r in conn.execute("PRAGMA table_info(knowledge_fts)").fetchall()]
    assert fts_cols, "knowledge_fts hat keine Spalten -- Schema kaputt"

    for trigger_name in ("knowledge_ai", "knowledge_ad", "knowledge_au"):
        sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'trigger' AND name = ?",
            (trigger_name,),
        ).fetchone()[0]
        column_lists = re.findall(r"INSERT INTO knowledge_fts\(([^)]*)\)", sql)
        assert column_lists, f"{trigger_name}: kein INSERT INTO knowledge_fts(...) gefunden"
        for raw in column_lists:
            cols = [c.strip() for c in raw.split(",")]
            cols = [c for c in cols if c not in ("rowid", "knowledge_fts")]
            assert len(cols) == len(fts_cols), (
                f"{trigger_name}: schreibt {len(cols)} Spalten ({cols}), "
                f"knowledge_fts hat {len(fts_cols)} ({fts_cols})"
            )


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        test_word_only_in_project_id_matches(p)
        test_project_id_change_updates_index(p)
        test_other_project_not_found_when_scoped(p)
        test_every_trigger_writes_every_fts_column(p)
    print("OK")
