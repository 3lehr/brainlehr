#!/usr/bin/env python3
"""P68: append-only explanations for UTC-only audit-chain rewrites.

The scanner reads a named pre-UTC SQLite backup and the current DB.  It emits
only row IDs and hashes; it never rewrites ``access_log`` or chain hashes.
``--apply`` requires a separate-process DB selection and uses the existing
MCP tool contract once per candidate, so an interrupted run safely resumes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import knowledge_mcp_server as kms  # noqa: E402

UTC_COMMIT = "ac4e1a0030322752bab18f72d19f9ff73a405749"
FIELDS = ("node_path", "action", "query", "project_id", "actor", "model", "session", "status", "timestamp", "zeilen_hash", "ketten_hash")


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _backup(db: Path, directory: Path) -> tuple[Path, str]:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{db.stem}.p68-pre-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}{db.suffix}"
    source = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close(); source.close()
    return target, _file_hash(target)


def candidates(current_db: Path, pre_utc_db: Path) -> list[dict[str, str | int]]:
    current = sqlite3.connect(f"file:{current_db}?mode=ro", uri=True)
    current.row_factory = sqlite3.Row
    previous = sqlite3.connect(f"file:{pre_utc_db}?mode=ro", uri=True)
    previous.row_factory = sqlite3.Row
    try:
        old = {row["id"]: row for row in previous.execute("SELECT id, " + ", ".join(FIELDS) + " FROM access_log")}
        explained = {
            (row[0], row[1], row[2]) for row in current.execute(
                "SELECT access_log_id, vorher_hash, nachher_hash FROM chain_explanations"
            )
        }
        previous_hash = None
        found: list[dict[str, str | int]] = []
        for row in current.execute("SELECT id, " + ", ".join(FIELDS) + " FROM access_log WHERE ketten_hash IS NOT NULL ORDER BY id"):
            expected = kms.compute_ketten_hash(
                previous_hash, node_path=row["node_path"], action=row["action"], query=row["query"],
                project_id=row["project_id"], actor=row["actor"], model=row["model"], session=row["session"],
                status=row["status"], timestamp=row["timestamp"], zeilen_hash=row["zeilen_hash"],
            )
            previous_hash = row["ketten_hash"]
            old_row = old.get(row["id"])
            if old_row is None or expected == row["ketten_hash"]:
                continue
            changed = [field for field in FIELDS if row[field] != old_row[field]]
            key = (row["id"], row["ketten_hash"], expected)
            if changed == ["timestamp"] and key not in explained:
                found.append({
                    "access_log_id": row["id"], "vorher_hash": row["ketten_hash"],
                    "nachher_hash": expected,
                    "old_timestamp_hash": hashlib.sha256(old_row["timestamp"].encode()).hexdigest(),
                    "new_timestamp_hash": hashlib.sha256(row["timestamp"].encode()).hexdigest(),
                })
        return found
    finally:
        previous.close(); current.close()


def manifest(items: list[dict[str, str | int]], pre_utc_db: Path) -> dict:
    encoded = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
    return {"utc_commit": UTC_COMMIT, "pre_utc_sha256": _file_hash(pre_utc_db),
            "count": len(items), "manifest_sha256": hashlib.sha256(encoded).hexdigest(), "candidates": items}


def _configured_db() -> Path:
    return Path(os.environ.get("BRAINLEHR_DB") or os.environ.get("BEGOD_KNOWLEDGE_DB") or kms.DB_PATH)


def apply(items: list[dict[str, str | int]], *, actor: str, reason: str) -> tuple[int, int]:
    recorded = already = 0
    for item in items:
        result = kms.kettenerklaerung_erklaeren(
            int(item["access_log_id"]), reason, commit_hash=UTC_COMMIT,
            actor=actor, model="migrate_auditkette_utc_p68", session="p68:utc-chain-repair",
        )
        if result.get("status") == "already_recorded":
            already += 1
        else:
            recorded += 1
    return recorded, already


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--pre-utc-db", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resume", action="store_true", help="continue by rescanning rows not yet explained")
    parser.add_argument("--limit", type=int, help="maximum candidates for this bounded apply batch")
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--actor")
    parser.add_argument("--reason", default="P68: proven UTC-only access-log timestamp migration")
    args = parser.parse_args(argv)
    if args.apply and (not args.actor or not args.backup_dir):
        parser.error("--apply requires --actor and --backup-dir")
    if args.apply and args.db.resolve() != _configured_db().resolve():
        parser.error("--apply DB must equal BRAINLEHR_DB/BEGOD_KNOWLEDGE_DB")
    if args.db.resolve() == args.pre_utc_db.resolve():
        parser.error("--pre-utc-db must be a distinct immutable backup")
    all_items = candidates(args.db, args.pre_utc_db)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    items = all_items[:args.limit] if args.limit else all_items
    report = manifest(items, args.pre_utc_db)
    report["remaining_candidates"] = len(all_items) - len(items)
    print(json.dumps(report, ensure_ascii=False))
    if not args.apply:
        return 0
    backup, digest = _backup(args.db, args.backup_dir)
    recorded, already = apply(report["candidates"], actor=args.actor, reason=args.reason)
    print(json.dumps({"backup": str(backup), "backup_sha256": digest,
                      "recorded": recorded, "already_recorded": already}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
