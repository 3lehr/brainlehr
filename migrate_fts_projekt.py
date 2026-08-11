#!/usr/bin/env python3
"""
migrate_fts_projekt.py — Einmal-Migration: knowledge_fts um `project_id`
erweitern (siehe schema.sql, Nachtrag zu P3 aus
docs/PLAN_WISSENSSYSTEM_2026-08-05.md).

Grund: Der Suchindex muss sich nach Bereich trennen lassen, bevor weiter an
ihm gebaut wird -- ein Filter HINTER der Suche leckt ueber Trefferzahl/Rang
(BM25 rechnet sonst ueber Dokumente, die der Fragende nie sehen duerfte).
Diese Migration wendet das erweiterte Schema auf die LEBENDE brainlehr.db an
und baut den Index aus den Rohspalten von knowledge_nodes neu auf (gleiches
Muster wie migrate_fts_pfad_tags.py) -- `INSERT INTO fts(fts) VALUES('rebuild')`
wuerde das NICHT tun, weil es die Rohspalten kopiert statt durch die Faltung
zu gehen.

Erstellt: 2026-08-05T00:00:00+01:00
Usage: python3 migrate_fts_projekt.py            (fuehrt Migration aus)
       python3 migrate_fts_projekt.py --dry-run   (nur pruefen, nichts schreiben)
"""

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from knowledge_mcp_server import DB_PATH  # noqa: E402

SCHEMA_SQL = Path(__file__).parent / "schema.sql"

# Dieselbe Faltung wie in schema.sql (Trigger) und knowledge_mcp_server.fold_de().
FOLD_SQL = (
    "LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE({col},"
    "'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss'))"
)


def backup_db() -> Path:
    ts = datetime.now(timezone(timedelta(hours=1))).strftime("%Y%m%dT%H%M%S")
    backup_path = DB_PATH.with_name(f"{DB_PATH.name}.bak-{ts}")
    shutil.copy2(DB_PATH, backup_path)
    if not backup_path.exists() or backup_path.stat().st_size == 0:
        raise SystemExit(f"Backup fehlgeschlagen: {backup_path}")
    print(f"Backup angelegt: {backup_path} ({backup_path.stat().st_size} bytes)")
    return backup_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"Datenbank: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    node_count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    fts_count_before = conn.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()[0]
    schema_before = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'knowledge_fts'"
    ).fetchone()[0]
    print(f"knowledge_nodes: {node_count} Zeilen")
    print(f"knowledge_fts vorher: {fts_count_before} Zeilen")
    print(f"knowledge_fts-Schema vorher: {schema_before}")

    if args.dry_run:
        print("--dry-run: kein Backup, keine Schreibaktion.")
        conn.close()
        return

    backup_path = backup_db()

    conn.execute("DROP TRIGGER IF EXISTS knowledge_ai")
    conn.execute("DROP TRIGGER IF EXISTS knowledge_ad")
    conn.execute("DROP TRIGGER IF EXISTS knowledge_au")
    conn.execute("DROP TABLE IF EXISTS knowledge_fts")
    conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))

    fold_title = FOLD_SQL.format(col="title")
    fold_summary = FOLD_SQL.format(col="summary")
    fold_content = FOLD_SQL.format(col="content")
    fold_path = FOLD_SQL.format(col="path")
    fold_tags = FOLD_SQL.format(col="tags")
    fold_project = FOLD_SQL.format(col="project_id")
    conn.execute(
        f"INSERT INTO knowledge_fts(rowid, title, summary, content, path, tags, project_id) "
        f"SELECT rowid, {fold_title}, {fold_summary}, {fold_content}, {fold_path}, {fold_tags}, {fold_project} "
        f"FROM knowledge_nodes"
    )
    conn.commit()

    fts_count_after = conn.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()[0]
    schema_after = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'knowledge_fts'"
    ).fetchone()[0]
    conn.close()

    print(f"Sicherung: {backup_path}")
    print(f"knowledge_fts-Schema nachher: {schema_after}")
    print(f"knowledge_fts nachher: {fts_count_after} Zeilen (erwartet {node_count})")
    if fts_count_after != node_count:
        print("ACHTUNG: Zeilenzahl weicht ab -- pruefen!")


if __name__ == "__main__":
    main()
