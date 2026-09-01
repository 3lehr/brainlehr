import pytest
from kern.evidence_adapters import normalize_record

def test_bdw_p42_ac1_tree_sitter_python():
    payload = {
        "source": "fixture",
        "revision": "fixture-123",
        "language": "python",
        "node": {"name": "func_name"},
        "edges": [{"type": "calls", "from": "func_name", "to": "other_func"}],
        "tool_version": "0.1"
    }
    res = normalize_record("tree_sitter", payload)
    assert res["kind"] == "tree_sitter"
    nodes = {n["id"]: n for n in res["nodes"]}
    assert "func_name" in nodes
    assert nodes["func_name"]["kind"] == "symbol"
    assert "other_func" in nodes
    assert res["edges"][0]["type"] == "syntax_calls"
    assert res["edges"][0]["from"] == "func_name"
    assert res["edges"][0]["to"] == "other_func"

def test_bdw_p42_ac1_tree_sitter_non_python():
    payload = {
        "source": "fixture",
        "revision": "fixture-123",
        "language": "rust",
        "node": {"name": "rust_func"},
        "edges": [{"type": "returns", "from": "rust_func", "to": "value"}],
        "tool_version": "0.2"
    }
    res = normalize_record("tree_sitter", payload)
    assert res["kind"] == "tree_sitter"
    nodes = {n["id"]: n for n in res["nodes"]}
    assert nodes["rust_func"]["language"] == "rust"

def test_bdw_p42_ac1_scip():
    payload = {
        "source": "fixture",
        "revision": "fixture-123",
        "tool_version": "0.3",
        "documents": [
            {
                "relative_path": "main.py",
                "language": "python",
                "symbols": [{"symbol": "main", "kind": "function"}]
            }
        ],
        "occurrences": [
            {"symbol": "main"}
        ]
    }
    res = normalize_record("scip", payload)
    assert res["kind"] == "scip"
    nodes = {n["id"]: n for n in res["nodes"]}
    assert "main.py" in nodes
    assert "main" in nodes
    assert "occurrence:main" in nodes
    edges = {(e["type"], e["from"], e["to"]) for e in res["edges"]}
    assert ("defines", "main.py", "main") in edges
    assert ("references", "occurrence:main", "main") in edges

def test_bdw_p42_ac1_semgrep():
    payload = {
        "source": "fixture",
        "revision": "fixture-123",
        "tool_version": "0.4",
        "results": [
            {"check_id": "rule_name", "path": "main.py"}
        ]
    }
    res = normalize_record("semgrep", payload)
    assert res["kind"] == "semgrep"
    nodes = {n["id"]: n for n in res["nodes"]}
    assert "main.py" in nodes
    assert "rule:rule_name" in nodes
    edges = {(e["type"], e["from"], e["to"]) for e in res["edges"]}
    assert ("rule_finding", "rule:rule_name", "main.py") in edges
