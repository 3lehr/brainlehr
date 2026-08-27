"""P103: a sealed code-retrieval decision is fail-closed and rank-only."""
from __future__ import annotations

import pytest
import json
from pathlib import Path

from messungen.sealed_retrieval_contract import decide, freeze_manifest


def manifest():
    return {
        "schema": 1,
        "splits": {"train": ["repo-a"], "dev": ["repo-b"], "test": ["repo-c"]},
        "test_queries_sha256": "a" * 64,
        "dev_grid": [{"rrf_k": 60, "weight": 1}, {"rrf_k": 60, "weight": 2}],
        "modalities": ["de_prose", "en_prose", "code", "signature", "consumer", "error", "impact", "no_hit"],
        "ablations": ["stripped", "comments_only", "combined", "generated_annotation"],
        "channels": ["bge_annotation", "coderank_raw", "rank_only_rrf"],
    }


def test_tracked_manifest_is_freezable_before_any_model_run():
    path = Path(__file__).parent / "fixtures" / "sealed_code_retrieval_manifest.json"
    assert freeze_manifest(json.loads(path.read_text()))["test_queries_sha256"] == "9562f432c91f6f3866896f4362953a5b5f083c1bce47114afa3db67830cde366"


def evidence(**overrides):
    base = {
        "test_runs": 1, "loro_runs": 3, "prose_bge_identical": True,
        "fallbacks": {"model_missing": "bge", "model_stale": "bge", "index_stale": "bge"},
        "operational": {"elapsed_seconds": 1.0, "max_rss_bytes": 1},
        "bge_annotation": {"recall_at_1": 0.5, "mrr": 0.5},
        "coderank_raw": {"recall_at_1": 0.6, "mrr": 0.6, "unique_relevant_hits": 1},
        "rank_only_rrf": {"recall_at_1": 0.7, "mrr": 0.7},
    }
    return base | overrides


def test_freeze_requires_disjoint_splits_finite_dev_grid_and_all_arms():
    frozen = freeze_manifest(manifest())
    assert frozen["sha256"]
    bad = manifest()
    bad["splits"]["dev"] = ["repo-a"]
    with pytest.raises(ValueError, match="disjoint"):
        freeze_manifest(bad)


def test_h1_needs_unique_coderank_hit_and_fusion_beating_both_singles():
    assert decide(manifest(), evidence())["hypothesis"] == "H1"
    result = decide(manifest(), evidence(coderank_raw={"recall_at_1": 0.6, "mrr": 0.6,
                                                       "unique_relevant_hits": 0}))
    assert result == {"hypothesis": "H0", "active_channel": "bge_annotation"}


@pytest.mark.parametrize("field", ["test_runs", "loro_runs", "prose_bge_identical", "fallbacks", "operational"])
def test_missing_or_nonsealed_evidence_fails_closed(field):
    value = evidence()
    value.pop(field)
    with pytest.raises(ValueError):
        decide(manifest(), value)


def test_second_sealed_test_run_is_rejected():
    with pytest.raises(ValueError, match="exactly once"):
        decide(manifest(), evidence(test_runs=2))
