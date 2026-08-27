"""Independent, fail-closed collector for P103-v3 reports.

Only hashes, counts, metrics and gate states are consumed.  Query/label
payloads are rejected and are never copied into the returned envelope.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping


def hash_report(report: Mapping[str, object]) -> str:
    return hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _commit(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _digest(value: object) -> str:
    return hash_report(value if isinstance(value, Mapping) else {"value": value})


def validate_manifest(manifest: Mapping[str, object]) -> dict[str, object]:
    """Check the immutable v2-shaped corpus without importing the v2 validator."""
    if manifest.get("schema") != 3:
        raise ValueError("P103-v3 manifest schema required")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 15:
        raise ValueError("sealed corpus needs exactly fifteen cases")
    ids: set[object] = set()
    query_hashes: set[str] = set()
    for case in cases:
        if not isinstance(case, Mapping) or not {"id", "repository", "split", "query", "query_sha256", "expected", "target"} <= set(case):
            raise ValueError("complete v2 case fields required")
        if case["id"] in ids or case["query_sha256"] in query_hashes or not _sha(case["query_sha256"]):
            raise ValueError("case/query identities must be unique and hashed")
        ids.add(case["id"])
        query_hashes.add(case["query_sha256"])
        query = case["query"]
        if not isinstance(query, str) or hashlib.sha256(query.encode()).hexdigest() != case["query_sha256"]:
            raise ValueError("query hash mismatch")
        target = case["target"]
        if case["expected"] == "target":
            if not isinstance(target, Mapping) or not isinstance(target.get("path"), str) or not isinstance(target.get("symbol"), str):
                raise ValueError("positive target required")
            if target["symbol"].casefold() in query.casefold() or target["path"].casefold() in query.casefold():
                raise ValueError("identifier leaks into query")
            proof = case.get("proof")
            if proof is not None and (not isinstance(proof, Mapping) or not _sha(proof.get("sha256"))):
                raise ValueError("positive proof hash required")
        elif case["expected"] != "no_hit" or target is not None:
            raise ValueError("no-hit case must have no target")
        if "document_sha256" in case and not _sha(case["document_sha256"]):
            raise ValueError("document hash required")
    evaluator = manifest.get("evaluator")
    if evaluator is not None and (not isinstance(evaluator, Mapping) or not _sha(evaluator.get("sha256"))):
        raise ValueError("evaluator hash required")
    repositories = manifest.get("repositories")
    if repositories is not None:
        if not isinstance(repositories, Mapping) or not repositories:
            raise ValueError("source revisions required")
        for source in repositories.values():
            if not isinstance(source, Mapping) or not _commit(source.get("commit")) or not _sha(source.get("license_sha256")):
                raise ValueError("source revision/license binding required")
    return {"schema": int(manifest["schema"]), "manifest_sha256": _digest(manifest), "case_count": len(cases)}


def _metrics(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _has_metrics(value: object) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(value.get(key), (int, float)) for key in ("recall_at_1", "mrr")
    )


def collect(manifest: Mapping[str, object], raw: Mapping[str, object], *, raw_sha256: str) -> dict[str, object]:
    """Collect metadata only; missing, stale, or malformed evidence stays visible."""
    try:
        frozen = validate_manifest(manifest)
    except (AttributeError, TypeError, ValueError) as error:
        return {"schema": 3, "manifest_sha256": _digest(manifest), "raw_sha256": raw_sha256,
                "status": "FAIL", "hypothesis": "UNDECIDED", "active_channel": "bge_m3",
                "missing": ["sealed_manifest"], "error": str(error)}
    missing: list[str] = []
    if not isinstance(raw, Mapping):
        raw = {}
        missing.append("raw_schema")
    if hash_report(raw) != raw_sha256:
        missing.append("raw_hash")
    forbidden = {"query", "queries", "label", "labels", "prompt", "prompts", "transcript", "payload"}
    if any(key in forbidden for key in raw):
        missing.append("raw_payload_redaction")
    if raw.get("schema") not in (5, 6):
        missing.append("runner_schema")
    if raw.get("case_count") != 15:
        missing.append("sealed_case_count")
    if raw.get("test_runs") != 1:
        missing.append("test_once")
    if not isinstance(raw.get("dev_choice"), Mapping) or not raw["dev_choice"].get("selected"):
        missing.append("dev_only_selection")
    if (not isinstance(raw.get("test_case_ids", ()), (list, tuple))
            or not isinstance(raw.get("dev_case_ids", ()), (list, tuple))):
        missing.append("split_ids")
    elif set(raw["test_case_ids"]) & set(raw.get("dev_case_ids", ())):
        missing.append("dev_test_disjoint")
    repositories = {case["repository"] for case in manifest["cases"]}
    folds = raw.get("loro_folds", ())
    if not isinstance(folds, list) or len(folds) != 3 or {fold.get("held_out") for fold in folds if isinstance(fold, Mapping)} != repositories:
        missing.append("leave_one_repo_out")
    elif any(not isinstance(fold.get("arm_metrics"), Mapping)
             or set(fold["arm_metrics"]) != {"stripped", "comments_only", "combined"}
             or any(not isinstance(fold["arm_metrics"].get(arm), Mapping)
                    or any(not _has_metrics(fold["arm_metrics"][arm].get(channel))
                           for channel in ("bge_m3", "coderank_raw", "rank_only_rrf"))
                    for arm in ("stripped", "comments_only", "combined"))
             for fold in folds):
        missing.append("loro_ablation_metrics")
    if set(raw.get("ablations", ())) != {"stripped", "comments_only", "combined"}:
        missing.append("comment_annotation_ablations")
    arm_metrics = raw.get("arm_metrics")
    if (not isinstance(arm_metrics, Mapping) or set(arm_metrics) != {"stripped", "comments_only", "combined"}
            or any(not isinstance(arm_metrics.get(arm), Mapping)
                   or any(not _has_metrics(arm_metrics[arm].get(channel))
                          for channel in ("bge_m3", "coderank_raw", "rank_only_rrf"))
                   for arm in ("stripped", "comments_only", "combined"))):
        missing.append("ablation_metrics")
    fallback_states = {"model_missing", "model_stale", "index_missing", "index_stale"}
    fallbacks = raw.get("fallbacks", {})
    if not isinstance(fallbacks, Mapping) or set(fallbacks) != fallback_states or any(value != "bge_m3" for value in fallbacks.values()):
        missing.append("missing_stale_bge_fallbacks")
    if raw.get("prose_bge_identity") is not True:
        missing.append("prose_bge_identity")
    if raw.get("leak_free") is not True:
        missing.append("leak_free")
    operational = raw.get("operational")
    if not isinstance(operational, Mapping) or not all(isinstance(operational.get(key), (int, float)) and operational.get(key) >= 0 for key in ("elapsed_seconds", "max_rss_bytes", "max_p95_latency_ms")):
        missing.append("time_ram_latency")
    for channel in ("bge_m3", "coderank_raw", "rank_only_rrf"):
        if not isinstance(raw.get(channel), Mapping):
            missing.append(channel)
        elif not _has_metrics(raw[channel]):
            missing.append(f"{channel}_metrics")
    fallback_results = raw.get("fallback_results")
    if (not isinstance(fallback_results, Mapping)
            or set(fallback_results) != {"model_missing", "model_stale", "index_missing", "index_stale"}
            or any(not isinstance(fallback_results[state], Mapping)
                   or fallback_results[state].get("channel") != "bge_m3"
                   or fallback_results[state].get("matches_bge") is not True
                   or not _has_metrics(fallback_results[state].get("metrics"))
                   for state in ("model_missing", "model_stale", "index_missing", "index_stale"))):
        missing.append("fallback_results")
    unique_hits = raw.get("unique_coderank_hits", 0)
    if not isinstance(unique_hits, (int, float)) or unique_hits < 0:
        missing.append("unique_coderank_hits")
        unique_hits = 0
    report = {"missing": missing, "prose_bge_identity": raw.get("prose_bge_identity"),
              "leak_free": raw.get("leak_free"), "test_runs": raw.get("test_runs"),
              "unique_coderank_hits": unique_hits,
              "bge_m3": _metrics(raw.get("bge_m3")), "coderank_raw": _metrics(raw.get("coderank_raw")),
              "rank_only_rrf": _metrics(raw.get("rank_only_rrf"))}
    if not missing:
        bge, code, fusion = report["bge_m3"], report["coderank_raw"], report["rank_only_rrf"]
        h1 = (report["unique_coderank_hits"] >= 1
              and float(fusion.get("recall_at_1", 0)) > max(float(bge.get("recall_at_1", 0)), float(code.get("recall_at_1", 0)))
              and float(fusion.get("mrr", 0)) > max(float(bge.get("mrr", 0)), float(code.get("mrr", 0))))
        hypothesis = "H1" if h1 else "H0"
    else:
        hypothesis = "UNDECIDED"
    return {"schema": 3, "manifest_sha256": frozen["manifest_sha256"], "raw_sha256": raw_sha256,
            "status": "PASS" if not missing else "FAIL", "hypothesis": hypothesis,
            "active_channel": "rank_only_rrf" if hypothesis == "H1" else "bge_m3",
            "missing": sorted(set(missing))}


__all__ = ["collect", "hash_report", "validate_manifest"]
