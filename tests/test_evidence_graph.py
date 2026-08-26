from kern.evidence_adapters import normalize_record, unavailable_record
from kern.evidence_graph import reconcile


def test_graph_v2_retains_revision_conflict_and_degraded_gap():
    snapshot = {"source_revision": "r1", "nodes": [], "edges": [], "coverage_gaps": []}
    good = normalize_record("scip", {"source": "scip", "revision": "r1", "documents": [], "occurrences": []})
    stale = normalize_record("semgrep", {"source": "semgrep", "revision": "r0", "results": []})
    gap = unavailable_record("joern", "r1", "joern executable unavailable")
    first = reconcile(snapshot, [good, stale, gap])
    assert first["schema"] == 2 and first["evidence"][0]["strength"] == "symbol"
    assert first["conflicts"][0]["kind"] == "revision_mismatch"
    assert "joern executable unavailable" in first["coverage_gaps"]
    assert first == reconcile(snapshot, [good, stale, gap])
