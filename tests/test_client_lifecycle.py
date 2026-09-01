from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import knowledge_mcp_server as kms
from client_lifecycle import ProjectLifecycle, as_evidence_witness, knowledge_only_flow, recovery_envelope
from project_context import witness_envelope


def test_knowledge_mode_is_a_real_code_bypass():
    result = knowledge_only_flow(mode="knowledge", knowledge={"count": 2})
    assert result["code_path"] == "bypassed"
    assert result["durable_writes"] == 0
    assert "analyzer" in result["must_not"]
    assert "raw" not in str(result).lower()
    assert witness_envelope(witnesses=[as_evidence_witness(result, witness_id="p77", requirement_id="P77")])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}
    assert knowledge_only_flow(mode="code")["code_path"] == "enabled"


def test_project_attach_reattach_detach_and_foreign_owner(tmp_path):
    store = ProjectLifecycle(tmp_path / "projects.json")
    first = store.attach(project_id="demo", revision="abc", capsule={"schema": 1}, owner="a")
    assert first["status"] == "attached"
    assert store.attach(project_id="demo", revision="abc", capsule={"schema": 1}, owner="a")["status"] == "unchanged"
    assert store.attach(project_id="demo", revision="def", capsule={"schema": 1}, owner="b")["status"] == "denied"
    assert store.detach(project_id="unknown", owner="a")["status"] == "unknown_project"
    assert store.detach(project_id="demo", owner="a")["status"] == "detached"
    assert store.context("demo") is None
    assert witness_envelope(witnesses=[as_evidence_witness(first, witness_id="p78", requirement_id="P78")])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_recovery_state_is_client_parity_and_never_empty_success():
    for state in ("current", "stale", "timeout", "empty"):
        envelopes = [recovery_envelope(client, state) for client in ("CODEX", "CLAUDE", "HERMES", "IDE")]
        assert envelopes.count(envelopes[0]) == 4
        assert envelopes[0]["status"] == state
        assert envelopes[0]["next_action"]
        assert envelopes[0]["durable_writes"] == 0
    current = recovery_envelope("CODEX", "current")
    assert witness_envelope(witnesses=[as_evidence_witness(current, witness_id="p79", requirement_id="P79")])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_project_attach_detach_real_mcp_contract_preserves_project_state(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
    untracked = root / "keep.untracked"
    untracked.write_text("keep\n", encoding="utf-8")

    db = tmp_path / "knowledge.db"
    connection = sqlite3.connect(db)
    connection.executescript((Path(__file__).parents[1] / "schema.sql").read_text())
    connection.commit()
    connection.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    receipt = kms.knowledge_add(
        "/", "Existing receipt", "Must survive detach", "receipt",
        project_id="demo", tags=["project-change-receipt"], source="test fixture",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Test fact.")
    assert receipt["status"] == "created"

    listed = kms.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    specs = {tool["name"]: tool["inputSchema"] for tool in listed["result"]["tools"]}
    assert specs["project_attach"]["required"] == ["project_root", "actor"]
    assert specs["project_detach"]["required"] == ["project_root", "actor"]

    def call(name, arguments, request_id, *, allow_error=False):
        response = kms.handle_request({
            "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        assert (response["result"].get("isError") is True) == allow_error
        return json.loads(response["result"]["content"][0]["text"])

    arguments = {"project_root": str(root), "project_id": "demo", "actor": "codex"}
    first = call("project_attach", arguments, 2)
    assert first["status"] == "attached"
    assert call("project_attach", arguments, 3)["status"] == "unchanged"

    connection = sqlite3.connect(db)
    before = connection.execute(
        "SELECT id, content FROM knowledge_nodes WHERE project_id='demo' ORDER BY id"
    ).fetchall()
    connection.close()
    detached = call("project_detach", {"project_root": str(root), "actor": "codex"}, 4)
    assert detached["status"] == "detached"

    context = call("project_context", {
        "project_root": str(root), "task": "demo", "depth": "summary"}, 5,
        allow_error=True)
    assert context == {
        "error": "project is detached", "state": "detached", "project_id": "demo",
        "next": "call project_attach to reactivate the existing local project association",
    }
    assert call("project_attach", arguments, 6)["status"] == "attached"

    connection = sqlite3.connect(db)
    after = connection.execute(
        "SELECT id, content FROM knowledge_nodes WHERE project_id='demo' ORDER BY id"
    ).fetchall()
    connection.close()
    lifecycle = json.loads((root / ".brainlehr-lifecycle.json").read_text())
    assert before == after
    assert [row["action"] for row in lifecycle["audit"]] == ["attach", "detach", "attach"]
    assert (root / "app.py").read_text() == "VALUE = 1\n"
    assert untracked.read_text() == "keep\n"
    assert str(tmp_path) not in json.dumps([first, detached])
