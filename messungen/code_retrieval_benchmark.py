#!/usr/bin/env python3
"""Measure local code retrieval against BGE-M3 on frozen modality matrices.

Source chunks come from one Git revision, stay below the model ceiling, and no
vector or model artifact is written to the repository or brainlehr.db.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import resource
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]
import embeddings  # noqa: E402

GOLDSET = ROOT / "tests" / "fixtures" / "code_retrieval_goldset.json"
MULTILINGUAL_FIXTURES = ROOT / "tests" / "fixtures" / "multilingual_code"
QUERY_PREFIX = "Represent this query for searching relevant code: "
MAX_CHUNK_CHARS = 12000
BATCH_SIZE = 4
CODE_MATRIX_IDS = frozenset({"en_prose_to_python", "de_prose_to_python", "code_signature_to_python"})
# Frozen scope: language claims require their own goldset; Python results never
# stand in for another language.
LANGUAGE_MATRIX_MANIFEST = {
    "python": {"goldset": str(GOLDSET), "status": "available"},
    "typescript": {"goldset": str(MULTILINGUAL_FIXTURES), "status": "available"},
    "rust": {"goldset": str(MULTILINGUAL_FIXTURES), "status": "available"},
    "swift": {"goldset": str(MULTILINGUAL_FIXTURES), "status": "available"},
    "dart_flutter": {"goldset": str(MULTILINGUAL_FIXTURES), "status": "available"},
    "java": {"goldset": str(MULTILINGUAL_FIXTURES), "status": "available"},
    "go": {"goldset": str(MULTILINGUAL_FIXTURES), "status": "available"},
}

DECLARATIVE_FIXTURE_LANGUAGES = ("sql", "shell", "yaml", "hcl")
EXTENSIBLE_LANGUAGE_GAPS = ("c_cpp", "csharp", "php", "kotlin", "ruby")
MANDATORY_LANGUAGES = ("python", "typescript", "rust", "java", "go", "swift", "dart_flutter")
MULTILINGUAL_MODALITIES = ("signature_to_implementation", "code_to_consumer",
                           "de_prose_to_code", "en_prose_to_code")
# Pre-registered before any multilingual model result is read.  A second
# channel needs macro improvement and may not lose more than this tolerance in
# a mandatory matrix or the prose control.
ACTIVATION_THRESHOLDS = {"macro_recall_at_1_gain": 0.01, "mrr_gain": 0.01,
                         "per_matrix_recall_at_1_drop": 0.0,
                         "prose_recall_at_1_drop": 0.0}


def language_coverage() -> dict:
    """Report frozen language scope without invoking a model or CodeRank."""
    gaps = [f"{language} goldset is absent" for language, spec in LANGUAGE_MATRIX_MANIFEST.items()
            if spec["status"] != "available"]
    return {"status": "coverage_gap" if gaps else "bounded",
            "languages": LANGUAGE_MATRIX_MANIFEST,
            "declarative_fixture_languages": DECLARATIVE_FIXTURE_LANGUAGES,
            "extensible_language_gaps": EXTENSIBLE_LANGUAGE_GAPS,
            "coverage_gaps": gaps,
            "code_rank_activated": False}


def _fixture_manifest() -> list[dict]:
    data = json.loads((MULTILINGUAL_FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    fixtures = data.get("fixtures", [])
    languages = {"dart_flutter" if row.get("language") == "dart" else row.get("language") for row in fixtures}
    if data.get("schema") != 1 or languages != set(MANDATORY_LANGUAGES):
        raise ValueError("multilingual fixture manifest must name each mandatory language exactly once")
    if any(len(row.get("symbols", [])) != 3 for row in fixtures):
        raise ValueError("each multilingual fixture needs exactly three target symbols")
    if any(len(row.get("behaviors", [])) != 3 for row in fixtures):
        raise ValueError("each multilingual fixture needs three identifier-free behaviors")
    if any(not row.get("hard_negative_symbol") for row in fixtures):
        raise ValueError("each multilingual fixture needs one dedicated code hard negative")
    return fixtures


def _fixture_documents() -> tuple[dict[str, dict[str, str]], list[dict]]:
    """Three source-derived candidate chunks per mandatory language.

    Chunks contain source text only; their file names and target IDs never enter
    a model payload. Symbol extraction deliberately uses a bounded textual
    window because syntax correctness is separately proven by the fixture test.
    """
    by_language: dict[str, dict[str, str]] = {}
    records = _fixture_manifest()
    for record in records:
        language = "dart_flutter" if record["language"] == "dart" else record["language"]
        text = (MULTILINGUAL_FIXTURES / record["file"]).read_text(encoding="utf-8")
        docs: dict[str, str] = {}
        starts = []
        for symbol in [*record["symbols"], record["hard_negative_symbol"]]:
            match = re.search(rf"(?m)^.*\b{re.escape(symbol)}\s*\(", text)
            if not match:
                raise ValueError(f"fixture symbol missing: {language}/{symbol}")
            starts.append((match.start(), symbol))
        for index, (start, symbol) in enumerate(sorted(starts)):
            end = sorted(starts)[index + 1][0] if index + 1 < len(starts) else len(text)
            docs[symbol] = text[start:min(end, start + MAX_CHUNK_CHARS)]
        by_language[language] = docs
    return by_language, records


def _identifier_tokens(value: str) -> set[str]:
    """Catch exact, split snake/camel, and case-normalized identifier leaks."""
    split = re.sub(r"([a-z])([A-Z])", r"\1 \2", value).casefold()
    bits = {bit for bit in re.split(r"[^a-z0-9]+", split) if bit}
    compact = "".join(bits)
    return bits | ({compact} if compact else set())


def _query_tokens(value: str) -> set[str]:
    return {bit for bit in re.split(r"[^a-z0-9]+", value.casefold()) if bit}


def _assert_identifier_free(query: str, identifiers: list[str]) -> None:
    leaked = _query_tokens(query) & set().union(*(_identifier_tokens(item) for item in identifiers))
    if leaked:
        raise ValueError(f"query leaks fixture identifier tokens: {sorted(leaked)}")


def _multilingual_cases(language: str, symbols: list[str], behaviors: list[str], modality: str,
                        fixture_file: str, hard_negative_symbol: str) -> list[dict]:
    queries = {
        "signature_to_implementation": lambda behavior: f"function(input) -> {behavior}",
        "code_to_consumer": lambda behavior: f"result = transform(input); use the routine that {behavior}",
        "de_prose_to_code": lambda behavior: f"Implementiere eine Routine, die {behavior}.",
        "en_prose_to_code": lambda behavior: f"Implement a routine that {behavior}.",
    }
    if modality not in queries:
        raise ValueError("unsupported multilingual modality")
    identifiers = [*symbols, hard_negative_symbol, fixture_file, Path(fixture_file).stem]
    cases = [{"id": f"{language}-{modality}-{symbol}", "query": queries[modality](behavior), "target": symbol}
             for symbol, behavior in zip(symbols, behaviors)]
    cases.extend([
        {"id": f"{language}-{modality}-negative-1", "query": "calculate a mortgage payment", "target": None},
        {"id": f"{language}-{modality}-negative-2", "query": "plan a dental appointment", "target": None},
    ])
    for case in cases:
        _assert_identifier_free(case["query"], identifiers)
    return cases


def _ranked_metrics(cases: list[dict], rankings: list[list[str]]) -> dict:
    positive, negative, rows = [], [], []
    for case, ordered in zip(cases, rankings):
        if case.get("target"):
            rank = ordered.index(case["target"]) + 1
            positive.append(rank)
            rows.append({"id": case["id"], "target": case["target"], "rank": rank, "top": ordered[0]})
        else:
            negative.append(ordered[0] if ordered else None)
    return {"positive_n": len(positive), "negative_n": len(negative),
            "recall_at_1": sum(rank <= 1 for rank in positive) / len(positive),
            "recall_at_5": sum(rank <= 5 for rank in positive) / len(positive),
            "recall_at_10": sum(rank <= 10 for rank in positive) / len(positive),
            "mrr": sum(1 / rank for rank in positive) / len(positive),
            "negative_top_ids": negative, "rows": rows}


def _rrf_order(first: list[tuple[str, float]], second: list[tuple[str, float]], *, k: int = 60) -> list[str]:
    score: dict[str, float] = {}
    for ranking in (first, second):
        for position, (key, _) in enumerate(ranking, 1):
            score[key] = score.get(key, 0.0) + 1 / (k + position)
    return [key for key, _ in sorted(score.items(), key=lambda item: (-item[1], item[0]))]


def _matrix(metrics: dict[str, dict], *, language: str, modality: str,
            elapsed: float, rss: int) -> dict:
    """Keep channels separate; RRF combines only ordered ranks, never vectors."""
    return {"id": f"{language}:{modality}", "language": language,
            "query_modality": modality, "document_modality": "source",
            "positive_n": 3, "negative_n": 1,
            "latency_seconds": round(elapsed, 4), "max_rss": rss,
            "model_prefix_contract": {"bge_m3": None, "coderankembed": QUERY_PREFIX,
                                      "rrf": "fixed-k=60", "router": "code->CodeRank; prose->BGE"},
            **{channel: {"metrics": value} for channel, value in metrics.items()}}


def run_multilingual(model_path: str, *, languages: set[str] | None = None) -> dict:
    """Measure all required language/modality pairs without persisting vectors."""
    documents, records = _fixture_documents()
    coderank = _load_coderank(model_path)
    started = time.perf_counter()
    matrices = []
    for record in records:
        language = "dart_flutter" if record["language"] == "dart" else record["language"]
        if languages is not None and language not in languages:
            continue
        docs = documents[language]
        keys = sorted(docs)
        bge_docs = _bge([docs[key] for key in keys])
        code_docs = _coderank(coderank, [docs[key] for key in keys], query=False)
        for modality in MULTILINGUAL_MODALITIES:
            matrix_started = time.perf_counter()
            cases = _multilingual_cases(language, record["symbols"], record["behaviors"], modality,
                                        record["file"], record["hard_negative_symbol"])
            bge_queries = _bge([case["query"] for case in cases])
            code_queries = _coderank(coderank, [case["query"] for case in cases], query=True)
            bge_rankings = [ranks(query, dict(zip(keys, bge_docs))) for query in bge_queries]
            code_rankings = [ranks(query, dict(zip(keys, code_docs))) for query in code_queries]
            bge_order = [[key for key, _ in rank] for rank in bge_rankings]
            code_order = [[key for key, _ in rank] for rank in code_rankings]
            rrf_order = [_rrf_order(left, right) for left, right in zip(bge_rankings, code_rankings)]
            router_order = code_order if modality in {"signature_to_implementation", "code_to_consumer"} else bge_order
            matrix = _matrix({"bge_m3": _ranked_metrics(cases, bge_order),
                                     "coderankembed": _ranked_metrics(cases, code_order),
                                     "rrf": _ranked_metrics(cases, rrf_order),
                                     "router": _ranked_metrics(cases, router_order)},
                                    language=language, modality=modality,
                                    elapsed=time.perf_counter() - matrix_started,
                                    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            matrix["positive_n"] = 3
            matrix["negative_n"] = 2
            matrix["validation"] = {"leak_free": True, "same_language_hard_negative_n": len(keys) - 1,
                                    "same_language_code_hard_negative_n": 1,
                                    "fixture_file_sha256": hashlib.sha256((MULTILINGUAL_FIXTURES / record["file"]).read_bytes()).hexdigest()}
            matrices.append(matrix)
    elapsed = round(time.perf_counter() - started, 3)
    ram = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"schema": 4, "mandatory_languages": list(MANDATORY_LANGUAGES),
            "measured_languages": sorted({matrix["language"] for matrix in matrices}),
            "thresholds": ACTIVATION_THRESHOLDS, "matrix_count": len(matrices), "matrices": matrices,
            "latency_seconds": elapsed, "max_rss": ram,
            "fixture_manifest_sha256": hashlib.sha256((MULTILINGUAL_FIXTURES / "manifest.json").read_bytes()).hexdigest(),
            "model": {"bge_m3": embeddings.model_identity("bge-m3"), "coderankembed": Path(model_path).name},
            "activation": {"active_channel": "bge_m3", "reason": "measurement only; no alternate channel is activated by this runner"}}


def run_prose_control(model_path: str) -> dict:
    """Measure the frozen Brainlehr prose control with the same four rankings."""
    goldset = load_goldset()
    spec = next(matrix for matrix in goldset["matrices"] if matrix["id"] == "de_brainlehr_prose_to_prose")
    docs = {entry["id"]: entry["text"] for entry in goldset["prose_candidates"]}
    keys = sorted(docs)
    coderank = _load_coderank(model_path)
    started = time.perf_counter()
    bge_docs = _bge([docs[key] for key in keys])
    code_docs = _coderank(coderank, [docs[key] for key in keys], query=False)
    cases = spec["cases"]
    bge_ranked = [ranks(vector, dict(zip(keys, bge_docs))) for vector in _bge([case["query"] for case in cases])]
    code_ranked = [ranks(vector, dict(zip(keys, code_docs)))
                   for vector in _coderank(coderank, [case["query"] for case in cases], query=True)]
    bge_order = [[key for key, _ in ranked] for ranked in bge_ranked]
    code_order = [[key for key, _ in ranked] for ranked in code_ranked]
    rrf_order = [_rrf_order(left, right) for left, right in zip(bge_ranked, code_ranked)]
    return _matrix({"bge_m3": _ranked_metrics(cases, bge_order),
                    "coderankembed": _ranked_metrics(cases, code_order),
                    "rrf": _ranked_metrics(cases, rrf_order),
                    "router": _ranked_metrics(cases, bge_order)},
                   language="brainlehr", modality="prose_to_prose",
                   elapsed=time.perf_counter() - started,
                   rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def multilingual_activation_decision(matrices: list[dict], prose_control: dict) -> dict:
    """Apply pre-registered gates after, never during, all required slices."""
    expected = {(language, modality) for language in MANDATORY_LANGUAGES
                for modality in MULTILINGUAL_MODALITIES}
    observed = {(matrix["language"], matrix["query_modality"]) for matrix in matrices}
    missing = sorted(f"{language}/{modality}" for language, modality in expected - observed)
    valid_input = (not missing and len(matrices) == len(expected)
                   and all(matrix.get("validation", {}).get("leak_free") is True for matrix in matrices)
                   and all(matrix.get("validation", {}).get("same_language_code_hard_negative_n") == 1
                           for matrix in matrices))
    outcome: dict[str, dict] = {}
    baseline = "bge_m3"
    for channel in ("coderankembed", "rrf", "router"):
        code_r1 = [matrix[channel]["metrics"]["recall_at_1"] for matrix in matrices]
        bge_r1 = [matrix[baseline]["metrics"]["recall_at_1"] for matrix in matrices]
        code_mrr = [matrix[channel]["metrics"]["mrr"] for matrix in matrices]
        bge_mrr = [matrix[baseline]["metrics"]["mrr"] for matrix in matrices]
        macro_r1_gain = sum(code_r1) / len(code_r1) - sum(bge_r1) / len(bge_r1) if matrices else 0.0
        macro_mrr_gain = sum(code_mrr) / len(code_mrr) - sum(bge_mrr) / len(bge_mrr) if matrices else 0.0
        per_matrix_ok = all(candidate - base >= ACTIVATION_THRESHOLDS["per_matrix_recall_at_1_drop"]
                            for candidate, base in zip(code_r1, bge_r1))
        prose_ok = (prose_control[channel]["metrics"]["recall_at_1"]
                    - prose_control[baseline]["metrics"]["recall_at_1"]
                    >= ACTIVATION_THRESHOLDS["prose_recall_at_1_drop"])
        outcome[channel] = {"macro_recall_at_1_gain": round(macro_r1_gain, 6),
                            "macro_mrr_gain": round(macro_mrr_gain, 6),
                            "per_matrix_nonregression": per_matrix_ok,
                            "prose_nonregression": prose_ok,
                            "eligible": valid_input and per_matrix_ok and prose_ok
                            and macro_r1_gain >= ACTIVATION_THRESHOLDS["macro_recall_at_1_gain"]
                            and macro_mrr_gain >= ACTIVATION_THRESHOLDS["mrr_gain"]}
    eligible = [(item["macro_recall_at_1_gain"], item["macro_mrr_gain"], channel)
                for channel, item in outcome.items() if item["eligible"]]
    winner = max(eligible)[2] if eligible else baseline
    return {"rule": "An alternate ranker needs leak-free frozen input, a >=1 percentage-point macro Recall@1 and MRR gain, zero mandatory-matrix Recall@1 loss, and zero prose-control Recall@1 loss.",
            "missing_matrices": missing, "candidates": outcome,
            "input_valid": valid_input, "active_channel": winner if valid_input else baseline,
            "activate_separate_code_channel": winner != baseline}


def aggregate_multilingual_reports(reports: list[dict], prose_control: dict) -> dict:
    """Combine independently bounded slices only when all mandatory matrices exist."""
    matrices = [matrix for report in reports for matrix in report.get("matrices", [])]
    decision = multilingual_activation_decision(matrices, prose_control)
    return {"schema": 3, "thresholds": ACTIVATION_THRESHOLDS,
            "mandatory_languages": list(MANDATORY_LANGUAGES), "matrix_count": len(matrices),
            "matrices": sorted(matrices, key=lambda matrix: matrix["id"]),
            "prose_control": prose_control, "activation": decision,
            "latency_seconds": round(sum(report.get("latency_seconds", 0.0) for report in reports), 3),
            "max_rss": max([report.get("max_rss", 0) for report in reports] + [prose_control["max_rss"]])}


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                          capture_output=True, check=True).stdout


def _chunks(revision: str, paths: list[str]) -> dict[str, str]:
    """Top-level source, keyed externally so paths never enter model input."""
    chunks: dict[str, str] = {}
    for path in paths:
        source = _git("show", f"{revision}:{path}")
        tree = ast.parse(source, filename=path)
        lines = source.splitlines(keepends=True)
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and getattr(node, "end_lineno", None):
                chunks[f"{path}#{node.name}"] = "".join(lines[node.lineno - 1:node.end_lineno])[:MAX_CHUNK_CHARS]
    return chunks


def load_goldset(path: Path = GOLDSET) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"candidate_paths", "prose_candidates", "matrices"}
    if data.get("schema") != 2 or not required <= set(data):
        raise ValueError("code goldset requires schema=2 and all candidate/matrix fields")
    if not data["matrices"] or not all(matrix.get("cases") and matrix.get("candidate_set") for matrix in data["matrices"]):
        raise ValueError("each code goldset matrix requires cases and candidate_set")
    return data


def cosine(left: list[float], right: list[float]) -> float:
    return embeddings.cosine_similarity(left, right)


def ranks(query_vec: list[float], vectors: dict[str, list[float]]) -> list[tuple[str, float]]:
    return sorted(((key, cosine(query_vec, vector)) for key, vector in vectors.items()),
                  key=lambda item: item[1], reverse=True)


def evaluate(cases: list[dict], vectors: dict[str, list[float]], query_vectors: list[list[float]]) -> dict:
    positive_ranks, negative_scores, rows = [], [], []
    for case, query_vec in zip(cases, query_vectors):
        ordered = ranks(query_vec, vectors)
        target = case.get("target")
        if target:
            rank = next((index for index, (key, _) in enumerate(ordered, 1) if key == target), None)
            if rank is None:
                raise ValueError(f"target absent from candidate set: {target}")
            positive_ranks.append(rank)
            rows.append({"id": case["id"], "target": target, "rank": rank, "top": ordered[0][0], "top_score": ordered[0][1]})
        else:
            score = ordered[0][1] if ordered else 0.0
            negative_scores.append(score)
            rows.append({"id": case["id"], "target": None, "top": ordered[0][0] if ordered else None, "top_score": score})
    weakest_top1 = min(row["top_score"] for row in rows if row["target"] and row["rank"] == 1)
    return {
        "positive_n": len(positive_ranks), "negative_n": len(negative_scores),
        "recall_at_1": sum(rank <= 1 for rank in positive_ranks) / len(positive_ranks),
        "recall_at_5": sum(rank <= 5 for rank in positive_ranks) / len(positive_ranks),
        "recall_at_10": sum(rank <= 10 for rank in positive_ranks) / len(positive_ranks),
        "mrr": sum(1 / rank for rank in positive_ranks) / len(positive_ranks),
        "negative_max_score": max(negative_scores, default=None),
        "negative_median_score": statistics.median(negative_scores) if negative_scores else None,
        "negative_false_alarm_rate_at_weakest_top1": sum(score >= weakest_top1 for score in negative_scores) / len(negative_scores) if negative_scores else 0.0,
        "rows": rows,
    }


def _load_coderank(path: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError("CodeRankEmbed runtime is unavailable") from error
    return SentenceTransformer(path, local_files_only=True, trust_remote_code=True)


def _coderank(model_or_path, texts: list[str], *, query: bool) -> list[list[float]]:
    model = _load_coderank(model_or_path) if isinstance(model_or_path, str) else model_or_path
    payload = [QUERY_PREFIX + text if query else text for text in texts]
    return [list(map(float, row)) for row in model.encode(payload, normalize_embeddings=True,
                                                            show_progress_bar=False, batch_size=BATCH_SIZE)]


def _bge(texts: list[str]) -> list[list[float]]:
    result = [embeddings.embed_text(text, model=embeddings.model_identity("bge-m3")) for text in texts]
    if any(vector is None for vector in result):
        raise RuntimeError("BGE-M3 is unavailable; no score is emitted")
    return [vector for vector in result if vector is not None]


def _measure(cases: list[dict], documents: dict[str, str], embed_documents, embed_queries) -> dict:
    keys = sorted(documents)
    started = time.perf_counter()
    document_vectors = embed_documents([documents[key] for key in keys])
    query_vectors = embed_queries([case["query"] for case in cases])
    return {"seconds": round(time.perf_counter() - started, 3),
            "metrics": evaluate(cases, dict(zip(keys, document_vectors)), query_vectors)}


def activation_decision(matrices: list[dict]) -> dict:
    code = [matrix for matrix in matrices if matrix["id"] in CODE_MATRIX_IDS]
    prose = next(matrix for matrix in matrices if matrix["id"] == "de_brainlehr_prose_to_prose")
    win = lambda matrix: (matrix["coderankembed"]["metrics"]["recall_at_1"] > matrix["bge_m3"]["metrics"]["recall_at_1"]
                           and matrix["coderankembed"]["metrics"]["mrr"] > matrix["bge_m3"]["metrics"]["mrr"])
    prose_ok = (prose["coderankembed"]["metrics"]["recall_at_1"] >= prose["bge_m3"]["metrics"]["recall_at_1"]
                and prose["coderankembed"]["metrics"]["mrr"] >= prose["bge_m3"]["metrics"]["mrr"])
    return {"rule": "CodeRankEmbed must strictly beat BGE-M3 in Recall@1 and MRR in every code matrix, while not reducing either metric in the Brainlehr prose matrix.",
            "code_matrices_win": all(win(matrix) for matrix in code), "prose_nonregression": prose_ok,
            "activate_separate_code_channel": all(win(matrix) for matrix in code) and prose_ok}


def run(model_path: str, revision: str = "HEAD") -> dict:
    goldset = load_goldset()
    revision = _git("rev-parse", revision).strip()
    python_docs = _chunks(revision, goldset["candidate_paths"])
    prose_docs = {entry["id"]: entry["text"] for entry in goldset["prose_candidates"]}
    candidate_sets = {"python": python_docs, "prose": prose_docs}
    model = _load_coderank(model_path)
    matrices = []
    for spec in goldset["matrices"]:
        docs = candidate_sets.get(spec["candidate_set"])
        if docs is None:
            raise ValueError(f"unknown candidate_set: {spec['candidate_set']}")
        missing = {case["target"] for case in spec["cases"] if case.get("target")} - set(docs)
        if missing:
            raise ValueError("goldset targets missing from revision: " + ", ".join(sorted(missing)))
        matrices.append({key: spec[key] for key in ("id", "language", "query_modality", "document_modality", "candidate_set")}
                        | {"candidate_count": len(docs), "positive_n": sum(bool(case.get("target")) for case in spec["cases"]),
                           "negative_n": sum(not case.get("target") for case in spec["cases"]),
                           "model_prefix_contract": {"bge_m3": {"query_prefix": None, "document_prefix": None},
                                                     "coderankembed": {"query_prefix": QUERY_PREFIX, "document_prefix": None}},
                           "bge_m3": _measure(spec["cases"], docs, _bge, _bge),
                           "coderankembed": _measure(spec["cases"], docs,
                                                        lambda texts: _coderank(model, texts, query=False),
                                                        lambda texts: _coderank(model, texts, query=True))})
    return {"schema": 2, "git_commit": revision, "goldset_sha256": hashlib.sha256(GOLDSET.read_bytes()).hexdigest(),
            "chunking": {"max_chars": MAX_CHUNK_CHARS, "batch_size": BATCH_SIZE,
                         "truncated_chunks": sum(len(text) >= MAX_CHUNK_CHARS for text in python_docs.values()),
                         "python_header_in_model_input": False},
            "model": {"id": "nomic-ai/CodeRankEmbed", "license": "MIT", "dimension": 768,
                      "query_prefix": QUERY_PREFIX, "model_revision": Path(model_path).name},
            "matrices": matrices, "activation": activation_decision(matrices)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default=os.environ.get("BRAINLEHR_CODE_MODEL_PATH", ""))
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--language", choices=MANDATORY_LANGUAGES,
                        help="measure exactly one mandatory language slice")
    parser.add_argument("--multilingual", action="store_true",
                        help="measure all frozen mandatory language slices")
    args = parser.parse_args()
    if not args.model_path:
        raise SystemExit("--model-path or BRAINLEHR_CODE_MODEL_PATH is required")
    if args.language and args.multilingual:
        parser.error("--language and --multilingual are mutually exclusive")
    result = (run_multilingual(args.model_path, languages={args.language}) if args.language
              else run_multilingual(args.model_path) if args.multilingual
              else run(args.model_path, args.revision))
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
