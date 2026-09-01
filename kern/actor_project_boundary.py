"""Fail-closed local actor/project checks.

This module is deliberately stateless: durable identity and remote tenancy are
outside Brainlehr's local authority and therefore return an explicit gap.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path


_CONTROL_KEYS = frozenset({"mode", "tool", "policy", "operation", "capability"})


def validate_actor_project(*, actor: str, project_id: str,
                           requested_project: str | None = None,
                           remote: bool = False) -> dict:
    """Allow only an identified local actor addressing its own project."""
    if remote:
        return {"status": "coverage_gap", "allow": False,
                "coverage_gaps": ["remote tenant/auth is not locally verifiable"]}
    if not actor.strip() or not project_id.strip():
        return {"status": "denied", "allow": False,
                "coverage_gaps": ["actor and project are required"]}
    if requested_project is not None and requested_project != project_id:
        return {"status": "denied", "allow": False,
                "coverage_gaps": ["cross-project access denied"]}
    return {"status": "allowed", "allow": True, "actor": actor,
            "project_id": project_id}


def reject_injection(payload: Mapping[str, object]) -> dict:
    """Reject request data that tries to promote policy/tool control fields."""
    found = sorted(key for key in payload if key in _CONTROL_KEYS)
    if found:
        return {"status": "rejected", "allow": False,
                "coverage_gaps": ["request data cannot promote policy or tools"],
                "rejected_keys": found}
    return {"status": "accepted", "allow": True}


def restart_idempotency(*, correlation_id: str, request: Mapping[str, object],
                        receipts: Sequence[Mapping[str, object]] | None = None) -> dict:
    """Return replay/new, or a visible gap when restart evidence is absent."""
    if not correlation_id.strip():
        return {"status": "denied", "allow": False,
                "coverage_gaps": ["correlation_id is required"]}
    fingerprint = hashlib.sha256(
        json.dumps(dict(request), sort_keys=True, separators=(",", ":"), default=str)
        .encode("utf-8")
    ).hexdigest()
    for receipt in receipts or ():
        if receipt.get("correlation_id") != correlation_id:
            continue
        if receipt.get("request_hash") == fingerprint:
            return {"status": "replay", "allow": False,
                    "correlation_id": correlation_id, "request_hash": fingerprint}
        return {"status": "denied", "allow": False,
                "coverage_gaps": ["correlation reused with different request"]}
    if receipts is None:
        return {"status": "coverage_gap", "allow": False,
                "correlation_id": correlation_id,
                "coverage_gaps": ["restart receipt store was not supplied"]}
    return {"status": "new", "allow": True, "correlation_id": correlation_id,
            "request_hash": fingerprint}


def durable_operation(path: str | Path, *, correlation_id: str,
                      request: Mapping[str, object], max_failures: int = 3) -> dict:
    """Append one local operation receipt; a fresh process sees the same replay state."""
    target = Path(path)
    receipts: list[dict] = []
    if target.exists():
        try:
            receipts = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines() if line]
        except (OSError, ValueError, json.JSONDecodeError):
            return {"status": "coverage_gap", "allow": False, "coverage_gaps": ["operation receipt store unreadable"]}
    result = restart_idempotency(correlation_id=correlation_id, request=request, receipts=receipts)
    if result["status"] != "new":
        return result
    failures = sum(1 for row in receipts if row.get("status") == "failed")
    if failures >= max_failures:
        return {"status": "coverage_gap", "allow": False, "coverage_gaps": ["persistent circuit breaker open"]}
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"correlation_id": correlation_id, "request_hash": result["request_hash"], "status": "accepted"}
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {**result, "receipt": receipt}
