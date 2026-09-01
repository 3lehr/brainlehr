"""P40/P41/P44: all normalized channels reconcile, conflict, and select transitively."""
import json
from pathlib import Path

from kern.evidence_adapters import normalize_record
from kern.evidence_graph import reconcile, transitive_selection


FIXTURES = Path(__file__).parent / "fixtures" / "evidence_adapters"


def _fixture(kind):
    names = {"tree_sitter": "tree_sitter_js.json", "scip": "scip.json",
             "joern": "joern_cpg.json", "otlp": "otlp.json", "semgrep": "semgrep.json"}
    payload = json.loads((FIXTURES / names[kind]).read_text())
    payload["revision"] = "fixture-e2e-r1"
    return normalize_record(kind, payload)


def test_all_channels_reconcile_conflict_and_select_indirect_consumers():
    fragments = [_fixture(kind) for kind in ("tree_sitter", "scip", "joern", "otlp", "semgrep")]
    revision = fragments[0]["revision"]
    snapshot = {"source_revision": revision, "nodes": [], "edges": [
        {"from": "changed.py", "to": "direct.py", "edge_type": "import"},
        {"from": "direct.py", "to": "indirect_test.py", "edge_type": "import"}],
        "coverage_gaps": ["dynamic imports"]}
    # A second analyzer claiming the same edge remains visible as conflict.
    fragments[1]["edges"].append({"from": "changed.py", "to": "direct.py", "type": "import"})
    merged = reconcile(snapshot, fragments)
    assert {item["kind"] for item in merged["conflicts"]} >= {"edge_evidence_conflict"}
    selected = transitive_selection(merged, ["changed.py"])
    assert [(item["id"], item["distance"]) for item in selected["selected"]] == [
        ("changed.py", 0), ("direct.py", 1), ("indirect_test.py", 2)]
    assert selected["coverage_gaps"] == ["dynamic imports"]
