"""P103-v4 collector: reuse immutable v3 gates, bind v4 seal schema."""
from __future__ import annotations

from collections.abc import Mapping

from messungen.sealed_retrieval_v3_collector import collect as _collect


def collect(manifest: Mapping[str, object], raw: Mapping[str, object], *, raw_sha256: str) -> dict[str, object]:
    """Run v3 fail-closed collector after exactly one schema adaptation."""
    if manifest.get("schema") != 4:
        return {"schema": 4, "status": "FAIL", "hypothesis": "UNDECIDED",
                "active_channel": "bge_m3", "missing": ["sealed_manifest"]}
    result = _collect({**manifest, "schema": 3}, raw, raw_sha256=raw_sha256)
    return {**result, "schema": 4}
