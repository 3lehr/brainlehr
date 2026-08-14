#!/usr/bin/env python3
"""
migrate_fts_trigram_fold.py — Einmal-Migration: knowledge_fts auf den
Trigram-Tokenizer + deutsche Umlaut-Faltung umstellen (siehe schema.sql).

Grund: FTS5-MATCH mit mehreren Woertern lief als implizites UND (ein Wort,
das nicht vorkommt, killt die ganze Anfrage) und "ue"-Schreibung fand "ü"
nicht (remove_diacritics macht nur ü→u, nicht ue→u). Behoben in
knowledge_mcp_server.py::knowledge_search (ODER-Verknuepfung) + schema.sql
(Trigram-Tokenizer + Faltung vor dem Indizieren). Diese Migration wendet das
neue Schema auf die LEBENDE brainlehr.db an und baut den Index aus den
(bereits gefaltet zu erwartenden) Spalten von knowledge_nodes neu auf --
`INSERT INTO fts(fts) VALUES('rebuild')` wuerde das NICHT tun, weil es die
Rohspalten kopiert statt durch die Trigger zu gehen.

Erstellt: 2026-08-01T07:45:00+01:00
Usage: python3 migrate_fts_trigram_fold.py            (fuehrt Migration aus)
       python3 migrate_fts_trigram_fold.py --dry-run   (nur pruefen, nichts schreiben)
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
from datetime import datetime

import zeitmarke
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
    ts = datetime.now(zeitmarke.BERLIN).strftime("%Y%m%dT%H%M%S")
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
    tokenizer_before = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'knowledge_fts'"
    ).fetchone()[0]
    print(f"knowledge_nodes: {node_count} Zeilen")
    print(f"knowledge_fts vorher: {tokenizer_before}")

    if args.dry_run:
        print("--dry-run: kein Backup, keine Schreibaktion.")
        conn.close()
        return

    backup_db()

    conn.execute("DROP TRIGGER IF EXISTS knowledge_ai")
    conn.execute("DROP TRIGGER IF EXISTS knowledge_ad")
    conn.execute("DROP TRIGGER IF EXISTS knowledge_au")
    conn.execute("DROP TABLE IF EXISTS knowledge_fts")
    conn.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))

    fold_title = FOLD_SQL.format(col="title")
    fold_summary = FOLD_SQL.format(col="summary")
    fold_content = FOLD_SQL.format(col="content")
    conn.execute(
        f"INSERT INTO knowledge_fts(rowid, title, summary, content) "
        f"SELECT rowid, {fold_title}, {fold_summary}, {fold_content} FROM knowledge_nodes"
    )
    conn.commit()

    indexed = conn.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()[0]
    tokenizer_after = conn.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'knowledge_fts'"
    ).fetchone()[0]
    conn.close()

    print(f"knowledge_fts nachher: {tokenizer_after}")
    print(f"neu indiziert: {indexed} Zeilen (erwartet {node_count})")
    if indexed != node_count:
        print("ACHTUNG: Zeilenzahl weicht ab -- pruefen!")


if __name__ == "__main__":
    main()
