"""V8 rank runner: reject identifiers, not ordinary single-word concepts."""
from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import messungen.sealed_retrieval_v3 as base
from messungen.sealed_retrieval_v3 import (ARMS, CHANNELS, FALLBACKS, _bge_metrics,
    _write_claimed, apply_fallback, evaluate, leave_one_repo_out, prose_identity,
    runtime_evidence, select_dev_grid)


def _identifier_parts(value: str, *, path: bool) -> list[str]:
    raw = Path(value).stem if path else value
    return [part for part in re.split(r"[^a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", raw.casefold())) if len(part) >= 3]


def identifier_leak(query: str, target: Mapping[str, Any]) -> bool:
    query_tokens = [part for part in re.split(r"[^a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", query.casefold())) if len(part) >= 3]
    for value, is_path in ((str(target.get("path", "")), True), (str(target.get("symbol", "")), False)):
        parts = _identifier_parts(value, path=is_path)
        if len(parts) == 1 and parts[0] in query_tokens:
            return True
        if len(parts) >= 2 and any(query_tokens[index:index + len(parts)] == parts for index in range(len(query_tokens))):
            return True
    return False


def validate_cases(cases: Sequence[Mapping[str, Any]]) -> None:
    ids: set[str] = set()
    if not cases:
        raise ValueError("sealed cases required")
    for case in cases:
        if not {"id", "repository", "split", "query", "expected", "target"} <= set(case):
            raise ValueError("case fields missing")
        if case["id"] in ids or not isinstance(case["query"], str) or not case["query"]:
            raise ValueError("case identity/query invalid")
        if "query_sha256" in case and case["query_sha256"] != hashlib.sha256(case["query"].encode()).hexdigest():
            raise ValueError("query hash mismatch")
        ids.add(case["id"])
        if case["expected"] == "target":
            if not isinstance(case["target"], Mapping) or identifier_leak(case["query"], case["target"]):
                raise ValueError("identifier leak in sealed query")
        elif case["expected"] != "no_hit" or case["target"] is not None:
            raise ValueError("target/no-hit expectation invalid")


def _base_call(function, *args, **kwargs):
    original = base.validate_cases
    base.validate_cases = validate_cases
    try:
        return function(*args, **kwargs)
    finally:
        base.validate_cases = original


def run(cases: Sequence[Mapping[str, Any]], vectors: Mapping[str, Any], grid: Sequence[Mapping[str, Any]], *, output_path: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    validate_cases(cases)
    repositories = sorted({case["repository"] for case in cases})
    if len(cases) != 15 or len(repositories) != 3:
        raise ValueError("P103-v8 requires exactly fifteen cases across three repositories")
    selection, test = _base_call(select_dev_grid, cases, vectors, grid), [case for case in cases if case.get("split") == "test"]
    if not test:
        raise ValueError("sealed test cases required")
    point = selection["selected"]
    arm_metrics = {arm: {channel: result[channel] for channel in CHANNELS}
                   for arm in ARMS for result in [_base_call(evaluate, test, vectors, arm=arm, rrf_k=point["rrf_k"], bge_weight=point["bge_weight"], coderank_weight=point["coderank_weight"])]}
    scored, bge_rows = arm_metrics["combined"], {row["id"]: row for row in arm_metrics["combined"]["bge_m3"]["rows"]}
    report: dict[str, Any] = {"schema": 8, "case_count": len(cases), "test_runs": 1, "dev_choice": selection,
        "dev_case_ids": [case["id"] for case in cases if case.get("split") == "dev"], "test_case_ids": [case["id"] for case in test],
        "ablations": list(ARMS), "fallbacks": dict(FALLBACKS), "prose_bge_identity": prose_identity(vectors), "leak_free": True,
        "unique_coderank_hits": sum(row["rank"] == 1 and bge_rows.get(row["id"], {}).get("rank") != 1 for row in scored["coderank_raw"]["rows"]),
        "operational": runtime_evidence(started), "bge_m3": scored["bge_m3"], "coderank_raw": scored["coderank_raw"], "rank_only_rrf": scored["rank_only_rrf"], "arm_metrics": arm_metrics}
    report["fallback_results"] = {state: {"channel": "bge_m3", "metrics": _bge_metrics(test, apply_fallback(vectors, state)), "matches_bge": _bge_metrics(test, apply_fallback(vectors, state)) == scored["bge_m3"]} for state in FALLBACKS}
    report["loro_folds"] = _base_call(leave_one_repo_out, cases, {repository: vectors for repository in repositories}, point=point)
    if output_path is not None:
        _write_claimed(Path(output_path), report)
    return report
