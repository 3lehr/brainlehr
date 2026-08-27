import hashlib
import json
from collections.abc import Mapping


REPOSITORIES = frozenset(("brainlehr", "hermes-brainlehr", "sigmaforge"))
SPLITS = {"brainlehr": "train", "hermes-brainlehr": "dev", "sigmaforge": "test"}
MODALITIES = frozenset(("code", "signature", "consumer", "error", "impact", "prose_control", "no_hit"))
ANNOTATION_SOURCES = frozenset(("source_comments_docstrings", "NONE"))


def _sha(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _commit(value: object) -> bool:
    return isinstance(value, str) and len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _text_sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _leaks_identifier(query: str, target: Mapping[str, object]) -> bool:
    candidate = query.casefold()
    identifiers = (str(target["symbol"]), str(target["path"]), str(target["path"]).rsplit("/", 1)[-1])
    return any(identifier.casefold() in candidate for identifier in identifiers)


def validate_manifest(manifest: Mapping[str, object]) -> dict[str, object]:
    required = {
        "schema", "evaluator", "decision", "scope", "repositories", "cases", "splits", "loro_folds",
        "annotation_arms", "channels", "prose_control", "dev_rrf_grid", "selection_rule", "test_once",
        "thresholds", "fallbacks", "operational_thresholds", "coverage_gaps",
    }
    if manifest.get("schema") != 2 or set(manifest) != required:
        raise ValueError("strict P103-v2 manifest required")
    evaluator = manifest["evaluator"]
    if not isinstance(evaluator, Mapping) or set(evaluator) != {"id", "version", "sha256"} or not _sha(evaluator["sha256"]):
        raise ValueError("evaluator version/hash required")
    if manifest["decision"] != "NOT RUN; BGE-only remains active" or not isinstance(manifest["scope"], str):
        raise ValueError("unscored BGE-only decision required")
    repositories = manifest["repositories"]
    if not isinstance(repositories, Mapping) or set(repositories) != REPOSITORIES:
        raise ValueError("exact source repositories required")
    for source in repositories.values():
        if not isinstance(source, Mapping) or set(source) != {"commit", "license", "license_sha256"} or not _commit(source["commit"]) or not _sha(source["license_sha256"]):
            raise ValueError("source revision/license binding required")
    if manifest["splits"] != SPLITS:
        raise ValueError("full-repository train/dev/test split required")
    cases = manifest["cases"]
    fields = {"id", "repository", "split", "modality", "query_language", "query", "query_sha256", "document_path", "document_sha256", "expected", "target", "proof"}
    if not isinstance(cases, list) or len(cases) < 15 or any(not isinstance(case, Mapping) or set(case) != fields for case in cases):
        raise ValueError("at least fifteen complete cases required")
    if len({case["id"] for case in cases}) != len(cases) or len({case["query_sha256"] for case in cases}) != len(cases):
        raise ValueError("case and query identities must be unique")
    for case in cases:
        if case["repository"] not in REPOSITORIES or case["split"] != SPLITS[case["repository"]] or case["modality"] not in MODALITIES:
            raise ValueError("case repository, split, or modality invalid")
        if case["query_language"] not in {"de", "en"} or not isinstance(case["query"], str) or not case["query"] or _text_sha(case["query"]) != case["query_sha256"]:
            raise ValueError("identifier-free hashed query required")
        if not isinstance(case["document_path"], str) or not _sha(case["document_sha256"]):
            raise ValueError("document hash required")
        if case["expected"] == "target":
            target, proof = case["target"], case["proof"]
            if not isinstance(target, Mapping) or set(target) != {"path", "symbol"} or not isinstance(proof, Mapping) or set(proof) != {"path", "test", "sha256"} or not _sha(proof["sha256"]):
                raise ValueError("positive target proof hash required")
            if _leaks_identifier(case["query"], target):
                raise ValueError("target identifier/path leaks into query")
        elif case["expected"] == "no_hit" and case["target"] is None and case["proof"] is None:
            continue
        else:
            raise ValueError("no-hit must have no target or proof")
    for repository in REPOSITORIES:
        rows = [case for case in cases if case["repository"] == repository]
        if sum(case["expected"] == "target" for case in rows) < 4 or not any(case["expected"] == "no_hit" for case in rows):
            raise ValueError("four positives and one no-hit per repository required")
    languages = [case["query_language"] for case in cases]
    if abs(languages.count("de") - languages.count("en")) > 1 or not {"code", "signature", "consumer", "error", "impact", "prose_control"} <= {case["modality"] for case in cases}:
        raise ValueError("balanced complete modality matrix required")
    folds = manifest["loro_folds"]
    if not isinstance(folds, list) or {fold.get("held_out") for fold in folds if isinstance(fold, Mapping)} != REPOSITORIES:
        raise ValueError("one LORO fold per repository required")
    for fold in folds:
        if not isinstance(fold, Mapping) or set(fold) != {"held_out", "train", "dev"} or set(fold["train"]) | set(fold["dev"]) != REPOSITORIES - {fold["held_out"]} or set(fold["train"]) & set(fold["dev"]):
            raise ValueError("LORO folds must be disjoint and complete")
    arms = manifest["annotation_arms"]
    if not isinstance(arms, list) or {arm.get("id") for arm in arms if isinstance(arm, Mapping)} != {"stripped", "comments_only", "combined"}:
        raise ValueError("all source-only annotation arms required")
    if any(set(arm) != {"id", "document_view", "annotation_source", "query_independent"} or arm["annotation_source"] not in ANNOTATION_SOURCES or arm["query_independent"] is not True for arm in arms):
        raise ValueError("annotation must be source-only and query-independent")
    if set(manifest["channels"]) != {"bge_m3", "coderank_raw_rank", "rank_only_rrf"}:
        raise ValueError("separate channels and rank-only fusion required")
    if manifest["prose_control"] != {"channel": "bge_m3", "identity": "same_bge_m3_query_document_prefix_hash", "required": True}:
        raise ValueError("BGE-identical prose control required")
    grid = manifest["dev_rrf_grid"]
    if not isinstance(grid, list) or len(grid) < 2 or len({_digest(row) for row in grid}) != len(grid) or any(not isinstance(row, Mapping) or set(row) != {"rrf_k", "bge_weight", "coderank_weight"} or not all(isinstance(value, int) and value > 0 for value in row.values()) for row in grid):
        raise ValueError("finite positive dev-only RRF grid required")
    if manifest["selection_rule"] != "select_one_grid_point_on_dev_only; test_once_after_selection":
        raise ValueError("dev-only selection rule required")
    test_once = manifest["test_once"]
    if not isinstance(test_once, Mapping) or test_once.get("state") != "sealed_not_evaluated" or not _sha(test_once.get("token")):
        raise ValueError("sealed unevaluated test-once lock required")
    thresholds = manifest["thresholds"]
    if not isinstance(thresholds, Mapping) or thresholds != {"unique_coderank_hits_min": 1, "fusion_metrics": ["recall_at_1", "mrr"], "fusion_operator": ">", "prose_bge_identity": True}:
        raise ValueError("unique hit, strict fusion, and prose thresholds required")
    if manifest["fallbacks"] != {"model_missing": "bge_m3", "model_stale": "bge_m3", "index_missing": "bge_m3", "index_stale": "bge_m3"}:
        raise ValueError("missing/stale BGE fallback required")
    operational = manifest["operational_thresholds"]
    if not isinstance(operational, Mapping) or set(operational) != {"max_elapsed_seconds", "max_rss_bytes", "max_p95_latency_ms"} or not all(isinstance(value, int) and value > 0 for value in operational.values()):
        raise ValueError("time/RAM/latency thresholds required")
    if not isinstance(manifest["coverage_gaps"], list) or not manifest["coverage_gaps"]:
        raise ValueError("scope gaps must remain visible")
    return {"schema": 2, "manifest_sha256": _digest(manifest), "decision": manifest["decision"], "test_once_token": test_once["token"]}
