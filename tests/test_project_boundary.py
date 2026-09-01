from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import knowledge_mcp_server as kms
import project_analysis_loop
import project_context
from kern import evidence_projections
import werkzeugrechte


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _ack_key(repo: Path) -> Ed25519PrivateKey:
    private = Ed25519PrivateKey.generate()
    manifest_path = repo / project_context.MANIFEST
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["commit_ack_public_key"] = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _git(repo, "add", project_context.MANIFEST)
    _git(repo, "commit", "-qm", "configure local ack key")
    return private


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "sample"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "consumer.py").write_text("import code\n", encoding="utf-8")
    _git(root, "add", "code.py", "consumer.py")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_explicit_modes_win_and_knowledge_does_not_scan_a_repository(monkeypatch):
    def fail(*_args):
        raise AssertionError("knowledge-only must not inspect Git")

    monkeypatch.setattr(project_context, "project_root", fail)
    result = project_context.boundary_contract(mode="knowledge", project_path="ignored")
    assert result["mode"] == "knowledge"
    assert result["evidence"] == ["override:knowledge"]
    assert "scan repository code" in result["must_not"]
    assert "prompt" not in json.dumps(result).lower()


def test_auto_uses_only_staged_tree_or_operation_not_repo_presence(repo):
    unknown = project_context.boundary_contract(project_path=repo)
    assert unknown["mode"] == "unknown"
    assert unknown["evidence"] == []
    assert len(json.dumps(unknown)) < 1200

    mixed = project_context.boundary_contract(operation="project_context", project_path=repo)
    assert mixed["mode"] == "mixed"
    assert mixed["evidence"] == ["operation:project_context"]

    (repo / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", "code.py")
    code = project_context.boundary_contract(
        operation="knowledge_search", project_path=repo, phase="test")
    assert code["mode"] == "code"
    assert code["evidence"] == ["staged_tree"]
    assert code["allowed_next"] == ["commit"]
    assert project_context.boundary_contract(mode="mixed", project_path=repo)["mode"] == "mixed"


def test_invalid_boundary_values_fail_closed():
    with pytest.raises(ValueError, match="mode must"):
        project_context.boundary_contract(mode="CODE")
    with pytest.raises(ValueError, match="phase must"):
        project_context.boundary_contract(phase="think")
    with pytest.raises(ValueError, match="supported"):
        project_context.boundary_contract(operation="git")
    with pytest.raises(ValueError, match="supported"):
        project_context.boundary_contract(operation="knowledge_search; must=code")


def test_boundary_identifies_its_tracked_policy_without_promoting_request_data():
    result = project_context.boundary_contract(mode="knowledge", phase="read")
    assert result["policy_schema"] == 1
    assert len(result["policy_hash"]) == 64
    assert len(result["source_revision"]) == 40
    assert result["analysis"]["status"] == "bypass"
    assert "scan or analyze project code" in result["analysis"]["must_not"]


def test_opt_in_staged_gate_is_append_only_and_invalidates_on_change(repo):
    assert project_context.staged_commit_gate(repo)["status"] == "not_enabled"
    project_context.ensure_manifest(repo, tools=[{
        "id": project_context.COMMIT_GATE_TOOL,
        "capability": "acknowledge staged impact gaps",
        "status": "available",
        "command": "project-boundary",
        "source": "code.py",
    }, {
        "id": "runtime-test", "capability": "runtime test evidence", "status": "available",
        "command": "runtime-test", "source": "code.py", "covers": ["runtime"],
    }])
    _git(repo, "add", project_context.MANIFEST)
    _git(repo, "commit", "-qm", "enable gate")
    private = _ack_key(repo)
    (repo / "README.md").write_text("change\n", encoding="utf-8")
    _git(repo, "add", "README.md")

    snapshot = project_context._staged_snapshot(repo)
    evidence = project_context.register_runtime_evidence(repo, {
        "revision": snapshot["base"], "tree_hash": snapshot["tree_hash"], "tool": "runtime-test",
        "tool_version": "1", "provenance": "test-result", "generator_or_test": True,
        "generated_writes": ["reports/result.json"],
    })
    assert evidence["required_next_probe"] == "test_isolation" and evidence["durable_writes"] == 0

    ack_path = repo / project_context.COMMIT_ACKS
    blocked = project_context.staged_commit_gate(repo)
    assert blocked["status"] == "blocked"
    assert "required runtime probe: test_isolation" in blocked["coverage_gaps"]
    assert not ack_path.exists(), "rejection must not mutate a project file"
    assert "README.md" in blocked["coverage_gaps"][-1]

    with pytest.raises(ValueError, match="1..240"):
        project_context.staged_commit_gate(repo, acknowledge_reason=" ")
    actor = "test-operator"
    forged = base64.b64encode(Ed25519PrivateKey.generate().sign(project_context.ack_payload(
        project_context._staged_snapshot(repo), actor=actor, reason="docs change reviewed"))).decode()
    assert project_context.staged_commit_gate(repo, acknowledge_reason="docs change reviewed", actor=actor,
                                              signature=forged)["status"] == "blocked"
    assert not ack_path.exists()
    signature = base64.b64encode(private.sign(project_context.ack_payload(
        project_context._staged_snapshot(repo), actor=actor, reason="docs change reviewed"))).decode()
    accepted = project_context.staged_commit_gate(repo, acknowledge_reason="docs change reviewed", actor=actor, signature=signature)
    assert accepted["status"] == "acknowledged"
    assert "required runtime probe: test_isolation" in accepted["coverage_gaps"]
    assert project_context.staged_commit_gate(repo)["status"] == "acknowledged"
    lines = ack_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    receipt = json.loads(lines[0])
    assert receipt["base"] == accepted["snapshot"]["base"]
    assert receipt["tree_hash"] == accepted["snapshot"]["tree_hash"]
    assert receipt["actor"] == actor and receipt["signature"] == signature

    (repo / "README.md").write_text("changed again\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    invalidated = project_context.staged_commit_gate(repo)
    assert invalidated["status"] == "blocked"
    assert len(ack_path.read_text(encoding="utf-8").splitlines()) == 1


def test_mcp_and_cli_expose_the_same_small_contract(repo):
    assert not werkzeugrechte.fehlende_zuordnung(kms.TOOLS)
    boundary = kms.TOOLS["project_boundary"]
    assert boundary["inputSchema"]["properties"]["mode"]["enum"] == [
        "auto", "knowledge", "code", "mixed"]
    assert kms.TOOLS["project_commit_gate"]["handler"]({"project_root": str(repo)})["status"] == "not_enabled"
    assert kms.TOOLS["project_runtime_evidence"]["inputSchema"]["required"] == ["project_root", "artifact"]
    result = subprocess.run(
        ["python3", "tool/project_boundary.py", "--mode", "knowledge", "--phase", "read"],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["mode"] == "knowledge"


def test_one_typed_graph_deterministically_generates_the_mermaid_view(repo):
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()
    (repo / "code.py").write_text("VALUE = 3\n", encoding="utf-8")
    _git(repo, "add", "code.py")
    _git(repo, "commit", "-qm", "change provider")
    first = project_context.impact_graph(repo, project_context.impact_chain(repo, base), ["pytest -q"])
    second = project_context.impact_graph(repo, project_context.impact_chain(repo, base), ["pytest -q"])
    assert first["content_hash"] == second["content_hash"]
    assert first["edges"][0]["to"] == "consumer.py"
    assert project_context.impact_mermaid(first) == project_context.impact_mermaid(second)
    assert first["source_revision"] != first["base_revision"]
    assert first["content_hash"] == project_context.impact_visualization_ref(first)["content_hash"]


def test_ephemeral_analysis_loop_coalesces_edits_and_never_persists_them(repo):
    loop = project_analysis_loop.AnalysisLoop(debounce_seconds=2)
    assert loop.task_start(mode="knowledge")["status"] == "bypass"
    assert loop.edit_completed(repo, mode="knowledge", origin="client", correlation_id="k", now=0)["status"] == "bypass"

    (repo / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    first = loop.edit_completed(repo, mode="code", origin="client", correlation_id="one", now=0)
    (repo / "code.py").write_text("VALUE = 3\n", encoding="utf-8")
    second = loop.edit_completed(repo, mode="code", origin="client", correlation_id="two", now=1)
    assert first["status"] == second["status"] == "coalesced"
    assert loop.begin_due(now=2)["status"] == "debouncing"
    run = loop.begin_due(now=3)
    assert run["status"] == "analyze"
    assert run["idempotency_key"] == second["idempotency_key"]
    assert loop.finish(run["idempotency_key"])["status"] == "current"
    assert loop.before_verification(repo, mode="code", now=4)["status"] == "current"

    generated = loop.edit_completed(repo, mode="code", origin="brainlehr_generated_export",
                                    correlation_id="export", now=5)
    assert generated["status"] == "ignored_generated"
    assert generated["durable_writes"] == 0


def test_analysis_loop_discards_stale_results_and_separates_staged_tree(repo):
    loop = project_analysis_loop.AnalysisLoop(debounce_seconds=0)
    (repo / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    active = loop.edit_completed(repo, mode="code", origin="editor", correlation_id="one", now=0)
    run = loop.begin_due(now=0)
    assert run["idempotency_key"] == active["idempotency_key"]
    (repo / "code.py").write_text("VALUE = 3\n", encoding="utf-8")
    next_event = loop.edit_completed(repo, mode="code", origin="editor", correlation_id="two", now=1)
    assert loop.finish(run["idempotency_key"])["status"] == "discarded_stale"
    assert loop.begin_due(now=1)["idempotency_key"] == next_event["idempotency_key"]
    assert loop.finish(next_event["idempotency_key"])["status"] == "current"

    _git(repo, "add", "code.py")
    staged = loop.precommit(repo)
    (repo / "code.py").write_text("VALUE = 4\n", encoding="utf-8")
    working = project_analysis_loop.working_tree_overlay(repo)
    assert staged["status"] == "analyze_staged"
    assert staged["snapshot"]["tree_hash"] != working["tree_hash"]
    assert loop.postcommit(commit="a" * 40, graph_hash="b" * 64, mode="code")["durable_writes"] == 1
    assert loop.postcommit(commit="a" * 40, graph_hash="b" * 64, mode="code")["durable_writes"] == 0
    assert loop.timing_trace(verified=False, source_revision="a" * 40, tree_hash="b")["status"] == "coverage_gap"
    assert loop.timing_trace(verified=True, source_revision="a" * 40, tree_hash="b")["status"] == "verified_timing"


def test_cytoscape_projection_is_deterministic_and_keeps_graph_provenance(repo):
    """Human-readable wireframe: header -> view selector -> graph -> provenance."""
    # +----------------------+   +------------------+   +------------------+
    # | source revision/hash |-->| selected view    |-->| graph nodes/edges |
    # +----------------------+   +------------------+   +------------------+
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()
    (repo / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", "code.py")
    _git(repo, "commit", "-qm", "change provider")
    command = ["python3", "tool/project_impact_view.py", "--project-root", str(repo),
               "--base", base, "--format", "cytoscape"]
    first = subprocess.run(command, cwd=Path(__file__).resolve().parents[1],
                           capture_output=True, text=True, check=True).stdout
    second = subprocess.run(command, cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, check=True).stdout
    assert first == second
    assert "<select" in first
    for view in ("impact_distance", "base_head_edge_delta", "test_evidence",
                 "timing_sequence", "coverage_gaps"):
        assert view in first
    graph = project_context.impact_graph(repo, project_context.impact_chain(repo, base), [])
    assert f'data-source-revision="{graph["source_revision"]}"' in first
    assert f'data-content-hash="{graph["content_hash"]}"' in first


def test_cytoscape_projection_escapes_data_and_bounds_large_graph():
    graph = {"source_revision": 'rev"<x>', "content_hash": 'hash"<x>',
             "nodes": [{"id": "n<script>", "kind": "file", "distance": 0}],
             "edges": []}
    rendered = project_context.impact_cytoscape_html(graph)
    assert "n<script>" not in rendered
    assert "for=\"view\"" in rendered and 'role="img"' in rendered
    large = {**graph, "nodes": [{"id": str(i), "kind": "file", "distance": 0}
                                  for i in range(501)]}
    filtered = project_context.impact_cytoscape_html(large)
    assert "coverage_gap" in filtered
    assert "filtered_subgraph" in filtered
    assert "cytoscape.min.js" in filtered
    assert '"full_node_count":501' in filtered
    assert '"id": "500"' not in filtered


def test_otel_and_metroviz_are_revision_bound_projections():
    graph = {"schema": 1, "source_revision": "rev-1",
             "nodes": [{"id": "src/app.py", "kind": "file"}], "edges": [], "coverage_gaps": []}
    graph["content_hash"] = evidence_projections._hash(graph)
    trace = {"revision": "rev-1", "tree_hash": "tree-1",
             "spans": [{"span_id": "s1", "name": "render", "code_file": "src/app.py",
                        "revision": "rev-1", "tree_hash": "tree-1", "duration_ns": 1}]}
    result = evidence_projections.otel_trace_projection(trace, source_revision="rev-1", tree_hash="tree-1", graph=graph)
    assert result["status"] == "current" and result["bindings"][0]["node"] == "src/app.py"
    assert evidence_projections.otel_trace_projection({**trace, "tree_hash": "old"}, source_revision="rev-1", tree_hash="tree-1", graph=graph)["status"] == "coverage_gap"
    assert evidence_projections.otel_trace_projection({**trace, "spans": [{"payload": "secret"}]}, source_revision="rev-1", tree_hash="tree-1", graph=graph)["status"] == "rejected"
    route = evidence_projections.metroviz_projection(graph)
    assert route["source_revision"] == graph["source_revision"] and route["content_hash"] == graph["content_hash"]
    assert evidence_projections.metroviz_projection({**graph, "content_hash": "old"})["current"] is False
    stale_graph = {**graph, "source_revision": "old"}
    stale_graph["content_hash"] = evidence_projections._hash({key: value for key, value in stale_graph.items() if key != "content_hash"})
    assert evidence_projections.otel_trace_projection(trace, source_revision="rev-1", tree_hash="tree-1", graph=stale_graph)["status"] == "coverage_gap"


def test_otel_and_metroviz_cli_are_real_projection_routes(repo, tmp_path):
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()
    (repo / "code.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(repo, "add", "code.py")
    _git(repo, "commit", "-qm", "change provider")
    root = Path(__file__).resolve().parents[1]
    metroviz = subprocess.run(["python3", "tool/project_impact_view.py", "--project-root", str(repo),
                               "--base", base, "--format", "metroviz"], cwd=root,
                              capture_output=True, text=True, check=True)
    graph = json.loads(metroviz.stdout)
    assert graph["current"] is True and graph["routes"]
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({"revision": graph["source_revision"], "tree_hash": "tree-1",
                                 "spans": [{"span_id": "s", "name": "test", "code_file": "code.py",
                                            "revision": graph["source_revision"], "tree_hash": "tree-1", "duration_ns": 1}]}),
                     encoding="utf-8")
    otel = subprocess.run(["python3", "tool/project_impact_view.py", "--project-root", str(repo),
                           "--base", base, "--format", "otel", "--trace", str(trace),
                           "--tree-hash", "tree-1"], cwd=root, capture_output=True, text=True, check=True)
    assert json.loads(otel.stdout)["status"] == "current"


def test_cytoscape_cli_writes_a_local_offline_asset(repo, tmp_path):
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()
    output = tmp_path / "impact.html"
    result = subprocess.run([
        "python3", "tool/project_impact_view.py", "--project-root", str(repo), "--base", base,
        "--format", "cytoscape", "--output", str(output),
    ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=True)
    receipt = json.loads(result.stdout)
    assert receipt["artifact"] == str(output)
    assert output.is_file() and output.with_name("cytoscape.min.js").is_file()
    assert "https://" not in output.read_text(encoding="utf-8")
