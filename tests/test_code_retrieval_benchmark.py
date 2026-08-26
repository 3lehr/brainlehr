from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "docs" / "REQUIREMENTS_BRAINLEHR.md"
PLAN = ROOT / "docs" / "PLAN_GESAMTBAU_2026-08-21.md"
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


def test_core_multilingual_matrix_and_extension_gaps_are_explicit():
    report = benchmark.language_coverage()
    assert report["status"] == "bounded"
    assert report["code_rank_activated"] is False
    assert report["coverage_gaps"] == []
    assert all(report["languages"][language]["status"] == "available"
               for language in benchmark.MANDATORY_LANGUAGES)
    assert report["declarative_fixture_languages"] == ("sql", "shell", "yaml", "hcl")
    assert report["extensible_language_gaps"] == ("c_cpp", "csharp", "php", "kotlin", "ruby")


def test_multilingual_goldset_shape_is_frozen_without_model_claims():
    docs, records = benchmark._fixture_documents()
    assert {"dart_flutter" if row["language"] == "dart" else row["language"] for row in records} == set(benchmark.MANDATORY_LANGUAGES)
    assert all(len(docs[language]) == 4 for language in benchmark.MANDATORY_LANGUAGES)
    cases = benchmark._multilingual_cases("rust", ["parse_value", "double_value", "render_value"],
                                          ["turns text digits into a number", "multiplies a numeric input by two", "formats a numeric result for display"],
                                          "de_prose_to_code", "rust.rs", "limit_range")
    assert len(cases) == 5
    assert all("parse" not in case["query"].casefold() for case in cases)


def test_multilingual_queries_reject_symbol_and_file_leaks():
    try:
        benchmark._assert_identifier_free("Call parse Value in rust", ["parseValue", "rust.rs"])
    except ValueError as error:
        assert "leaks" in str(error)
    else:
        raise AssertionError("split identifiers must reject the goldset")


def test_multilingual_metrics_keep_models_and_fusion_in_separate_rankings():
    cases = [{"id": "a", "target": "one"}, {"id": "b", "target": None}]
    metrics = benchmark._ranked_metrics(cases, [["one", "two"], ["two", "one"]])
    assert metrics["recall_at_1"] == metrics["mrr"] == 1.0
    assert benchmark._rrf_order([("one", 1.0), ("two", 0.0)], [("two", 1.0), ("one", 0.0)]) == ["one", "two"]
    assert benchmark.ACTIVATION_THRESHOLDS["per_matrix_recall_at_1_drop"] == 0.0


def test_multilingual_activation_needs_every_matrix_and_prose_control():
    channels = lambda r1, mrr: {"metrics": {"recall_at_1": r1, "mrr": mrr}}
    matrices = [{"language": language, "query_modality": modality,
                 "validation": {"leak_free": True, "same_language_hard_negative_n": 3,
                                "same_language_code_hard_negative_n": 1},
                 "bge_m3": channels(0.5, 0.5), "coderankembed": channels(0.6, 0.6),
                 "rrf": channels(0.5, 0.5), "router": channels(0.6, 0.6)}
                for language in benchmark.MANDATORY_LANGUAGES
                for modality in benchmark.MULTILINGUAL_MODALITIES]
    prose = {"bge_m3": channels(0.7, 0.7), "coderankembed": channels(0.7, 0.7),
             "rrf": channels(0.7, 0.7), "router": channels(0.7, 0.7)}
    decision = benchmark.multilingual_activation_decision(matrices, prose)
    assert decision["active_channel"] == "router"
    assert decision["candidates"]["router"]["eligible"] is True
    matrices.pop()
    assert benchmark.multilingual_activation_decision(matrices, prose)["active_channel"] == "bge_m3"


def test_ai_lineage_requirements_are_decided_but_not_implemented():
    catalog = CATALOG.read_text()
    plan = PLAN.read_text()
    required = {
        "BDW-P99": ("AI-Kommentare", "brainlehr:link", "menschliche"),
        "BDW-P100": ("Registry", "lazy", "MUSS"),
        "BDW-P101": ("Merkle", "Joins", "MUSS"),
        "BDW-P102": ("Failure", "tombstone", "MUSS"),
        "BDW-P103": ("CodeRank", "leak-freie", "MUSS"),
        "BDW-P104": ("Freiform", "LLM", "MUSS-NICHT"),
    }
    for requirement_id, terms in required.items():
        row = next(line for line in catalog.splitlines() if line.startswith(f"| {requirement_id} "))
        assert "DECIDED" in row and "NOT IMPLEMENTED" in row and "NOT RUN" in row
        assert all(term.casefold() in row.casefold() for term in terms)
        assert requirement_id in plan
