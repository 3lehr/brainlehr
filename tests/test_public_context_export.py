from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest


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


def _repo(tmp_path: Path, monkeypatch, path: str = "/public/self") -> tuple[Path, Path]:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "source.py").write_text("SOURCE = 1\n", encoding="utf-8")
    allowlist = root / "nodes.json"
    allowlist.write_text(json.dumps({"schema": 1, "project_id": "sample", "nodes": [{
        "path": path, "sources": ["source.py"]
    }]}), encoding="utf-8")
    subprocess.run(["git", "add", "source.py", "nodes.json"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    monkeypatch.setattr(public_context, "ROOT", root)
    return root, allowlist


def test_allowlisted_export_is_deterministic_and_omits_private_db_fields(tmp_path, monkeypatch):
    root, allowlist = _repo(tmp_path, monkeypatch)
    db, output = _db(tmp_path), root / "context.json"
    first = public_context.export(db, output, allowlist, commit="abc", source_timestamps={"source.py": 0})
    before = output.read_bytes()
    second = public_context.export(db, output, allowlist, commit="abc", source_timestamps={"source.py": 0})
    payload = json.loads(before)
    assert first["status"] == "written" and second["status"] == "current"
    assert output.read_bytes() == before
    assert [node["path"] for node in payload["nodes"]] == ["/public/self"]
    assert all("source" not in node for node in payload["nodes"])
    assert "/private" not in json.dumps(payload)
    assert payload["provenance"]["source_git_commit"] == "abc"


def test_missing_stale_or_private_allowlist_node_rejects_without_overwriting(tmp_path, monkeypatch):
    root, allowlist = _repo(tmp_path, monkeypatch)
    db, output = _db(tmp_path), root / "context.json"
    output.write_text("old", encoding="utf-8")
    data = json.loads(allowlist.read_text(encoding="utf-8"))
    data["nodes"][0]["path"] = "/missing"
    allowlist.write_text(json.dumps(data), encoding="utf-8")
    missing = public_context.export(db, output, allowlist, source_timestamps={"source.py": 0})
    assert missing["status"] == "rejected" and output.read_text() == "old"
    data["nodes"][0]["path"] = "/public/self"
    allowlist.write_text(json.dumps(data), encoding="utf-8")
    stale = public_context.export(db, output, allowlist, source_timestamps={"source.py": 4_000_000_000})
    assert stale["status"] == "rejected" and stale["errors"] == ["stale:/public/self"]
    data["nodes"][0]["path"] = "/private"
    allowlist.write_text(json.dumps(data), encoding="utf-8")
    private = public_context.export(db, output, allowlist, source_timestamps={"source.py": 0})
    assert private["status"] == "rejected" and private["errors"] == ["not-public:/private"]


def test_private_pattern_is_rejected(tmp_path, monkeypatch):
    root, allowlist = _repo(tmp_path, monkeypatch)
    db, output = _db(tmp_path), root / "context.json"
    conn = sqlite3.connect(db)
    conn.execute("UPDATE knowledge_nodes SET content='/Users/private/secret' WHERE path='/public/self'")
    conn.commit()
    conn.close()
    result = public_context.export(db, output, allowlist, source_timestamps={"source.py": 0})
    assert result == {"status": "rejected", "errors": ["private-content:/public/self"]}


def test_export_rejects_external_or_untracked_contract_paths(tmp_path, monkeypatch):
    root, allowlist = _repo(tmp_path, monkeypatch)
    db = _db(tmp_path)
    external = tmp_path / "external.json"
    external.write_text(allowlist.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="inside repository"):
        public_context.export(db, root / "context.json", external)
    with pytest.raises(ValueError, match="inside repository"):
        public_context.export(db, tmp_path / "outside.json", allowlist)
    data = json.loads(allowlist.read_text(encoding="utf-8"))
    data["nodes"][0]["sources"] = ["not-tracked.py"]
    allowlist.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="tracked source"):
        public_context.export(db, root / "context.json", allowlist)
