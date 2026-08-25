from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import pytest

import knowledge_mcp_server as kms
import project_context


def _run(root: Path, *args: str) -> None:
    subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture()
def project(tmp_path, monkeypatch):
    root = tmp_path / "sample"
    root.mkdir()
    _run(root, "git", "init", "-q")
    _run(root, "git", "config", "user.email", "test@example.invalid")
    _run(root, "git", "config", "user.name", "Test")
    (root / "app.py").write_text(
        '"""Feedback architecture entry point."""\n\ndef feedback_loop():\n    return "explicit"\n',
        encoding="utf-8",
    )
    (root / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "service.py").write_text("import core\n\ndef value(): return core.VALUE\n", encoding="utf-8")
    (root / "api.py").write_text("import service\n\ndef output(): return service.value()\n", encoding="utf-8")
    (root / "cycle_a.py").write_text("import cycle_b\nA = 1\n", encoding="utf-8")
    (root / "cycle_b.py").write_text("import cycle_a\nB = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname="sample"\nversion="0"\n[project.scripts]\nsample-check="app:feedback_loop"\n',
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps({"scripts": {"diagram": "node diagram.js"}}), encoding="utf-8")
    _run(root, "git", "add", "app.py", "core.py", "service.py", "api.py",
         "cycle_a.py", "cycle_b.py", "pyproject.toml", "package.json")
    _run(root, "git", "commit", "-qm", "fixture")

    db = tmp_path / "knowledge.db"
    conn = sqlite3.connect(db)
    conn.executescript((Path(__file__).parents[1] / "schema.sql").read_text())
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    return root, db


def test_ensure_adopts_existing_project_and_second_run_changes_nothing(project):
    root, db = project
    existing = kms.knowledge_add(
        "/", "Existing project decision", "Existing scoped knowledge",
        "Verified before project-context adoption.", project_id="sample",
        source=f"generated from {root}/app.py at Git HEAD",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Test fact.")
    assert existing["status"] == "created"

    first = kms.project_ensure(str(root), "sample")
    assert first["before"] == "missing"
    assert first["knowledge_state"] == "adopted"
    marker_bytes = (root / project_context.MANIFEST).read_bytes()

    second = kms.project_ensure(str(root), "sample")
    assert second["changed"] is False
    assert second["knowledge_changed"] is False
    assert second["knowledge_state"] == "current"
    assert (root / project_context.MANIFEST).read_bytes() == marker_bytes
    conn = sqlite3.connect(db)
    roots = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE project_id='sample' "
        "AND tags LIKE '%project-context-root%'"
    ).fetchone()[0]
    conn.close()
    assert roots == 1


def test_ensure_adopts_even_if_an_old_lesson_has_non_json_projects(project):
    root, db = project
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, projects, status) "
        "VALUES ('L-legacy', 'pattern', 'Historic project reference', 'sample', 'active')"
    )
    conn.commit()
    conn.close()
    ensured = kms.project_ensure(str(root), "sample")
    assert ensured["knowledge_state"] == "adopted"
    assert ensured["existing_project_entries"] == 1


def test_manifest_states_and_refresh_are_explicit(project):
    root, _ = project
    marker = root / project_context.MANIFEST
    assert project_context.inspect_manifest(root)["state"] == "missing"
    marker.write_text("not json", encoding="utf-8")
    assert project_context.inspect_manifest(root)["state"] == "partial"
    project_context.ensure_manifest(root, project_id="sample")
    assert project_context.inspect_manifest(root)["state"] == "current"
    data = json.loads(marker.read_text())
    data["schema"] = 0
    marker.write_text(json.dumps(data), encoding="utf-8")
    assert project_context.inspect_manifest(root)["state"] == "stale"


def test_new_commit_keeps_manifest_stable_but_marks_knowledge_capsule_stale(project):
    root, _ = project
    kms.project_ensure(str(root), "sample")
    marker = root / project_context.MANIFEST
    before = marker.read_bytes()
    (root / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
    _run(root, "git", "add", "core.py")
    _run(root, "git", "commit", "-qm", "change core")
    assert marker.read_bytes() == before
    assert project_context.inspect_manifest(root)["state"] == "current"
    stale = kms.project_context_get(str(root), "feedback")
    assert stale["state"] == "stale"
    assert stale["current_head"] != stale["stored_head"]


def test_tool_registry_keeps_planned_tools_non_callable_and_task_scoped(project):
    root, _ = project
    ensured = project_context.ensure_manifest(root, project_id="sample", tools=[{
        "id": "architecture-graph",
        "capability": "build architecture dependency graph",
        "status": "planned",
        "reference": "docs/PLAN_ARCHITECTURE.md#tool",
        "when": "architecture dependency investigation",
    }])
    assert {tool["id"] for tool in ensured["manifest"]["tools"]} == {"architecture-graph"}
    capsule_tools = project_context.capsule(root)["declared_tools"]
    assert {tool["id"] for tool in capsule_tools} >= {"sample-check", "npm:diagram"}
    merged = {"tools": project_context.all_tools(ensured["manifest"], project_context.capsule(root))}
    relevant = project_context.relevant_tools(merged, "architecture dependency")
    planned = next(tool for tool in relevant if tool["id"] == "architecture-graph")
    assert planned["callable"] is False
    assert "command" not in planned
    assert project_context.relevant_tools(ensured["manifest"], "invoice tax") == []
    override = project_context.all_tools({"tools": [{
        "id": "sample-check", "capability": "planned replacement", "status": "planned",
        "reference": "docs/PLAN_ARCHITECTURE.md#replacement",
    }]}, project_context.capsule(root))
    assert [tool for tool in override if tool["id"] == "sample-check"] == [{
        "id": "sample-check", "capability": "planned replacement", "status": "planned",
        "reference": "docs/PLAN_ARCHITECTURE.md#replacement",
    }]
    tool_schema = kms.TOOLS["project_ensure"]["inputSchema"]["properties"]["tools"]["items"]["properties"]
    assert {"covers", "edge_types", "artifact"} <= set(tool_schema)
    with pytest.raises(ValueError, match="must not expose"):
        project_context.ensure_manifest(root, tools=[{
            "id": "future", "capability": "future tool", "status": "planned",
            "command": "future", "reference": "PLAN.md",
        }])


def test_context_ladder_requires_selection_and_returns_bounded_evidence(project):
    root, _ = project
    kms.project_ensure(str(root), "sample")
    node = kms.knowledge_add(
        "/", "Feedback architecture", "Explicit feedback architecture decision",
        "A reusable semantic statement, not a source-code dump.", project_id="sample",
        source=f"verified in {root}/app.py:3 at Git HEAD",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Test fact.")
    assert node["status"] == "created"

    summary = kms.project_context_get(str(root), "feedback architecture")
    assert summary["depth"] == "summary"
    assert "full" not in summary and "relations" not in summary
    assert summary["choice"]["must_not"].startswith("recursively")
    assert len(summary["knowledge_summaries"]) <= 5
    assert len(summary["code_hits"]) <= project_context.MAX_CODE_HITS
    assert any(hit["path"] == "app.py" for hit in summary["code_hits"])

    with pytest.raises(ValueError, match="requires explicitly selected"):
        kms.project_context_get(str(root), "feedback architecture", depth="full")
    with pytest.raises(ValueError, match="at most 3"):
        project_context.selection_contract("relations", ["1", "2", "3", "4"])
    full = kms.project_context_get(
        str(root), "feedback architecture", depth="full",
        selected_node_ids=[node["id"]])
    assert full["full"][0]["id"] == node["id"]
    assert "source-code dump" in full["full"][0]["content"]


def test_context_refuses_stale_or_uninitialized_project(project):
    root, _ = project
    result = kms.project_context_get(str(root), "feedback")
    assert result["state"] == "missing"
    assert result["next"].startswith("call project_ensure")


def test_change_receipt_follows_indirect_consumers_lazily_and_terminates_cycles(project):
    root, db = project
    kms.project_ensure(str(root), "sample")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True).stdout.strip()
    (root / "core.py").write_text("VALUE = 3\n", encoding="utf-8")
    _run(root, "git", "add", "core.py")
    _run(root, "git", "commit", "-qm", "change provider")

    first = kms.project_change_record(
        str(root), base, "Core value changed; consumers require validation.",
        ["pytest -q"], max_distance=1)
    assert first["consumers_by_distance"] == {"1": ["service.py"]}
    assert first["deeper_distances_available"] == [2]
    assert first["receipt"]["consumer_counts_by_distance"] == {"1": 1, "2": 1}

    deeper = kms.project_change_record(
        str(root), base, "Core value changed; consumers require validation.",
        ["pytest -q"], max_distance=2)
    assert deeper["consumers_by_distance"]["2"] == ["api.py"]
    assert deeper["receipt_node_id"] == first["receipt_node_id"]
    conn = sqlite3.connect(db)
    receipts = conn.execute(
        "SELECT content FROM knowledge_nodes WHERE project_id='sample' "
        "AND tags LIKE '%project-change-receipt%'"
    ).fetchall()
    conn.close()
    assert len(receipts) == 1
    assert json.loads(receipts[0][0])["base"] == first["receipt"]["base"]

    cycle_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True).stdout.strip()
    (root / "cycle_a.py").write_text("import cycle_b\nA = 2\n", encoding="utf-8")
    _run(root, "git", "add", "cycle_a.py")
    _run(root, "git", "commit", "-qm", "change cycle")
    cycle = project_context.impact_chain(root, cycle_base)
    assert cycle["consumers_by_distance"] == {"1": ["cycle_b.py"]}


def test_change_receipts_are_append_only_and_ambiguous_imports_are_not_edges(project):
    root, db = project
    kms.project_ensure(str(root), "sample")
    first_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True).stdout.strip()
    (root / "core.py").write_text("VALUE = 4\n", encoding="utf-8")
    _run(root, "git", "add", "core.py")
    _run(root, "git", "commit", "-qm", "first receipt")
    first = kms.project_change_record(str(root), first_base, "First verified change.", ["pytest -q"])

    second_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True).stdout.strip()
    (root / "core.py").write_text("VALUE = 5\n", encoding="utf-8")
    _run(root, "git", "add", "core.py")
    _run(root, "git", "commit", "-qm", "second receipt")
    second = kms.project_change_record(str(root), second_base, "Second verified change.", ["pytest -q"])
    assert first["receipt_node_id"] != second["receipt_node_id"]
    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE project_id='sample' "
        "AND tags LIKE '%project-change-receipt%'"
    ).fetchone()[0]
    conn.close()
    assert count == 2

    ambiguous_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True).stdout.strip()
    (root / "one").mkdir()
    (root / "two").mkdir()
    (root / "one" / "shared.py").write_text("ONE = 1\n", encoding="utf-8")
    (root / "two" / "shared.py").write_text("TWO = 2\n", encoding="utf-8")
    (root / "ambiguous_consumer.py").write_text("import shared\n", encoding="utf-8")
    _run(root, "git", "add", "one/shared.py", "two/shared.py", "ambiguous_consumer.py")
    _run(root, "git", "commit", "-qm", "add ambiguous import")
    ambiguous = project_context.impact_chain(root, ambiguous_base)
    assert ambiguous["coverage_status"] == "coverage_gap"
    assert ambiguous["ambiguous_imports"]
    assert all(edge["to"] != "ambiguous_consumer.py" for edge in ambiguous["impact_edges"])


def test_deleted_provider_keeps_base_consumers_in_impact_chain(project):
    root, _ = project
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True).stdout.strip()
    _run(root, "git", "rm", "core.py")
    _run(root, "git", "commit", "-qm", "remove provider")
    impact = project_context.impact_chain(root, base)
    assert "core.py" in impact["changed_files"]
    assert impact["consumers_by_distance"]["1"] == ["service.py"]
