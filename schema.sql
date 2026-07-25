-- Knowledge Database Schema (SQLite + FTS5)
-- Erstellt: 2026-03-25T16:20:00+01:00
-- Zweck: Baumstruktur-Wissens-DB für Cross-Projekt Agent-Zugriff

-- Haupttabelle: Wissensknoten mit Materialized Path
CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id TEXT PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,               -- Materialized Path: /shared/arch/mcp
    parent_path TEXT,                        -- Parent: /shared/arch
    project_id TEXT NOT NULL DEFAULT 'shared', -- shared|begod|aka|bebetter
    title TEXT NOT NULL,
    summary TEXT NOT NULL,                   -- 1-2 Sätze (Token-sparend!)
    content TEXT,                            -- Volltext (nur bei Bedarf laden)
    level INTEGER NOT NULL DEFAULT 0,        -- Tiefe im Baum (0=root)
    tags TEXT DEFAULT '[]',                  -- JSON Array
    source TEXT,                             -- Herkunft: Datei/Konsil/Research
    confidence REAL DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00', 'now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00', 'now', 'localtime'))
);

-- Volltext-Suche über Titel, Summary und Content
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title, summary, content,
    content='knowledge_nodes',
    content_rowid='rowid'
);

-- Trigger: FTS bei INSERT/UPDATE/DELETE synchron halten
CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge_nodes BEGIN
    INSERT INTO knowledge_fts(rowid, title, summary, content)
    VALUES (new.rowid, new.title, new.summary, new.content);
END;

CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge_nodes BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary, content)
    VALUES ('delete', old.rowid, old.title, old.summary, old.content);
END;

CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge_nodes BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, summary, content)
    VALUES ('delete', old.rowid, old.title, old.summary, old.content);
    INSERT INTO knowledge_fts(rowid, title, summary, content)
    VALUES (new.rowid, new.title, new.summary, new.content);
END;

-- Lessons Learned Tabelle
CREATE TABLE IF NOT EXISTS lessons_learned (
    id TEXT PRIMARY KEY,
    node_path TEXT,                           -- Referenz auf knowledge_nodes.path
    type TEXT NOT NULL,                       -- error|insight|pattern|antipattern
    severity TEXT DEFAULT 'medium',           -- critical|high|medium|low
    description TEXT NOT NULL,
    root_cause TEXT,
    resolution TEXT,
    prevention TEXT,
    occurrences INTEGER DEFAULT 1,
    projects TEXT DEFAULT '[]',               -- JSON Array: ["begod","aka"]
    status TEXT DEFAULT 'active',             -- active|resolved|escalated_to_rule
    first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00', 'now', 'localtime')),
    last_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00', 'now', 'localtime')),
    auto_rule_generated INTEGER DEFAULT 0     -- 1 wenn bereits Regel generiert
);

-- Session-Log (wer hat wann was abgefragt)
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_path TEXT,
    action TEXT NOT NULL,                     -- browse|read|search|add|lesson
    query TEXT,
    project_id TEXT,
    timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00', 'now', 'localtime'))
);

-- Indices für Performance
CREATE INDEX IF NOT EXISTS idx_nodes_path ON knowledge_nodes(path);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON knowledge_nodes(parent_path);
CREATE INDEX IF NOT EXISTS idx_nodes_project ON knowledge_nodes(project_id);
CREATE INDEX IF NOT EXISTS idx_nodes_level ON knowledge_nodes(level);
CREATE INDEX IF NOT EXISTS idx_lessons_type ON lessons_learned(type);
CREATE INDEX IF NOT EXISTS idx_lessons_status ON lessons_learned(status);
CREATE INDEX IF NOT EXISTS idx_lessons_project ON lessons_learned(projects);
