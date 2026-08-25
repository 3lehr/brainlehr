#!/usr/bin/env python3
"""Export a small allowlisted public project description from Brainlehr."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ALLOWLIST = ROOT / "docs/public-knowledge/brainlehr-nodes.json"
DEFAULT_OUTPUT = ROOT / "docs/public-knowledge/brainlehr-context.json"
_PRIVATE = (
    re.compile(r"/Users/[^/\s]+/"), re.compile(r"/Volumes/[^/\s]+/"),
    re.compile(r"-----BEGIN(?: [A-Z]+)? PRIVATE KEY-----"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                          capture_output=True, check=True).stdout.strip()


def _config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("project_id"), str):
        raise ValueError("allowlist requires schema=1 and project_id")
    if not isinstance(data.get("nodes"), list) or not data["nodes"]:
        raise ValueError("allowlist requires nodes")
    for node in data["nodes"]:
        if not isinstance(node, dict) or not str(node.get("path", "")).startswith("/"):
            raise ValueError("allowlist node requires a knowledge path")
        if not isinstance(node.get("sources"), list) or not node["sources"]:
            raise ValueError("allowlist node requires source paths")
    return data


def _source_timestamps(config: dict) -> dict[str, int]:
    sources = {source for node in config["nodes"] for source in node["sources"]}
    return {source: int(_git("log", "-1", "--format=%ct", "--", source) or 0)
            for source in sources}


def _stale(updated_at: str, sources: list[str], timestamps: dict[str, int]) -> bool:
    try:
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return True
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return updated.timestamp() < max(timestamps[source] for source in sources)


def _public_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return path.name


def build(db: Path, allowlist: Path = DEFAULT_ALLOWLIST, *, commit: str | None = None,
          source_timestamps: dict[str, int] | None = None) -> tuple[dict | None, list[str]]:
    config = _config(allowlist)
    timestamps = source_timestamps if source_timestamps is not None else _source_timestamps(config)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    nodes, errors = [], []
    try:
        for wanted in config["nodes"]:
            row = conn.execute(
                "SELECT path,title,summary,content,updated_at,freigabe FROM knowledge_nodes "
                "WHERE path=? AND project_id=?", (wanted["path"], config["project_id"])
            ).fetchone()
            if row is None:
                errors.append(f"missing:{wanted['path']}")
            elif row["freigabe"] != "offen":
                errors.append(f"not-public:{wanted['path']}")
            elif _stale(row["updated_at"], wanted["sources"], timestamps):
                errors.append(f"stale:{wanted['path']}")
            else:
                item = {key: row[key] for key in ("path", "title", "summary", "content", "updated_at")}
                if any(pattern.search(json.dumps(item, ensure_ascii=False)) for pattern in _PRIVATE):
                    errors.append(f"private-content:{wanted['path']}")
                else:
                    nodes.append(item)
    finally:
        conn.close()
    if errors:
        return None, errors
    return {
        "schema": 1, "project_id": config["project_id"],
        "provenance": {"allowlist": _public_path(allowlist),
                       "exporter": "pflege/export_public_context.py",
                       "git_commit": commit or _git("rev-parse", "HEAD")},
        "nodes": nodes,
    }, []


def export(db: Path, output: Path = DEFAULT_OUTPUT, allowlist: Path = DEFAULT_ALLOWLIST,
           *, commit: str | None = None, source_timestamps: dict[str, int] | None = None) -> dict:
    payload, errors = build(db, allowlist, commit=commit, source_timestamps=source_timestamps)
    if errors:
        return {"status": "rejected", "errors": errors}
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output.exists() and output.read_text(encoding="utf-8") == encoded:
        return {"status": "current", "path": str(output)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")
    return {"status": "written", "path": str(output), "nodes": len(payload["nodes"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    args = parser.parse_args()
    result = export(args.db, args.output, args.allowlist)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] in {"written", "current"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
