import json
import subprocess
import sys

import knowledge_mcp_server as kms
from kern.actor_project_boundary import durable_operation, reject_injection, restart_idempotency, validate_actor_project


def test_local_actor_cannot_cross_project_and_remote_is_a_gap():
    assert validate_actor_project(actor="worker", project_id="a",
                                  requested_project="b")["status"] == "denied"
    assert validate_actor_project(actor="worker", project_id="a", remote=True)["status"] == "coverage_gap"
    assert validate_actor_project(actor="worker", project_id="a")["status"] == "allowed"


def test_mcp_boundary_denies_remote_and_cross_project_before_tenant_auth():
    handler = kms.TOOLS["project_actor_boundary"]["handler"]
    assert handler({"actor": "worker", "project_id": "a", "requested_project": "b"})["status"] == "denied"
    remote = handler({"actor": "worker", "project_id": "a", "remote": True})
    assert remote == {"status": "coverage_gap", "allow": False,
                      "coverage_gaps": ["remote tenant/auth is not locally verifiable"]}


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


def test_separate_process_restart_replays_durable_receipt_once(tmp_path):
    store = tmp_path / "receipts.jsonl"
    script = ("import json,sys; from kern.actor_project_boundary import durable_operation; "
              "print(json.dumps(durable_operation(sys.argv[1],correlation_id='c1',request={'project':'a','action':'analyze'})))")
    first = subprocess.run([sys.executable, "-c", script, str(store)], capture_output=True, text=True, check=True)
    second = subprocess.run([sys.executable, "-c", script, str(store)], capture_output=True, text=True, check=True)
    assert json.loads(first.stdout)["status"] == "new"
    assert json.loads(second.stdout)["status"] == "replay"
    assert len(store.read_text(encoding="utf-8").splitlines()) == 1
    assert durable_operation(store, correlation_id="c1", request={"project": "a", "action": "different"})["status"] == "denied"
