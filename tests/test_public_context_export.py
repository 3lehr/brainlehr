from __future__ import annotations

import importlib.util
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("public_context", ROOT / "pflege/export_public_context.py")
public_context = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(public_context)


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "knowledge.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE knowledge_nodes (path TEXT, title TEXT, summary TEXT, content TEXT, updated_at TEXT, freigabe TEXT, project_id TEXT)")
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany("INSERT INTO knowledge_nodes VALUES (?,?,?,?,?,?,?)", [
        ("/public/self", "Self", "summary", "safe content", now, "offen", "sample"),
        ("/private", "Private", "summary", "secret", now, "intern", "sample"),
    ])
    conn.commit()
    conn.close()
    return db


def _allowlist(tmp_path: Path, path: str = "/public/self") -> Path:
    allowlist = tmp_path / "nodes.json"
    allowlist.write_text(json.dumps({"schema": 1, "project_id": "sample", "nodes": [{
        "path": path, "sources": ["source.py"]
    }]}), encoding="utf-8")
    return allowlist


def test_allowlisted_export_is_deterministic_and_omits_private_db_fields(tmp_path):
    db, allowlist, output = _db(tmp_path), _allowlist(tmp_path), tmp_path / "context.json"
    first = public_context.export(db, output, allowlist, commit="abc", source_timestamps={"source.py": 0})
    before = output.read_bytes()
    second = public_context.export(db, output, allowlist, commit="abc", source_timestamps={"source.py": 0})
    payload = json.loads(before)
    assert first["status"] == "written" and second["status"] == "current"
    assert output.read_bytes() == before
    assert [node["path"] for node in payload["nodes"]] == ["/public/self"]
    assert "source" not in json.dumps(payload) and "/private" not in json.dumps(payload)


def test_missing_stale_or_private_allowlist_node_rejects_without_overwriting(tmp_path):
    db, output = _db(tmp_path), tmp_path / "context.json"
    output.write_text("old", encoding="utf-8")
    missing = public_context.export(db, output, _allowlist(tmp_path, "/missing"), source_timestamps={"source.py": 0})
    assert missing["status"] == "rejected" and output.read_text() == "old"
    stale = public_context.export(db, output, _allowlist(tmp_path), source_timestamps={"source.py": 4_000_000_000})
    assert stale["status"] == "rejected" and stale["errors"] == ["stale:/public/self"]
    private = public_context.export(db, output, _allowlist(tmp_path, "/private"), source_timestamps={"source.py": 0})
    assert private["status"] == "rejected" and private["errors"] == ["not-public:/private"]


def test_private_pattern_is_rejected(tmp_path):
    db, allowlist, output = _db(tmp_path), _allowlist(tmp_path), tmp_path / "context.json"
    conn = sqlite3.connect(db)
    conn.execute("UPDATE knowledge_nodes SET content='/Users/private/secret' WHERE path='/public/self'")
    conn.commit()
    conn.close()
    result = public_context.export(db, output, allowlist, source_timestamps={"source.py": 0})
    assert result == {"status": "rejected", "errors": ["private-content:/public/self"]}
