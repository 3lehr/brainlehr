"""Deterministic, revision-bound workflow impact from local JSON metadata (P97)."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DEFINITIONS = {
    "defect_near_miss_prevention": ("prevented", "eligible", "max"),
    "rework": ("rework", "work", "min"),
    "time_to_green": ("seconds", "green_runs", "min"),
    "token_context_bytes": ("bytes", "sessions", "min"),
    "false_positive_cost": ("cost", "findings", "min"),
}


def load_metadata(path: str | Path) -> Mapping[str, Any]:
    """Read one local JSON object; no network or external analytics adapter."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("workflow metadata must be a JSON object")
    return value


def _window(value: Mapping[str, Any], label: str, definition: str) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(value, Mapping):
        return None, f"missing_{label}_window"
    if set(value) & {"loc", "lines_of_code", "commits", "agent_count", "agents"}:
        return None, "forbidden_productivity_proxy"
    if value.get("definition") != definition:
        return None, "definition_drift"
    if not value.get("revision") or not value.get("window_start") or not value.get("window_end"):
        return None, f"missing_{label}_metadata"
    numerator, denominator, _ = DEFINITIONS[definition]
    n, d = value.get("numerator", value.get(numerator)), value.get("denominator", value.get(denominator))
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or x < 0 for x in (n, d)) or not d:
        return None, "invalid_or_empty_denominator"
    return {"revision": str(value["revision"]), "window_start": str(value["window_start"]),
            "window_end": str(value["window_end"]), "definition": definition,
            "numerator": n, "denominator": d, "rate": n / d}, None


def evaluate_workflow_impact(baseline: Mapping[str, Any], comparison: Mapping[str, Any], *,
                             revision: str | None = None, config_hash: str = "local",
                             artifact_hash: str = "local", min_samples: int = 1) -> dict[str, Any]:
    """Compare explicit baseline/comparison windows; never infer productivity from LOC/commits/agents."""
    if not isinstance(baseline, Mapping) or not isinstance(comparison, Mapping):
        return {"status": "UNKNOWN", "gap": "missing_baseline_or_comparison"}
    if not isinstance(min_samples, int) or min_samples < 1:
        return {"status": "UNKNOWN", "gap": "invalid_sample_requirement"}
    metrics: dict[str, Any] = {}
    gaps: list[str] = []
    for definition, (_, _, direction) in DEFINITIONS.items():
        left, lgap = _window(baseline.get(definition), "baseline", definition)
        right, rgap = _window(comparison.get(definition), "comparison", definition)
        samples = [x.get("samples", 1) for x in (baseline.get(definition, {}), comparison.get(definition, {}))
                   if isinstance(x, Mapping)]
        if any(isinstance(s, bool) or not isinstance(s, (int, float)) for s in samples):
            gap = "invalid_sample_count"
        else:
            gap = lgap or rgap or ("insufficient_samples" if any(s < min_samples for s in samples) else None)
        if gap:
            metrics[definition] = {"status": "UNKNOWN", "gap": gap}
            gaps.append(f"{definition}:{gap}")
            continue
        if revision and right["revision"] != revision:
            metrics[definition] = {"status": "UNKNOWN", "gap": "revision_mismatch"}
            gaps.append(f"{definition}:revision_mismatch")
            continue
        improved = right["rate"] > left["rate"] if direction == "max" else right["rate"] < left["rate"]
        metrics[definition] = {"status": "PASS" if improved else "FAIL", "direction": direction,
                              "baseline": left, "comparison": right}
    known = [x["status"] for x in metrics.values() if x["status"] != "UNKNOWN"]
    status = "UNKNOWN" if not known or gaps else ("PASS" if all(x == "PASS" for x in known) else "FAIL")
    return {"schema": 1, "status": status, "metrics": metrics, "coverage_gaps": sorted(gaps),
            "metadata": {"revision": revision or str(comparison.get("revision", "local")),
                         "config_hash": config_hash, "artifact_hash": artifact_hash,
                         "source": "local_json"}}


workflow_impact = evaluate_workflow_impact


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str, requirement_ids: list[str] | tuple[str, ...],
                        independence_group: str = "workflow", lineage_id: str = "workflow-impact") -> dict[str, Any]:
    metadata = result.get("metadata")
    status = str(result.get("status", "UNKNOWN")).lower()
    if not isinstance(metadata, Mapping) or status not in {"pass", "fail", "unknown"}:
        raise ValueError("workflow result lacks witness metadata or verdict")
    return {"id": witness_id, "requirement_ids": list(requirement_ids), "kind": "workflow_impact",
            "tool": "workflow_impact", "tool_version": "1", "revision": metadata["revision"],
            "config_hash": metadata["config_hash"], "artifact_hash": metadata["artifact_hash"],
            "verdict": status, "independence_group": independence_group, "lineage_id": lineage_id,
            "freshness": "current", "evidence_rank": "local_json", "confidence": 1.0 if status != "unknown" else 0.0,
            "gaps": result.get("coverage_gaps", [])}


def witness_envelope(result: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    from .project_context import witness_envelope as envelope
    return envelope(witnesses=[as_evidence_witness(result, **kwargs)])
