from kern.behavioral_oracle import evaluate


META = {"revision": "abc123", "config_hash": "sha256:cfg", "artifact": "wheel:sha256:art"}


def test_independent_control_and_matching_behavior_pass():
    result = evaluate({"count": 2, "keys": ["a", "b"]}, {"count": 2, "keys": ["a", "b"]}, metadata=META, independent_control=lambda: True)
    assert result["status"] == "PASS"


def test_mismatch_fails():
    result = evaluate(2, 3, metadata=META, independent_control=True)
    assert result["status"] == "FAIL"


def test_missing_or_identical_independent_evidence_is_unknown():
    assert evaluate(1, 1, metadata=META)["gap"] == "missing_independent_control"
    assert evaluate(1, 1, metadata=META, independent_control=True, high_risk=True)["gap"] == "self_oracle"


def test_invalid_metadata_or_control_fails_closed():
    assert evaluate(1, 1, metadata={"revision": "r"}, independent_control=True)["gap"] == "invalid_metadata"
    assert evaluate(1, 1, metadata=META, independent_control=False)["gap"] == "invalid_independent_control"
