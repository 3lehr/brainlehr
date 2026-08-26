#!/usr/bin/env python3
"""P67 path-hygiene migration.

Default is a read-only report.  Historical fields listed in the B/C exception
basis are skipped.  ``--apply`` calls the real MCP ``tools/call`` dispatcher;
it never updates SQLite directly.  The server's normal update path supplies
its backup/audit/validation behavior.
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
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kern import pfad_hygiene  # noqa: E402
from kern import speicher  # noqa: E402

NODE_FIELDS = ("title", "summary", "content")
LESSON_FIELDS = ("description", "root_cause", "resolution", "prevention", "pruefstelle")


def _basis(path: Path) -> set[tuple[str, str, str]]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {(e["tabelle"], e["id"], e["feld"]) for e in entries}


def scan(db: Path, basis: Path) -> list[dict[str, str]]:
    excluded = _basis(basis)
    findings: list[dict[str, str]] = []
    with speicher.lesen(db) as conn:
        tables = (("knowledge_nodes", NODE_FIELDS), ("lessons_learned", LESSON_FIELDS))
        for table, fields in tables:
            try:
                columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            except Exception:  # pragma: no cover - defensive for old DB copies
                continue
            fields = tuple(field for field in fields if field in columns)
            if not fields:
                continue
            for row in conn.execute(f"SELECT id, {', '.join(fields)} FROM {table}"):
                key_prefix = (table, str(row["id"]))
                for field in fields:
                    key = (*key_prefix, field)
                    if key in excluded or not isinstance(row[field], str):
                        continue
                    new, changes = pfad_hygiene.rewrite(row[field])
                    if not changes or new == row[field]:
                        continue
                    categories = sorted({change.category for change in changes})
                    findings.append({
                        "id": str(row["id"]),
                        "field": field,
                        "table": table,
                        "category": "+".join(categories),
                        "old_hash": pfad_hygiene.digest(row[field]),
                        "new_hash": pfad_hygiene.digest(new),
                        "replacement": new,
                    })
    return findings


def _call_update(finding: dict[str, str], *, actor: str, reason: str,
                 call: Callable[[dict], dict]) -> dict:
    """Send one update through a caller-supplied MCP dispatcher."""
    args = {
        finding["field"]: finding["replacement"],
        "actor": actor,
        "model": "migrate_pfad_hygiene_p67",
        # The update contract has no free ``reason`` argument.  Its durable
        # access-log session is therefore the validated, bounded audit carrier.
        "session": f"p67:{reason}",
    }
    if finding["table"] == "knowledge_nodes":
        tool = "knowledge_update"
        args["node_id"] = finding["id"]
    else:
        tool = "lesson_update"
        args["lesson_id"] = finding["id"]
    return call({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                 "params": {"name": tool, "arguments": args}})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _configured_db() -> Path:
    configured = os.environ.get("BRAINLEHR_DB") or os.environ.get("BEGOD_KNOWLEDGE_DB")
    if not configured:
        # haken/ort.py binds the default at import.  Importing it here would
        # make the same value explicit without duplicating its resolution.
        import ort
        return Path(ort.DB)
    return Path(configured)


def _backup(db: Path, backup_dir: Path) -> tuple[Path, str]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"{db.stem}.p67-pre-{stamp}{db.suffix}"
    if target.exists():  # No silent overwrite of an operator backup.
        raise FileExistsError(target)
    # SQLite's backup API includes committed WAL pages.  A byte copy can look
    # valid while omitting a concurrent writer's committed transaction.
    source = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    return target, _sha256(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("BEGOD_KNOWLEDGE_DB", "brainlehr.db")))
    parser.add_argument("--basis", type=Path, default=ROOT / "tests" / "absolute_pfade_basis.json")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path,
                        help="outside-repository directory for the required pre-apply DB copy")
    parser.add_argument("--actor")
    parser.add_argument("--reason")
    args = parser.parse_args(argv)
    if args.backup_dir and not args.apply:
        parser.error("--backup-dir is available only with --apply; dry-run never writes")
    if args.apply and (not args.actor or not args.reason):
        parser.error("--apply requires non-empty --actor and --reason")
    if args.apply and not args.backup_dir:
        parser.error("--apply requires --backup-dir; writes are resumable but not atomic")
    if args.apply and args.db.resolve() != _configured_db().resolve():
        parser.error("--apply DB must equal BRAINLEHR_DB/BEGOD_KNOWLEDGE_DB; start a new process for a copy")
    findings = scan(args.db, args.basis)
    public = [{key: value for key, value in item.items() if key != "replacement"}
              for item in findings]
    print(json.dumps(public, ensure_ascii=False, indent=2))
    if not args.apply:
        return 0
    backup_path, backup_hash = _backup(args.db, args.backup_dir)
    print(json.dumps({"backup": str(backup_path), "sha256": backup_hash}, ensure_ascii=False))
    import knowledge_mcp_server as server
    call = server.handle_request
    for finding in findings:
        result = _call_update(finding, actor=args.actor, reason=args.reason, call=call)
        if result.get("result", {}).get("isError"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
