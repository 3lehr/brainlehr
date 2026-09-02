"""P30: v9 CodeRank H0/H1 evaluation — test-driven preparation.

These tests verify that the v9 sealed pipeline (v8 scorer + v8 collector
+ v3 gate) correctly decides H0, H1, or UNDECIDED given the v9 manifest
thresholds and schema.
"""
from __future__ import annotations

import json
from pathlib import Path

from messungen.sealed_retrieval_v3 import gate
from messungen.sealed_retrieval_v8_runner import run
from messungen.sealed_retrieval_v8_collector import collect as collect_v8, _resolved
from messungen.sealed_retrieval_v3_collector import hash_report


ROOT = Path(__file__).resolve().parents[1]


def _v9_manifest():
    return json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v9.json").read_text())


def _simulated_vectors(cases):
    """Produce deterministic identity vectors: every case hits its own target."""
    paths = sorted({case["target"]["path"] for case in cases if case["target"]})
    docs = {path: [float(i == j) for j in range(len(paths))] for i, path in enumerate(paths)}
    queries = {case["id"]: docs[case["target"]["path"]] if case["target"] else [0.0] * len(paths)
               for case in cases}
    vectors = {channel: {arm: {"queries": dict(queries), "documents": docs}
                         for arm in ("stripped", "comments_only", "combined")}
               for channel in ("bge_m3", "coderank_raw")}
    vectors["prose_bge_identity"] = True
    return vectors


def test_v9_gate_h1_when_fusion_strictly_wins_and_all_gates_pass():
    """Fusion must be strictly better than BOTH bge_m3 and coderank_raw."""
    base = {
        "prose_bge_identity": True,
        "leak_free": True,
        "test_runs": 1,
        "unique_coderank_hits": 1,
        "bge_m3": {"recall_at_1": 0.4, "mrr": 0.45},
        "coderank_raw": {"recall_at_1": 0.5, "mrr": 0.55},
        "rank_only_rrf": {"recall_at_1": 0.6, "mrr": 0.65},
    }
    result = gate(base)
    assert result["hypothesis"] == "H1"
    assert result["active_channel"] == "rank_only_rrf"
    assert result["missing"] == []


def test_v9_gate_h0_when_fusion_ties_bge_on_recall():
    """Strict > required; == is not enough."""
    base = {
        "prose_bge_identity": True,
        "leak_free": True,
        "test_runs": 1,
        "unique_coderank_hits": 1,
        "bge_m3": {"recall_at_1": 0.6, "mrr": 0.45},
        "coderank_raw": {"recall_at_1": 0.5, "mrr": 0.55},
        "rank_only_rrf": {"recall_at_1": 0.6, "mrr": 0.65},
    }
    result = gate(base)
    assert result["hypothesis"] == "H0"
    assert result["active_channel"] == "bge_m3"


def test_v9_gate_h0_when_fusion_ties_coderank_on_mrr():
    """Must beat BOTH channels, not just one."""
    base = {
        "prose_bge_identity": True,
        "leak_free": True,
        "test_runs": 1,
        "unique_coderank_hits": 1,
        "bge_m3": {"recall_at_1": 0.4, "mrr": 0.45},
        "coderank_raw": {"recall_at_1": 0.5, "mrr": 0.65},
        "rank_only_rrf": {"recall_at_1": 0.6, "mrr": 0.65},
    }
    result = gate(base)
    assert result["hypothesis"] == "H0"


def test_v9_gate_undecided_when_prose_identity_missing():
    """Missing gates → UNDECIDED, not H0."""
    base = {
        "prose_bge_identity": False,
        "leak_free": True,
        "test_runs": 1,
        "unique_coderank_hits": 1,
        "bge_m3": {"recall_at_1": 0.4, "mrr": 0.45},
        "coderank_raw": {"recall_at_1": 0.5, "mrr": 0.55},
        "rank_only_rrf": {"recall_at_1": 0.6, "mrr": 0.65},
    }
    result = gate(base)
    assert result["hypothesis"] == "UNDECIDED"
    assert "prose_bge_identity" in result["missing"]


def test_v9_gate_undecided_when_unique_hits_below_threshold():
    """unique_coderank_hits < 1 blocks H1."""
    base = {
        "prose_bge_identity": True,
        "leak_free": True,
        "test_runs": 1,
        "unique_coderank_hits": 0,
        "bge_m3": {"recall_at_1": 0.4, "mrr": 0.45},
        "coderank_raw": {"recall_at_1": 0.5, "mrr": 0.55},
        "rank_only_rrf": {"recall_at_1": 0.6, "mrr": 0.65},
    }
    result = gate(base)
    assert result["hypothesis"] == "H0"  # 0 is not UNDECIDED because gates are present


def test_v9_collector_produces_schema_eight_with_seal_hash():
    """The v8 collector wrapped for v9 must emit schema 8 + seal_sha256."""
    manifest = _v9_manifest()
    cases = _resolved(manifest)["cases"]
    vectors = _simulated_vectors(cases)
    raw = run(cases, vectors, manifest["dev_rrf_grid"])

    report = collect_v8(manifest, raw, raw_sha256=hash_report(raw))
    assert report["status"] == "PASS"
    assert report["schema"] == 8
    assert "seal_sha256" in report


def test_v9_collector_h1_with_artificial_metrics():
    """Collector decides H1 when raw metrics show strict fusion wins."""
    manifest = _v9_manifest()
    cases = _resolved(manifest)["cases"]
    vectors = _simulated_vectors(cases)
    raw = run(cases, vectors, manifest["dev_rrf_grid"])
    # Override metrics to force H1 while keeping all structural fields intact
    raw["unique_coderank_hits"] = 5
    raw["bge_m3"] = {"recall_at_1": 0.4, "mrr": 0.45}
    raw["coderank_raw"] = {"recall_at_1": 0.5, "mrr": 0.55}
    raw["rank_only_rrf"] = {"recall_at_1": 0.6, "mrr": 0.65}
    for arm in ("stripped", "comments_only", "combined"):
        for ch in ("bge_m3", "coderank_raw", "rank_only_rrf"):
            raw["arm_metrics"][arm][ch] = dict(raw[ch])
    for fold in raw["loro_folds"]:
        for arm in ("stripped", "comments_only", "combined"):
            for ch in ("bge_m3", "coderank_raw", "rank_only_rrf"):
                fold["arm_metrics"][arm][ch] = dict(raw[ch])
        fold["metrics"] = dict(raw["rank_only_rrf"])

    report = collect_v8(manifest, raw, raw_sha256=hash_report(raw))
    assert report["status"] == "PASS"
    assert report["hypothesis"] == "H1"
    assert report["active_channel"] == "rank_only_rrf"


def test_v9_collector_rejects_wrong_raw_hash():
    manifest = _v9_manifest()
    cases = _resolved(manifest)["cases"]
    vectors = _simulated_vectors(cases)
    raw = run(cases, vectors, manifest["dev_rrf_grid"])

    report = collect_v8(manifest, raw, raw_sha256="0" * 64)
    assert report["status"] == "FAIL"
    assert "raw_hash" in report["missing"]


def test_v9_collector_rejects_schema_five_raw():
    """v8 collector requires schema 8 raw from the runner."""
    manifest = _v9_manifest()
    cases = _resolved(manifest)["cases"]
    vectors = _simulated_vectors(cases)
    raw = run(cases, vectors, manifest["dev_rrf_grid"])
    raw["schema"] = 5  # force downgrade to trigger rejection

    report = collect_v8(manifest, raw, raw_sha256=hash_report(raw))
    assert report["status"] == "FAIL"
    assert "runner_schema" in report["missing"]


def test_v9_full_run_emits_all_required_v8_fields():
    """End-to-end: simulated v9 run must produce every field the collector gates on."""
    manifest = _v9_manifest()
    cases = _resolved(manifest)["cases"]
    vectors = _simulated_vectors(cases)
    raw = run(cases, vectors, manifest["dev_rrf_grid"])

    # v8 runner emits schema 8 directly.
    assert set(raw["arm_metrics"]) == {"stripped", "comments_only", "combined"}
    for arm in ("stripped", "comments_only", "combined"):
        for channel in ("bge_m3", "coderank_raw", "rank_only_rrf"):
            assert "recall_at_1" in raw["arm_metrics"][arm][channel]
            assert "mrr" in raw["arm_metrics"][arm][channel]

    assert len(raw["loro_folds"]) == 3
    assert {fold["held_out"] for fold in raw["loro_folds"]} == {"brainlehr", "hermes-brainlehr", "sigmaforge"}
    assert set(raw["fallback_results"]) == {"model_missing", "model_stale", "index_missing", "index_stale"}
    assert raw["unique_coderank_hits"] >= 0
    assert raw["prose_bge_identity"] is True
    assert raw["leak_free"] is True
