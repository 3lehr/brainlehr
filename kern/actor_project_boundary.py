"""Fail-closed local actor/project checks.

This module is deliberately stateless: durable identity and remote tenancy are
outside Brainlehr's local authority and therefore return an explicit gap.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence


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
