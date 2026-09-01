import pytest

from kern.project_context import witness_envelope
from kern.runtime_config_evidence import as_evidence_witness, runtime_config_evidence


HASH_A, HASH_B = "a" * 64, "b" * 64


def test_current_runtime_config_is_hash_only_and_projects_to_p98():
    result = runtime_config_evidence({"revision": "r1", "config_hash": HASH_A, "environment_hash": HASH_B, "state": "current"}, revision="r1", config_hash=HASH_A, environment_hash=HASH_B)
    assert result["status"] == "PASS"
    assert witness_envelope(witnesses=[as_evidence_witness(result, witness_id="p82")])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_stale_missing_mismatched_and_raw_runtime_config_fail_closed():
    stale = runtime_config_evidence({"revision": "old", "config_hash": HASH_B, "environment_hash": HASH_A, "state": "unknown"}, revision="r1", config_hash=HASH_A, environment_hash=HASH_B)
    assert {"runtime_revision_mismatch", "runtime_config_stale", "runtime_environment_mismatch", "runtime_config_state_unknown"} <= set(stale["coverage_gaps"])
    missing = runtime_config_evidence({"revision": "r1", "config_hash": HASH_A, "environment_hash": HASH_B, "state": "missing"}, revision="r1", config_hash=HASH_A, environment_hash=HASH_B)
    assert "runtime_config_missing" in missing["coverage_gaps"]
    with pytest.raises(ValueError, match="values"):
        runtime_config_evidence({"value": "secret"}, revision="r1", config_hash=HASH_A, environment_hash=HASH_B)
