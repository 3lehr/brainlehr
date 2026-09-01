from kern.project_context import witness_envelope
from kern.workflow_impact import as_evidence_witness, evaluate_workflow_impact


def window(definition, numerator, denominator, revision="r2", samples=4):
    return {"definition": definition, "revision": revision, "window_start": "2026-01-01",
            "window_end": "2026-01-07", "numerator": numerator, "denominator": denominator,
            "samples": samples}


def pair():
    names = {"defect_near_miss_prevention": (1, 10, 3, 10), "rework": (4, 10, 2, 10),
             "time_to_green": (100, 2, 50, 2), "token_context_bytes": (1000, 2, 500, 2),
             "false_positive_cost": (20, 2, 5, 2)}
    return ({k: window(k, a, b, revision="r1") for k, (a, b, _, _) in names.items()},
            {k: window(k, c, d) for k, (_, _, c, d) in names.items()})


def test_improvement_and_p98_witness():
    baseline, comparison = pair()
    result = evaluate_workflow_impact(baseline, comparison, revision="r2", config_hash="c", artifact_hash="a")
    assert result["status"] == "PASS"
    witness = as_evidence_witness(result, witness_id="w-p97", requirement_ids=["P97"], lineage_id="run-1")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_regression_and_unknown_inputs_fail_closed():
    baseline, comparison = pair()
    comparison["rework"]["numerator"] = 9
    assert evaluate_workflow_impact(baseline, comparison, revision="r2")["status"] == "FAIL"
    assert evaluate_workflow_impact(baseline, {}, revision="r2")["status"] == "UNKNOWN"
    comparison["time_to_green"]["samples"] = 0
    assert evaluate_workflow_impact(baseline, comparison, revision="r2")["status"] == "UNKNOWN"
    comparison["time_to_green"]["samples"] = 2
    comparison["time_to_green"]["definition"] = "changed"
    assert evaluate_workflow_impact(baseline, comparison, revision="r2")["metrics"]["time_to_green"]["gap"] == "definition_drift"
    comparison["time_to_green"] = window("time_to_green", 50, 2)
    comparison["time_to_green"]["loc"] = 4
    assert evaluate_workflow_impact(baseline, comparison, revision="r2")["metrics"]["time_to_green"]["gap"] == "forbidden_productivity_proxy"
