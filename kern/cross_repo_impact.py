"""Explicit, local cross-repository impact metadata (P80)."""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


_ID = re.compile(r"[A-Za-z0-9_.-]{1,96}\Z")


def cross_repo_impact(projects: Mapping[str, Mapping[str, Any]], links: Sequence[Mapping[str, Any]], *,
                      changed_project: str, changed_revision: str) -> dict[str, Any]:
    """Follow only registered contract edges; never discover a foreign checkout."""
    if not _ID.fullmatch(changed_project) or not _ID.fullmatch(changed_revision):
        raise ValueError("project and revision must be bounded identifiers")
    gaps: list[str] = []
    if changed_project not in projects:
        return {"status": "UNKNOWN", "coverage_gaps": ["changed_project_unregistered"], "impacted": []}
    if str(projects[changed_project].get("revision", "")) != changed_revision:
        return {"status": "UNKNOWN", "coverage_gaps": ["changed_project_revision_stale"], "impacted": []}
    outgoing: dict[str, list[dict[str, str]]] = {}
    for raw in links:
        producer, consumer = str(raw.get("producer_project", "")), str(raw.get("consumer_project", ""))
        contract = str(raw.get("contract_id", ""))
        if not all(_ID.fullmatch(value) for value in (producer, consumer, contract)):
            gaps.append("invalid_registered_contract_edge")
            continue
        if producer not in projects or consumer not in projects:
            gaps.append("registered_counterpart_missing")
            continue
        if raw.get("producer_revision") != projects[producer].get("revision") or raw.get("consumer_revision") != projects[consumer].get("revision"):
            gaps.append("registered_contract_edge_stale")
            continue
        outgoing.setdefault(producer, []).append({"consumer_project": consumer, "contract_id": contract})
    seen = {changed_project}
    queue = [(changed_project, 0)]
    impacted: list[dict[str, Any]] = []
    while queue:
        source, distance = queue.pop(0)
        for edge in sorted(outgoing.get(source, []), key=lambda item: (item["consumer_project"], item["contract_id"])):
            target = edge["consumer_project"]
            if target in seen:
                continue
            seen.add(target)
            impacted.append({"project_id": target, "distance": distance + 1,
                             "via_contract": edge["contract_id"]})
            queue.append((target, distance + 1))
    metadata = {"changed_project": changed_project, "revision": changed_revision,
                "project_registry_hash": hashlib.sha256(json.dumps(projects, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
    return {"schema": 1, "status": "PASS" if not gaps else "UNKNOWN", "impacted": impacted,
            "coverage_gaps": sorted(set(gaps + ["runtime/deployment cross-project evidence not registered"])),
            "metadata": metadata}


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        independence_group: str = "cross-project-contract", lineage_id: str = "registry") -> dict[str, Any]:
    metadata = result.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("cross-repository impact metadata missing")
    verdict = str(result.get("status", "UNKNOWN")).lower()
    return {"id": witness_id, "requirement_ids": ["P80"], "kind": "cross_repository_impact",
            "tool": "cross_repo_impact", "tool_version": "1", "revision": metadata.get("revision", "unknown"),
            "config_hash": metadata.get("project_registry_hash", "unknown"), "artifact_hash": "no-artifact",
            "verdict": verdict if verdict in {"pass", "fail", "unknown"} else "unknown",
            "independence_group": independence_group, "lineage_id": lineage_id, "freshness": "current",
            "evidence_rank": "registered_contract", "confidence": 1.0 if verdict == "pass" else 0.0,
            "gaps": result.get("coverage_gaps", [])}
