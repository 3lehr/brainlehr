from __future__ import annotations

import json
from pathlib import Path

from messungen.sealed_retrieval_collector import collect, hash_report


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "tests" / "fixtures" / "sealed_code_retrieval_manifest.json").read_text())


def test_raw_score_report_is_fail_closed_without_sealed_metadata():
    raw = {"schema": 4, "matrix_count": 28, "model": {"bge_m3": "bge", "coderankembed": "code"},
           "latency_seconds": 1, "max_rss": 2}
    result = collect(MANIFEST, raw, raw_sha256=hash_report(raw))
    assert result["status"] == "FAIL"
    assert result["hypothesis"] == "UNDECIDED"
    assert set(result["missing"]) == {
        "bge_identical_prose_control", "sealed_train_dev_test_once", "leave_one_repo_out",
        "comment_annotation_ablations", "missing_stale_bge_fallbacks",
    }


def test_collector_never_reads_query_or_label_payloads():
    raw = {"schema": 4, "matrix_count": 28, "model": {"bge_m3": "bge"},
           "queries": "should not be inspected", "labels": ["also ignored"]}
    result = collect(MANIFEST, raw, raw_sha256="b" * 64)
    assert result["status"] == "FAIL"
    assert "queries" not in result and "labels" not in result
