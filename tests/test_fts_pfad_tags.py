"""Tests fuer P3: `path` und `tags` in knowledge_fts (schema.sql).

Belegt, dass ein Suchwort, das nur im Materialized Path oder nur in `tags`
steht, trotzdem gefunden wird -- und dass ein Pfadwechsel (UPDATE) den alten
Pfad aus dem Index nimmt und den neuen einfuegt (die Luecke, die der
unvollstaendige knowledge_au-Trigger zuvor still verschluckt hat).
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


def _insert_node(conn, node_id, path, title="x", summary="y", content="", tags="[]"):
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, tags) "
        "VALUES (?, ?, 'shared', ?, ?, ?, 0, ?)",
        (node_id, path, title, summary, content, tags),
    )


def _hits(conn, word: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM knowledge_fts WHERE knowledge_fts MATCH ?", (word,)
    ).fetchone()[0]


def test_word_only_in_path_matches(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_node(conn, "n1", "/apps/fahrtenbuch/irgendwas",
                  title="Titel ohne Bezug", summary="Zusammenfassung ohne Bezug")
    conn.commit()
    assert _hits(conn, "fahrtenbuch") == 1


def test_word_only_in_tags_matches(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_node(conn, "n1", "/shared/irgendwas",
                  title="Titel ohne Bezug", summary="Zusammenfassung ohne Bezug",
                  tags='["kaskade"]')
    conn.commit()
    assert _hits(conn, "kaskade") == 1


def test_path_change_updates_index(tmp_path):
    """Der eigentliche Regressionsfall: knowledge_au muss path/tags mitfuehren."""
    conn = _fresh_db(tmp_path)
    _insert_node(conn, "n1", "/apps/altenpfad/zzz",
                  title="Titel ohne Bezug", summary="Zusammenfassung ohne Bezug")
    conn.commit()
    assert _hits(conn, "altenpfad") == 1
    assert _hits(conn, "neuerpfad") == 0

    conn.execute("UPDATE knowledge_nodes SET path = '/apps/neuerpfad/zzz' WHERE id = 'n1'")
    conn.commit()

    assert _hits(conn, "neuerpfad") == 1
    assert _hits(conn, "altenpfad") == 0


def test_unrelated_path_does_not_match(tmp_path):
    conn = _fresh_db(tmp_path)
    _insert_node(conn, "n1", "/apps/fahrtenbuch/irgendwas",
                  title="Titel ohne Bezug", summary="Zusammenfassung ohne Bezug")
    conn.commit()
    assert _hits(conn, "openlehr") == 0


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        test_word_only_in_path_matches(p)
        test_word_only_in_tags_matches(p)
        test_path_change_updates_index(p)
        test_unrelated_path_does_not_match(p)
    print("OK")
