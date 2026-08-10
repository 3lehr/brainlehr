#!/usr/bin/env python3
"""
migrate_unmangle_knowledge.py — Einmal-Migration: repariert knowledge_nodes mit
verrutschten Parametergrenzen (Feld-Tags im falschen Textfeld gelandet, meist
summary statt content/tags/source). Gegenstueck zu migrate_unmangle_lessons.py,
nur fuer knowledge_nodes statt lessons_learned.

Erstellt: 2026-08-01T07:30:00+01:00
Usage: python3 migrate_unmangle_knowledge.py            (fuehrt Reparatur aus)
       python3 migrate_unmangle_knowledge.py --dry-run   (nur Bericht, keine Schreibaktion)

Ablauf:
  1. Backup der DB (Zeitstempel im Dateinamen) — ohne Backup kein Weitermachen.
  2. Alle Zeilen scannen, deren Textfelder Feld-Tags enthalten (generisch, nicht
     nur die vorab bekannten IDs efa1f597/7781dea1/2a6098d1/c60b1b46/3a978881/
     5d899304).
  3. unmangle_knowledge_fields() anwenden, Spalten neu schreiben. Nur leere
     Zielfelder werden befuellt (siehe Docstring dort) -- kein Inhalt geht verloren.
  4. Bericht: je Eintrag ID + Feldlaengen vorher/nachher.
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
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from knowledge_mcp_server import (  # noqa: E402
    DB_PATH, KNOWLEDGE_TEXT_FIELDS, _KNOWLEDGE_FIELD_TAG, now_iso, unmangle_knowledge_fields,
)

TEXT_COLS = ("title", "summary", "content", "source")


def backup_db() -> Path:
    ts = datetime.now(timezone(timedelta(hours=1))).strftime("%Y%m%dT%H%M%S")
    backup_path = DB_PATH.with_name(f"{DB_PATH.name}.bak-{ts}")
    shutil.copy2(DB_PATH, backup_path)
    if not backup_path.exists() or backup_path.stat().st_size == 0:
        raise SystemExit(f"Backup fehlgeschlagen: {backup_path}")
    print(f"Backup angelegt: {backup_path} ({backup_path.stat().st_size} bytes)")
    return backup_path


def find_mangled_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    rows = conn.execute("SELECT * FROM knowledge_nodes").fetchall()
    mangled = []
    for row in rows:
        for col in TEXT_COLS:
            val = row[col]
            if isinstance(val, str) and _KNOWLEDGE_FIELD_TAG.search(val):
                mangled.append(row)
                break
    return mangled


def repair_row(conn: sqlite3.Connection, row: sqlite3.Row, dry_run: bool) -> dict:
    before = {col: (row[col] or "") for col in TEXT_COLS}
    before["tags"] = row["tags"] or "[]"

    fields = {
        "title": row["title"] or "",
        "summary": row["summary"] or "",
        "content": row["content"] or "",
        "source": row["source"] or "",
        "tags": json.loads(row["tags"]) if row["tags"] else [],
    }
    fixed = unmangle_knowledge_fields(fields)

    leftover = [c for c in TEXT_COLS if isinstance(fixed.get(c), str) and _KNOWLEDGE_FIELD_TAG.search(fixed[c])]

    if not dry_run:
        conn.execute(
            """UPDATE knowledge_nodes
               SET title = ?, summary = ?, content = ?, source = ?, tags = ?, updated_at = ?
               WHERE id = ?""",
            (fixed["title"] or row["title"], fixed["summary"], fixed["content"],
             fixed["source"], json.dumps(fixed["tags"] or []), now_iso(), row["id"])
        )

    after = {col: (fixed.get(col) or "") for col in TEXT_COLS}
    after["tags"] = json.dumps(fixed["tags"] or [])

    return {
        "id": row["id"],
        "before_len": {k: len(v) for k, v in before.items()},
        "after_len": {k: len(v) for k, v in after.items()},
        "leftover_tags": leftover,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Nur Bericht, keine Schreibaktion")
    args = parser.parse_args()

    print(f"Datenbank: {DB_PATH}")
    if not args.dry_run:
        backup_db()
    else:
        print("--dry-run: kein Backup, keine Schreibaktion.")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    mangled = find_mangled_rows(conn)
    print(f"\n{len(mangled)} verstuemmelte Eintraege gefunden.\n")

    reports = []
    for row in mangled:
        reports.append(repair_row(conn, row, args.dry_run))

    if not args.dry_run:
        conn.commit()
    conn.close()

    print("=== Bericht: Feldlaengen vorher -> nachher ===")
    any_leftover = False
    for r in reports:
        print(f"\n{r['id']}:")
        for col in TEXT_COLS + ("tags",):
            b = r["before_len"].get(col, 0)
            a = r["after_len"].get(col, 0)
            marker = "  <-- geaendert" if b != a else ""
            print(f"  {col:8s} vorher={b:5d} nachher={a:5d}{marker}")
        if r["leftover_tags"]:
            any_leftover = True
            print(f"  !! VERBLEIBENDE TAGS in: {r['leftover_tags']}")

    print(f"\n{'(dry-run, nichts geschrieben) ' if args.dry_run else ''}"
          f"{len(reports)} Eintraege repariert.")
    if any_leftover:
        print("ACHTUNG: mindestens ein Eintrag hat nach der Reparatur noch Tags im Text — pruefen!")


if __name__ == "__main__":
    main()
