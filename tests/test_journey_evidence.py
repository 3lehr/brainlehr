from kern.journey_evidence import as_evidence_witness, journey_envelope
from kern.project_context import witness_envelope


META = dict(requirement_id="P90", journey_id="journey.login", revision="r1", config_hash="c1",
            artifact_hash="a1", browser_hash="b1", platform_hash="p1", start_state="signed_out",
            steps=[{"id": "open", "expected": "login", "observed": "login"}],
            recovery={"id": "retry", "expected": "login", "observed": "login"},
            expected_outcome="signed_in", observed_outcome="signed_in", accessibility={"status": "pass", "tool_hash": "axe1"})


def test_recovery_and_automation_do_not_auto_approve_human_comprehension():
    result = journey_envelope(**META)
    assert result["automation_status"] == "PASS"
    assert result["status"] == "UNKNOWN"
    assert result["human_comprehension"]["status"] == "pending"
    assert "human_comprehension_pending" in result["coverage_gaps"]


def test_a11y_failure_and_missing_browser_are_visible():
    failed = journey_envelope(**dict(META, accessibility={"status": "fail", "tool_hash": "axe1"}))
    assert failed["status"] == "FAIL"
    missing = journey_envelope(**dict(META, browser_hash=None))
    assert missing["status"] == "UNKNOWN"
    assert "browser_or_platform_evidence_missing" in missing["coverage_gaps"]
    no_adapter = journey_envelope(**dict(META, accessibility={"status": "pass"}))
    assert "accessibility_adapter_missing" in no_adapter["coverage_gaps"]


def test_bound_operator_witness_is_explicit_and_p98_loadable():
    approved = journey_envelope(**dict(META, operator_witness={"witness_id": "operator-p90",
                                                               "revision": "r1", "artifact_hash": "a1",
                                                               "verdict": "approved"}))
    assert approved["status"] == "PASS"
    witness = as_evidence_witness(approved, witness_id="w-p90", independence_group="browser",
                                  lineage_id="journey-login")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}
