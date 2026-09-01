"""Deterministic feasibility checks for measurable requirements."""

import re
from typing import Any


TYPES = {"ratio", "duration", "boolean"}
ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")


def validate_requirement(requirement: dict[str, Any]) -> dict[str, Any]:
    """Return a machine-checkable feasibility result; never infer truth."""
    gaps: list[str] = []
    rid = requirement.get("id")
    if not isinstance(rid, str) or not ID.fullmatch(rid):
        gaps.append("invalid_requirement_id")
    claim = requirement.get("claim")
    if not isinstance(claim, str) or not claim.strip():
        gaps.append("missing_measurable_claim")
    elif not re.search(r"\d|%|\b(at least|at most|under|over|within|equals?)\b", claim, re.I):
        gaps.append("unmeasurable_claim")
    kind = requirement.get("type")
    if kind not in TYPES:
        gaps.append("invalid_type")
    unit = requirement.get("unit")
    if kind == "boolean":
        if unit not in ("", None, "boolean"):
            gaps.append("invalid_unit")
    elif not isinstance(unit, str) or not unit.strip():
        gaps.append("missing_unit")
    source = requirement.get("data_source")
    if not isinstance(source, str) or not source.strip():
        gaps.append("missing_data_source")
    falsifier = requirement.get("falsifier")
    if not isinstance(falsifier, str) or not falsifier.strip():
        gaps.append("missing_falsifier")
    threshold = requirement.get("threshold")
    valid_threshold = isinstance(threshold, (int, float)) and not isinstance(threshold, bool)
    if kind == "boolean":
        valid_threshold = isinstance(threshold, bool)
    elif valid_threshold and kind == "ratio" and not 0 <= threshold <= 1:
        valid_threshold = False
    elif valid_threshold and kind == "duration" and threshold < 0:
        valid_threshold = False
    if not valid_threshold:
        gaps.append("invalid_threshold")
    return {
        "requirement_id": rid,
        "status": "feasible" if not gaps else "invalid",
        "coverage_gaps": gaps,
        "required_next_probe": None if not gaps else "requirement_feasibility",
    }

