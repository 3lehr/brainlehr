"""Conservative coverage provenance for code evidence.

This is a classifier, not an analyzer: absence of a signal is a coverage gap,
never evidence that the project is complete.
"""
from __future__ import annotations

from pathlib import PurePosixPath

_PATH_GAPS = (
    ("dynamic", ("eval(", "exec(", "importlib", "__import__(", "dynamic import")),
    ("reflection", ("getattr(", "setattr(", "inspect.", "globals[")),
    ("plugin", ("entry_points", "plugins/", "plugin/")),
    ("vendor", ("vendor/", "third_party/", "site-packages/")),
    ("generated", ("generated/", ".generated.", "_generated/")),
    ("iac", ("terraform", ".tf", "cloudformation", "pulumi")),
    ("mobile", ("android/", "ios/", "flutter", "react-native")),
)


def classify_coverage(*, files: list[str] | tuple[str, ...] = (),
                      signals: list[str] | tuple[str, ...] = (),
                      evidence: dict[str, object] | None = None) -> dict[str, object]:
    """Return explicit gaps for unsupported provenance and missing evidence.

    ``evidence`` may mark channels as ``ci``, ``local`` or ``flaky``.  A clean
    result is deliberately called ``bounded``; callers must not relabel it
    ``complete`` without a separate, explicit acceptance decision.
    """
    values = tuple(str(x).lower() for x in (*files, *signals))
    gaps: set[str] = set()
    for name, needles in _PATH_GAPS:
        if any(needle in value for value in values for needle in needles):
            gaps.add(name)
    channels = evidence or {}
    for channel in ("ci", "local", "flaky"):
        value = channels.get(channel)
        if channel == "flaky" and value:
            gaps.add("flaky evidence is non-reproducible")
        elif value is False or value is None and channel in channels:
            gaps.add(f"{channel} evidence unavailable")
    return {"status": "coverage_gap" if gaps else "bounded",
            "coverage_gaps": sorted(gaps), "complete": False,
            "provenance": {"files": len(files), "signals": len(signals)}}
