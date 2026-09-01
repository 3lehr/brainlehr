from __future__ import annotations

import subprocess

import pytest

import project_analysis_loop as pal


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "provider.py").write_text("VALUE = 1\n")
    (root / "direct.py").write_text("import provider\n")
    (root / "indirect.py").write_text("import direct\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_working_event_hashes_owned_only_and_finds_transitive_consumers(repo):
    (repo / "provider.py").write_text("VALUE = 2\n")
    (repo / "owned.py").write_text("import provider\n")
    (repo / "secret.txt").write_text("excluded\n")
    result = pal.AnalysisLoop(debounce_seconds=0).edit_batch_complete(
        repo, batch_id="b1", agent_owned_untracked_paths=["owned.py"], now=0)
    snapshot = result["snapshot"]
    assert result["status"] == "coalesced"
    assert snapshot["owned_untracked_files"] == ["owned.py"]
    assert "repo" not in snapshot and "secret.txt" not in str(result)
    assert "secret.txt" not in snapshot["working_graph"]["nodes"]
    assert {node["id"] for node in snapshot["working_graph"]["nodes"]} >= {
        "provider.py", "direct.py", "indirect.py", "owned.py"}
    distances = {node["id"]: node["distance"] for node in snapshot["working_graph"]["nodes"]}
    assert distances["direct.py"] == 1 and distances["indirect.py"] == 2
    assert snapshot["working_graph"]["durable_writes"] == 0
    assert "prompt" not in str(result).lower()
    (repo / "owned.py").write_text("import provider\nVALUE = 2\n")
    changed = pal.working_tree_overlay(repo, agent_owned_untracked_paths=["owned.py"])
    assert changed["tree_hash"] != snapshot["tree_hash"]


def test_unowned_path_cannot_be_claimed_and_upward_is_rejected(repo):
    (repo / "other.py").write_text("VALUE = 3\n")
    loop = pal.AnalysisLoop(debounce_seconds=0)
    result = loop.edit_batch_complete(repo, batch_id="b2", now=0)
    assert result["status"] == "coalesced"
    assert result["snapshot"]["owned_untracked_files"] == []
    with pytest.raises(ValueError, match="relative"):
        loop.edit_batch_complete(repo, batch_id="b3", agent_owned_untracked_paths=["../other.py"], now=1)


def test_latest_batch_discards_stale_result_and_is_idempotent(repo):
    loop = pal.AnalysisLoop(debounce_seconds=0)
    (repo / "provider.py").write_text("VALUE = 2\n")
    first = loop.edit_batch_complete(repo, batch_id="one", now=0)
    run = loop.begin_due(now=0)
    (repo / "provider.py").write_text("VALUE = 3\n")
    second = loop.edit_batch_complete(repo, batch_id="two", now=1)
    assert loop.finish(run["idempotency_key"])["status"] == "discarded_stale"
    current = loop.begin_due(now=1)
    assert loop.finish(current["idempotency_key"])["status"] == "current"
    assert loop.edit_batch_complete(repo, batch_id="two", now=2)["status"] == "current"
    assert first["snapshot"]["tree_hash"] != second["snapshot"]["tree_hash"]
    assert (pal.working_tree_overlay(repo)["working_graph"]["content_hash"]
            == pal.working_tree_overlay(repo)["working_graph"]["content_hash"])


def test_deleted_or_renamed_provider_keeps_baseline_consumers(repo):
    (repo / "provider.py").unlink()
    deleted = pal.working_tree_overlay(repo)
    assert "direct.py" in {node["id"] for node in deleted["working_graph"]["nodes"]}

    _git(repo, "restore", "--source=HEAD", "--", "provider.py")
    _git(repo, "mv", "provider.py", "renamed.py")
    renamed = pal.working_tree_overlay(repo)
    nodes = {node["id"] for node in renamed["working_graph"]["nodes"]}
    assert {"provider.py", "renamed.py", "direct.py"} <= nodes


def test_static_graph_keeps_multiple_ingress_paths_separate_without_runtime_claim(repo):
    (repo / "first.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "second.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "effect.py").write_text("import first\nimport second\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "add two static ingress paths")
    (repo / "first.py").write_text("VALUE = 3\n", encoding="utf-8")
    (repo / "second.py").write_text("VALUE = 4\n", encoding="utf-8")
    graph = pal.working_tree_overlay(repo)["working_graph"]
    pairs = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    assert {("first.py", "effect.py"), ("second.py", "effect.py")} <= pairs
    assert "exactly_once" not in str(graph)


def test_mcp_event_schema_is_strict_and_does_not_create_receipt(repo, monkeypatch):
    import knowledge_mcp_server as kms

    monkeypatch.setattr(kms, "get_db", lambda: (_ for _ in ()).throw(AssertionError("no DB")))
    tool = kms.TOOLS["edit_batch_complete"]
    schema = tool["inputSchema"]
    assert schema["additionalProperties"] is False
    assert "project_root" in schema["required"]
    assert schema["properties"]["event_source"]["maxLength"] == 64
    (repo / "provider.py").write_text("VALUE = 4\n")
    result = tool["handler"]({"project_root": str(repo), "batch_id": "mcp", "now": 0})
    assert result["snapshot"]["working_graph"]["durable_writes"] == 0
    assert len(str(result)) < 12000
    assert not (repo / ".brainlehr-commit-acks.jsonl").exists()


def test_machine_event_identifiers_reject_prompt_sized_or_non_machine_values(repo):
    loop = pal.AnalysisLoop(debounce_seconds=0)
    with pytest.raises(ValueError, match="machine identifier"):
        loop.edit_batch_complete(repo, event_source="prompt text with spaces", batch_id="b", now=0)
    with pytest.raises(ValueError, match="machine identifier"):
        loop.edit_batch_complete(repo, event_source="codex", batch_id="x" * 65, now=0)


def test_client_event_sources_share_the_same_working_contract(repo):
    (repo / "provider.py").write_text("VALUE = 4\n")
    graphs = []
    for source in ("codex", "claude", "hermes", "ide"):
        result = pal.AnalysisLoop(debounce_seconds=0).edit_batch_complete(
            repo, event_source=source, batch_id=source, now=0)
        graphs.append(result["snapshot"]["working_graph"])
        assert result["durable_writes"] == 0
    assert len({graph["content_hash"] for graph in graphs}) == 1


def test_shadow_overlay_excludes_unowned_tracked_changes(repo):
    (repo / "provider.py").write_text("VALUE = 2\n")
    (repo / "direct.py").write_text("import provider\nVALUE = 'user'\n")
    shadow = pal.working_tree_overlay(repo, agent_owned_tracked_paths=["provider.py"])
    assert shadow["owned_tracked_files"] == ["provider.py"]
    assert shadow["changed_files"] == ["provider.py"]
    assert "direct.py" not in {node["id"] for node in shadow["working_graph"]["nodes"] if node["kind"] == "changed"}
    with pytest.raises(ValueError, match="modified tracked"):
        pal.working_tree_overlay(repo, agent_owned_tracked_paths=["missing.py"])


def test_working_overlay_redacts_baseline_gap_source_locations(repo, monkeypatch):
    monkeypatch.setattr(pal.project_context, "_python_import_edges", lambda *_: (
        [], [], [{"consumer": "private.py", "form": "dynamic_import", "source_ref": "private.py:9"}]))
    graph = pal.working_tree_overlay(repo)["working_graph"]
    assert graph["coverage_gaps"] == ["baseline unsupported static form: dynamic_import"]
    assert "private.py" not in str(graph["coverage_gaps"])


def test_shadow_ledger_is_hash_only_and_reports_false_negatives(repo):
    (repo / "tests").mkdir()
    (repo / "tests" / "test_direct.py").write_text("import direct\n")
    _git(repo, "add", "tests/test_direct.py")
    _git(repo, "commit", "-qm", "test consumer")
    (repo / "provider.py").write_text("VALUE = 2\n")
    ledger = pal.shadow_ledger(repo, agent_owned_tracked_paths=["provider.py"],
                               agent_owned_untracked_paths=[],
                               verified_paths=["tests/test_direct.py", "tests/test_missed.py"])
    assert ledger["prediction_count"] == 1 and ledger["verified_count"] == 2
    assert ledger["false_negative_count"] == 1 and len(ledger["ledger_hash"]) == 64
    assert ledger["durable_writes"] == 0 and ledger["complete"] is False
    assert "test_direct.py" not in str(ledger) and "test_missed.py" not in str(ledger)


def test_working_graph_output_is_bounded(repo):
    for index in range(70):
        (repo / f"consumer_{index}.py").write_text("import provider\n", encoding="utf-8")
    _git(repo, "add", ".")
    (repo / "provider.py").write_text("VALUE = 9\n", encoding="utf-8")
    graph = pal.working_tree_overlay(repo)["working_graph"]
    assert len(graph["nodes"]) <= pal.MAX_WORKING_NODES
    assert len(graph["edges"]) <= pal.MAX_WORKING_EDGES
    assert any("output bounded" in gap for gap in graph["coverage_gaps"])
