import sqlite3
import json

import pytest

import knowledge_mcp_server as kms
from kern import session_checkpoint as sc


def _payload(**overrides):
    data = {
        "session_id": "session-1",
        "project": "brainlehr",
        "context_fraction": 0.5,
        "topic_fingerprint": "topic-abc123",
        "active_requirement_ids": ["MUST-SESSION-001"],
        "expected_child_ids": ["child-1"],
        "terminal_child_ids": ["child-1"],
        "unresolved_evidence_ids": [],
        "next_authorized_action": "ACTION-CONTINUE-1",
    }
    data.update(overrides)
    return data


def test_session_checkpoint_upsert_read_expire_and_close():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    sc.ensure_schema(conn)

    first = sc.setzen(conn, _payload(), now="2026-08-17T18:00:00Z", ttl_seconds=60)
    second = sc.setzen(
        conn, _payload(context_fraction=0.76), now="2026-08-17T18:00:30Z", ttl_seconds=60
    )
    assert first["session_id"] == second["session_id"]
    assert conn.execute("SELECT COUNT(*) FROM session_checkpoints").fetchone()[0] == 1
    assert sc.lesen(conn, "session-1", now="2026-08-17T18:01:00Z")["context_fraction"] == 0.76
    assert sc.lesen(conn, "session-1", now="2026-08-17T18:01:31Z") is None

    sc.setzen(conn, _payload(), now="2026-08-17T18:02:00Z", ttl_seconds=60)
    assert sc.schliessen(conn, "session-1") is True
    assert sc.schliessen(conn, "session-1") is False


def test_rollover_gate_is_deterministic():
    checkpoint = _payload()
    pending = sc.empfehlen(_payload(terminal_child_ids=[]), "topic-abc123")
    assert pending == {"action": "integrate_children", "recommend_new_chat": False, "pending_child_ids": ["child-1"]}

    assert sc.empfehlen(_payload(context_fraction=0.76), "topic-abc123")["action"] == "secure_findings"
    assert sc.empfehlen(_payload(context_fraction=0.90), "topic-abc123")["action"] == "secure_all"
    assert sc.empfehlen(checkpoint, "topic-new456") == {
        "action": "recommend_new_chat", "recommend_new_chat": True, "pending_child_ids": []
    }


def test_agent_reuse_recommendation_is_compact_and_never_spawns():
    checkpoint = _payload(
        role_capability="terra-code", source_revision="abc123",
        used_knowledge_ids=["node-1", "L-lesson-1"], open_gate_ids=["BDW-P35"],
    )
    same = sc.reuse_empfehlen(checkpoint, project_id="brainlehr", task_fingerprint="topic-abc123",
                              role_capability="terra-code", source_revision="abc123")
    assert same["action"] == "reuse_followup"
    assert same["load"] == "direct_neighbors_only"
    assert set(same["checkpoint"]) == {
        "project_id", "task_fingerprint", "role_capability", "source_revision",
        "used_node_or_lesson_ids", "open_gate_ids", "terminal_state"}
    assert sc.reuse_empfehlen(checkpoint, project_id="brainlehr", task_fingerprint="topic-abc123",
                              role_capability="terra-code", source_revision="def456")["action"] == "refresh_delta"
    assert sc.reuse_empfehlen(checkpoint, project_id="brainlehr", task_fingerprint="topic-abc123",
                              role_capability="terra-code", source_revision="abc123",
                              independent_review=True)["action"] == "fresh_agent"
    assert sc.reuse_empfehlen(_payload(context_fraction=.8, role_capability="terra-code", source_revision="abc123"),
                              project_id="brainlehr", task_fingerprint="topic-abc123",
                              role_capability="terra-code", source_revision="abc123")["reason"] == "context saturation"
    blocked = sc.empfehlen(_payload(unresolved_evidence_ids=["EVIDENCE-OPEN-1"]), "topic-new456")
    assert blocked["action"] == "complete_handoff" and not blocked["recommend_new_chat"]


def test_agent_capability_registry_reuses_only_compatible_entry():
    registry = sc.AgentCapabilityRegistry()
    entry = registry.register(agent_id="terra-1", task_id="task-1", project_id="brainlehr",
                              task_fingerprint="topic-1", role_capability="terra-code",
                              source_revision="rev-1", tree_hash="tree-1",
                              checkpoint_session_id="session-1", open_gate_ids=["BDW-P48"])
    assert entry.agent_id == "terra-1"
    same = registry.recommend(project_id="brainlehr", task_fingerprint="topic-1",
                              role_capability="terra-code", source_revision="rev-1", tree_hash="tree-1")
    assert same == {"action": "reuse_followup", "load": "direct_neighbors_only",
                    "agent_id": "terra-1", "task_id": "task-1"}
    assert registry.recommend(project_id="brainlehr", task_fingerprint="topic-1",
                              role_capability="terra-code", source_revision="rev-2", tree_hash="tree-2")["action"] == "refresh_delta"
    assert registry.recommend(project_id="brainlehr", task_fingerprint="topic-1",
                              role_capability="terra-review", source_revision="rev-1", tree_hash="tree-1")["action"] == "fresh_agent"
    assert registry.recommend(project_id="brainlehr", task_fingerprint="topic-1",
                              role_capability="terra-code", source_revision="rev-1", tree_hash="tree-1",
                              independent_review=True)["action"] == "fresh_agent"
    assert "checkpoint_session_id" in registry.get("brainlehr", "topic-1")


@pytest.mark.parametrize(
    "bad",
    [
        {"raw_prompt": "vollständiger Prompt"},
        {"topic_fingerprint": "person@example.org"},
        {"next_authorized_action": "Bitte analysiere den gesamten Chat"},
        {"next_authorized_action": "sk-live-abcdef"},
    ],
)
def test_privacy_boundary_rejects_free_text_and_unknown_fields(bad):
    conn = sqlite3.connect(":memory:")
    sc.ensure_schema(conn)
    with pytest.raises(ValueError):
        sc.setzen(conn, _payload(**bad), now="2026-08-17T18:00:00Z")
    assert conn.execute("SELECT COUNT(*) FROM session_checkpoints").fetchone()[0] == 0


def test_mcp_contract_and_agent_rules(monkeypatch, tmp_path):
    monkeypatch.setattr(kms, "DB_PATH", tmp_path / "checkpoint.db")
    set_result = kms.TOOLS["session_checkpoint_setzen"]["handler"](_payload())
    assert set_result["checkpoint"]["session_id"] == "session-1"
    read_result = kms.TOOLS["session_checkpoint_lesen"]["handler"](
        {"session_id": "session-1", "current_topic_fingerprint": "topic-new456"}
    )
    assert read_result["recommendation"]["recommend_new_chat"] is True
    assert kms.TOOLS["session_checkpoint_schliessen"]["handler"]({"session_id": "session-1"})["closed"]

    properties = kms.TOOLS["session_checkpoint_setzen"]["inputSchema"]["properties"]
    assert "raw_prompt" not in properties and "transcript" not in properties
    assert kms.TOOLS["session_checkpoint_setzen"]["inputSchema"]["additionalProperties"] is False
    reuse = kms.TOOLS["session_agent_reuse"]["handler"]({
        "session_id": "session-1", "project_id": "brainlehr", "task_fingerprint": "topic-abc123",
        "role_capability": "terra-code", "source_revision": "abc123"})
    assert reuse["action"] == "fresh_agent"
    assert "raw_prompt" not in kms.TOOLS["session_agent_reuse"]["inputSchema"]["properties"]


def test_agent_templates_share_checkpoint_rule():
    from pathlib import Path

    root = Path(__file__).parents[1] / "auszug-offen" / "prompts"
    marker = "Ein Sitzungscheckpoint ist kein Chatlog"
    texts = [(root / f"{name}.md").read_text() for name in ("CLAUDE", "CHATGPT", "HERMES")]
    assert all(marker in text for text in texts)


def test_mcp_jsonrpc_end_to_end_and_rejects_raw_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(kms, "DB_PATH", tmp_path / "mcp-checkpoint.db")
    request = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "session_checkpoint_setzen", "arguments": _payload()},
    }
    saved = kms.handle_request(request)
    payload = json.loads(saved["result"]["content"][0]["text"])
    assert payload["checkpoint"]["session_id"] == "session-1"

    request["id"] = 2
    request["params"]["arguments"] = _payload(raw_prompt="nicht speichern")
    rejected = kms.handle_request(request)
    assert rejected["result"]["isError"] is True
    assert "nicht erlaubte Checkpoint-Felder" in rejected["result"]["content"][0]["text"]
