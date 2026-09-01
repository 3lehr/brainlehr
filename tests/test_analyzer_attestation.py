import pytest

from kern.analyzer_attestation import attest
from kern.project_context import witness_envelope


def base(**extra):
    value = dict(tool={"binary": "syft", "version": "1.0", "sha256": "a" * 64},
                 input_tree={"src/app.py": "b" * 64}, config={"rules": ["x"]},
                 policy={"network": "disabled"}, network_mode="disabled",
                 exit_code=0, output=b"normalized report", revision="r1",
                 advisory_db={"status": "fresh"}, sbom={"status": "fresh", "sha256": "c" * 64},
                 sandbox={"resource_limit": "applied", "network": "disabled"})
    value.update(extra)
    return value


def test_benign_attestation_and_p98_witness():
    row = attest(**base())
    assert row["status"] == "pass"
    assert row["witness"]["requirement_ids"] == ["P95"]
    assert "raw" not in row
    assert witness_envelope(witnesses=[row["witness"]])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_drift_and_stale_advisory_are_visible_gaps():
    first = attest(**base())
    second = attest(**base(config={"rules": ["changed"]}, advisory_db={"status": "stale"}))
    assert first["config_policy_sha256"] != second["config_policy_sha256"]
    assert second["status"] == "coverage_gap"
    assert "advisory database stale" in second["coverage_gaps"]


@pytest.mark.parametrize("field,value", [("input_tree", {"/etc/passwd": "x"}), ("output", {"raw": "secret"}),
                                          ("network_mode", "internet"), ("advisory_db", {"status": "wat"})])
def test_malicious_or_invalid_metadata_rejected(field, value):
    with pytest.raises(ValueError):
        attest(**base(**{field: value}))


def test_no_tool_is_explicit_gap_not_fake_install():
    row = attest(**base(tool=None))
    assert row["status"] == "coverage_gap"
    assert "tool identity unavailable" in row["coverage_gaps"]
    assert row["witness"]["tool"] == "unavailable"
    assert attest(**base(sandbox=None))["coverage_gaps"] == ["sandbox evidence missing"]


def test_tool_drift_and_non_digest_input_are_not_silently_equivalent():
    first = attest(**base())
    second = attest(**base(tool={"binary": "syft", "version": "1.1", "sha256": "d" * 64}))
    assert first["tool"] != second["tool"]
    with pytest.raises(ValueError, match="input tree"):
        attest(**base(input_tree="raw source"))
