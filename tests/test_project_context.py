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
    (root / "provider.py").write_text("class SearchProvider:\n    pass\n", encoding="utf-8")
    (root / "store.py").write_text("def save(path):\n    return open(path, 'w')\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_journey.py").write_text("def test_journey():\n    assert True\n", encoding="utf-8")
    (root / "cycle_a.py").write_text("import cycle_b\nA = 1\n", encoding="utf-8")
    (root / "cycle_b.py").write_text("import cycle_a\nB = 1\n", encoding="utf-8")
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "pkg" / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "pkg" / "consumer.py").write_text("from . import helper\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname="sample"\nversion="0"\n[project.scripts]\nsample-check="app:feedback_loop"\n',
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps({"scripts": {"diagram": "node diagram.js"}}), encoding="utf-8")
    _run(root, "git", "add", "app.py", "core.py", "service.py", "api.py", "provider.py", "store.py", "tests/test_journey.py",
         "cycle_a.py", "cycle_b.py", "pkg/__init__.py", "pkg/helper.py", "pkg/consumer.py",
         "pyproject.toml", "package.json")
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
    assert first["capsule"]["schema"] == project_context.SCHEMA

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
    envelope = summary["context_envelope"]
    assert envelope["step"] == 8 and envelope["required_next_probe"] == "widen_to_32"
    assert envelope["working_hash"] is None and envelope["searched_scope"] == ["tracked-code"]
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


def test_context_completeness_envelope_only_widens_for_a_named_gap():
    fixed = dict(revision="r1", working_hash=None, searched_scope=["src/app.py"],
                 analyzer_versions={"static": "v1"}, proven_edge_types=["import"])
    smallest = project_context.context_completeness_envelope(**fixed, coverage_gaps=[])
    assert smallest["step"] == 8 and smallest["required_next_probe"] is None
    widened = project_context.context_completeness_envelope(**fixed, coverage_gaps=["dynamic import"], step=32)
    assert widened["required_next_probe"] == "load_selected_definition"
    assert widened == project_context.context_completeness_envelope(**fixed, coverage_gaps=["dynamic import"], step=32)
    with pytest.raises(ValueError, match="project-relative"):
        project_context.context_completeness_envelope(
            revision="r1", working_hash=None, searched_scope=["/host/path"],
            analyzer_versions={"static": "v1"}, proven_edge_types=["import"], coverage_gaps=[])


def test_witness_envelope_is_bounded_independent_and_read_only():
    def witness(index, *, verdict="pass", lineage=None, freshness="current", gaps=None):
        return {"id": f"w-{index:02d}", "requirement_ids": ["P98"],
                "kind": "test", "tool": "pytest", "tool_version": "8",
                "revision": "r1", "config_hash": "c1", "artifact_hash": f"a-{index:02d}",
                "verdict": verdict, "independence_group": lineage or f"g-{index}",
                "lineage_id": lineage or f"g-{index}", "freshness": freshness,
                "evidence_rank": "verified", "confidence": 0.9,
                "gaps": gaps or [], "observed_at": f"2026-08-26T00:00:{index:02d}Z"}
    witnesses = [witness(index, verdict="fail" if index == 19 else "pass",
                         lineage="lineage-a" if index < 3 else None,
                         freshness="stale" if index == 18 else "current",
                         gaps=["coverage gap"] if index == 17 else [])
                 for index in range(20)]
    envelope = project_context.witness_envelope(
        witnesses=witnesses, requirement_ids=["P98"], max_summary_bytes=100_000)
    summary = envelope["requirement_summaries"][0]
    assert summary["independence_group_count"] == 18  # Three wrappers, one lineage.
    assert summary["verdict_counts"] == {"fail": 1, "pass": 19}
    assert envelope["conflict"] is True and envelope["stale"] is True
    assert "coverage gap" in envelope["coverage_gaps"] and envelope["durable_writes"] == 0
    assert "raw_trace" not in json.dumps(envelope).casefold()
    capped = project_context.witness_envelope(
        witnesses=witnesses, max_summary_bytes=128)
    assert capped["truncated"] is True and capped["allowed_witness_ids"] == []
    with pytest.raises(ValueError, match="unknown witness"):
        project_context.witness_envelope(witnesses=witnesses, depth="full", selected_ids=["nope"])
    selected = project_context.witness_envelope(
        witnesses=witnesses, depth="full", selected_ids=["w-00"])
    assert [item["id"] for item in selected["witness_details"]] == ["w-00"]
    with pytest.raises(ValueError, match="unsupported or raw"):
        project_context.witness_envelope(witnesses=[{**witness(99), "raw_trace": "secret"}])


def test_project_context_exposes_witnesses_lazily_without_durable_write(project):
    root, db = project
    kms.project_ensure(str(root), "sample")
    witness = {
        "id": "w-p98", "requirement_ids": ["P98"], "kind": "test", "tool": "pytest",
        "tool_version": "8", "revision": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip(), "config_hash": "c1", "artifact_hash": "a1",
        "verdict": "pass", "independence_group": "g1", "lineage_id": "l1",
        "freshness": "current", "evidence_rank": "verified", "confidence": 1.0,
    }
    conn = sqlite3.connect(db)
    before = conn.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    conn.close()
    summary = kms.project_context_get(str(root), "P98 witnesses", evidence_witnesses=[witness])
    assert summary["evidence_witnesses"]["allowed_witness_ids"] == ["w-p98"]
    with pytest.raises(ValueError, match="unknown witness"):
        kms.project_context_get(str(root), "P98 witnesses", depth="full",
                                evidence_witnesses=[witness], selected_witness_ids=["nope"])
    full = kms.project_context_get(str(root), "P98 witnesses", depth="full",
                                   evidence_witnesses=[witness], selected_witness_ids=["w-p98"])
    assert full["evidence_witnesses"]["witness_details"][0]["id"] == "w-p98"
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM access_log").fetchone()[0] == before
    conn.close()


def test_capability_inventory_is_source_backed_bounded_and_lazy(project):
    root, _ = project
    kms.project_ensure(str(root), "sample")
    task = "Explain everything this repository can do"
    summary = kms.project_context_get(str(root), task)
    cards = summary["capability_cards"]
    assert cards and len(cards) <= project_context.MAX_CAPABILITY_CARDS
    assert {card["kind"] for card in cards} >= {"cli", "provider", "persistence", "test_journey"}
    for card in cards:
        assert set(card) >= {"id", "entrypoints", "triggers", "inputs", "phases", "timing",
                             "files", "symbols", "state_stores", "outputs", "side_effects",
                             "direct_consumers", "indirect_consumers", "provenance",
                             "coverage_gaps", "required_next_probe"}
        assert all(not item.startswith("/") for item in card["files"])
        assert "raw" not in json.dumps(card).casefold()
    coverage = summary["capability_discovery"]["discovery_coverage"]
    assert all(value["attempted"] for value in coverage.values())
    assert "build/deploy variants are not inspected" in summary["capability_discovery"]["coverage_gaps"]
    selected = cards[0]["id"]
    relations = kms.project_context_get(str(root), task, depth="relations", selected_node_ids=[selected])
    assert relations["capability_relations"][0]["id"] == selected
    full = kms.project_context_get(str(root), task, depth="full", selected_node_ids=[selected])
    assert full["capability_full"][0]["id"] == selected
    stale = kms.project_context_get(str(root), task,
                                    capability_config_hash="0" * 64)
    assert stale["state"] == "stale"


def test_capability_inventory_tracks_revision_and_rejects_unknown_card(project):
    root, _ = project
    kms.project_ensure(str(root), "sample")
    task = "Explain everything this repository can do"
    before = project_context.capability_inventory(root)
    with pytest.raises(ValueError, match="capability IDs"):
        kms.project_context_get(str(root), task, depth="full", selected_node_ids=["cap-unknown"])
    (root / "app.py").write_text("def main():\n    return 'changed'\n", encoding="utf-8")
    _run(root, "git", "add", "app.py")
    _run(root, "git", "commit", "-qm", "capability delta")
    after = project_context.capability_inventory(root)
    assert after["revision"] != before["revision"]
    with pytest.raises(ValueError, match="readable Git project"):
        project_context.capability_inventory(root.parent)


def test_capability_inventory_fails_closed_for_dirty_tracked_configuration(project):
    root, _ = project
    kms.project_ensure(str(root), "sample")
    _run(root, "git", "add", project_context.MANIFEST)
    _run(root, "git", "commit", "-qm", "track manifest")
    kms.project_ensure(str(root), "sample")
    (root / "pyproject.toml").write_text(
        (root / "pyproject.toml").read_text(encoding="utf-8") + "# dirty\n",
        encoding="utf-8")
    inventory = project_context.capability_inventory(root)
    assert inventory["state"] == "stale"
    assert inventory["config_binding"]["dirty"] == ["pyproject.toml"]
    result = kms.project_context_get(str(root), "Explain everything this repository can do")
    assert result["state"] == "stale"
    assert result["next"] == "commit_or_revert_discovery_configuration"


def test_manifest_tool_source_must_be_tracked_relative(project):
    root, _ = project
    with pytest.raises(ValueError, match="project-relative"):
        project_context.ensure_manifest(root, tools=[{
            "id": "leak", "capability": "leak", "status": "available",
            "command": "leak", "source": "/Users/operator/secret.py",
        }])
    with pytest.raises(ValueError, match="tracked project-relative"):
        project_context.ensure_manifest(root, tools=[{
            "id": "missing", "capability": "missing", "status": "available",
            "command": "missing", "source": "not-tracked.py",
        }])
    (root / project_context.MANIFEST).write_text(json.dumps({
        "schema": project_context.SCHEMA, "project_id": "sample", "tools": [{
            "id": "legacy", "capability": "legacy", "status": "available",
            "command": "legacy", "source": "/host/legacy.py",
        }],
    }), encoding="utf-8")
    assert project_context.inspect_manifest(root)["state"] == "partial"


def test_capability_inventory_preserves_family_accounting_at_96_file_bound(project):
    root, _ = project
    bulk = root / "zz_bulk"
    bulk.mkdir()
    for index in range(100):
        (bulk / f"unit_{index:03d}.py").write_text(
            f"def run_{index}():\n    return {index}\n", encoding="utf-8")
    _run(root, "git", "add", "zz_bulk")
    _run(root, "git", "commit", "-qm", "large static fixture")
    inventory = project_context.capability_inventory(root)
    assert inventory["state"] == "current"
    assert len(inventory["cards"]) <= project_context.MAX_CAPABILITY_CARDS
    assert {card["kind"] for card in inventory["cards"]} >= {
        "cli", "provider", "persistence", "test_journey",
    }
    for family in ("http_routes", "providers", "workflows", "persistence"):
        assert any("Python files unscanned" in item
                   for item in inventory["discovery_coverage"][family]["omitted"])
    assert "static capability scan bounded; unscanned Python files require selection" in inventory["coverage_gaps"]
    assert all("static consumers omitted because source scan is bounded" in card["coverage_gaps"]
               for card in inventory["cards"])


def test_capability_inventory_surfaces_nested_repo_and_unborn_head_boundaries(tmp_path):
    outer = tmp_path / "outer"
    outer.mkdir()
    _run(outer, "git", "init", "-q")
    _run(outer, "git", "config", "user.email", "test@example.invalid")
    _run(outer, "git", "config", "user.name", "Test")
    (outer / "README").write_text("outer\n", encoding="utf-8")
    _run(outer, "git", "add", "README")
    _run(outer, "git", "commit", "-qm", "outer")
    nested = outer / "nested"
    nested.mkdir()
    _run(nested, "git", "init", "-q")
    _run(nested, "git", "config", "user.email", "test@example.invalid")
    _run(nested, "git", "config", "user.name", "Test")
    (nested / "main.py").write_text("def main(): pass\n", encoding="utf-8")
    _run(nested, "git", "add", "main.py")
    _run(nested, "git", "commit", "-qm", "nested")
    nested_inventory = project_context.capability_inventory(nested)
    assert "nested repository boundary; outer repository is not analysed" in nested_inventory["coverage_gaps"]

    module_source = tmp_path / "module_source"
    module_source.mkdir()
    _run(module_source, "git", "init", "-q")
    _run(module_source, "git", "config", "user.email", "test@example.invalid")
    _run(module_source, "git", "config", "user.name", "Test")
    (module_source / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _run(module_source, "git", "add", "mod.py")
    _run(module_source, "git", "commit", "-qm", "module")
    _run(outer, "git", "-c", "protocol.file.allow=always", "submodule", "add", "-q",
         str(module_source), "vendor/module")
    _run(outer, "git", "commit", "-qm", "add module")
    outer_inventory = project_context.capability_inventory(outer)
    assert "submodule boundary; submodule contents are not analysed" in outer_inventory["coverage_gaps"]

    unborn = tmp_path / "unborn"
    unborn.mkdir()
    _run(unborn, "git", "init", "-q")
    with pytest.raises(ValueError, match="readable Git project"):
        project_context.capability_inventory(unborn)


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
    assert first["receipt"]["coverage_status"] == "static_python_imports_complete"
    assert first["receipt"]["impact_graph_schema"] == project_context.IMPACT_GRAPH_SCHEMA
    assert first["receipt"]["impact_graph_hash"] == first["impact_graph"]["content_hash"]
    assert first["visualization"]["source_revision"] == first["receipt"]["head"]
    assert first["deeper_distances_available"] == [2]
    assert first["receipt"]["consumer_counts_by_distance"] == {"1": 1, "2": 1}

    deeper = kms.project_change_record(
        str(root), base, "Core value changed; consumers require validation.",
        ["pytest -q"], max_distance=2)
    assert deeper["consumers_by_distance"]["2"] == ["api.py"]
    assert deeper["receipt_node_id"] == first["receipt_node_id"]
    corrected = kms.project_change_record(
        str(root), base, "Corrected verification statement.", ["pytest -q", "lint"], max_distance=2)
    assert corrected["receipt_node_id"] != first["receipt_node_id"]
    assert corrected["receipt"]["supersedes"] == first["receipt_node_id"]
    conn = sqlite3.connect(db)
    receipts = conn.execute(
        "SELECT content FROM knowledge_nodes WHERE project_id='sample' "
        "AND tags LIKE '%project-change-receipt%'"
    ).fetchall()
    conn.close()
    assert len(receipts) == 2
    assert json.loads(receipts[0][0])["base"] == first["receipt"]["base"]
    conn = sqlite3.connect(db)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM knowledge_embeddings WHERE ref_id IN "
            "(SELECT id FROM knowledge_nodes WHERE project_id='sample' AND tags LIKE '%project-change-receipt%')"
        ).fetchone()[0]
    finally:
        conn.close()
    assert count == 0, "machine graph receipts must not become prose vectors"

    cycle_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True).stdout.strip()
    (root / "cycle_a.py").write_text("import cycle_b\nA = 2\n", encoding="utf-8")
    _run(root, "git", "add", "cycle_a.py")
    _run(root, "git", "commit", "-qm", "change cycle")
    cycle = project_context.impact_chain(root, cycle_base)
    assert cycle["consumers_by_distance"] == {"1": ["cycle_b.py"]}


def test_change_receipt_never_rewrites_tracked_manifest(project):
    root, _ = project
    kms.project_ensure(str(root), "sample")
    marker = root / project_context.MANIFEST
    manifest = json.loads(marker.read_text(encoding="utf-8"))
    manifest["tools"] = [{
        "id": "sample-check", "capability": "sample check", "status": "available",
        "command": "sample-check", "source": "pyproject.toml [project.scripts]",
    }, {
        "id": "operator-tool", "capability": "operator tool", "status": "available",
        "command": "operator-tool", "source": "app.py",
    }]
    marker.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    before = marker.read_bytes()
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()
    (root / "core.py").write_text("VALUE = 7\n", encoding="utf-8")
    _run(root, "git", "add", "core.py")
    _run(root, "git", "commit", "-qm", "receipt must not alter manifest")

    receipt = kms.project_change_record(str(root), base, "Receipt-only check.", ["pytest -q"])

    assert receipt.get("receipt_node_id"), receipt
    assert marker.read_bytes() == before


def test_change_receipt_requires_explicit_project_context(project):
    root, _ = project
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()
    (root / "core.py").write_text("VALUE = 8\n", encoding="utf-8")
    _run(root, "git", "add", "core.py")
    _run(root, "git", "commit", "-qm", "receipt needs explicit context")

    result = kms.project_change_record(str(root), base, "Receipt-only check.", ["pytest -q"])

    assert result["state"] == "missing"
    assert not (root / project_context.MANIFEST).exists()


def test_equal_project_ids_fail_closed_before_receipt(project, tmp_path):
    root, db = project
    other = tmp_path / "other" / "sample"
    other.mkdir(parents=True)
    _run(other, "git", "init", "-q")
    _run(other, "git", "config", "user.email", "test@example.invalid")
    _run(other, "git", "config", "user.name", "Test")
    (other / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    _run(other, "git", "add", "core.py")
    _run(other, "git", "commit", "-qm", "other fixture")

    first = kms.project_ensure(str(root), "sample")
    project_context.ensure_manifest(other, project_id="sample")
    marker = other / project_context.MANIFEST
    before = marker.read_bytes()
    second = kms.project_ensure(str(other), "sample")
    assert first["knowledge_root_id"]
    assert second["error"] == "project_id is already bound to another manifest origin"
    assert marker.read_bytes() == before
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=other, check=True,
                          capture_output=True, text=True).stdout.strip()
    (other / "core.py").write_text("VALUE = 2\n", encoding="utf-8")
    _run(other, "git", "add", "core.py")
    _run(other, "git", "commit", "-qm", "other receipt")

    receipt = kms.project_change_record(str(other), base, "Other receipt.", ["pytest -q"])

    assert receipt["state"] == "partial"
    conn = sqlite3.connect(db)
    receipts = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE tags LIKE '%project-change-receipt%'"
    ).fetchone()[0]
    conn.close()
    assert receipts == 0


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


def test_relative_import_is_an_edge_and_non_python_change_is_a_coverage_gap(project):
    root, _ = project
    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()
    (root / "pkg" / "helper.py").write_text("VALUE = 2\n", encoding="utf-8")
    _run(root, "git", "add", "pkg/helper.py")
    _run(root, "git", "commit", "-qm", "change relative provider")
    impact = project_context.impact_chain(root, base)
    assert impact["consumers_by_distance"]["1"] == ["pkg/consumer.py"]
    assert impact["coverage_status"] == "static_python_imports_complete"

    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()
    (root / "runtime.py").write_text(
        "import importlib\nimportlib.import_module('optional')\n", encoding="utf-8")
    _run(root, "git", "add", "runtime.py")
    _run(root, "git", "commit", "-qm", "add dynamic import")
    dynamic = project_context.impact_chain(root, base)
    assert dynamic["coverage_status"] == "static_python_imports_with_known_unsupported_forms"
    assert dynamic["unsupported_static_forms"][0]["form"] == "dynamic_import"

    base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True,
                          capture_output=True, text=True).stdout.strip()
    (root / "README.md").write_text("changed\n", encoding="utf-8")
    _run(root, "git", "add", "README.md")
    _run(root, "git", "commit", "-qm", "change docs")
    assert project_context.impact_chain(root, base)["coverage_status"] == "coverage_gap"
