import json

from kern.incident_lifecycle import IncidentLifecycle, as_evidence_witness
from kern.project_context import witness_envelope


def test_incident_lifecycle_is_ordered_append_only_and_verified(tmp_path):
    path = tmp_path / "incidents.json"
    lifecycle = IncidentLifecycle(path)
    assert lifecycle.append(incident_id="inc-1", stage="recover") == {
        "status": "REJECT", "coverage_gaps": ["invalid_lifecycle_transition"]}
    assert not path.exists()

    assert lifecycle.append(incident_id="inc-1", stage="detect")["status"] == "OPEN"
    assert lifecycle.append(incident_id="inc-1", stage="contain")["status"] == "OPEN"
    assert lifecycle.append(incident_id="inc-1", stage="recover")["status"] == "OPEN"
    unresolved = lifecycle.append(
        incident_id="inc-1", stage="verify", revision=" ",
        artifact_hash=" ", config_hash=" ")
    assert unresolved == {"status": "UNKNOWN", "coverage_gaps": ["verification_identity_missing"]}

    verified = lifecycle.append(
        incident_id="inc-1", stage="verify", revision="r1",
        artifact_hash="a" * 64, config_hash="c" * 64)
    assert verified["status"] == "PASS"
    stored = json.loads(path.read_text())["incidents"]["inc-1"]
    assert [event["stage"] for event in stored] == ["detect", "contain", "recover", "verify"]
    assert all(len(event["event_sha256"]) == 64 for event in stored)
    witness = as_evidence_witness(verified, witness_id="p85-incident")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_incident_lifecycle_rejects_blank_id_and_duplicate_transition(tmp_path):
    lifecycle = IncidentLifecycle(tmp_path / "incidents.json")
    try:
        lifecycle.append(incident_id=" ", stage="detect")
    except ValueError as error:
        assert "incident_id" in str(error)
    else:
        raise AssertionError("blank incident id accepted")
    lifecycle.append(incident_id="inc-1", stage="detect")
    assert lifecycle.append(incident_id="inc-1", stage="detect") == {
        "status": "REJECT", "coverage_gaps": ["invalid_lifecycle_transition"]}
