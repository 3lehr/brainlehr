"""Live local P42 channels: syntax, symbols and rules stay distinct."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from kern.evidence_graph import reconcile
from kern import project_context
from tool import static_evidence


ROOT = Path(__file__).resolve().parents[1]
PY_SOURCE = ROOT / "kern" / "evidence_adapters.py"
JS_SOURCE = ROOT / "tests" / "fixtures" / "evidence_adapters" / "tree_sitter_input.js"


def _revision() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout.strip()


@pytest.mark.skipif(not static_evidence.available(), reason="P42 local tools unavailable")
def test_live_static_channels_normalize_and_reconcile_into_impact_graph():
    revision = _revision()
    syntax_py = static_evidence.run("tree_sitter", PY_SOURCE, revision=revision)
    syntax_js = static_evidence.run("tree_sitter", JS_SOURCE, revision=revision)
    symbols = static_evidence.run("scip", PY_SOURCE, revision=revision)
    rules = static_evidence.run("semgrep", PY_SOURCE, revision=revision)

    assert syntax_py["provenance"]["strength"] == "syntax" and syntax_py["edges"]
    assert syntax_js["provenance"]["strength"] == "syntax" and syntax_js["edges"]
    assert symbols["provenance"]["strength"] == "symbol" and symbols["edges"]
    assert rules["provenance"]["strength"] == "rule"
    assert {row["provenance"]["tool_version"] for row in (syntax_py, syntax_js, symbols, rules)}

    impact = project_context.impact_graph(ROOT, project_context.impact_chain(ROOT, "HEAD^"), [])
    merged = reconcile(impact, [syntax_py, symbols, rules])
    assert {entry["strength"] for entry in merged["evidence"]} >= {"syntax", "symbol", "rule"}
    assert merged["content_hash"] and merged["source_revision"] == revision
