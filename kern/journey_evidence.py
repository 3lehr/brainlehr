"""Bounded executable-journey evidence; automation and human comprehension differ."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_ID = re.compile(r"[A-Za-z0-9_.:@/-]{1,160}$")


def _id(value: object, field: str) -> str:
    text = str(value or "")
    if not _ID.fullmatch(text):
        raise ValueError(f"{field} must be a bounded identifier")
    return text


def _steps(value: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, str]], bool]:
    rows, passing = [], True
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("journey steps must be mappings")
        row = {key: _id(item.get(key), "journey step " + key) for key in ("id", "expected", "observed")}
        passing = passing and row["expected"] == row["observed"]
        rows.append(row)
    if not rows:
        raise ValueError("journey requires ordered observable steps")
    return rows, passing


def journey_envelope(*, requirement_id: str, journey_id: str, revision: str, config_hash: str,
                     artifact_hash: str, browser_hash: str | None, platform_hash: str | None,
                     start_state: str, steps: Sequence[Mapping[str, Any]], recovery: Mapping[str, Any],
                     expected_outcome: str, observed_outcome: str, accessibility: Mapping[str, Any],
                     operator_witness: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return deterministic status without treating automation as human approval."""
    metadata = {"revision": _id(revision, "revision"), "config_hash": _id(config_hash, "config_hash"),
                "artifact_hash": _id(artifact_hash, "artifact_hash")}
    req, journey = _id(requirement_id, "requirement_id"), _id(journey_id, "journey_id")
    start, expected, observed = _id(start_state, "start_state"), _id(expected_outcome, "expected_outcome"), _id(observed_outcome, "observed_outcome")
    rows, steps_pass = _steps(steps)
    gaps: list[str] = []
    if not browser_hash or not platform_hash:
        gaps.append("browser_or_platform_evidence_missing")
    browser = {"browser_hash": _id(browser_hash, "browser_hash") if browser_hash else None,
               "platform_hash": _id(platform_hash, "platform_hash") if platform_hash else None}
    recovery_rows, recovery_pass = _steps([recovery])
    a11y = accessibility.get("status") if isinstance(accessibility, Mapping) else None
    if a11y not in {"pass", "fail", "unknown"}:
        raise ValueError("accessibility status must be pass/fail/unknown")
    a11y_tool = accessibility.get("tool_hash") if isinstance(accessibility, Mapping) else None
    if a11y_tool is None:
        gaps.append("accessibility_adapter_missing")
    else:
        a11y_tool = _id(a11y_tool, "accessibility tool hash")
    if a11y == "unknown":
        gaps.append("accessibility_unobserved")
    human = {"status": "pending", "witness_id": None}
    if operator_witness is not None:
        if not isinstance(operator_witness, Mapping):
            raise ValueError("operator witness must be metadata")
        if (operator_witness.get("revision") != revision or operator_witness.get("artifact_hash") != artifact_hash
                or operator_witness.get("verdict") not in {"approved", "rejected"}):
            gaps.append("operator_comprehension_witness_unbound")
        else:
            human = {"status": str(operator_witness["verdict"]),
                     "witness_id": _id(operator_witness.get("witness_id"), "operator witness id")}
    if human["status"] == "pending":
        gaps.append("human_comprehension_pending")
    automation_pass = (steps_pass and recovery_pass and expected == observed and a11y == "pass"
                       and bool(a11y_tool) and not browser_or_platform_missing(browser))
    status = "FAIL" if a11y == "fail" or not steps_pass or not recovery_pass or expected != observed or human["status"] == "rejected" else (
        "PASS" if automation_pass and human["status"] == "approved" else "UNKNOWN")
    return {
        "schema": 1, "status": status, "automation_status": "PASS" if automation_pass else "FAIL" if status == "FAIL" else "UNKNOWN",
        "requirement_id": req, "journey_id": journey, "metadata": metadata, "browser": browser,
        "start_state": start, "steps": rows, "recovery": recovery_rows[0],
        "outcome": {"expected": expected, "observed": observed},
        "accessibility": {"status": a11y, "tool_hash": a11y_tool},
        "human_comprehension": human, "coverage_gaps": sorted(set(gaps)),
    }


def browser_or_platform_missing(browser: Mapping[str, Any]) -> bool:
    return not browser.get("browser_hash") or not browser.get("platform_hash")


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        independence_group: str, lineage_id: str) -> dict[str, Any]:
    """Project evidence into P98; this never manufactures operator approval."""
    metadata = result.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("journey result lacks metadata")
    status = str(result.get("status", "UNKNOWN")).lower()
    return {
        "id": witness_id, "requirement_ids": [result["requirement_id"]], "kind": "journey",
        "tool": "journey_evidence", "tool_version": "1", "revision": metadata["revision"],
        "config_hash": metadata["config_hash"], "artifact_hash": metadata["artifact_hash"],
        "verdict": status if status in {"pass", "fail", "unknown"} else "unknown",
        "independence_group": independence_group, "lineage_id": lineage_id,
        "freshness": "current", "evidence_rank": "journey_automation",
        "confidence": 1.0 if status == "pass" else 0.0, "gaps": result.get("coverage_gaps", []),
    }
