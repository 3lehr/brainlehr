"""Normalize bounded, revision-tagged evidence from optional local analyzers.

The adapters consume already-produced artifacts.  They never invoke a tool,
write Brainlehr, or turn an unavailable analyzer into guessed evidence.
"""
from __future__ import annotations

import hashlib
import json
import re


SCHEMA = 2
EVIDENCE_STRENGTH = {
    "tree_sitter": "syntax", "scip": "symbol", "joern": "cpg",
    "otlp": "runtime", "semgrep": "rule", "codeql": "rule",
}

_JOERN_NODE = re.compile(r'^\s*"(?P<id>\d+)"\s+\[label="(?P<label>[^"]+)"(?P<attrs>[^\]]*)\];$', re.M)
_JOERN_EDGE = re.compile(r'^\s*"(?P<out>\d+)"\s+->\s+"(?P<in>\d+)"\s+\[label="(?P<label>[^"]+)"', re.M)
_JOERN_ATTR = re.compile(r'\s(?P<key>NAME|FILENAME)="(?P<value>[^"]*)"')


def joern_dot_payload(dot: str, *, revision: str, source: str) -> dict:
    """Extract typed CPG evidence from Joern DOT; deliberately drop raw CODE."""
    nodes = []
    for match in _JOERN_NODE.finditer(dot):
        attrs = {entry["key"].lower(): entry["value"]
                 for entry in _JOERN_ATTR.finditer(match["attrs"])}
        nodes.append({"id": match["id"], "label": match["label"],
                      "name": attrs.get("name", ""), "file": attrs.get("filename", "")})
    return {"source": source, "revision": revision, "nodes": nodes,
            "edges": [{"out": edge["out"], "in": edge["in"], "label": edge["label"]}
                      for edge in _JOERN_EDGE.finditer(dot)]}


def _safe_otlp_text(value: object) -> str:
    """Bounded display metadata; never carry arbitrary attribute values."""
    text = str(value)
    return text[:256] if text.isprintable() else "[redacted]"


def _node(value: str, kind: str, **extra: object) -> dict:
    return {"id": value, "kind": kind, **{key: extra[key] for key in sorted(extra)}}


def _edge(kind: str, source: str, target: str, evidence: dict) -> dict:
    return {"type": kind, "from": source, "to": target, "evidence": evidence}


def _base(kind: str, payload: dict) -> dict:
    if kind not in EVIDENCE_STRENGTH:
        raise ValueError("unsupported analyzer")
    revision = str(payload.get("revision", "")).strip()
    source = str(payload.get("source", "")).strip()
    if not revision or not source:
        raise ValueError("analyzer record requires source and revision")
    return {"kind": kind, "revision": revision, "source": source, "nodes": [], "edges": [],
            "provenance": {"schema": SCHEMA, "fixture": revision.startswith("fixture-"),
                           "strength": EVIDENCE_STRENGTH[kind], "source_ref": source}}


def normalize_record(kind: str, payload: dict) -> dict:
    """Return the common graph-fragment ABI for one optional analyzer artifact."""
    row = _base(kind, payload)
    evidence = dict(row["provenance"], revision=row["revision"])
    if kind == "tree_sitter":
        node = payload.get("node") or {}
        name = str(node.get("name") or node.get("type") or "syntax")
        row["nodes"].append(_node(name, "symbol", language=payload.get("language", "unknown")))
        for edge in payload.get("edges", []):
            target = str(edge.get("to", "unknown"))
            row["nodes"].append(_node(target, "symbol"))
            row["edges"].append(_edge("syntax_" + str(edge.get("type", "relation")),
                                      str(edge.get("from", name)), target, evidence))
    elif kind == "scip":
        for document in payload.get("documents", []):
            path = str(document.get("relative_path", "unknown"))
            row["nodes"].append(_node(path, "file", language=document.get("language", "unknown")))
            for symbol in document.get("symbols", []):
                symbol_id = str(symbol.get("symbol", "unknown"))
                row["nodes"].append(_node(symbol_id, "symbol", symbol_kind=symbol.get("kind", "unknown")))
                row["edges"].append(_edge("defines", path, symbol_id, evidence))
        for occurrence in payload.get("occurrences", []):
            symbol_id = str(occurrence.get("symbol", "unknown"))
            row["nodes"].append(_node("occurrence:" + symbol_id, "reference"))
            row["edges"].append(_edge("references", "occurrence:" + symbol_id, symbol_id, evidence))
    elif kind == "joern":
        for node in payload.get("nodes", []):
            ident = "cpg:" + str(node.get("id", "unknown"))
            row["nodes"].append(_node(ident, "cpg_" + str(node.get("label", "node")).lower(),
                                      name=node.get("name", ""), file=node.get("file", "")))
        for edge in payload.get("edges", []):
            source, target = "cpg:" + str(edge.get("out", "unknown")), "cpg:" + str(edge.get("in", "unknown"))
            row["nodes"].extend([_node(source, "cpg_unknown"), _node(target, "cpg_unknown")])
            row["edges"].append(_edge("cpg_" + str(edge.get("label", "relation")).lower(), source, target, evidence))
    elif kind == "otlp":
        for resource in payload.get("resourceSpans", []):
            for scope in resource.get("scopeSpans", []):
                for span in scope.get("spans", []):
                    ident = "span:" + str(span.get("spanId", "unknown"))
                    # OTLP attributes/events/status are deliberately dropped:
                    # they are untrusted payload, not causal graph metadata.
                    extra = {"name": _safe_otlp_text(span.get("name", ""))}
                    for key in ("startTimeUnixNano", "endTimeUnixNano"):
                        if isinstance(span.get(key), (int, float)):
                            extra[key] = span[key]
                    row["nodes"].append(_node(ident, "runtime_span", **extra))
                    parent = str(span.get("parentSpanId", ""))
                    if parent:
                        parent_id = "span:" + parent
                        row["nodes"].append(_node(parent_id, "runtime_span"))
                        row["edges"].append(_edge("runtime_parent", parent_id, ident, evidence))
        if not row["edges"] and row["nodes"]:
            row["edges"].append(_edge("runtime_observed", row["nodes"][0]["id"], row["nodes"][0]["id"], evidence))
    else:  # semgrep / codeql SARIF
        if kind == "codeql":
            payload = {"source": payload.get("source", "codeql"), "revision": payload.get("revision", ""),
                       "results": [
                           {"check_id": result.get("ruleId", "unknown"),
                            "path": result.get("locations", [{}])[0].get("physicalLocation", {}).get("artifactLocation", {}).get("uri", "unknown")}
                           for result in payload.get("runs", [{}])[0].get("results", [])]}
        for result in payload.get("results", []):
            path = str(result.get("path", "unknown"))
            rule = str(result.get("check_id", "unknown"))
            row["nodes"].extend([_node(path, "file"), _node("rule:" + rule, "rule")])
            row["edges"].append(_edge("rule_finding", "rule:" + rule, path, evidence))
    row["nodes"] = list({node["id"]: node for node in row["nodes"]}.values())
    row["nodes"].sort(key=lambda node: node["id"])
    row["edges"].sort(key=lambda edge: (edge["type"], edge["from"], edge["to"]))
    canonical = json.dumps(row, sort_keys=True, separators=(",", ":"))
    row["content_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    return row


def unavailable_record(kind: str, revision: str, reason: str) -> dict:
    """An honest non-result used for missing executables, timeout or invalid output."""
    row = _base(kind, {"source": kind, "revision": revision})
    row["coverage_gaps"] = [reason]
    row["status"] = "coverage_gap"
    return row
