"""Canonical graph-v2 merge/reconciliation without analyzer execution or writes."""
from __future__ import annotations

import hashlib
import json


SCHEMA = 2


def evidence_envelope(*, source_kind: str, source_ref: str, strength: str,
                      revision: str, analyzer_version: str = "unknown",
                      status: str = "observed") -> dict:
    if not all(isinstance(value, str) and value for value in
               (source_kind, source_ref, strength, revision, analyzer_version, status)):
        raise ValueError("evidence envelope requires non-empty typed identity")
    return {"source_kind": source_kind, "source_ref": source_ref, "strength": strength,
            "revision": revision, "analyzer_version": analyzer_version, "status": status}


def reconcile(snapshot: dict, fragments: list[dict]) -> dict:
    """Attach revision-compatible fragments, retaining conflicts and gaps visibly."""
    graph = json.loads(json.dumps({key: value for key, value in snapshot.items() if key != "content_hash"}))
    graph["schema"] = SCHEMA
    graph.setdefault("evidence", [])
    graph.setdefault("conflicts", [])
    graph.setdefault("coverage_gaps", [])
    node_ids = {node["id"] for node in graph.get("nodes", [])}
    edge_keys = {(edge.get("from"), edge.get("to"), edge.get("edge_type", edge.get("type")))
                 for edge in graph.get("edges", [])}
    for fragment in fragments:
        if fragment.get("revision") != graph.get("source_revision"):
            graph["conflicts"].append({"kind": "revision_mismatch", "source": fragment.get("source"),
                                       "fragment_revision": fragment.get("revision")})
            continue
        if fragment.get("status") == "coverage_gap":
            graph["coverage_gaps"].extend(fragment.get("coverage_gaps", []))
            continue
        provenance = fragment.get("provenance", {})
        envelope = evidence_envelope(source_kind=fragment["kind"], source_ref=fragment["source"],
                                     strength=provenance.get("strength", "unknown"),
                                     revision=fragment["revision"], analyzer_version=provenance.get("version", "unknown"))
        graph["evidence"].append(envelope)
        for node in fragment.get("nodes", []):
            if node["id"] not in node_ids:
                graph["nodes"].append(node); node_ids.add(node["id"])
        for edge in fragment.get("edges", []):
            key = (edge["from"], edge["to"], edge.get("edge_type", edge.get("type")))
            if key not in edge_keys:
                graph["edges"].append({"from": edge["from"], "to": edge["to"],
                                       "edge_type": key[2], "evidence": envelope})
                edge_keys.add(key)
    graph["nodes"].sort(key=lambda node: node["id"])
    graph["edges"].sort(key=lambda edge: (edge["from"], edge["to"], edge["edge_type"]))
    graph["evidence"] = sorted({json.dumps(item, sort_keys=True): item for item in graph["evidence"]}.values(),
                               key=lambda item: (item["source_kind"], item["source_ref"]))
    graph["conflicts"].sort(key=lambda item: json.dumps(item, sort_keys=True))
    graph["coverage_gaps"] = sorted(set(graph["coverage_gaps"]))
    encoded = json.dumps(graph, sort_keys=True, separators=(",", ":"))
    graph["content_hash"] = hashlib.sha256(encoded.encode()).hexdigest()
    return graph
