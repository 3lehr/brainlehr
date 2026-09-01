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
    graph.setdefault("required_next_probe", [])
    node_ids = {node["id"] for node in graph.get("nodes", [])}
    edge_keys = {(edge.get("from"), edge.get("to"), edge.get("edge_type", edge.get("type")))
                 for edge in graph.get("edges", [])}
    for fragment in fragments:
        if fragment.get("revision") != graph.get("source_revision"):
            graph["conflicts"].append({"kind": "revision_mismatch", "source": fragment.get("source"),
                                       "fragment_revision": fragment.get("revision")})
            continue
        graph["coverage_gaps"].extend(fragment.get("coverage_gaps", []))
        required_probe = fragment.get("required_next_probe")
        if isinstance(required_probe, str) and required_probe:
            graph["required_next_probe"].append(required_probe)
        for probe in fragment.get("required_next_probes", []):
            if isinstance(probe, str) and probe:
                graph["required_next_probe"].append(probe)
        if fragment.get("status") == "coverage_gap":
            continue
        provenance = fragment.get("provenance", {})
        envelope = evidence_envelope(source_kind=fragment["kind"], source_ref=fragment["source"],
                                     strength=provenance.get("strength", "unknown"),
                                     revision=fragment["revision"], analyzer_version=provenance.get("tool_version", "unknown"))
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
            else:
                prior = next(item for item in graph["edges"]
                             if (item.get("from"), item.get("to"), item.get("edge_type", item.get("type"))) == key)
                prior_source = (prior.get("evidence") or {}).get("source_kind")
                if prior_source != fragment.get("kind"):
                    graph["conflicts"].append({"kind": "edge_evidence_conflict", "edge": list(key),
                                               "sources": sorted({str(prior_source), str(fragment.get("kind"))})})
    graph["nodes"].sort(key=lambda node: node["id"])
    graph["edges"].sort(key=lambda edge: (edge["from"], edge["to"], edge["edge_type"]))
    graph["evidence"] = sorted({json.dumps(item, sort_keys=True): item for item in graph["evidence"]}.values(),
                               key=lambda item: (item["source_kind"], item["source_ref"]))
    graph["conflicts"].sort(key=lambda item: json.dumps(item, sort_keys=True))
    graph["coverage_gaps"] = sorted(set(graph["coverage_gaps"]))
    graph["required_next_probe"] = sorted(set(graph["required_next_probe"]))
    encoded = json.dumps(graph, sort_keys=True, separators=(",", ":"))
    graph["content_hash"] = hashlib.sha256(encoded.encode()).hexdigest()
    return graph


def transitive_selection(graph: dict, roots: list[str]) -> dict:
    """Return conservative downstream selection with hop distance and gaps."""
    consumers: dict[str, set[str]] = {}
    for edge in graph.get("edges", []):
        consumers.setdefault(str(edge.get("from")), set()).add(str(edge.get("to")))
    distances: dict[str, int] = {str(root): 0 for root in roots}
    frontier = sorted(distances)
    while frontier:
        next_frontier = []
        for node in frontier:
            for consumer in sorted(consumers.get(node, ())):
                if consumer not in distances:
                    distances[consumer] = distances[node] + 1
                    next_frontier.append(consumer)
        frontier = next_frontier
    return {"roots": sorted(set(roots)), "selected": [
        {"id": node, "distance": distance}
        for node, distance in sorted(distances.items(), key=lambda item: (item[1], item[0]))
    ], "coverage_gaps": sorted(set(graph.get("coverage_gaps", [])))}
