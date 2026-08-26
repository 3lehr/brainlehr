from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern"), str(ROOT / "messungen")]

import code_retrieval_benchmark as benchmark  # noqa: E402


def test_frozen_goldset_targets_exist_at_head():
    goldset = benchmark.load_goldset()
    chunks = benchmark._chunks("HEAD", goldset["candidate_paths"])
    targets = {case["target"] for case in goldset["cases"] if case.get("target")}
    assert targets <= set(chunks)
    assert len([case for case in goldset["cases"] if case.get("target")]) == 10
    assert len([case for case in goldset["cases"] if not case.get("target")]) == 3


def test_metrics_are_rank_based_and_negative_cases_are_reported():
    cases = [
        {"id": "p", "query": "p", "target": "a"},
        {"id": "n", "query": "n", "target": None},
    ]
    vectors = {"a": [1.0, 0.0], "b": [0.0, 1.0]}
    result = benchmark.evaluate(cases, vectors, [[1.0, 0.0], [0.0, 1.0]])
    assert result["recall_at_1"] == 1.0
    assert result["mrr"] == 1.0
    assert result["negative_n"] == 1
    assert result["negative_max_score"] == 1.0


def test_missing_code_model_is_a_loud_unavailable_state(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    try:
        benchmark._coderank("/does/not/exist", ["x"], query=True)
    except RuntimeError as error:
        assert "unavailable" in str(error)
    else:  # pragma: no cover - import availability varies by developer machine
        raise AssertionError("missing code model runtime must not produce a score")
