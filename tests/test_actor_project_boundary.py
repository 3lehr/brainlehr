from kern.actor_project_boundary import reject_injection, restart_idempotency, validate_actor_project


def test_local_actor_cannot_cross_project_and_remote_is_a_gap():
    assert validate_actor_project(actor="worker", project_id="a",
                                  requested_project="b")["status"] == "denied"
    assert validate_actor_project(actor="worker", project_id="a", remote=True)["status"] == "coverage_gap"
    assert validate_actor_project(actor="worker", project_id="a")["status"] == "allowed"


def test_request_data_cannot_promote_control_fields():
    result = reject_injection({"task": "x", "tool": "project-commit-gate"})
    assert result["status"] == "rejected"
    assert reject_injection({"task": "x"})["status"] == "accepted"


def test_restart_replay_is_idempotent_and_missing_store_fails_closed():
    request = {"project": "a", "action": "analyze"}
    first = restart_idempotency(correlation_id="c1", request=request, receipts=[])
    assert first["status"] == "new"
    receipt = {"correlation_id": "c1", "request_hash": first["request_hash"]}
    assert restart_idempotency(correlation_id="c1", request=request,
                               receipts=[receipt])["status"] == "replay"
    assert restart_idempotency(correlation_id="c1", request=request)["status"] == "coverage_gap"
