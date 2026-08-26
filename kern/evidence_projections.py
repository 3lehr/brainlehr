"""Small, source-bound projections for optional runtime evidence."""
from __future__ import annotations

import hashlib
import json


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _current_graph(graph: dict) -> bool:
    """Reject a forged visualization/trace anchor before projecting it."""
    required = {"schema", "source_revision", "content_hash", "nodes", "edges"}
    if not required <= set(graph) or not isinstance(graph["nodes"], list) or not isinstance(graph["edges"], list):
        return False
    node_ids = {node.get("id") for node in graph["nodes"] if isinstance(node, dict) and isinstance(node.get("id"), str)}
    if len(node_ids) != len(graph["nodes"]):
        return False
    if any(not isinstance(edge, dict) or edge.get("from") not in node_ids or edge.get("to") not in node_ids
           for edge in graph["edges"]):
        return False
    unsigned = {key: value for key, value in graph.items() if key != "content_hash"}
    return graph["content_hash"] == _hash(unsigned)


def otel_trace_projection(trace: dict, *, source_revision: str, tree_hash: str,
                          graph: dict) -> dict:
    """Accept only sanitized spans bound to the graph revision and tree."""
    if not _current_graph(graph) or graph["source_revision"] != source_revision:
        return {"status": "coverage_gap", "coverage_gaps": ["graph hash/schema is not current"]}
    if trace.get("revision") != source_revision or trace.get("tree_hash") != tree_hash:
        return {"status": "coverage_gap", "coverage_gaps": ["trace revision/tree hash is not current"]}
    spans = trace.get("spans", [])
    if not isinstance(spans, list) or any(not isinstance(span, dict) for span in spans):
        return {"status": "coverage_gap", "coverage_gaps": ["sanitized span list missing"]}
    forbidden = {"payload", "events", "body", "exception", "attributes_raw"}
    if any(forbidden.intersection(span) or span.get("revision") != source_revision
           or span.get("tree_hash") != tree_hash or not isinstance(span.get("duration_ns"), int)
           or span["duration_ns"] < 0 for span in spans):
        return {"status": "rejected", "coverage_gaps": ["raw span payload is not accepted"]}
    nodes = {node["id"] for node in graph.get("nodes", [])}
    bindings = []
    gaps = []
    for span in spans:
        file_name = span.get("code_file")
        if file_name not in nodes:
            gaps.append("span has no graph node binding")
            continue
        bindings.append({"span_id": span.get("span_id", ""), "name": span.get("name", ""), "node": file_name})
    return {"status": "current" if not gaps else "coverage_gap", "source_revision": source_revision,
            "tree_hash": tree_hash, "bindings": bindings, "coverage_gaps": sorted(set(gaps)),
            "content_hash": _hash(bindings)}


def metroviz_projection(graph: dict) -> dict:
    """Project the canonical typed graph into a deterministic route contract."""
    if not _current_graph(graph):
        return {"schema": 1, "current": False,
                "coverage_gaps": ["graph hash/schema is not current"]}
    nodes = sorted(graph.get("nodes", []), key=lambda node: node.get("id", ""))
    edges = sorted(graph.get("edges", []), key=lambda edge: (edge.get("from", ""), edge.get("to", "")))
    routes = [{"from": edge.get("from"), "to": edge.get("to"), "edge_type": edge.get("edge_type"),
               "source_ref": edge.get("source_ref")} for edge in edges]
    return {"schema": 1, "source_graph_schema": graph["schema"],
            "source_revision": graph["source_revision"], "content_hash": graph["content_hash"],
            "nodes": [{"id": node["id"], "kind": node.get("kind")} for node in nodes],
            "routes": routes, "coverage_gaps": list(graph.get("coverage_gaps", [])),
            "current": bool(graph.get("source_revision") and graph.get("content_hash"))}
