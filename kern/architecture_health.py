"""Conservative architecture-health evidence; static silence is never proof."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from typing import Any


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _relative(value: object) -> str | None:
    text = str(value or "").replace("\\", "/")
    if not text or text.startswith("/") or ".." in text.split("/"):
        return None
    return text


def _metadata(revision: object, config_hash: object, artifact_hash: object) -> dict[str, str] | None:
    values = {"revision": revision, "config_hash": config_hash, "artifact_hash": artifact_hash}
    if any(not isinstance(value, str) or not value for value in values.values()):
        return None
    return values  # type: ignore[return-value]


def _runtime_absence_ok(runtime: Mapping[str, Any] | None, metadata: Mapping[str, str]) -> bool:
    return bool(isinstance(runtime, Mapping)
                and runtime.get("status") == "observed"
                and all(runtime.get(key) == metadata[key] for key in metadata))


def architecture_envelope(
    *,
    revision: str,
    config_hash: str,
    artifact_hash: str,
    language: str,
    scope: Sequence[str],
    import_edges: Sequence[Mapping[str, Any]] = (),
    semgrep_fragment: Mapping[str, Any] | None = None,
    layer_policy: Sequence[Mapping[str, str]] = (),
    clone_candidates: Sequence[Mapping[str, Any]] = (),
    reachability: Sequence[Mapping[str, Any]] = (),
    runtime_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic advisory findings without claiming whole-repo health."""
    metadata = _metadata(revision, config_hash, artifact_hash)
    safe_scope = sorted({item for value in scope if (item := _relative(value))})
    if metadata is None or not language or not safe_scope:
        return {"status": "UNKNOWN", "coverage_gaps": ["invalid_architecture_metadata"]}
    gaps: list[str] = []
    analyzer = {"tool": "semgrep", "version": "unknown", "status": "missing"}
    if isinstance(semgrep_fragment, Mapping):
        provenance = semgrep_fragment.get("provenance", {})
        if (semgrep_fragment.get("kind") == "semgrep" and semgrep_fragment.get("revision") == revision
                and isinstance(provenance, Mapping)):
            analyzer = {"tool": "semgrep", "version": str(provenance.get("tool_version", "unknown")),
                        "status": "observed"}
        else:
            gaps.append("semgrep_fragment_not_bound_to_revision")
    else:
        gaps.append("semgrep_not_registered_for_scope")

    normalized_edges = []
    for edge in import_edges:
        source, target = _relative(edge.get("from")), _relative(edge.get("to"))
        if source and target:
            normalized_edges.append((source, target))
        else:
            gaps.append("invalid_static_import_edge")
    violations = []
    for policy in layer_policy:
        source_prefix, target_prefix = _relative(policy.get("from_prefix")), _relative(policy.get("to_prefix"))
        if not source_prefix or not target_prefix:
            gaps.append("invalid_layer_policy")
            continue
        for source, target in normalized_edges:
            if source.startswith(source_prefix) and target.startswith(target_prefix):
                violations.append({"from": source, "to": target, "policy": _digest(source_prefix + "->" + target_prefix)})

    clones = []
    for candidate in clone_candidates:
        left, right = _relative(candidate.get("left")), _relative(candidate.get("right"))
        if left and right:
            clones.append({"pair": _digest(left + "\0" + right), "status": "advisory"})
        else:
            gaps.append("invalid_clone_candidate")

    dead = []
    for candidate in reachability:
        path = _relative(candidate.get("path"))
        if not path:
            gaps.append("invalid_reachability_candidate")
            continue
        refs = {name: int(candidate.get(name, -1)) for name in
                ("importers", "route_refs", "config_refs", "test_refs")}
        if any(value < 0 for value in refs.values()):
            gaps.append("incomplete_reachability_reference_count")
            continue
        if any(refs.values()):
            dead.append({"path": path, "status": "reachable", "references": refs})
        elif _runtime_absence_ok(runtime_evidence, metadata):
            # A bounded run supports only a stronger candidate, never proof of absence.
            dead.append({"path": path, "status": "candidate", "references": refs,
                         "runtime_absence_bound": True})
        else:
            dead.append({"path": path, "status": "UNKNOWN", "references": refs})
            gaps.append("dead_code_requires_bound_runtime_evidence")
    result = {
        "schema": 1, "status": "observed" if analyzer["status"] == "observed" else "UNKNOWN",
        "metadata": metadata, "language": language, "scope": safe_scope, "analyzer": analyzer,
        "layer_violations": sorted(violations, key=lambda item: (item["from"], item["to"])),
        "clone_candidates": sorted(clones, key=lambda item: item["pair"]),
        "reachability": sorted(dead, key=lambda item: item["path"]),
        "coverage_gaps": sorted(set(gaps + [
            "no_finding_is_not_architecture_absence",
            "dynamic_reflection_plugin_generated_paths_require_runtime_evidence",
        ])),
        "required_next_probe": "register_runtime_or_expand_language_scope",
    }
    return result


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        requirement_ids: Sequence[str], independence_group: str,
                        lineage_id: str) -> dict[str, Any]:
    """Project advisory architecture evidence into P98's non-normative shape."""
    metadata = result.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("architecture result lacks bound metadata")
    verdict = "fail" if result.get("layer_violations") else (
        "pass" if result.get("status") == "observed" else "unknown")
    return {
        "id": witness_id, "requirement_ids": list(requirement_ids), "kind": "static",
        "tool": "semgrep", "tool_version": result["analyzer"]["version"],
        "revision": metadata["revision"], "config_hash": metadata["config_hash"],
        "artifact_hash": metadata["artifact_hash"], "verdict": verdict,
        "independence_group": independence_group, "lineage_id": lineage_id,
        "freshness": "current", "evidence_rank": "advisory_static",
        "confidence": 1.0 if verdict != "unknown" else 0.0,
        "gaps": result.get("coverage_gaps", []),
    }
