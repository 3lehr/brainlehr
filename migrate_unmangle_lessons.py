#!/usr/bin/env python3
"""
migrate_unmangle_lessons.py — Einmal-Migration: repariert Lessons mit verrutschten
Parametergrenzen (Feld-Tags im falschen Textfeld gelandet) und entfernt den
Muell-Eintrag L-f4f48f.

Erstellt: 2026-07-29T09:30:00+01:00
Usage: python3 migrate_unmangle_lessons.py            (fuehrt Reparatur aus)
       python3 migrate_unmangle_lessons.py --dry-run   (nur Bericht, keine Schreibaktion)

Ablauf:
  1. Backup der DB (Zeitstempel im Dateinamen) — ohne Backup kein Weitermachen.
  2. Alle Zeilen scannen, deren Textfelder Feld-Tags enthalten (generisch, nicht nur
     die vorab bekannten IDs).
  3. unmangle_lesson_fields() anwenden, Spalten neu schreiben.
  4. L-f4f48f loeschen (Muell-Eintrag "Zeitstempel fuer STAND.md").
  5. Bericht: je Eintrag ID + Feldlaengen vorher/nachher.
"""

import argparse
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from knowledge_mcp_server import DB_PATH, unmangle_lesson_fields, _FIELD_TAG, now_iso  # noqa: E402

JUNK_ID = "L-f4f48f"
TEXT_COLS = ("description", "root_cause", "resolution", "prevention", "severity", "node_path")


def backup_db() -> Path:
    ts = datetime.now(timezone(timedelta(hours=1))).strftime("%Y%m%dT%H%M%S")
    backup_path = DB_PATH.with_name(f"knowledge.db.bak-{ts}")
    shutil.copy2(DB_PATH, backup_path)
    if not backup_path.exists() or backup_path.stat().st_size == 0:
        raise SystemExit(f"Backup fehlgeschlagen: {backup_path}")
    print(f"Backup angelegt: {backup_path} ({backup_path.stat().st_size} bytes)")
    return backup_path


def find_mangled_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    rows = conn.execute("SELECT * FROM lessons_learned").fetchall()
    mangled = []
    for row in rows:
        for col in TEXT_COLS:
            val = row[col]
            if isinstance(val, str) and _FIELD_TAG.search(val):
                mangled.append(row)
                break
    return mangled


def repair_row(conn: sqlite3.Connection, row: sqlite3.Row, dry_run: bool) -> dict:
    before = {col: (row[col] or "") for col in TEXT_COLS}
    before["projects"] = row["projects"] or "[]"

    fields = {
        "type": row["type"],
        "description": row["description"] or "",
        "root_cause": row["root_cause"] or "",
        "resolution": row["resolution"] or "",
        "prevention": row["prevention"] or "",
        "severity": row["severity"] or "",
        "node_path": row["node_path"] or "",
        "projects": json.loads(row["projects"]) if row["projects"] else [],
    }
    fixed = unmangle_lesson_fields(fields)

    leftover = [c for c in TEXT_COLS if isinstance(fixed.get(c), str) and _FIELD_TAG.search(fixed[c])]

    if not dry_run:
        conn.execute(
            """UPDATE lessons_learned
               SET description = ?, root_cause = ?, resolution = ?, prevention = ?,
                   severity = ?, node_path = ?, projects = ?, last_seen = ?
               WHERE id = ?""",
            (fixed["description"], fixed["root_cause"], fixed["resolution"], fixed["prevention"],
             fixed["severity"] or row["severity"], fixed["node_path"] or None,
             json.dumps(fixed["projects"] or []), now_iso(), row["id"])
        )

    after = {col: (fixed.get(col) or "") for col in TEXT_COLS}
    after["projects"] = json.dumps(fixed["projects"] or [])

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

    junk = conn.execute("SELECT id, description FROM lessons_learned WHERE id = ?", (JUNK_ID,)).fetchone()
    junk_deleted = False
    if junk:
        print(f"Muell-Eintrag gefunden: {JUNK_ID} description={junk['description']!r}")
        if not args.dry_run:
            conn.execute("DELETE FROM lessons_learned WHERE id = ?", (JUNK_ID,))
            junk_deleted = True
    else:
        print(f"Muell-Eintrag {JUNK_ID} nicht gefunden (evtl. bereits entfernt).")

    if not args.dry_run:
        conn.commit()
    conn.close()

    print("\n=== Bericht: Feldlaengen vorher -> nachher ===")
    any_leftover = False
    for r in reports:
        print(f"\n{r['id']}:")
        for col in TEXT_COLS + ("projects",):
            b = r["before_len"].get(col, 0)
            a = r["after_len"].get(col, 0)
            marker = "  <-- geaendert" if b != a else ""
            print(f"  {col:12s} vorher={b:5d} nachher={a:5d}{marker}")
        if r["leftover_tags"]:
            any_leftover = True
            print(f"  !! VERBLEIBENDE TAGS in: {r['leftover_tags']}")

    print(f"\n{'(dry-run, nichts geschrieben) ' if args.dry_run else ''}"
          f"{len(reports)} Eintraege repariert, "
          f"Muell-Eintrag {JUNK_ID} {'geloescht' if junk_deleted else 'nicht geloescht'}.")
    if any_leftover:
        print("ACHTUNG: mindestens ein Eintrag hat nach der Reparatur noch Tags im Text — pruefen!")


if __name__ == "__main__":
    main()
