"""Append-only, hash-only incident lifecycle fixture (P85)."""
from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_STAGES = ("detect", "contain", "recover", "verify")


class IncidentLifecycle:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": 1, "incidents": {}}
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("incidents"), dict):
            raise ValueError("incident store is invalid")
        return value

    def append(self, *, incident_id: str, stage: str, revision: str | None = None,
               artifact_hash: str | None = None, config_hash: str | None = None) -> dict[str, Any]:
        if not isinstance(incident_id, str) or not incident_id.strip() or stage not in _STAGES:
            raise ValueError("incident_id and valid stage are required")
        value = self._read()
        events = value["incidents"].setdefault(incident_id, [])
        if (not events and stage != "detect") or (
                events and _STAGES.index(stage) != _STAGES.index(events[-1]["stage"]) + 1):
            return {"status": "REJECT", "coverage_gaps": ["invalid_lifecycle_transition"]}
        if stage == "verify" and not all(
                isinstance(value, str) and value.strip()
                for value in (revision, artifact_hash, config_hash)):
            return {"status": "UNKNOWN", "coverage_gaps": ["verification_identity_missing"]}
        event = {"stage": stage, "revision": revision, "artifact_hash": artifact_hash,
                 "config_hash": config_hash}
        event["event_sha256"] = hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        events.append(event)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)
        return {"schema": 1, "status": "PASS" if stage == "verify" else "OPEN",
                "incident_id": incident_id, "stage": stage, "coverage_gaps": [],
                "evidence": {"revision": revision, "artifact_hash": artifact_hash,
                             "config_hash": config_hash, "event_sha256": event["event_sha256"]}}


def incident_lifecycle(path: str | Path, **event: Any) -> dict[str, Any]:
    return IncidentLifecycle(path).append(**event)


def as_evidence_witness(result: Mapping[str, Any], *, witness_id: str,
                        independence_group: str = "incident-lifecycle",
                        lineage_id: str = "incident-lifecycle") -> dict[str, Any]:
    evidence = result.get("evidence", {})
    if not isinstance(evidence, Mapping) or not all(
            isinstance(evidence.get(key), str) and evidence[key]
            for key in ("revision", "artifact_hash", "config_hash", "event_sha256")):
        raise ValueError("verified incident result lacks evidence identity")
    verdict = str(result.get("status", "UNKNOWN")).lower()
    return {"id": witness_id, "requirement_ids": ["P85"], "kind": "incident_lifecycle",
            "tool": "incident_lifecycle", "tool_version": "1",
            "revision": evidence["revision"], "config_hash": evidence["config_hash"],
            "artifact_hash": evidence["artifact_hash"],
            "verdict": verdict if verdict in {"pass", "fail", "unknown"} else "unknown",
            "independence_group": independence_group, "lineage_id": lineage_id,
            "freshness": "current", "evidence_rank": "local_incident_lifecycle",
            "confidence": 1.0 if verdict == "pass" else 0.0,
            "gaps": result.get("coverage_gaps", [])}
