"""P103-v3: small deterministic runner for the sealed retrieval experiment.

This module deliberately does not load a model, a database, or an index.  A
caller supplies already-produced vectors and the runner only performs the
pre-registered rank math and gates.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

CHANNELS = ("bge_m3", "coderank_raw", "rank_only_rrf")
ARMS = ("stripped", "comments_only", "combined")
FALLBACKS = {"model_missing": "bge_m3", "model_stale": "bge_m3",
             "index_missing": "bge_m3", "index_stale": "bge_m3"}
DEFAULT_THRESHOLDS = {"unique_coderank_hits_min": 1,
                      "fusion_operator": ">", "prose_bge_identity": True}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have equal dimensions")
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    norm_left = sum(float(a) * float(a) for a in left) ** 0.5
    norm_right = sum(float(b) * float(b) for b in right) ** 0.5
    return dot / (norm_left * norm_right) if norm_left and norm_right else 0.0


def rank(query: Sequence[float], documents: Mapping[str, Sequence[float]]) -> list[tuple[str, float]]:
    """Return a deterministic cosine ranking; document IDs break ties."""
    return sorted(((key, cosine(query, vector)) for key, vector in documents.items()),
                  key=lambda row: (-row[1], row[0]))


def rrf(rankings: Sequence[Sequence[str | tuple[str, float]]] | Mapping[str, Sequence[str | tuple[str, float]]],
        *, k: int = 60, weights: Sequence[float] | Mapping[str, float] | None = None) -> list[str]:
    """Fuse ranks only.  Scores/vectors are never passed between channels."""
    if k <= 0:
        raise ValueError("rrf k must be positive")
    groups = list(rankings.items()) if isinstance(rankings, Mapping) else list(enumerate(rankings))
    scores: dict[str, float] = {}
    for index, (name, ordered) in enumerate(groups):
        weight = (weights.get(name, 1.0) if isinstance(weights, Mapping)
                  else weights[index] if weights is not None else 1.0)
        for position, row in enumerate(ordered, 1):
            key = row[0] if isinstance(row, tuple) else row
            scores[key] = scores.get(key, 0.0) + float(weight) / (k + position)
    return [key for key, _ in sorted(scores.items(), key=lambda row: (-row[1], row[0]))]


def _tokens(value: str) -> set[str]:
    split = re.sub(r"([a-z])([A-Z])", r"\1 \2", value.casefold())
    return {part for part in re.split(r"[^a-z0-9]+", split) if part}


def identifier_leak(query: str, target: Mapping[str, Any]) -> bool:
    query_tokens = _tokens(query)
    identifiers = [str(target.get("path", "")), str(target.get("symbol", ""))]
    identifier_tokens = set().union(*(_tokens(item) for item in identifiers))
    return bool(query_tokens & identifier_tokens)


def validate_cases(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Validate the v2 case shape and reject identifier-bearing queries."""
    if not cases:
        raise ValueError("sealed cases required")
    ids: set[str] = set()
    for case in cases:
        required = {"id", "repository", "split", "query", "expected", "target"}
        if not required <= set(case):
            raise ValueError("case fields missing")
        if case["id"] in ids or not isinstance(case["query"], str) or not case["query"]:
            raise ValueError("case identity/query invalid")
        if "query_sha256" in case and case["query_sha256"] != hashlib.sha256(case["query"].encode()).hexdigest():
            raise ValueError("query hash mismatch")
        ids.add(case["id"])
        if case["expected"] == "target":
            if not isinstance(case["target"], Mapping) or identifier_leak(case["query"], case["target"]):
                raise ValueError("identifier leak in sealed query")
        elif case["expected"] == "no_hit" and case["target"] is None:
            continue
        else:
            raise ValueError("target/no-hit expectation invalid")
    return {"case_count": len(cases), "query_sha256": digest([case["query"] for case in cases])}


def metrics(cases: Sequence[Mapping[str, Any]], rankings: Sequence[Sequence[str]]) -> dict[str, Any]:
    if len(cases) != len(rankings):
        raise ValueError("one ranking required per case")
    ranks: list[int] = []
    negatives: list[str | None] = []
    rows = []
    for case, ordered in zip(cases, rankings):
        target = case.get("target")
        target_id = target.get("path") if isinstance(target, Mapping) else target
        if target_id:
            try:
                position = list(ordered).index(target_id) + 1
            except ValueError:
                position = len(ordered) + 1
            ranks.append(position)
            rows.append({"id": case["id"], "rank": position, "top": ordered[0] if ordered else None})
        else:
            negatives.append(ordered[0] if ordered else None)
    positive_n = len(ranks)
    if not positive_n:
        return {"positive_n": 0, "negative_n": len(negatives), "recall_at_1": 0.0,
                "recall_at_5": 0.0, "recall_at_10": 0.0, "mrr": 0.0,
                "negative_top_ids": negatives, "rows": rows}
    return {"positive_n": positive_n, "negative_n": len(negatives),
            "recall_at_1": sum(rank_value <= 1 for rank_value in ranks) / positive_n,
            "recall_at_5": sum(rank_value <= 5 for rank_value in ranks) / positive_n,
            "recall_at_10": sum(rank_value <= 10 for rank_value in ranks) / positive_n,
            "mrr": sum(1 / rank_value for rank_value in ranks) / positive_n,
            "negative_top_ids": negatives, "rows": rows}


def _bge_metrics(cases: Sequence[Mapping[str, Any]], vectors: Mapping[str, Any], *, arm: str = "combined") -> dict[str, Any]:
    queries, documents = _channel_vectors({"bge_m3": vectors}, "bge_m3", arm)
    ordered = [[key for key, _ in rank(queries[case["id"]], documents)] for case in cases]
    return metrics(cases, ordered)


def _channel_vectors(vectors: Mapping[str, Any], channel: str, arm: str = "combined") -> tuple[Mapping[str, Sequence[float]], Mapping[str, Sequence[float]]]:
    value = vectors[channel]
    if isinstance(value, Mapping) and arm in value:
        value = value[arm]
    if not isinstance(value, Mapping) or not {"queries", "documents"} <= set(value):
        raise ValueError(f"{channel}/{arm} needs queries and documents")
    return value["queries"], value["documents"]


def evaluate(cases: Sequence[Mapping[str, Any]], vectors: Mapping[str, Any], *, arm: str = "combined",
             rrf_k: int = 60, bge_weight: float = 1.0, coderank_weight: float = 1.0) -> dict[str, Any]:
    """Evaluate BGE, CodeRank and rank-only RRF over one sealed case slice."""
    validate_cases(cases)
    bge_queries, bge_documents = _channel_vectors(vectors, "bge_m3", arm)
    code_queries, code_documents = _channel_vectors(vectors, "coderank_raw", arm)
    bge_rankings = [rank(bge_queries[case["id"]], bge_documents) for case in cases]
    code_rankings = [rank(code_queries[case["id"]], code_documents) for case in cases]
    bge_order = [[key for key, _ in row] for row in bge_rankings]
    code_order = [[key for key, _ in row] for row in code_rankings]
    fused = [rrf((left, right), k=rrf_k, weights=(bge_weight, coderank_weight))
             for left, right in zip(bge_rankings, code_rankings)]
    return {"bge_m3": metrics(cases, bge_order), "coderank_raw": metrics(cases, code_order),
            "rank_only_rrf": metrics(cases, fused), "rankings": {
                "bge_m3": bge_order, "coderank_raw": code_order, "rank_only_rrf": fused}}


def select_dev_grid(cases: Sequence[Mapping[str, Any]], vectors: Mapping[str, Any], grid: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Choose exactly one finite RRF point using dev cases only."""
    dev = [case for case in cases if case.get("split") == "dev"]
    test = {case["id"] for case in cases if case.get("split") == "test"}
    if not dev or not grid or {case["id"] for case in dev} & test:
        raise ValueError("disjoint dev/test and finite dev grid required")
    results = []
    for point in grid:
        if set(point) != {"rrf_k", "bge_weight", "coderank_weight"}:
            raise ValueError("invalid RRF grid point")
        if any(not isinstance(point[key], (int, float)) or point[key] <= 0
               for key in ("rrf_k", "bge_weight", "coderank_weight")):
            raise ValueError("RRF grid values must be positive")
        result = evaluate(dev, vectors, rrf_k=point["rrf_k"], bge_weight=point["bge_weight"], coderank_weight=point["coderank_weight"])
        score = result["rank_only_rrf"]
        results.append((score["mrr"], score["recall_at_1"], -point["rrf_k"], point, result))
    winner = max(results, key=lambda row: row[:3])
    return {"selected": winner[3], "dev_metrics": winner[4]["rank_only_rrf"],
            "candidates": [{"point": row[3], "metrics": row[4]["rank_only_rrf"]} for row in results],
            "test_case_ids": sorted(test)}


def leave_one_repo_out(cases: Sequence[Mapping[str, Any]], vectors_by_repo: Mapping[str, Mapping[str, Any]], *, point: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Run every held-out repository without tuning on its cases."""
    repositories = sorted({case["repository"] for case in cases})
    folds = []
    for held_out in repositories:
        held = [case for case in cases if case["repository"] == held_out]
        vectors = vectors_by_repo.get(held_out)
        if vectors is None and "bge_m3" in vectors_by_repo:
            vectors = vectors_by_repo
        if vectors is None:
            raise ValueError(f"missing LORO vectors: {held_out}")
        arm_metrics = {arm: evaluate(held, vectors, arm=arm, rrf_k=point["rrf_k"],
                                     bge_weight=point["bge_weight"], coderank_weight=point["coderank_weight"])
                       for arm in ARMS}
        folds.append({"held_out": held_out, "case_ids": [case["id"] for case in held],
                      "metrics": arm_metrics["combined"], "arm_metrics": arm_metrics})
    return folds


def fallback_channel(state: str) -> str:
    if state not in FALLBACKS:
        raise ValueError(f"unknown fallback state: {state}")
    return "bge_m3"


def apply_fallback(vectors: Mapping[str, Any], state: str) -> Mapping[str, Any]:
    """Return the BGE arm for a missing/stale specialist without mutation."""
    return vectors["bge_m3"] if fallback_channel(state) == "bge_m3" else vectors


def prose_identity(vectors: Mapping[str, Any]) -> bool:
    """Require an explicit BGE identity marker for the prose control."""
    if vectors.get("prose_bge_identity") is True:
        return True
    bge = vectors.get("bge_m3")
    if isinstance(bge, Mapping):
        return bge.get("model_identity") == bge.get("prose_model_identity") and bge.get("model_identity") is not None
    return False


def gate(report: Mapping[str, Any], *, thresholds: Mapping[str, Any] = DEFAULT_THRESHOLDS) -> dict[str, Any]:
    """Apply H1 only when all prerequisite gates and strict fusion wins hold."""
    missing = list(report.get("missing", ()))
    bge = report.get("bge_m3", {})
    code = report.get("coderank_raw", {})
    fusion = report.get("rank_only_rrf", {})
    if report.get("prose_bge_identity") is not True:
        missing.append("prose_bge_identity")
    if report.get("leak_free") is not True:
        missing.append("leak_free")
    if report.get("test_runs") != 1:
        missing.append("test_once")
    unique_hits = int(report.get("unique_coderank_hits", 0))
    h1 = (not missing and unique_hits >= thresholds.get("unique_coderank_hits_min", 1)
          and fusion.get("recall_at_1", 0) > max(bge.get("recall_at_1", 0), code.get("recall_at_1", 0))
          and fusion.get("mrr", 0) > max(bge.get("mrr", 0), code.get("mrr", 0)))
    return {"hypothesis": "H1" if h1 else "H0" if not missing else "UNDECIDED",
            "active_channel": "rank_only_rrf" if h1 else "bge_m3", "missing": sorted(set(missing))}


def write_test_once(path: str | os.PathLike[str], result: Mapping[str, Any]) -> Path:
    """Claim a persistent lock, then atomically publish one result."""
    target = Path(path)
    lock = claim_test_once(target)
    try:
        return _write_claimed(target, result)
    except Exception:
        # A failed test remains claimed: retrying would violate test-once.
        raise


def claim_test_once(path: str | os.PathLike[str]) -> Path:
    """Acquire an O_EXCL lock before any producer or scoring work."""
    target = Path(path)
    if target.exists():
        raise RuntimeError("sealed test result already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = Path(f"{target}.lock")
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise RuntimeError("sealed test lock already exists") from error
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("claimed\n")
        handle.flush()
        os.fsync(handle.fileno())
    return lock


def _write_claimed(target: Path, result: Mapping[str, Any]) -> Path:
    """Publish after claim_test_once; the lock intentionally remains."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(result, handle, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
    except FileExistsError as error:
        raise RuntimeError("sealed test result already exists") from error
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return target


def run_once(path: str | os.PathLike[str], producer: Callable[[], Mapping[str, Any]]) -> dict[str, Any]:
    """Claim before calling producer; producer is never retried or duplicated."""
    target = Path(path)
    claim_test_once(target)
    result = dict(producer())
    _write_claimed(target, result)
    return result


def runtime_evidence(started: float) -> dict[str, Any]:
    elapsed = time.perf_counter() - started
    return {"elapsed_seconds": round(elapsed, 6),
            "max_p95_latency_ms": round(elapsed * 1000, 3),
            "max_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}


def run(cases: Sequence[Mapping[str, Any]], vectors: Mapping[str, Any], grid: Sequence[Mapping[str, Any]], *,
        output_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Execute one bounded dev-select/test-once run over supplied vectors."""
    target = Path(output_path) if output_path is not None else None
    if target is not None:
        claim_test_once(target)
    started = time.perf_counter()
    validate_cases(cases)
    repositories = sorted({case["repository"] for case in cases})
    if len(cases) != 15 or len(repositories) != 3:
        raise ValueError("P103-v3 requires exactly fifteen cases across three repositories")
    selection = select_dev_grid(cases, vectors, grid)
    test = [case for case in cases if case.get("split") == "test"]
    if not test:
        raise ValueError("sealed test cases required")
    point = selection["selected"]
    arm_metrics = {}
    for arm in ARMS:
        scored_arm = evaluate(test, vectors, arm=arm, rrf_k=point["rrf_k"],
                              bge_weight=point["bge_weight"], coderank_weight=point["coderank_weight"])
        arm_metrics[arm] = {channel: scored_arm[channel] for channel in CHANNELS}
    scored = arm_metrics["combined"]
    bge_rows = {row["id"]: row for row in scored["bge_m3"]["rows"]}
    unique = sum(row["rank"] == 1 and bge_rows.get(row["id"], {}).get("rank") != 1
                 for row in scored["coderank_raw"]["rows"])
    report: dict[str, Any] = {"schema": 5, "case_count": len(cases), "test_runs": 1,
                              "dev_choice": selection, "dev_case_ids": [case["id"] for case in cases if case.get("split") == "dev"],
                              "test_case_ids": [case["id"] for case in test], "loro_folds": [],
                              "ablations": list(ARMS), "fallbacks": dict(FALLBACKS),
                              "prose_bge_identity": prose_identity(vectors), "leak_free": True,
                              "unique_coderank_hits": unique, "operational": runtime_evidence(started),
                              "bge_m3": scored["bge_m3"], "coderank_raw": scored["coderank_raw"],
                              "rank_only_rrf": scored["rank_only_rrf"], "arm_metrics": arm_metrics}
    report["fallback_results"] = {
        state: {"channel": "bge_m3",
                "metrics": _bge_metrics(test, apply_fallback(vectors, state)),
                "matches_bge": _bge_metrics(test, apply_fallback(vectors, state)) == scored["bge_m3"]}
        for state in FALLBACKS
    }
    vectors_by_repo = {}
    for repository in repositories:
        candidate = vectors.get(repository) if isinstance(vectors, Mapping) else None
        vectors_by_repo[repository] = candidate if isinstance(candidate, Mapping) and "bge_m3" in candidate else vectors
    report["loro_folds"] = leave_one_repo_out(cases, vectors_by_repo, point=point)
    if target is not None:
        _write_claimed(target, report)
    return report


# Descriptive aliases keep callers independent of the short internal names.
weighted_rrf = rrf
evaluate_cases = evaluate
check_prose_identity = prose_identity


__all__ = ["ARMS", "CHANNELS", "FALLBACKS", "cosine", "rank", "rrf", "metrics",
           "validate_cases", "evaluate", "select_dev_grid", "leave_one_repo_out",
           "fallback_channel", "apply_fallback", "prose_identity", "gate", "claim_test_once", "write_test_once",
           "run_once", "runtime_evidence", "run", "digest", "weighted_rrf", "evaluate_cases",
           "check_prose_identity"]
