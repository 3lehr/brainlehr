#!/usr/bin/env python3
"""
migrate_fts_pfad_tags.py — Einmal-Migration: knowledge_fts um `path` und
`tags` erweitern (siehe schema.sql, P3 aus docs/PLAN_WISSENSSYSTEM_2026-08-05.md).

Grund: Der Materialized Path (z.B. "/apps/fahrtenbuch/…") ist die staerkste
Kontextangabe eines Knotens, war im FTS-Index aber nicht durchsuchbar --
"fahrtenbuch" fand Knoten unter /apps/fahrtenbuch/ nur, wenn das Wort
zufaellig auch im Text stand. Diese Migration wendet das erweiterte Schema
auf die LEBENDE knowledge.db an und baut den Index aus den Rohspalten von
knowledge_nodes neu auf (gleiches Muster wie migrate_fts_trigram_fold.py) --
`INSERT INTO fts(fts) VALUES('rebuild')` wuerde das NICHT tun, weil es die
Rohspalten kopiert statt durch die Faltung zu gehen.

Erstellt: 2026-08-05T00:00:00+01:00
Usage: python3 migrate_fts_pfad_tags.py            (fuehrt Migration aus)
       python3 migrate_fts_pfad_tags.py --dry-run   (nur pruefen, nichts schreiben)
"""

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
    conn.execute(
        f"INSERT INTO knowledge_fts(rowid, title, summary, content, path, tags) "
        f"SELECT rowid, {fold_title}, {fold_summary}, {fold_content}, {fold_path}, {fold_tags} "
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
