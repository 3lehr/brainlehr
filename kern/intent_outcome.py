"""Small, deterministic Intent -> Journey -> Evidence -> Outcome trace."""

from __future__ import annotations

from typing import Any

from .requirement_feasibility import validate_requirement


_ALLOWED = {
    "intent": {"id", "requirement"},
    "journey": {"id", "steps"},
    "evidence": {"id", "source", "measurement", "value"},
    "outcome": {"status", "observed"},
}
_STATUSES = {"success", "failure"}


def _clean(part: dict[str, Any], kind: str) -> dict[str, Any]:
    if not isinstance(part, dict) or set(part) - _ALLOWED[kind]:
        raise ValueError(f"invalid_{kind}_fields")
    if kind != "outcome" and (not isinstance(part.get("id"), str) or not part["id"].strip()):
        raise ValueError(f"missing_{kind}_id")
    return part


def build_trace(*, intent: dict[str, Any], journey: dict[str, Any],
                evidence: dict[str, Any], outcome: dict[str, Any],
                source_revision: str, tree_hash: str) -> dict[str, Any]:
    """Build a revision-bound trace; raw content and model labels are rejected."""
    if not isinstance(source_revision, str) or not source_revision.strip():
        raise ValueError("missing_source_revision")
    if not isinstance(tree_hash, str) or not tree_hash.strip():
        raise ValueError("missing_tree_hash")
    intent, journey, evidence, outcome = (
        _clean(intent, "intent"), _clean(journey, "journey"),
        _clean(evidence, "evidence"), _clean(outcome, "outcome"))
    if not isinstance(intent.get("requirement"), dict):
        raise ValueError("missing_requirement")
    feasibility = validate_requirement(intent["requirement"])
    if feasibility["status"] != "feasible":
        return {"status": "unmeasurable", "coverage_gaps": feasibility["coverage_gaps"],
                "source_revision": source_revision, "tree_hash": tree_hash}
    if (not isinstance(journey.get("steps"), list) or not journey["steps"]
            or len(journey["steps"]) > 32
            or any(not isinstance(step, str) or not step.strip() or len(step) > 96
                   for step in journey["steps"])):
        raise ValueError("missing_journey_steps")
    source = evidence.get("source")
    if (not isinstance(source, str) or not source.strip() or len(source) > 96
            or source.startswith(("/", "\\")) or ".." in source.split("/")):
        raise ValueError("missing_evidence_source")
    if "value" not in evidence or isinstance(evidence["value"], (dict, list)):
        raise ValueError("raw_evidence_rejected")
    status = outcome.get("status")
    if status not in _STATUSES:
        raise ValueError("invalid_observed_outcome")
    if not isinstance(outcome.get("observed"), bool):
        raise ValueError("missing_observation")
    return {"status": status, "intent_id": intent["id"], "journey_id": journey["id"],
            "evidence_id": evidence["id"], "observed": outcome["observed"],
            "source_revision": source_revision, "tree_hash": tree_hash,
            "coverage_gaps": []}


trace_intent_outcome = build_trace
