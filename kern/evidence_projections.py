"""Small, source-bound projections for optional runtime evidence."""
from __future__ import annotations

import hashlib
import json


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def otel_trace_projection(trace: dict, *, source_revision: str, tree_hash: str,
                          graph: dict) -> dict:
    """Accept only sanitized spans bound to the graph revision and tree."""
    if trace.get("revision") != source_revision or trace.get("tree_hash") != tree_hash:
        return {"status": "coverage_gap", "coverage_gaps": ["trace revision/tree hash is not current"]}
    spans = trace.get("spans", [])
    if not isinstance(spans, list) or any(not isinstance(span, dict) for span in spans):
        return {"status": "coverage_gap", "coverage_gaps": ["sanitized span list missing"]}
    forbidden = {"payload", "events", "body", "exception", "attributes_raw"}
    if any(forbidden.intersection(span) for span in spans):
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
    nodes = sorted(graph.get("nodes", []), key=lambda node: node.get("id", ""))
    edges = sorted(graph.get("edges", []), key=lambda edge: (edge.get("from", ""), edge.get("to", "")))
    routes = [{"from": edge.get("from"), "to": edge.get("to"), "edge_type": edge.get("edge_type"),
               "source_ref": edge.get("source_ref")} for edge in edges]
    return {"schema": 1, "source_graph_schema": graph["schema"],
            "source_revision": graph["source_revision"], "content_hash": graph["content_hash"],
            "nodes": [{"id": node["id"], "kind": node.get("kind")} for node in nodes],
            "routes": routes, "coverage_gaps": list(graph.get("coverage_gaps", [])),
            "current": bool(graph.get("source_revision") and graph.get("content_hash"))}
