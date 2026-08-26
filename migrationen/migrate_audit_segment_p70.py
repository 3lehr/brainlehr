#!/usr/bin/env python3
"""P70 local cutover anchor: classify, hash-only bind, never rewrite history."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]

import audit_segment  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402
from migrationen.migrate_auditkette_utc_p68 import FIELDS  # noqa: E402


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unresolved(current_db: Path, pre_utc_db: Path) -> dict[str, list[int]]:
    """Only classifies unexplained current breaks; returned IDs never leave this process."""
    current = sqlite3.connect(f"file:{current_db}?mode=ro", uri=True)
    current.row_factory = sqlite3.Row
    previous = sqlite3.connect(f"file:{pre_utc_db}?mode=ro", uri=True)
    previous.row_factory = sqlite3.Row
    try:
        old = {row["id"]: row for row in previous.execute("SELECT id," + ",".join(FIELDS) + " FROM access_log")}
        explained = {(row[0], row[1], row[2]) for row in current.execute(
            "SELECT access_log_id,vorher_hash,nachher_hash FROM chain_explanations")}
        found = {"model+timestamp": [], "missing_pre": []}
        prev = None
        for row in current.execute("SELECT id," + ",".join(FIELDS) + " FROM access_log WHERE ketten_hash IS NOT NULL ORDER BY id"):
            expected = kms.compute_ketten_hash(
                prev, node_path=row["node_path"], action=row["action"], query=row["query"],
                project_id=row["project_id"], actor=row["actor"], model=row["model"],
                session=row["session"], status=row["status"], timestamp=row["timestamp"],
                zeilen_hash=row["zeilen_hash"])
            prev = row["ketten_hash"]
            if expected == row["ketten_hash"] or (row["id"], row["ketten_hash"], expected) in explained:
                continue
            old_row = old.get(row["id"])
            if old_row is None:
                found["missing_pre"].append(row["id"])
            elif [field for field in FIELDS if row[field] != old_row[field]] == ["model", "timestamp"]:
                found["model+timestamp"].append(row["id"])
            else:
                raise RuntimeError(f"unproven legacy-chain class at access_log id={row['id']}")
        return found
    finally:
        previous.close(); current.close()


def sqlite_backup(source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    origin = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    copy = sqlite3.connect(target)
    try:
        origin.backup(copy)
    finally:
        copy.close(); origin.close()
    return file_hash(target)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""CREATE TABLE IF NOT EXISTS audit_segment_anchors (
        id TEXT PRIMARY KEY, previous_tail_id INTEGER NOT NULL, previous_tail_hash TEXT NOT NULL,
        unresolved_count INTEGER NOT NULL, unresolved_classes TEXT NOT NULL,
        unresolved_manifest_hash TEXT NOT NULL, db_profile_hash TEXT NOT NULL,
        created_at TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL,
        anchor_hash TEXT NOT NULL,
        UNIQUE(previous_tail_id, previous_tail_hash, unresolved_manifest_hash))""")
    conn.commit()


def apply(db: Path, pre_utc_db: Path, *, actor: str, reason: str) -> dict[str, object]:
    classes = unresolved(db, pre_utc_db)
    if {key: len(value) for key, value in classes.items()} != {"model+timestamp": 19, "missing_pre": 31}:
        raise RuntimeError("P70 requires exactly the independently proven 19+31 legacy classes")
    conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        outcome = audit_segment.create(conn, unresolved=classes, actor=actor, reason=reason)
        anchor = outcome["id"]
        validation = audit_segment.validate(conn, anchor)
        if not validation["current_segment_healthy"] or not validation["profile_matches"]:
            raise RuntimeError("new P70 anchor failed immediate validation")
        return {"outcome": outcome, "validation": validation,
                "manifest_sha256": hashlib.sha256(json.dumps(classes, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "pre_utc_sha256": file_hash(pre_utc_db)}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--pre-utc-db", type=Path, required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.db.resolve() == args.pre_utc_db.resolve():
        parser.error("--db and --pre-utc-db must differ")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = args.backup_dir / f"{args.db.stem}.p70-pre-{stamp}{args.db.suffix}"
    backup_sha256 = sqlite_backup(args.db, backup)
    report = apply(args.db, args.pre_utc_db, actor=args.actor, reason=args.reason)
    report.update({"backup": str(backup), "backup_sha256": backup_sha256, "db_sha256": file_hash(args.db)})
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
