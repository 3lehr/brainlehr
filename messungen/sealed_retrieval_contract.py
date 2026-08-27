"""Small, fail-closed P103 decision contract; it never embeds or activates."""
from __future__ import annotations

import hashlib
import json


_MODALITIES = frozenset(("de_prose", "en_prose", "code", "signature", "consumer", "error", "impact", "no_hit"))
_ABLATIONS = frozenset(("stripped", "comments_only", "combined", "generated_annotation"))
_CHANNELS = frozenset(("bge_annotation", "coderank_raw", "rank_only_rrf"))


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def freeze_manifest(manifest: dict) -> dict:
    """Validate immutable pre-test inputs; no query/label text is retained."""
    if manifest.get("schema") != 1 or set(manifest) != {"schema", "splits", "test_queries_sha256", "dev_grid", "modalities", "ablations", "channels"}:
        raise ValueError("strict sealed manifest required")
    splits = manifest["splits"]
    if set(splits) != {"train", "dev", "test"} or not all(isinstance(splits[name], list) and splits[name] for name in splits):
        raise ValueError("train/dev/test splits required")
    groups = [set(splits[name]) for name in ("train", "dev", "test")]
    if any(left & right for index, left in enumerate(groups) for right in groups[index + 1:]):
        raise ValueError("splits must be disjoint by repository")
    if not isinstance(manifest["test_queries_sha256"], str) or len(manifest["test_queries_sha256"]) != 64:
        raise ValueError("sealed test hash required")
    if not isinstance(manifest["dev_grid"], list) or not manifest["dev_grid"]:
        raise ValueError("finite dev grid required")
    if set(manifest["modalities"]) != _MODALITIES or set(manifest["ablations"]) != _ABLATIONS or set(manifest["channels"]) != _CHANNELS:
        raise ValueError("all required sealed arms required")
    return {"schema": 1, "sha256": _digest(manifest), "test_queries_sha256": manifest["test_queries_sha256"]}


def decide(manifest: dict, report: dict) -> dict:
    """Return H0 unless every predeclared sealed gate proves H1."""
    freeze_manifest(manifest)
    required = {"test_runs", "loro_runs", "prose_bge_identical", "fallbacks", "operational", *_CHANNELS}
    if not required <= set(report) or report["test_runs"] != 1 or report["loro_runs"] < 3:
        raise ValueError("sealed test exactly once and leave-one-repo-out required")
    if report["prose_bge_identical"] is not True or set(report["fallbacks"]) != {"model_missing", "model_stale", "index_stale"}:
        raise ValueError("prose/fallback contract missing")
    if not all(report["fallbacks"][key] == "bge" for key in report["fallbacks"]):
        raise ValueError("fallback must be BGE")
    if not all(isinstance(report["operational"].get(key), (int, float)) for key in ("elapsed_seconds", "max_rss_bytes")):
        raise ValueError("time and RAM evidence required")
    bge, code, fusion = (report[name] for name in ("bge_annotation", "coderank_raw", "rank_only_rrf"))
    win = (code.get("unique_relevant_hits", 0) > 0 and
           all(fusion.get(metric, 0) > max(bge.get(metric, 0), code.get(metric, 0))
               for metric in ("recall_at_1", "mrr")))
    return {"hypothesis": "H1", "active_channel": "rank_only_rrf"} if win else {"hypothesis": "H0", "active_channel": "bge_annotation"}
