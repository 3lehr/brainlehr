from kern.evidence_adapters import normalize_runtime_artifact
from kern.evidence_graph import reconcile


def _artifact(**extra):
    value = {"revision": "rev-1", "tree_hash": "tree-1", "tool": "openlehr",
             "tool_version": "1.2", "provenance": "isolated-test", "registered": True}
    value.update(extra)
    return value


def test_runtime_artifact_is_bounded_and_requires_exactly_once_probe():
    result = normalize_runtime_artifact(_artifact(
        generated_writes=["docs/reports.jsonl", "/secret", "../outside", "docs/reports.jsonl"],
        ingress=["foreground", "background"], event_identity="report:1"))
    assert result["generated_writes"] == ["docs/reports.jsonl"]
    assert result["event_identity_hash"] and "report:1" not in str(result)
    assert result["required_next_probe"] == "exactly_once"
    assert "missing_exactly_once_evidence" in result["coverage_gaps"]


def test_runtime_artifact_keeps_gaps_for_caller_supplied_proof_booleans():
    result = normalize_runtime_artifact(_artifact(generator_or_test=True))
    assert result["required_next_probe"] == "test_isolation"
    opaque = normalize_runtime_artifact(_artifact(
        generator_or_test=True, proof={"isolated_output_boundary": True,
                                       "cardinality": True}, ingress=["one", "two"]))
    assert opaque["status"] == "observed"
    assert opaque["required_next_probes"] == ["exactly_once", "test_isolation"]
    assert {"missing_exactly_once_evidence", "missing_isolated_output_boundary"} <= set(opaque["coverage_gaps"])


def test_unregistered_artifact_stays_a_gap_even_with_runtime_fields():
    result = normalize_runtime_artifact(_artifact(registered=False))
    assert result["status"] == "coverage_gap"
    assert result["coverage_gaps"] == ["unregistered_tool_result"]


def test_registered_runtime_write_reconciles_with_hash_only_event_identity_and_gap():
    fragment = normalize_runtime_artifact(_artifact(
        generated_writes=["docs/reports.jsonl"], ingress=["listener", "watch"],
        event_identity="trip-42"))
    graph = reconcile({"source_revision": "rev-1", "nodes": [], "edges": []}, [fragment])
    assert any(edge["edge_type"] == "runtime_generated_write" for edge in graph["edges"])
    assert graph["required_next_probe"] == ["exactly_once"]
    assert "missing_exactly_once_evidence" in graph["coverage_gaps"]
    assert "trip-42" not in str(graph)


def test_openlehr_gold_never_claims_a_current_read_only_index_test_wrote_reports():
    current = normalize_runtime_artifact(_artifact(
        tool="openlehr-knowledge-index", generator_or_test=False,
        provenance="OpenLehr 7bfb3ccc exact test in disposable worktree"))
    assert current["generated_writes"] == []
    assert current["required_next_probe"] is None

    seeded_hidden_write = normalize_runtime_artifact(_artifact(
        tool="openlehr-knowledge-index", generator_or_test=True,
        provenance="P73 deterministic hidden-write fixture",
        generated_writes=["docs/openlehr/reports/reports.jsonl",
                          "docs/openlehr/reports/reports/2026-08/report_001.json"]))
    assert seeded_hidden_write["status"] == "observed"
    assert seeded_hidden_write["required_next_probe"] == "test_isolation"
    assert seeded_hidden_write["generated_writes"] == [
        "docs/openlehr/reports/reports.jsonl",
        "docs/openlehr/reports/reports/2026-08/report_001.json"]


def test_runtime_cardinality_distinguishes_same_event_from_a_later_event_without_clearing_probe():
    common = dict(proof={"cardinality": True}, ingress=["listener", "watch"])
    first = normalize_runtime_artifact(_artifact(event_identity="trip-1", **common))
    retry = normalize_runtime_artifact(_artifact(event_identity="trip-1", **common))
    later = normalize_runtime_artifact(_artifact(event_identity="trip-2", **common))
    assert first["event_identity_hash"] == retry["event_identity_hash"]
    assert first["event_identity_hash"] != later["event_identity_hash"]
    assert all(item["required_next_probe"] == "exactly_once" for item in (first, retry, later))
