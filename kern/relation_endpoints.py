"""P69 typed endpoint validation and one explicit legacy-table migration."""
from __future__ import annotations

import sqlite3

KINDS = ("node", "lesson", "file")


def _safe_file(value: str) -> bool:
    return bool(value) and not value.startswith(("/", "\\")) and ".." not in value and "\\" not in value


def ensure_triggers(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_relations)")}
    if not {"source_kind", "target_kind"} <= columns:
        return
    conn.executescript("""
    DROP TRIGGER IF EXISTS knowledge_relations_endpoints_bi;
    DROP TRIGGER IF EXISTS knowledge_relations_endpoints_bu;
    CREATE TRIGGER knowledge_relations_endpoints_bi BEFORE INSERT ON knowledge_relations BEGIN
      SELECT CASE
        WHEN NEW.source_kind NOT IN ('node','lesson','file') OR NEW.target_kind NOT IN ('node','lesson','file') THEN RAISE(ABORT, 'unknown relation endpoint kind')
        WHEN NEW.source_kind='node' AND NOT EXISTS(SELECT 1 FROM knowledge_nodes WHERE path=NEW.source_path) THEN RAISE(ABORT, 'relation source node missing')
        WHEN NEW.target_kind='node' AND NOT EXISTS(SELECT 1 FROM knowledge_nodes WHERE path=NEW.target_path) THEN RAISE(ABORT, 'relation target node missing')
        WHEN NEW.source_kind='lesson' AND NOT EXISTS(SELECT 1 FROM lessons_learned WHERE id=NEW.source_path) THEN RAISE(ABORT, 'relation source lesson missing')
        WHEN NEW.target_kind='lesson' AND NOT EXISTS(SELECT 1 FROM lessons_learned WHERE id=NEW.target_path) THEN RAISE(ABORT, 'relation target lesson missing')
        WHEN NEW.source_kind='file' AND (NEW.source_path='' OR NEW.source_path GLOB '/*' OR NEW.source_path GLOB '*..*' OR NEW.source_path GLOB '*\\*') THEN RAISE(ABORT, 'relation source file is not repo-relative')
        WHEN NEW.target_kind='file' AND (NEW.target_path='' OR NEW.target_path GLOB '/*' OR NEW.target_path GLOB '*..*' OR NEW.target_path GLOB '*\\*') THEN RAISE(ABORT, 'relation target file is not repo-relative')
      END;
    END;
    CREATE TRIGGER knowledge_relations_endpoints_bu BEFORE UPDATE OF source_path,target_path,source_kind,target_kind ON knowledge_relations BEGIN
      SELECT CASE
        WHEN NEW.source_kind NOT IN ('node','lesson','file') OR NEW.target_kind NOT IN ('node','lesson','file') THEN RAISE(ABORT, 'unknown relation endpoint kind')
        WHEN NEW.source_kind='node' AND NOT EXISTS(SELECT 1 FROM knowledge_nodes WHERE path=NEW.source_path) THEN RAISE(ABORT, 'relation source node missing')
        WHEN NEW.target_kind='node' AND NOT EXISTS(SELECT 1 FROM knowledge_nodes WHERE path=NEW.target_path) THEN RAISE(ABORT, 'relation target node missing')
        WHEN NEW.source_kind='lesson' AND NOT EXISTS(SELECT 1 FROM lessons_learned WHERE id=NEW.source_path) THEN RAISE(ABORT, 'relation source lesson missing')
        WHEN NEW.target_kind='lesson' AND NOT EXISTS(SELECT 1 FROM lessons_learned WHERE id=NEW.target_path) THEN RAISE(ABORT, 'relation target lesson missing')
        WHEN NEW.source_kind='file' AND (NEW.source_path='' OR NEW.source_path GLOB '/*' OR NEW.source_path GLOB '*..*' OR NEW.source_path GLOB '*\\*') THEN RAISE(ABORT, 'relation source file is not repo-relative')
        WHEN NEW.target_kind='file' AND (NEW.target_path='' OR NEW.target_path GLOB '/*' OR NEW.target_path GLOB '*..*' OR NEW.target_path GLOB '*\\*') THEN RAISE(ABORT, 'relation target file is not repo-relative')
      END;
    END;
    """)


def _kinds(row: sqlite3.Row) -> tuple[str, str]:
    if row["relation_type"] == "lesson_mentions_file" and row["source_path"].startswith("L-") and _safe_file(row["target_path"]):
        return "lesson", "file"
    if row["relation_type"] == "abgeleitet_von" and row["target_path"].startswith("L-"):
        return "node", "lesson"
    return "node", "node"


def migrate(conn: sqlite3.Connection) -> dict[str, int]:
    """Atomically rebuild legacy relations without polymorphism-invalid FKs."""
    conn.row_factory = sqlite3.Row
    cols = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_relations)")}
    if {"source_kind", "target_kind"} <= cols:
        ensure_triggers(conn)
        return {"node_node": 0, "node_lesson": 0, "lesson_file": 0, "unchanged": 1}
    rows = list(conn.execute("SELECT id,source_path,target_path,relation_type,confidence,weight,evidence,source,creator,model,session,created_at,updated_at,hinsicht FROM knowledge_relations ORDER BY id"))
    typed = [(row, *_kinds(row)) for row in rows]
    nodes = {r[0] for r in conn.execute("SELECT path FROM knowledge_nodes")}
    lessons = {r[0] for r in conn.execute("SELECT id FROM lessons_learned")}
    for row, sk, tk in typed:
        if (sk == "node" and row["source_path"] not in nodes) or (tk == "node" and row["target_path"] not in nodes) or (sk == "lesson" and row["source_path"] not in lessons) or (tk == "lesson" and row["target_path"] not in lessons):
            raise ValueError(f"unclassifiable relation {row['id']}")
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.executescript("""
        CREATE TABLE knowledge_relations_p69 (
          id TEXT PRIMARY KEY, source_path TEXT NOT NULL, target_path TEXT NOT NULL,
          source_kind TEXT NOT NULL DEFAULT 'node' CHECK(source_kind IN ('node','lesson','file')),
          target_kind TEXT NOT NULL DEFAULT 'node' CHECK(target_kind IN ('node','lesson','file')),
          relation_type TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0.8 CHECK(confidence BETWEEN 0.0 AND 1.0),
          weight REAL NOT NULL DEFAULT 1.0 CHECK(weight >= 0.0), evidence TEXT, source TEXT, creator TEXT,
          model TEXT, session TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, hinsicht TEXT,
          UNIQUE(source_path,target_path,relation_type));
        """)
        for row, sk, tk in typed:
            conn.execute("INSERT INTO knowledge_relations_p69 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (row['id'],row['source_path'],row['target_path'],sk,tk,row['relation_type'],row['confidence'],row['weight'],row['evidence'],row['source'],row['creator'],row['model'],row['session'],row['created_at'],row['updated_at'],row['hinsicht']))
        conn.execute("DROP TABLE knowledge_relations")
        conn.execute("ALTER TABLE knowledge_relations_p69 RENAME TO knowledge_relations")
        conn.executescript("CREATE INDEX idx_relations_source ON knowledge_relations(source_path); CREATE INDEX idx_relations_target ON knowledge_relations(target_path); CREATE INDEX idx_relations_type ON knowledge_relations(relation_type);")
        ensure_triggers(conn)
        conn.commit()
    except BaseException:
        conn.rollback(); raise
    counts = {"node_node": 0, "node_lesson": 0, "lesson_file": 0}
    for _, sk, tk in typed: counts[f"{sk}_{tk}"] += 1
    return counts
