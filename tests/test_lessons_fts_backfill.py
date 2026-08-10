"""Rot-vor-gruen fuer _ensure_lessons_fts_backfill (Auftrag 2026-08-07).
Bestands-Lehren (vor lessons_ai/ad/au angelegt, z.B. per rohem INSERT ohne
den knowledge_mcp_server-Weg) muessen nach ensure_schema() per Volltext
auffindbar sein -- Trigger allein erreichen nur kuenftige Schreibvorgaenge.

Deckt zusaetzlich den beim Bau gefundenen ROT-Befund ab: eine externe
FTS5-Inhaltstabelle meldet COUNT(*)/rowid OHNE MATCH bereits die Zeilenzahl
der Inhaltstabelle, auch wenn der invertierte Index leer ist -- ein Test,
der nur auf COUNT(*) prueft, haette den ursprbuenglichen Bug nicht gefangen.
Deshalb hier ausschliesslich ueber echte MATCH-Treffer geprueft.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


def _db_with_preexisting_lesson(tmp_path) -> tuple[sqlite3.Connection, Path]:
    """Simuliert eine Bestands-DB: lessons_learned bekommt eine Zeile VOR
    lessons_fts angelegt wird (roher INSERT vor CREATE VIRTUAL TABLE), genau
    das Layout, das schema.sql fuer eine bereits gepflegte Alt-DB antrifft."""
    db_path = tmp_path / "backfill_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE lessons_learned (
            id TEXT PRIMARY KEY, node_path TEXT, type TEXT NOT NULL,
            severity TEXT DEFAULT 'medium', description TEXT NOT NULL,
            root_cause TEXT, resolution TEXT, prevention TEXT,
            occurrences INTEGER DEFAULT 1, projects TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            last_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            auto_rule_generated INTEGER DEFAULT 0,
            anlass TEXT NOT NULL DEFAULT 'unbekannt', actor TEXT, session TEXT, model TEXT
        );
        CREATE TABLE knowledge_nodes (
            id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, parent_path TEXT,
            project_id TEXT NOT NULL DEFAULT 'shared', title TEXT NOT NULL,
            summary TEXT NOT NULL, content TEXT, level INTEGER NOT NULL DEFAULT 0,
            tags TEXT DEFAULT '[]', source TEXT, confidence REAL DEFAULT 0.8,
            access_count INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
            zurueckgezogen INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, root_cause, prevention) "
        "VALUES ('L-bf001', 'insight', 'bestandslehreauffindbarxyz', "
        "'bestandsursachexyz', 'bestandsvorbeugungxyz')"
    )
    conn.commit()
    conn.close()
    return db_path


def _hits(conn, word: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM lessons_fts WHERE lessons_fts MATCH ?", (word,)
    ).fetchone()[0]


def test_rot_vor_fix_bestandszeile_ohne_backfill_nicht_auffindbar(tmp_path, monkeypatch):
    """Rot-Probe: schema.sql allein (CREATE VIRTUAL TABLE + Trigger, OHNE
    den Backfill-Aufruf) laesst die Bestandszeile unauffindbar -- belegt den
    Befund woertlich, nicht nur behauptet."""
    db_path = _db_with_preexisting_lesson(tmp_path)
    conn = sqlite3.connect(str(db_path))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    assert _hits(conn, "bestandslehreauffindbarxyz") == 0, (
        "Rot-Probe fehlgeschlagen: schema.sql allein haette die Bestandszeile "
        "NICHT indizieren duerfen (das ist der Befund, den der Backfill behebt)"
    )
    conn.close()


def test_gruen_nach_ensure_schema_bestandszeile_auffindbar(tmp_path, monkeypatch):
    monkeypatch.setattr(kms, "DB_PATH", tmp_path / "backfill_test.db")
    db_path = _db_with_preexisting_lesson(tmp_path)
    conn = sqlite3.connect(str(db_path))
    kms.ensure_schema(conn)  # ruft _ensure_lessons_fts_backfill mit auf
    conn.commit()
    assert _hits(conn, "bestandslehreauffindbarxyz") == 1
    assert _hits(conn, "bestandsursachexyz") == 1
    assert _hits(conn, "bestandsvorbeugungxyz") == 1
    conn.close()


def test_zweiter_lauf_ist_ein_reiner_noop(tmp_path, monkeypatch):
    """NICHTAENDERUNG: eine bereits vollstaendig indizierte DB bleibt beim
    zweiten ensure_schema()-Lauf unveraendert (kein doppelter Indexeintrag,
    keine Backup-Datei ohne Grund)."""
    monkeypatch.setattr(kms, "DB_PATH", tmp_path / "backfill_test.db")
    db_path = _db_with_preexisting_lesson(tmp_path)
    conn = sqlite3.connect(str(db_path))
    kms.ensure_schema(conn)
    conn.commit()
    vor = _hits(conn, "bestandslehreauffindbarxyz")
    backups_vor = len(list(tmp_path.glob("*.bak-*")))

    kms.ensure_schema(conn)
    conn.commit()

    nach = _hits(conn, "bestandslehreauffindbarxyz")
    backups_nach = len(list(tmp_path.glob("*.bak-*")))
    assert vor == nach == 1, "kein doppelter Indexeintrag durch den zweiten Lauf"
    assert backups_vor == backups_nach, "zweiter Lauf darf keine neue Sicherung anlegen (nichts zu tun)"
    conn.close()
