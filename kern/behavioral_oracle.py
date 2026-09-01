"""Small, deterministic behavioral oracle for analyzed code paths.

The oracle deliberately fails closed: a result without independent evidence is
``UNKNOWN`` rather than a self-comparison being mistaken for a passing test.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def evaluate(
    expected: Any,
    observed: Any,
    *,
    metadata: Mapping[str, Any],
    independent_control: Callable[[], bool] | bool | None = None,
    high_risk: bool = False,
) -> dict[str, Any]:
    """Compare behavior and return a typed, provenance-carrying verdict."""
    required = ("revision", "config_hash", "artifact")
    missing = [key for key in required if not isinstance(metadata.get(key), str) or not metadata[key]]
    base = {"metadata": dict(metadata), "expected": expected, "observed": observed}
    if missing:
        return {**base, "status": "UNKNOWN", "gap": "invalid_metadata", "missing": missing}
    if independent_control is None:
        return {**base, "status": "UNKNOWN", "gap": "missing_independent_control"}
    control = independent_control() if callable(independent_control) else independent_control
    if not isinstance(control, bool) or not control:
        return {**base, "status": "UNKNOWN", "gap": "invalid_independent_control"}
    if high_risk and expected == observed:
        return {**base, "status": "UNKNOWN", "gap": "self_oracle"}
    if expected == observed:
        return {**base, "status": "PASS"}
    return {**base, "status": "FAIL", "gap": "behavior_mismatch"}


def check_behavior(expected: Any, observed: Any, **kwargs: Any) -> dict[str, Any]:
    """Readable alias for callers describing a behavioral check."""
    return evaluate(expected, observed, **kwargs)
