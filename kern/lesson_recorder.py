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
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(_w))
import knowledge_mcp_server as kms  # noqa: E402  -- liefert kalibrierte Aehnlichkeitserkennung
import geltungsbereich  # noqa: E402  -- exakter Projektfilter (sql_projects_exact), statt LIKE

DB_PATH = _w / "brainlehr.db"
BERLIN = ZoneInfo("Europe/Berlin")

RULE_THRESHOLD = 3  # Minimum occurrences to auto-generate a rule

# Abgeleitet statt ausgeschrieben (2026-08-10): absolute Pfade EINES Rechners
# machen ein weitergebbares Repo unbrauchbar, ohne dass etwas fehlschlaegt --
# es wird nur nichts gefunden. ort.VERBUND sucht die Verbundwurzel am
# Merkmal; die Nachbarprojekte liegen daneben.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "haken"))
import ort  # noqa: E402
import speicher  # noqa: E402 -- nur verbinde_bestand() fuer get_db()
import zeitmarke  # Aufgabe 111: die eine Quelle fuer Zeitstempel

PROJECTS = {
    "begod": ort.VERBUND / "hub",
    "aka": ort.VERBUND.parent / "AKA2026",
    "bebetter": ort.VERBUND.parent / "BEBETTER",
}


def now_iso() -> str:
    return zeitmarke.jetzt()  # Aufgabe 111: UTC mit Z, eine Quelle


def get_db() -> sqlite3.Connection:
    # verbinde_bestand statt sqlite3.connect: erfasst Lehren in einem
    # bestehenden Bestand, legt keinen an -- siehe
    # kern/speicher.py::verbinde_bestand.
    conn = speicher.verbinde_bestand(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─── record ──────────────────────────────────────────────────────────────

def cmd_record(args):
    conn = get_db()

    # same_as: expliziter Vorgaengerbezug -- erhoeht dessen occurrences, haengt
    # diesen Text als Wiederholungs-Absatz an, legt KEINEN neuen Eintrag an.
    # Unbekanntes same_as ist ein Fehler, kein stiller Fallback (wie kms.lesson_record).
    if args.same_as:
        target = conn.execute(
            "SELECT id, occurrences, description FROM lessons_learned WHERE id = ?", (args.same_as,)
        ).fetchone()
        if not target:
            print(f"✗ same_as verweist auf keine bestehende Lesson: {args.same_as}")
            conn.close()
            sys.exit(1)
        merged = kms._append_repetition(target["description"], args.desc, now_iso())
        result = kms._bump_lesson(conn, target["id"], None, args.desc, new_description=merged)
        print(f"✓ Lesson [{result['id']}] Occurrences: {target['occurrences']} → {result['occurrences']} (Wiederholung von {args.same_as})")
        if result["escalated"]:
            print(f"  ⚡ {result['message']}")
        conn.close()
        return

    # Exakte Dublette (gleicher Typ + byte-identische Beschreibung) -- bisheriges
    # Verhalten fuer diesen Fall bleibt: bump statt neuer Zeile.
    existing = conn.execute(
        "SELECT id, occurrences FROM lessons_learned WHERE type = ? AND description = ? AND status = 'active'",
        (args.type, args.desc)
    ).fetchone()
    if existing:
        result = kms._bump_lesson(conn, existing["id"], None, args.desc)
        print(f"✓ Lesson [{result['id']}] Occurrences: {existing['occurrences']} → {result['occurrences']} (exakte Dublette)")
        if result["escalated"]:
            print(f"  ⚡ {result['message']}")
        conn.close()
        return

    lesson_id = str(uuid.uuid4())[:12]
    projects_json = json.dumps(args.projects.split(",") if args.projects else ["shared"])

    # Aehnlichkeits-Hinweis (Wortmengen-Jaccard, Schwelle kms.SIMILARITY_THRESHOLD,
    # kalibriert gegen den echten Lessons-Bestand) -- nur Hinweis, kein Auto-Merge.
    similar = kms._find_similar_lesson(conn, args.type, args.desc)
    if similar:
        print(f"⚠  Ähnliches Lesson gefunden: [{similar['id']}] {similar['description_first_line'][:80]} (Score {similar['score']})")
        print(f"   Occurrences: {similar['occurrences']} → Wiederholung? lesson_recorder.py record ... --same-as {similar['id']}")

    # Beinahefehler: dieselbe Pruefung wie im Werkzeugpfad, damit der CLI-Weg
    # die Kennzeichnung ohne 'woran' nicht durchlaesst. Der Trigger in der
    # Datenbank haelt es ohnehin -- diese Meldung ist nur die sprechendere.
    # getattr statt args.beinahe: cmd_record wird auch aus Tests und Skripten
    # mit einem selbstgebauten Namensraum aufgerufen, der die neuen Felder
    # nicht kennt -- ohne Vorgabe bricht dort der bestehende Weg.
    beinahe = bool(getattr(args, "beinahe", False))
    bemerkt = getattr(args, "bemerkt", "") or ""
    beinahe_fehler = kms._validate_beinahefehler(beinahe, bemerkt)
    if beinahe_fehler:
        print(f"✗ {beinahe_fehler}")
        conn.close()
        sys.exit(1)

    conn.execute("""
        INSERT INTO lessons_learned (id, type, severity, description, root_cause, resolution, prevention, projects, status, first_seen, last_seen, beinahefehler, bemerkt_woran)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
    """, (lesson_id, args.type, args.severity, args.desc, args.cause, args.fix, args.prevent, projects_json, now_iso(), now_iso(),
          1 if beinahe else 0, bemerkt.strip() if beinahe else None))
    conn.commit()

    print(f"✓ Lesson [{lesson_id}] erfasst: {args.type}/{args.severity}")
    print(f"  Beschreibung: {args.desc[:100]}")

    conn.close()


# ─── bump ────────────────────────────────────────────────────────────────

def cmd_bump(args):
    conn = get_db()
    row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (args.lesson_id,)).fetchone()
    if not row:
        print(f"✗ Lesson [{args.lesson_id}] nicht gefunden.")
        sys.exit(1)

    result = kms._bump_lesson(conn, args.lesson_id, None, "manual bump")
    print(f"✓ Lesson [{args.lesson_id}] Occurrences: {row['occurrences']} → {result['occurrences']}")
    if result["escalated"]:
        print(f"  ⚡ {result['message']}")

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
        conditions.append(geltungsbereich.sql_projects_exact())
        params.append(args.project)
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
    # status='escalated_to_rule' ist der Vorschlags-Marker, den kms._bump_lesson beim
    # Erreichen von RULE_THRESHOLD setzt (same_as- und Exact-Dubletten-Pfad in cmd_record/cmd_bump).
    candidates = conn.execute("""
        SELECT * FROM lessons_learned
        WHERE occurrences >= ? AND auto_rule_generated = 0 AND status = 'escalated_to_rule'
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
    p_record.add_argument("--same-as", dest="same_as", default="", help="ID einer bestehenden Lesson, falls dies eine Wiederholung ist")
    p_record.add_argument("--beinahe", action="store_true",
                          help="Beinahefehler: bemerkt und behoben, BEVOR Schaden entstand (verlangt --bemerkt)")
    p_record.add_argument("--bemerkt", dest="bemerkt", default="",
                          choices=sorted(kms.ALLOWED_BEMERKT_WORAN) + [""],
                          help="woran der Beinahefehler bemerkt wurde -- Pflicht bei --beinahe")

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
