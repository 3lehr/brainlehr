#!/usr/bin/env python3
"""
lesson_recorder.py — CLI für das automatische Fehler-Lern-System.

Erstellt: 2026-03-25T17:30:00+01:00
Zweck: Erfasst Fehler/Lessons, erkennt Muster (n≥3 → Regel-Generierung),
       exportiert Regeln in .instructions.md Dateien.

Usage:
    python3 lesson_recorder.py record --type error --desc "..." --cause "..." --fix "..." --prevent "..." --projects begod,aka
    python3 lesson_recorder.py query [--type error] [--project begod] [--status active]
    python3 lesson_recorder.py stats
    python3 lesson_recorder.py auto-rules [--dry-run]
    python3 lesson_recorder.py bump <lesson_id>  # Inkrementiert occurrence-Zähler
"""

import argparse
import json
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "knowledge.db"
CET = timezone(timedelta(hours=1))

RULE_THRESHOLD = 3  # Minimum occurrences to auto-generate a rule

PROJECTS = {
    "begod": Path("/Volumes/daten/Begod2026/hub"),
    "aka": Path("/Volumes/daten/AKA2026"),
    "bebetter": Path("/Volumes/daten/BEBETTER"),
}


def now_iso() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S+01:00")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─── record ──────────────────────────────────────────────────────────────

def cmd_record(args):
    conn = get_db()
    lesson_id = str(uuid.uuid4())[:12]
    projects_json = json.dumps(args.projects.split(",") if args.projects else ["shared"])

    # Check for similar existing lessons (simple keyword match)
    similar = find_similar(conn, args.desc)
    if similar:
        print(f"⚠  Ähnliches Lesson gefunden: [{similar['id']}] {similar['description'][:80]}")
        print(f"   Occurrences: {similar['occurrences']} → bump statt neu? (lesson_recorder.py bump {similar['id']})")

    conn.execute("""
        INSERT INTO lessons_learned (id, type, severity, description, root_cause, resolution, prevention, projects, status, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
    """, (lesson_id, args.type, args.severity, args.desc, args.cause, args.fix, args.prevent, projects_json, now_iso(), now_iso()))
    conn.commit()

    print(f"✓ Lesson [{lesson_id}] erfasst: {args.type}/{args.severity}")
    print(f"  Beschreibung: {args.desc[:100]}")

    # Auto-escalation check
    check_escalation(conn)
    conn.close()


def find_similar(conn: sqlite3.Connection, desc: str) -> dict | None:
    """Sucht nach ähnlichen bestehenden Lessons basierend auf Keywords."""
    words = set(re.findall(r'\w{4,}', desc.lower()))
    if not words:
        return None
    rows = conn.execute("SELECT * FROM lessons_learned WHERE status = 'active'").fetchall()
    best, best_score = None, 0
    for row in rows:
        row_words = set(re.findall(r'\w{4,}', row["description"].lower()))
        overlap = len(words & row_words)
        if overlap > best_score and overlap >= 2:
            best, best_score = dict(row), overlap
    return best


# ─── bump ────────────────────────────────────────────────────────────────

def cmd_bump(args):
    conn = get_db()
    row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (args.lesson_id,)).fetchone()
    if not row:
        print(f"✗ Lesson [{args.lesson_id}] nicht gefunden.")
        sys.exit(1)

    new_count = row["occurrences"] + 1
    conn.execute("""
        UPDATE lessons_learned SET occurrences = ?, last_seen = ? WHERE id = ?
    """, (new_count, now_iso(), args.lesson_id))
    conn.commit()

    print(f"✓ Lesson [{args.lesson_id}] Occurrences: {row['occurrences']} → {new_count}")
    if new_count >= RULE_THRESHOLD and not row["auto_rule_generated"]:
        print(f"  ⚡ Erreicht Threshold ({RULE_THRESHOLD}x) — auto-rule Kandidat!")

    check_escalation(conn)
    conn.close()


# ─── query ───────────────────────────────────────────────────────────────

def cmd_query(args):
    conn = get_db()
    conditions = []
    params = []

    if args.type:
        conditions.append("type = ?")
        params.append(args.type)
    if args.project:
        conditions.append("projects LIKE ?")
        params.append(f'%"{args.project}"%')
    if args.status:
        conditions.append("status = ?")
        params.append(args.status)

    where = " AND ".join(conditions) if conditions else "1=1"
    rows = conn.execute(f"SELECT * FROM lessons_learned WHERE {where} ORDER BY last_seen DESC LIMIT 20", params).fetchall()

    if not rows:
        print("Keine Lessons gefunden.")
        return

    for row in rows:
        print(f"[{row['id']}] {row['type']}/{row['severity']} | x{row['occurrences']} | {row['status']}")
        print(f"  {row['description'][:120]}")
        if row["resolution"]:
            print(f"  Fix: {row['resolution'][:100]}")
        print()

    conn.close()


# ─── stats ───────────────────────────────────────────────────────────────

def cmd_stats(args):
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) as c FROM lessons_learned").fetchone()["c"]
    by_type = conn.execute("SELECT type, COUNT(*) as c FROM lessons_learned GROUP BY type ORDER BY c DESC").fetchall()
    by_status = conn.execute("SELECT status, COUNT(*) as c FROM lessons_learned GROUP BY status").fetchall()
    rule_candidates = conn.execute(
        "SELECT COUNT(*) as c FROM lessons_learned WHERE occurrences >= ? AND auto_rule_generated = 0",
        (RULE_THRESHOLD,)
    ).fetchone()["c"]
    top_recurring = conn.execute(
        "SELECT id, type, description, occurrences FROM lessons_learned ORDER BY occurrences DESC LIMIT 5"
    ).fetchall()

    print(f"=== Lesson Stats ===")
    print(f"Total: {total}")
    print(f"\nNach Typ:  " + "  ".join(f"{r['type']}={r['c']}" for r in by_type))
    print(f"Nach Status:  " + "  ".join(f"{r['status']}={r['c']}" for r in by_status))
    print(f"\nRule-Kandidaten (≥{RULE_THRESHOLD}x, nicht generiert): {rule_candidates}")

    if top_recurring:
        print(f"\nTop-Recurring:")
        for r in top_recurring:
            print(f"  [{r['id']}] x{r['occurrences']} {r['type']}: {r['description'][:80]}")

    conn.close()


# ─── auto-rules ──────────────────────────────────────────────────────────

def cmd_auto_rules(args):
    conn = get_db()
    candidates = conn.execute("""
        SELECT * FROM lessons_learned
        WHERE occurrences >= ? AND auto_rule_generated = 0 AND status = 'active'
        ORDER BY occurrences DESC
    """, (RULE_THRESHOLD,)).fetchall()

    if not candidates:
        print("Keine Rule-Kandidaten (alle Lessons unter Threshold oder bereits generiert).")
        return

    print(f"=== {len(candidates)} Rule-Kandidaten ===\n")
    rules = []

    for c in candidates:
        rule_text = generate_rule(c)
        rules.append((c, rule_text))
        print(f"[{c['id']}] x{c['occurrences']} {c['type']}: {c['description'][:80]}")
        print(f"  → Regel: {rule_text[:120]}")
        print()

    if args.dry_run:
        print("(Dry-run — keine Dateien geschrieben)")
        return

    # Write rules to project-specific instruction files
    written = write_rules_to_instructions(rules)
    for lesson, _ in rules:
        conn.execute("UPDATE lessons_learned SET auto_rule_generated = 1, status = 'escalated_to_rule' WHERE id = ?",
                      (lesson["id"],))
    conn.commit()
    print(f"\n✓ {written} Regeln in .instructions.md Dateien geschrieben.")
    conn.close()


def generate_rule(lesson: sqlite3.Row) -> str:
    """Generiert eine Regel-Formulierung aus einem Lesson."""
    parts = []
    if lesson["prevention"]:
        parts.append(lesson["prevention"])
    elif lesson["resolution"]:
        parts.append(f"Bei: {lesson['description'][:60]} → Fix: {lesson['resolution'][:80]}")
    else:
        parts.append(f"VERMEIDEN: {lesson['description'][:120]}")
    return " ".join(parts)


def write_rules_to_instructions(rules: list[tuple]) -> int:
    """Schreibt generierte Regeln in lessons-learned.instructions.md pro Projekt."""
    by_project: dict[str, list[str]] = {}
    for lesson, rule_text in rules:
        projects = json.loads(lesson["projects"]) if lesson["projects"] else ["shared"]
        for proj in projects:
            by_project.setdefault(proj, []).append(rule_text)

    written = 0
    for proj_key, proj_rules in by_project.items():
        proj_path = PROJECTS.get(proj_key)
        if not proj_path:
            # 'shared' → write to all projects
            if proj_key == "shared":
                for p in PROJECTS.values():
                    written += _write_instructions_file(p, proj_rules)
                continue
            continue
        written += _write_instructions_file(proj_path, proj_rules)

    return written


def _write_instructions_file(proj_path: Path, rules: list[str]) -> int:
    """Schreibt/aktualisiert eine lessons-learned.instructions.md Datei."""
    instructions_dir = proj_path / ".github" / "instructions"
    instructions_dir.mkdir(parents=True, exist_ok=True)
    filepath = instructions_dir / "lessons-learned.instructions.md"

    header = f"""---
applyTo: "**"
---
# Auto-Generated Lessons Learned
# Generiert: {now_iso()}
# Quelle: lesson_recorder.py auto-rules (Threshold: {RULE_THRESHOLD}x)

"""
    existing_rules = []
    if filepath.exists():
        content = filepath.read_text(encoding="utf-8")
        # Extract existing rules (lines starting with "- ")
        existing_rules = [line for line in content.split("\n") if line.startswith("- ")]

    all_rules = existing_rules + [f"- {r}" for r in rules]
    filepath.write_text(header + "\n".join(all_rules) + "\n", encoding="utf-8")
    return 1


# ─── Check Escalation ────────────────────────────────────────────────────

def check_escalation(conn: sqlite3.Connection):
    """Prüft ob Lessons den Threshold erreichen und informiert."""
    candidates = conn.execute("""
        SELECT id, type, description, occurrences FROM lessons_learned
        WHERE occurrences >= ? AND auto_rule_generated = 0 AND status = 'active'
    """, (RULE_THRESHOLD,)).fetchall()

    if candidates:
        print(f"\n⚡ {len(candidates)} Lesson(s) haben ≥{RULE_THRESHOLD} Occurrences → Rule-Kandidaten!")
        print(f"   Führe 'lesson_recorder.py auto-rules' aus, um Regeln zu generieren.")


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fehler-Lern-System: Lessons erfassen, auswerten, Regeln generieren")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # record
    p_record = subparsers.add_parser("record", help="Neue Lesson erfassen")
    p_record.add_argument("--type", required=True, choices=["error", "insight", "pattern", "antipattern"])
    p_record.add_argument("--desc", required=True, help="Beschreibung")
    p_record.add_argument("--cause", help="Root Cause")
    p_record.add_argument("--fix", help="Resolution/Fix")
    p_record.add_argument("--prevent", help="Prävention")
    p_record.add_argument("--severity", default="medium", choices=["critical", "high", "medium", "low"])
    p_record.add_argument("--projects", default="shared", help="Projekte (kommagetrennt)")

    # bump
    p_bump = subparsers.add_parser("bump", help="Occurrence-Zähler erhöhen")
    p_bump.add_argument("lesson_id", help="ID der Lesson")

    # query
    p_query = subparsers.add_parser("query", help="Lessons abfragen")
    p_query.add_argument("--type", choices=["error", "insight", "pattern", "antipattern"])
    p_query.add_argument("--project", help="Projekt-Filter")
    p_query.add_argument("--status", choices=["active", "resolved", "escalated_to_rule"])

    # stats
    subparsers.add_parser("stats", help="Übersichts-Statistiken")

    # auto-rules
    p_rules = subparsers.add_parser("auto-rules", help="Automatische Regeln aus häufigen Lessons generieren")
    p_rules.add_argument("--dry-run", action="store_true", help="Nur anzeigen, nicht schreiben")

    args = parser.parse_args()

    cmds = {
        "record": cmd_record,
        "bump": cmd_bump,
        "query": cmd_query,
        "stats": cmd_stats,
        "auto-rules": cmd_auto_rules,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
