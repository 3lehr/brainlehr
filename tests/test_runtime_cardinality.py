from kern.project_context import witness_envelope
from kern.runtime_cardinality import as_evidence_witness, evaluate_runtime


META = {"revision": "r1", "tree_hash": "t1", "config_hash": "c1", "artifact_hash": "a1"}
ORACLE = {"status": "PASS"}


def event(key, ingress="ui", target="dialog"):
    return {"event_key": key, "kind": "ui", "target": target, "ingress": ingress}


def test_same_trip_key_duplicate_fails_and_later_key_passes():
    events = [event("trip-1", "save"), event("trip-1", "retry"), event("trip-2")]
    duplicate = evaluate_runtime(events, expected_count=1, event_key="trip-1", metadata=META, oracle=ORACLE)
    later = evaluate_runtime(events, expected_count=1, event_key="trip-2", metadata=META, oracle=ORACLE)
    assert (duplicate["status"], duplicate["observed_count"]) == ("FAIL", 2)
    assert later["status"] == "PASS"
    assert "trip-1" not in str(duplicate)


def test_static_candidates_never_prove_runtime_and_missing_trace_is_gap():
    result = evaluate_runtime(None, expected_count=1, event_key="trip-1", metadata=META,
                              oracle=ORACLE, static_candidates=("a.py", "b.py"))
    assert result["status"] == "UNKNOWN"
    assert result["gap"] == "missing_runtime_trace"


def test_dynamic_dispatch_observed_and_unobserved_are_separate():
    result = evaluate_runtime([event("k", target="plugin:one")], expected_count=1, event_key="k",
                              metadata=META, oracle=ORACLE,
                              dispatch_targets=(
                                  {"target": "plugin:one", "kind": "plugin"},
                                  {"target": "reflect:two", "kind": "reflection"},
                                  {"target": "generated:three", "kind": "generated"},
                              ))
    assert result["status"] == "PASS"
    assert [item["status"] for item in result["dispatch"]] == ["observed", "UNKNOWN", "UNKNOWN"]
    assert len(result["coverage_gaps"]) == 2


def test_high_risk_requires_independent_oracle_and_metadata():
    assert evaluate_runtime([], expected_count=0, event_key="k", metadata=META)["gap"] == "missing_independent_oracle"
    assert evaluate_runtime([], expected_count=0, event_key="k", metadata=META, oracle={"status": "UNKNOWN"})["status"] == "UNKNOWN"
    assert evaluate_runtime([], expected_count=0, event_key="k", metadata={"revision": "r1"}, oracle=ORACLE)["gap"] == "invalid_metadata"


def test_runtime_result_is_a_non_normative_p98_witness():
    result = evaluate_runtime([event("trip-1")], expected_count=1, event_key="trip-1",
                              metadata=META, oracle=ORACLE)
    witness = as_evidence_witness(result, witness_id="w-runtime-1", requirement_ids=["P88"],
                                  independence_group="runner", lineage_id="trace-1")
    envelope = witness_envelope(witnesses=[witness])
    assert envelope["normative"] is False
    assert envelope["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}
