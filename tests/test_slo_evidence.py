from kern.project_context import witness_envelope
from kern.slo_evidence import as_evidence_witness, evaluate_slo


def contract():
    return {"metric": "latency", "unit": "ms", "window": "5m",
            "load_profile": {"users": 10}, "threshold": 200,
            "direction": "at_most", "quantile": "p95"}


def evidence(**updates):
    value = {"revision": "r1", "config_hash": "c1", "environment_hash": "e1",
             "tool_hashes": {"prometheus": "t1"}, "sample_count": 10,
             "observed_quantiles": {"p95": 150}, "errors": {},
             "degradation": {"observed": False}, "recovery": {"observed": True}}
    return {**value, **updates}


def test_slo_pass_fail_and_p98_witness():
    passed = evaluate_slo(contract(), evidence())
    assert passed["status"] == "PASS"
    assert evaluate_slo(contract(), evidence(observed_quantiles={"p95": 250}))["status"] == "FAIL"
    witness = as_evidence_witness(passed, witness_id="w-p94", requirement_ids=["P94"],
                                  independence_group="load", lineage_id="run-1")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_slo_rejects_mismatch_stale_and_insufficient_data():
    assert evaluate_slo(contract(), evidence(unit="s"))["gap"] == "unit_mismatch"
    assert evaluate_slo(contract(), evidence(config_current=False))["gap"] == "stale_config"
    assert evaluate_slo(contract(), evidence(), expected_config_hash="other")["gap"] == "stale_config"
    assert evaluate_slo(contract(), evidence(sample_count=0))["gap"] == "insufficient_samples"
    assert evaluate_slo({**contract(), "threshold": None}, evidence())["gap"] == "invalid_threshold"


def test_degradation_requires_observed_recovery():
    result = evaluate_slo(contract(), evidence(degradation={"observed": True}, recovery={"observed": False}))
    assert result["status"] == "FAIL"
    assert result["coverage_gaps"] == ["degradation_not_recovered"]
