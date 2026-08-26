from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

from kern.pfad_hygiene import digest, rewrite


def _migration():
    path = Path(__file__).parents[1] / "migrationen" / "migrate_pfad_hygiene_p67.py"
    spec = importlib.util.spec_from_file_location("p67_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_rewrite_is_limited_and_hashes_do_not_expose_text():
    old = "See /Volumes/daten/Begod2026/brainlehr/kern/x.py and /tmp/keep."
    new, changes = rewrite(old)
    assert "project://brainlehr/kern/x.py" in new
    assert "/tmp/keep" in new
    assert changes[0].category == "project-path"
    assert digest(old) != digest(new)


def test_rewrite_preserves_the_historical_videoki_space_as_a_uri_component():
    new, changes = rewrite("Project `/Volumes/daten/videoki studio` has a host-bound path.")
    assert new == "Project `project://videoki%20studio` has a host-bound path."
    assert changes[0].category == "project-path"


def test_scan_skips_existing_exception_basis_and_emits_hashes(tmp_path):
    db = tmp_path / "x.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE knowledge_nodes (id TEXT, title TEXT, summary TEXT, content TEXT)")
    conn.execute("INSERT INTO knowledge_nodes VALUES ('a','A','plain','/Volumes/daten/Begod2026/change')")
    conn.commit(); conn.close()
    basis = tmp_path / "basis.json"
    basis.write_text(json.dumps([{"tabelle": "knowledge_nodes", "id": "a", "feld": "title"}]))
    findings = _migration().scan(db, basis)
    assert [(x["id"], x["field"]) for x in findings] == [("a", "content")]
    assert set(findings[0]) == {"id", "field", "table", "category", "old_hash", "new_hash", "replacement"}
    assert "/Volumes" not in json.dumps([{k: v for k, v in findings[0].items() if k != "replacement"}])


def test_apply_dispatches_tools_call_and_requires_reason():
    finding = {"id": "node-1", "table": "knowledge_nodes", "field": "content", "replacement": "project://x", "category": "project-path", "old_hash": "a", "new_hash": "b"}
    seen = []
    response = _migration()._call_update(finding, actor="tester", reason="P67 migration", call=seen.append)
    assert response is None
    request = seen[0]
    assert request["method"] == "tools/call"
    args = request["params"]["arguments"]
    assert args["actor"] == "tester" and args["session"] == "p67:P67 migration"
    assert "reason" not in args
    assert args["content"] == "project://x"


def test_backup_uses_recoverable_sqlite_snapshot(tmp_path):
    db = tmp_path / "source.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE values_ (value TEXT)")
    conn.execute("INSERT INTO values_ VALUES ('persisted')")
    conn.commit(); conn.close()
    target, _ = _migration()._backup(db, tmp_path / "backups")
    recovered = sqlite3.connect(target)
    try:
        assert recovered.execute("SELECT value FROM values_").fetchone()[0] == "persisted"
        assert recovered.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        recovered.close()
