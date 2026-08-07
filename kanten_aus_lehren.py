#!/usr/bin/env python3
"""
Extract file paths from lessons and create knowledge graph edges.

Reads lessons_learned.description/root_cause/resolution/prevention for file paths,
validates them against the real filesystem, and inserts knowledge_relations edges.

Dry-run is default. Use --write to create edges in a database copy.
Use --delete to remove edges created by this script.
"""

import sqlite3
import re
import os
import sys
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Set, Tuple, List

# Config
DB_PATH = Path("/Volumes/daten/Begod2026/hub/shared-knowledge/knowledge.db")
REPO_ROOT = Path("/Volumes/daten/Begod2026")
RELATION_TYPE = "lesson_mentions_file"  # Distinguishes edges created by this script

# Regex patterns to find file paths
FILE_PATTERNS = [
    r'\b([a-zA-Z_][a-zA-Z0-9_]*(?:/[a-zA-Z_\-.][a-zA-Z0-9_\-\.]*)+\.(?:py|dart|ts|tsx|js|jsx|java|kt|swift|m|c|cpp|h|sh|json|yaml|yml|xml|md))\b',
    r"'([a-zA-Z_][a-zA-Z0-9_]*(?:/[a-zA-Z_\-.][a-zA-Z0-9_\-\.]*)+\.(?:py|dart|ts|tsx|js|jsx|java|kt|swift|m|c|cpp|h|sh|json|yaml|yml|xml|md))'",
    r'"([a-zA-Z_][a-zA-Z0-9_]*(?:/[a-zA-Z_\-.][a-zA-Z0-9_\-\.]*)+\.(?:py|dart|ts|tsx|js|jsx|java|kt|swift|m|c|cpp|h|sh|json|yaml|yml|xml|md))"',
    r'(?:file|path|path_pattern|function|method|script|class|tool):?\s*["`]?([a-zA-Z_][a-zA-Z0-9_]*(?:/[a-zA-Z_\-.][a-zA-Z0-9_\-\.]*)+\.(?:py|dart|ts|tsx|js|jsx|java|kt|swift|m|c|cpp|h|sh|json|yaml|yml|xml|md))["`]?',
]

@dataclass
class FileReference:
    path: str
    exists: bool
    lesson_id: str
    field: str  # description, root_cause, resolution, prevention

def extract_file_refs(text: str, lesson_id: str, field: str) -> List[FileReference]:
    """Extract file path references from text."""
    if not text:
        return []

    refs = []
    seen = set()

    for pattern in FILE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            path = match.group(1)
            if path not in seen:
                seen.add(path)
                # Validate against filesystem
                full_path = REPO_ROOT / path
                exists = full_path.exists() and full_path.is_file()
                refs.append(FileReference(
                    path=path,
                    exists=exists,
                    lesson_id=lesson_id,
                    field=field
                ))

    return refs

def connect_db(path: Path) -> sqlite3.Connection:
    """Connect to database."""
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn

def fetch_lessons(conn: sqlite3.Connection) -> List[dict]:
    """Fetch all lessons with text fields."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, description, root_cause, resolution, prevention
        FROM lessons_learned
        ORDER BY id
    """)
    return [dict(row) for row in cursor.fetchall()]

def collect_all_refs(conn: sqlite3.Connection) -> Tuple[List[FileReference], int]:
    """Scan all lessons for file references."""
    lessons = fetch_lessons(conn)
    refs = []

    for lesson in lessons:
        for field in ['description', 'root_cause', 'resolution', 'prevention']:
            if lesson[field]:
                refs.extend(extract_file_refs(lesson[field], lesson['id'], field))

    return refs, len(lessons)

def dry_run(refs: List[FileReference], lesson_count: int):
    """Report what would be created without writing."""
    existing = [r for r in refs if r.exists]
    missing = [r for r in refs if not r.exists]

    print(f"Dry run: {lesson_count} lessons scanned")
    print(f"  Found {len(refs)} file references")
    print(f"  {len(existing)} exist on filesystem")
    print(f"  {len(missing)} do NOT exist (stale paths)")
    print()

    if existing:
        print(f"Ready to create {len(existing)} edges:")
        for r in sorted(existing, key=lambda x: (x.lesson_id, x.path))[:10]:
            print(f"  lesson {r.lesson_id[:8]} → {r.path}")
        if len(existing) > 10:
            print(f"  ... and {len(existing) - 10} more")
        print()

    if missing:
        print(f"Stale paths (not created):")
        for r in sorted(missing, key=lambda x: (x.lesson_id, x.path))[:15]:
            print(f"  lesson {r.lesson_id[:8]} | {r.path}")
        if len(missing) > 15:
            print(f"  ... and {len(missing) - 15} more")

    return len(existing), len(missing)

def edge_exists(conn: sqlite3.Connection, source_path: str, target_path: str) -> bool:
    """Check if edge already exists."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM knowledge_relations
        WHERE source_path = ? AND target_path = ? AND relation_type = ?
        LIMIT 1
    """, (source_path, target_path, RELATION_TYPE))
    return cursor.fetchone() is not None

def create_edges(conn: sqlite3.Connection, refs: List[FileReference]) -> Tuple[int, int]:
    """Create edges in database. Returns (created, skipped)."""
    created = 0
    skipped = 0
    cursor = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    # Group by lesson
    by_lesson = {}
    for ref in refs:
        if ref.exists:
            if ref.lesson_id not in by_lesson:
                by_lesson[ref.lesson_id] = []
            by_lesson[ref.lesson_id].append(ref)

    for lesson_id, refs_for_lesson in by_lesson.items():
        unique_paths = set(r.path for r in refs_for_lesson)

        for path in unique_paths:
            target_path = f"files/{path}"  # Namespace file paths

            if not edge_exists(conn, lesson_id, target_path):
                edge_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO knowledge_relations
                    (id, source_path, target_path, relation_type, confidence, weight,
                     evidence, source, creator, model, session, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    edge_id,
                    lesson_id,
                    target_path,
                    RELATION_TYPE,
                    0.9,  # confidence
                    1.0,  # weight
                    "Extracted from lesson text",
                    "kanten_aus_lehren.py",
                    "mechanik",
                    "haiku",
                    None,
                    now,
                    now
                ))
                created += 1
            else:
                skipped += 1

    conn.commit()
    return created, skipped

def verify_state(conn: sqlite3.Connection, before_count: int, after_count: int):
    """Verify node/lesson counts unchanged."""
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_nodes")
    nodes = cursor.fetchone()['cnt']

    cursor.execute("SELECT COUNT(*) as cnt FROM lessons_learned")
    lessons = cursor.fetchone()['cnt']

    print(f"Node count: {nodes} (expected 1975) {'✓' if nodes == 1975 else '✗ MISMATCH'}")
    print(f"Lesson count: {lessons} (expected 610) {'✓' if lessons == 610 else '✗ MISMATCH'}")
    return nodes == 1975 and lessons == 610

def delete_edges(conn: sqlite3.Connection) -> int:
    """Delete all edges created by this script. Returns count."""
    cursor = conn.cursor()
    cursor.execute(f"""
        DELETE FROM knowledge_relations
        WHERE relation_type = ?
    """, (RELATION_TYPE,))
    conn.commit()
    return cursor.rowcount

def main():
    if "--write" not in sys.argv and "--delete" not in sys.argv:
        # Dry run
        conn = connect_db(DB_PATH)
        refs, lesson_count = collect_all_refs(conn)
        conn.close()

        existing, missing = dry_run(refs, lesson_count)
        print(f"\nTo create edges, run: python {sys.argv[0]} --write")
        print(f"To delete edges, run: python {sys.argv[0]} --delete")
        return

    if "--delete" in sys.argv:
        print("Deleting edges created by this script...")
        conn = connect_db(DB_PATH)
        count = delete_edges(conn)
        conn.close()
        print(f"Deleted {count} edges.")
        return

    # Write mode: need a copy
    if "--write" in sys.argv:
        import shutil
        copy_path = DB_PATH.parent / "knowledge.db.copy"

        if copy_path.exists():
            print(f"Using existing copy: {copy_path}")
        else:
            print(f"Creating database copy: {copy_path}")
            shutil.copy2(DB_PATH, copy_path)

        conn = connect_db(copy_path)

        # Collect
        refs, lesson_count = collect_all_refs(conn)
        existing = [r for r in refs if r.exists]
        missing = [r for r in refs if not r.exists]

        print(f"Scanned {lesson_count} lessons")
        print(f"Found {len(existing)} existing file paths, {len(missing)} stale")

        # Before counts
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_relations")
        before_relations = cursor.fetchone()['cnt']

        # Create
        created, skipped = create_edges(conn, refs)

        # After counts
        cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_relations")
        after_relations = cursor.fetchone()['cnt']

        print(f"\nCreated {created} new edges (skipped {skipped} duplicates)")
        print(f"Relations before: {before_relations}, after: {after_relations}")

        # Verify
        if verify_state(conn, before_relations, after_relations):
            print("\n✓ Counts verified")
        else:
            print("\n✗ Count mismatch!")

        # Second run should create 0
        print("\nSecond run (should create 0)...")
        before = after_relations
        created2, skipped2 = create_edges(conn, refs)
        cursor.execute("SELECT COUNT(*) as cnt FROM knowledge_relations")
        after2 = cursor.fetchone()['cnt']

        if created2 == 0 and after2 == after_relations:
            print(f"✓ Second run created 0 edges (count stays {after2})")
        else:
            print(f"✗ Second run created {created2}! Count {before} → {after2}")

        conn.close()
        print(f"\nCopy database: {copy_path}")
        print("Review, then: cp knowledge.db.copy knowledge.db")

def run_self_test():
    """Quick sanity check on regex patterns."""
    test_strings = [
        ("Check apps/fahrtenbuch_legacy/CODEMAP.md for details", True, "apps/fahrtenbuch_legacy/CODEMAP.md"),
        ("file: `lib/features/trips/trip_screen.dart`", True, "lib/features/trips/trip_screen.dart"),
        ("See hub/CLAUDE.md (rules above)", True, "hub/CLAUDE.md"),
        ("tools/build_smoke.sh runs the test", True, "tools/build_smoke.sh"),
        ("No dots here, just words", False, None),
    ]

    for text, should_find, expected in test_strings:
        refs = extract_file_refs(text, "test-lesson", "description")
        if should_find:
            if refs and refs[0].path == expected:
                print(f"✓ {text[:40]}")
            else:
                print(f"✗ {text[:40]} - expected '{expected}', got {[r.path for r in refs]}")
        else:
            if not refs:
                print(f"✓ {text[:40]} (correctly found nothing)")
            else:
                print(f"✗ {text[:40]} - should find nothing, got {[r.path for r in refs]}")

if __name__ == "__main__":
    # Run self-test if --test requested
    if "--test" in sys.argv:
        print("Running self-tests...")
        run_self_test()
        sys.exit(0)

    main()
