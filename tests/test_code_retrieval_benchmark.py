from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern"), str(ROOT / "messungen")]

import code_retrieval_benchmark as benchmark  # noqa: E402


def test_frozen_goldset_targets_exist_at_head():
    goldset = benchmark.load_goldset()
    chunks = benchmark._chunks("HEAD", goldset["candidate_paths"])
    matrices = {matrix["id"]: matrix for matrix in goldset["matrices"]}
    assert set(matrices) == {"en_prose_to_python", "de_prose_to_python", "code_signature_to_python", "de_brainlehr_prose_to_prose"}
    targets = {case["target"] for matrix in goldset["matrices"] for case in matrix["cases"]
               if matrix["candidate_set"] == "python" and case.get("target")}
    assert targets <= set(chunks)
    for matrix in matrices.values():
        assert sum(bool(case.get("target")) for case in matrix["cases"]) == 10
        assert sum(not case.get("target") for case in matrix["cases"]) == 3
    assert all(not text.startswith("# ") for text in chunks.values())


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


def test_activation_requires_all_code_wins_and_prose_nonregression():
    metrics = lambda r1, mrr: {"metrics": {"recall_at_1": r1, "mrr": mrr}}
    matrices = [
        {"id": matrix_id, "bge_m3": metrics(0.4, 0.4), "coderankembed": metrics(0.5, 0.5)}
        for matrix_id in benchmark.CODE_MATRIX_IDS
    ] + [{"id": "de_brainlehr_prose_to_prose", "bge_m3": metrics(0.6, 0.6), "coderankembed": metrics(0.6, 0.6)}]
    assert benchmark.activation_decision(matrices)["activate_separate_code_channel"] is True
    matrices[0]["coderankembed"] = metrics(0.4, 0.5)
    assert benchmark.activation_decision(matrices)["activate_separate_code_channel"] is False
