"""Bounded runtime witnesses for effect cardinality and dynamic dispatch.

Static call graphs only produce candidates.  This module accepts a registered
runtime event list and fails closed when the trace, binding, or independent
oracle is missing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
from typing import Any

from .evidence_adapters import normalize_runtime_artifact

_META = ("revision", "tree_hash", "config_hash", "artifact_hash")
_EVENT = ("event_key", "kind", "target", "ingress")


def _identifier_hash(value: str) -> str:
    """Keep stable correlation without returning a raw runtime payload."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _metadata(metadata: Mapping[str, Any]) -> tuple[dict[str, str] | None, list[str]]:
    missing = [name for name in _META if not isinstance(metadata.get(name), str) or not metadata[name]]
    return (None, missing) if missing else ({name: metadata[name] for name in _META}, [])


def _oracle_ok(oracle: Mapping[str, Any] | None, high_risk: bool) -> str | None:
    if not high_risk:
        return None
    if not isinstance(oracle, Mapping):
        return "missing_independent_oracle"
    if oracle.get("status") != "PASS":
        return "independent_oracle_not_pass"
    if oracle.get("gap") in {"self_oracle", "missing_independent_control", "invalid_independent_control"}:
        return "independent_oracle_not_pass"
    return None


def evaluate_runtime(
    events: Sequence[Mapping[str, Any]] | None,
    *,
    expected_count: int,
    event_key: str,
    metadata: Mapping[str, Any],
    oracle: Mapping[str, Any] | None = None,
    high_risk: bool = True,
    static_candidates: Sequence[str] = (),
    dispatch_targets: Sequence[Mapping[str, Any]] = (),
    runtime_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a redacted, revision-bound cardinality/dispatch witness."""
    bound, missing = _metadata(metadata)
    if bound is None:
        return {"status": "UNKNOWN", "gap": "invalid_metadata", "missing": missing}
    if not isinstance(event_key, str) or not event_key or not isinstance(expected_count, int) or expected_count < 0:
        return {"status": "UNKNOWN", "gap": "invalid_expected_cardinality", "metadata": bound}
    oracle_gap = _oracle_ok(oracle, high_risk)
    if oracle_gap:
        return {"status": "UNKNOWN", "gap": oracle_gap, "metadata": bound, "event_key": event_key}
    if events is None:
        return {
            "status": "UNKNOWN", "gap": "missing_runtime_trace", "metadata": bound,
            "event_key_hash": _identifier_hash(event_key), "expected_count": expected_count,
            "static_candidate_count": len(static_candidates), "static_candidates_status": "candidate_only",
        }
    artifact = dict(runtime_artifact or {
        "revision": bound["revision"], "tree_hash": bound["tree_hash"],
        "config_hash": bound["config_hash"], "artifact_hash": bound["artifact_hash"],
        "tool": "runtime_cardinality", "tool_version": "1",
        "provenance": "registered-runtime-cardinality", "registered": True,
        "ingress": [event.get("ingress") for event in events if isinstance(event, Mapping)],
        "event_identity": event_key,
    })
    if artifact.get("revision") != bound["revision"] or artifact.get("tree_hash") != bound["tree_hash"]:
        return {"status": "UNKNOWN", "gap": "runtime_artifact_binding_mismatch", "metadata": bound}
    try:
        adapter = normalize_runtime_artifact(artifact)
    except (TypeError, ValueError):
        return {"status": "UNKNOWN", "gap": "invalid_runtime_artifact", "metadata": bound}
    if adapter.get("status") == "coverage_gap":
        return {"status": "UNKNOWN", "gap": "runtime_artifact_gap", "coverage_gaps": adapter.get("coverage_gaps", []), "metadata": bound}
    safe: list[dict[str, str]] = []
    for event in events:
        if not isinstance(event, Mapping) or any(key not in event for key in _EVENT):
            return {"status": "UNKNOWN", "gap": "invalid_runtime_event", "metadata": bound}
        if any(not isinstance(event[key], str) or not event[key] for key in _EVENT):
            return {"status": "UNKNOWN", "gap": "invalid_runtime_event", "metadata": bound}
        safe.append({key: event[key] for key in _EVENT})
    matching = [event for event in safe if event["event_key"] == event_key]
    count = len(matching)
    result: dict[str, Any] = {
        "status": "PASS" if count == expected_count else "FAIL",
        "metadata": bound, "event_key_hash": _identifier_hash(event_key),
        "expected_count": expected_count, "observed_count": count,
        "observed": [{"ingress_hash": _identifier_hash(event["ingress"]), "kind": event["kind"],
                      "target_hash": _identifier_hash(event["target"])} for event in matching],
        "static_candidate_count": len(static_candidates),
        "runtime_artifact": {"status": adapter["status"], "event_identity_hash": adapter["event_identity_hash"]},
    }
    if static_candidates:
        result["static_candidates_status"] = "candidate_only"
    if dispatch_targets:
        observed_targets = {event["target"] for event in matching}
        dispatch: list[dict[str, str]] = []
        for target in dispatch_targets:
            name, kind = target.get("target"), target.get("kind", "dynamic")
            if not isinstance(name, str) or not name or not isinstance(kind, str) or not kind:
                return {"status": "UNKNOWN", "gap": "invalid_dispatch_target", "metadata": bound}
            dispatch.append({"target_hash": _identifier_hash(name), "kind": kind,
                             "status": "observed" if name in observed_targets else "UNKNOWN"})
        result["dispatch"] = dispatch
        result["coverage_gaps"] = [f"unobserved_{item['kind']}_dispatch" for item in dispatch if item["status"] == "UNKNOWN"]
    return result


def as_evidence_witness(
    result: Mapping[str, Any],
    *,
    witness_id: str,
    requirement_ids: Sequence[str],
    independence_group: str,
    lineage_id: str,
    observed_at: str = "",
) -> dict[str, Any]:
    """Project a bounded runtime verdict into the non-normative P98 contract."""
    metadata = result.get("metadata")
    status = str(result.get("status", "UNKNOWN")).lower()
    if not isinstance(metadata, Mapping) or status not in {"pass", "fail", "unknown"}:
        raise ValueError("runtime result lacks witness metadata or verdict")
    gaps = result.get("coverage_gaps", [])
    if result.get("gap"):
        gaps = [*gaps, str(result["gap"])]
    return {
        "id": witness_id, "requirement_ids": list(requirement_ids),
        "kind": "runtime", "tool": "runtime_cardinality", "tool_version": "1",
        "revision": metadata["revision"], "config_hash": metadata["config_hash"],
        "artifact_hash": metadata["artifact_hash"], "verdict": status,
        "independence_group": independence_group, "lineage_id": lineage_id,
        "freshness": "current", "evidence_rank": "registered_runtime",
        "confidence": 1.0 if status != "unknown" else 0.0,
        "gaps": sorted(set(gaps)), "observed_at": observed_at,
    }


check_runtime_cardinality = evaluate_runtime
