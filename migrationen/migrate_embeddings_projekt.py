#!/usr/bin/env python3
"""
migrate_embeddings_projekt.py — Einmal-Migration: knowledge_embeddings auf die
Form aus schema.sql bringen (project_id-Spalte, PRIMARY KEY (kind, ref_id,
project_id)). Nachtrag zur FTS-Migration migrate_fts_projekt.py -- die hatte
nur den FTS-Index angefasst, nicht die zweite Tabelle mit Bereichsbezug.

SQLite kann weder eine Spalte in einen bestehenden Primaerschluessel aufnehmen
noch einen Primaerschluessel aendern -- daher neue Tabelle, Zeilen umkopieren
(dabei project_id herleiten), alte Tabelle droppen, neue umbenennen. Gleiches
Sicherungsmuster wie migrate_fts_projekt.py.

Bereichsherkunft beim Umkopieren:
  - node-Zeilen: project_id = knowledge_nodes.project_id (einwertig).
  - lesson-Zeilen: resolve_lesson_projects() aus build_embeddings.py -- NICHT
    zum zweiten Mal geschrieben, importiert. Eine Lehre mit N Bereichen ergibt
    N Zeilen mit demselben Vektor (kein neues Embedding, nur kopiert).
  - Ref-IDs ohne (mehr) passenden Node/Lesson (verwaist) fallen auf 'shared'
    zurueck, statt den Vektor zu verlieren.

Kein Vektor wird neu berechnet -- reines Umkopieren bestehender BLOBs.

Idempotent: liegt project_id schon in knowledge_embeddings, wird nichts
getan (erkannt an PRAGMA table_info).

Erstellt: 2026-08-05T00:00:00+01:00
Usage: python3 migrate_embeddings_projekt.py            (fuehrt Migration aus)
       python3 migrate_embeddings_projekt.py --dry-run   (nur pruefen, nichts schreiben)
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
sys.path.insert(0, str(Path(__file__).parent / "kern"))
from knowledge_mcp_server import DB_PATH  # noqa: E402
from build_embeddings import resolve_lesson_projects  # noqa: E402

NEW_TABLE_SQL = """
CREATE TABLE knowledge_embeddings_new (
    kind TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    project_id TEXT NOT NULL DEFAULT 'shared',
    model TEXT NOT NULL,
    vector BLOB NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (kind, ref_id, project_id)
);
"""


def already_migrated(conn: sqlite3.Connection) -> bool:
    cols = [r[1] for r in conn.execute("PRAGMA table_info(knowledge_embeddings)").fetchall()]
    return "project_id" in cols


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
    row_count_before = conn.execute("SELECT COUNT(*) FROM knowledge_embeddings").fetchone()[0]
    pairs_before = conn.execute(
        "SELECT COUNT(DISTINCT kind || '|' || ref_id) FROM knowledge_embeddings"
    ).fetchone()[0]
    print(f"knowledge_embeddings vorher: {row_count_before} Zeilen, "
          f"{pairs_before} verschiedene (kind, ref_id)-Paare")
    print("PRAGMA table_info vorher: "
          + str(conn.execute("PRAGMA table_info(knowledge_embeddings)").fetchall()))

    if already_migrated(conn):
        print("project_id bereits vorhanden -- nichts zu tun (idempotent).")
        conn.close()
        return

    if args.dry_run:
        print("--dry-run: kein Backup, keine Schreibaktion.")
        conn.close()
        return

    backup_path = backup_db()

    node_projects = dict(conn.execute("SELECT id, project_id FROM knowledge_nodes").fetchall())
    lesson_projects_raw = dict(conn.execute("SELECT id, projects FROM lessons_learned").fetchall())

    conn.execute("DROP TABLE IF EXISTS knowledge_embeddings_new")
    conn.execute(NEW_TABLE_SQL)

    rows_written = 0
    orphans = 0
    for kind, ref_id, model, vector, updated_at in conn.execute(
        "SELECT kind, ref_id, model, vector, updated_at FROM knowledge_embeddings"
    ):
        if kind == "node":
            projects = [node_projects.get(ref_id, "shared")]
            if ref_id not in node_projects:
                orphans += 1
        elif kind == "lesson":
            if ref_id in lesson_projects_raw:
                projects = resolve_lesson_projects(lesson_projects_raw[ref_id])
            else:
                projects = ["shared"]
                orphans += 1
        else:
            projects = ["shared"]
            orphans += 1

        for proj in projects:
            conn.execute(
                "INSERT OR REPLACE INTO knowledge_embeddings_new "
                "(kind, ref_id, project_id, model, vector, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (kind, ref_id, proj, model, vector, updated_at),
            )
            rows_written += 1

    conn.execute("DROP TABLE knowledge_embeddings")
    conn.execute("ALTER TABLE knowledge_embeddings_new RENAME TO knowledge_embeddings")
    conn.commit()

    row_count_after = conn.execute("SELECT COUNT(*) FROM knowledge_embeddings").fetchone()[0]
    pairs_after = conn.execute(
        "SELECT COUNT(DISTINCT kind || '|' || ref_id) FROM knowledge_embeddings"
    ).fetchone()[0]
    table_info_after = conn.execute("PRAGMA table_info(knowledge_embeddings)").fetchall()
    conn.close()

    print(f"Sicherung: {backup_path}")
    print(f"Zeilen umkopiert: {rows_written} (davon {orphans} verwaist -> Bucket 'shared')")
    print(f"knowledge_embeddings nachher: {row_count_after} Zeilen, "
          f"{pairs_after} verschiedene (kind, ref_id)-Paare")
    print("PRAGMA table_info nachher: " + str(table_info_after))
    if pairs_after != pairs_before:
        print(f"ACHTUNG: (kind, ref_id)-Paare weichen ab -- vorher {pairs_before}, "
              f"nachher {pairs_after}!")


if __name__ == "__main__":
    main()
