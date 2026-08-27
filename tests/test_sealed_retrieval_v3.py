from __future__ import annotations

import hashlib
import json
import threading
import time

import pytest

from messungen.sealed_retrieval_v3 import (
    cosine,
    evaluate,
    fallback_channel,
    gate,
    leave_one_repo_out,
    metrics,
    rank,
    rrf,
    run_once,
    select_dev_grid,
    validate_cases,
    write_test_once,
)
from messungen.sealed_retrieval_v3_collector import collect, hash_report


def _cases():
    return [{"id": f"c{i}", "repository": "repo", "split": "dev" if i < 2 else "test",
             "query": f"behaviour number {i}", "expected": "target", "target": {"path": f"d{i}", "symbol": f"s{i}"}}
            for i in range(3)]


def _vectors():
    docs = {f"d{i}": [1.0 if i == j else 0.0 for j in range(3)] for i in range(3)}
    queries = {f"c{i}": docs[f"d{i}"] for i in range(3)}
    return {channel: {"queries": queries, "documents": docs} for channel in ("bge_m3", "coderank_raw")}


def test_cosine_rank_and_rrf_are_deterministic_and_rank_only():
    assert cosine([1, 0], [1, 0]) == 1
    assert rank([1, 0], {"b": [0, 1], "a": [1, 0]}) == [("a", 1.0), ("b", 0.0)]
    assert rrf([["b", "a"], ["a", "b"]], k=1) == ["a", "b"]


def test_leak_and_missing_case_data_fail_closed():
    with pytest.raises(ValueError, match="leak"):
        validate_cases([{**_cases()[0], "query": "s0"}])
    with pytest.raises(ValueError):
        validate_cases([{**_cases()[0], "expected": "no_hit", "target": {}}])


def test_evaluate_and_dev_selection_never_use_test_cases():
    result = evaluate(_cases(), _vectors())
    assert result["bge_m3"]["recall_at_1"] == 1.0
    selected = select_dev_grid(_cases(), _vectors(), [{"rrf_k": 1, "bge_weight": 1, "coderank_weight": 1}])
    assert selected["test_case_ids"] == ["c2"]
    assert [row["point"] for row in selected["candidates"]] == [{"rrf_k": 1, "bge_weight": 1, "coderank_weight": 1}]


def test_loro_and_fallbacks_are_explicit():
    cases = [{**case, "repository": "a" if i < 2 else "b"} for i, case in enumerate(_cases())]
    folds = leave_one_repo_out(cases, {"a": _vectors(), "b": _vectors()}, point={"rrf_k": 1, "bge_weight": 1, "coderank_weight": 1})
    assert {fold["held_out"] for fold in folds} == {"a", "b"}
    assert all(fallback_channel(state) == "bge_m3" for state in ("model_missing", "model_stale", "index_missing", "index_stale"))
    with pytest.raises(ValueError):
        fallback_channel("healthy")


def test_gate_requires_strict_fusion_and_prose_identity():
    base = {"prose_bge_identity": True, "leak_free": True, "test_runs": 1,
            "unique_coderank_hits": 1, "bge_m3": {"recall_at_1": .5, "mrr": .5},
            "coderank_raw": {"recall_at_1": .6, "mrr": .6},
            "rank_only_rrf": {"recall_at_1": .7, "mrr": .7}}
    assert gate(base)["hypothesis"] == "H1"
    base["rank_only_rrf"] = {"recall_at_1": .6, "mrr": .7}
    assert gate(base)["hypothesis"] == "H0"
    base["prose_bge_identity"] = False
    assert gate(base)["hypothesis"] == "UNDECIDED"


def test_test_once_writes_atomically_and_rejects_reuse(tmp_path):
    result_path = tmp_path / "result.json"
    assert run_once(result_path, lambda: {"test_runs": 1}) == {"test_runs": 1}
    with pytest.raises(RuntimeError, match="already exists"):
        run_once(result_path, lambda: {"test_runs": 2})
    with pytest.raises(RuntimeError, match="already exists"):
        write_test_once(result_path, {"test_runs": 3})
    assert json.loads(result_path.read_text()) == {"test_runs": 1}
    assert result_path.with_name("result.json.lock").exists()


def test_test_once_claim_precedes_producer_and_allows_one_concurrent_caller(tmp_path):
    result_path = tmp_path / "race.json"
    calls = []
    def producer():
        calls.append(1)
        time.sleep(.02)
        return {"test_runs": 1}

    outcomes = []
    errors = []

    def call_once():
        try:
            outcomes.append(run_once(result_path, producer))
        except RuntimeError as error:
            errors.append(error)

    threads = [threading.Thread(target=call_once) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3)
    assert len(calls) == 1
    assert len(outcomes) == 1
    assert len(errors) == 1


def test_collector_validates_hashes_and_never_returns_payloads():
    cases = [{**case, "id": f"{case['id']}-{index}", "query": f"{case['query']} copy {index}",
              "repository": "abc"[index // 5]}
             for index, case in enumerate(_cases() * 5)]
    manifest = {"schema": 3, "cases": [{**case, "query_sha256": hashlib.sha256(case["query"].encode()).hexdigest()} for case in cases]}
    channel_metrics = {channel: {"recall_at_1": .1, "mrr": .1} for channel in ("bge_m3", "coderank_raw", "rank_only_rrf")}
    arm_metrics = {arm: {channel: dict(values) for channel, values in channel_metrics.items()}
                   for arm in ("stripped", "comments_only", "combined")}
    raw = {"schema": 5, "case_count": 15, "test_runs": 1,
           "dev_choice": {"selected": {"rrf_k": 1}}, "test_case_ids": ["c2"], "dev_case_ids": ["c0", "c1"],
           "loro_folds": [{"held_out": name, "arm_metrics": arm_metrics}
                          for name in ("a", "b", "c")],
           "ablations": ["stripped", "comments_only", "combined"],
           "arm_metrics": arm_metrics,
           "fallbacks": {key: "bge_m3" for key in ("model_missing", "model_stale", "index_missing", "index_stale")},
           "prose_bge_identity": True, "leak_free": True,
           "operational": {"elapsed_seconds": 1, "max_rss_bytes": 2, "max_p95_latency_ms": 3},
           "fallback_results": {state: {"channel": "bge_m3", "metrics": dict(channel_metrics["bge_m3"]), "matches_bge": True}
                                for state in ("model_missing", "model_stale", "index_missing", "index_stale")},
           "unique_coderank_hits": 1, "bge_m3": {"recall_at_1": .1, "mrr": .1},
           "coderank_raw": {"recall_at_1": .2, "mrr": .2}, "rank_only_rrf": {"recall_at_1": .3, "mrr": .3}}
    output = collect(manifest, raw, raw_sha256=hash_report(raw))
    assert output["status"] == "PASS" and output["hypothesis"] == "H1"
    assert "query" not in output and "labels" not in output
    old_manifest = {**manifest, "schema": 2}
    assert collect(old_manifest, raw, raw_sha256=hash_report(raw))["status"] == "FAIL"
    raw["queries"] = "must not be accepted"
    assert collect(manifest, raw, raw_sha256=hash_report(raw))["status"] == "FAIL"


def test_run_emits_all_ablations_and_three_loro_folds_for_v2_shape():
    from messungen.sealed_retrieval_v3 import run

    cases = []
    for repo, split, offset in (("brainlehr", "train", 0), ("hermes-brainlehr", "dev", 5), ("sigmaforge", "test", 10)):
        for index in range(offset, offset + 5):
            cases.append({"id": f"case-{index}", "repository": repo, "split": split,
                          "query": f"behaviour letter {chr(97 + index)}", "expected": "target",
                          "target": {"path": f"doc-{index}", "symbol": f"symbol-{index}"}})
    documents = {f"doc-{index}": [1.0 if index == dimension else 0.0 for dimension in range(15)] for index in range(15)}
    queries = {f"case-{index}": documents[f"doc-{index}"] for index in range(15)}
    vectors = {channel: {arm: {"queries": dict(queries), "documents": documents} for arm in ("stripped", "comments_only", "combined")}
               for channel in ("bge_m3", "coderank_raw")}
    for channel in ("bge_m3", "coderank_raw"):
        vectors[channel]["comments_only"]["queries"]["case-10"] = [0.0] * 15
    vectors["prose_bge_identity"] = True
    report = run(cases, vectors, [{"rrf_k": 60, "bge_weight": 1, "coderank_weight": 1}])
    assert set(report["arm_metrics"]) == {"stripped", "comments_only", "combined"}
    assert report["arm_metrics"]["comments_only"]["bge_m3"]["mrr"] < report["arm_metrics"]["combined"]["bge_m3"]["mrr"]
    assert {fold["held_out"] for fold in report["loro_folds"]} == {"brainlehr", "hermes-brainlehr", "sigmaforge"}
    assert set(report["fallback_results"]) == {"model_missing", "model_stale", "index_missing", "index_stale"}
    assert all(row["channel"] == "bge_m3" and row["matches_bge"] for row in report["fallback_results"].values())
