"""Offline, deterministic SLO evidence (P94).

This module evaluates supplied observations only.  It never starts a load
test or contacts k6, OpenTelemetry, Prometheus, Locust, or any other service.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_DIRECTIONS = {"at_most", "at_least", "max", "min"}
_REQUIRED = ("metric", "unit", "window", "load_profile", "threshold", "direction")


def _unknown(gap: str, **extra: Any) -> dict[str, Any]:
    return {"status": "UNKNOWN", "gap": gap, **extra}


def _metadata(value: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    tool_hashes = value.get("tool_hashes")
    if tool_hashes is None and isinstance(value.get("tool_hash"), str):
        tool_hashes = {"tool": value["tool_hash"]}
    missing = [key for key in ("revision", "config_hash", "environment_hash", "tool_hashes")
               if not value.get(key) and not (key == "tool_hashes" and tool_hashes)]
    if missing or not all(isinstance(value.get(key), str) and value[key] for key in
                          ("revision", "config_hash", "environment_hash")):
        return None, missing or ["invalid_metadata"]
    tools = tool_hashes
    if not isinstance(tools, Mapping) or not tools or any(
            not isinstance(k, str) or not k or not isinstance(v, str) or not v
            for k, v in tools.items()):
        return None, ["invalid_tool_hashes"]
    return {
        "revision": value["revision"], "config_hash": value["config_hash"],
        "environment_hash": value["environment_hash"],
        "artifact_hash": value.get("artifact_hash", value["environment_hash"]),
                "tool_hashes": dict(sorted(tools.items())),
    }, []


def evaluate_slo(slo: Mapping[str, Any], observation: Mapping[str, Any] | None = None,
                *, expected_config_hash: str | None = None,
                min_samples: int = 1, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return PASS/FAIL/UNKNOWN from an SLO contract and supplied evidence."""
    if not isinstance(slo, Mapping):
        return _unknown("invalid_slo_contract")
    missing = [key for key in _REQUIRED if key not in slo]
    if missing:
        return _unknown("missing_slo_field", missing=missing)
    if any(not isinstance(slo[key], str) or not str(slo[key]).strip()
           for key in ("metric", "unit", "window")):
        return _unknown("invalid_slo_contract")
    if not isinstance(slo["load_profile"], (str, Mapping)) or not slo["load_profile"]:
        return _unknown("invalid_slo_contract")
    threshold = slo["threshold"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        return _unknown("invalid_threshold")
    direction = slo["direction"]
    if direction not in _DIRECTIONS:
        return _unknown("invalid_direction")
    if not isinstance(min_samples, int) or min_samples < 1:
        return _unknown("invalid_sample_requirement")
    obs = dict(observation if observation is not None else slo)
    if metadata is not None:
        obs = {**metadata, **obs}
    if not isinstance(obs, Mapping):
        return _unknown("missing_observation")
    metadata, missing_metadata = _metadata(obs)
    if metadata is None:
        return _unknown("invalid_metadata", missing=missing_metadata)
    if expected_config_hash is not None and metadata["config_hash"] != expected_config_hash:
        return _unknown("stale_config", metadata=metadata)
    if obs.get("config_current") is False or obs.get("stale_config") is True:
        return _unknown("stale_config", metadata=metadata)
    if "unit" in obs and obs["unit"] != slo["unit"]:
        return _unknown("unit_mismatch", metadata=metadata)
    count = obs.get("sample_count")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return _unknown("invalid_sample_count", metadata=metadata)
    if count < min_samples:
        return _unknown("insufficient_samples", metadata=metadata, sample_count=count,
                        required_samples=min_samples)
    if "observed_quantiles" not in obs or "errors" not in obs:
        return _unknown("missing_observation_fields", metadata=metadata, sample_count=count)
    if "degradation" not in obs or "recovery" not in obs:
        return _unknown("missing_recovery_evidence", metadata=metadata, sample_count=count)
    quantiles = obs.get("observed_quantiles")
    if not isinstance(quantiles, Mapping) or not quantiles:
        return _unknown("missing_quantiles", metadata=metadata, sample_count=count)
    quantile = str(slo.get("quantile", "p95"))
    value = quantiles.get(quantile)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return _unknown("missing_observed_quantile", metadata=metadata, quantile=quantile)
    errors = obs.get("errors")
    if not isinstance(errors, Mapping):
        return _unknown("invalid_errors", metadata=metadata)
    degraded = obs.get("degradation", {})
    recovered = obs.get("recovery", {})
    if not isinstance(degraded, Mapping) or not isinstance(recovered, Mapping):
        return _unknown("invalid_recovery_evidence", metadata=metadata)
    if not isinstance(degraded.get("observed"), bool) or not isinstance(recovered.get("observed"), bool):
        return _unknown("invalid_recovery_evidence", metadata=metadata)
    upper = direction in {"at_most", "max"}
    passed = value <= threshold if upper else value >= threshold
    if degraded["observed"] and not recovered["observed"]:
        passed = False
    result: dict[str, Any] = {
        "status": "PASS" if passed else "FAIL", "metric": slo["metric"], "unit": slo["unit"],
        "window": slo["window"], "quantile": quantile, "threshold": threshold,
        "direction": direction, "sample_count": count, "observed_quantile": value,
        "errors": dict(sorted(errors.items())), "degradation": dict(degraded),
        "recovery": dict(recovered), "metadata": metadata,
    }
    if degraded["observed"] and not recovered["observed"]:
        result["coverage_gaps"] = ["degradation_not_recovered"]
    return result


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        requirement_ids: list[str] | tuple[str, ...],
                        independence_group: str, lineage_id: str,
                        observed_at: str = "") -> dict[str, Any]:
    """Project SLO output into P98's non-normative, metadata-only witness."""
    metadata = result.get("metadata")
    status = str(result.get("status", "UNKNOWN")).lower()
    if not isinstance(metadata, Mapping) or status not in {"pass", "fail", "unknown"}:
        raise ValueError("SLO result lacks witness metadata or verdict")
    gaps = [str(result["gap"])] if result.get("gap") else []
    return {"id": witness_id, "requirement_ids": list(requirement_ids), "kind": "slo",
            "tool": "slo_evidence", "tool_version": "1", "revision": metadata["revision"],
            "config_hash": metadata["config_hash"], "artifact_hash": metadata["artifact_hash"],
            "verdict": status, "independence_group": independence_group,
            "lineage_id": lineage_id, "freshness": "current",
            "evidence_rank": "registered_slo", "confidence": 1.0 if status != "unknown" else 0.0,
            "gaps": gaps, "observed_at": observed_at}


def witness_envelope(result: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Convenience wrapper retaining the canonical P98 envelope implementation."""
    from .project_context import witness_envelope as envelope
    return envelope(witnesses=[as_evidence_witness(result, **kwargs)])
