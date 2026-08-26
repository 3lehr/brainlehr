#!/usr/bin/env python3
"""Measure a local code embedder against BGE-M3 on a frozen code goldset.

The goldset fixes prompts and target symbols; source chunks always come from
the requested Git revision.  No vector is written to brainlehr.db and model
artifacts are deliberately external to this repository.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]
import embeddings  # noqa: E402

GOLDSET = ROOT / "tests" / "fixtures" / "code_retrieval_goldset.json"
QUERY_PREFIX = "Represent this query for searching relevant code: "
MAX_CHUNK_CHARS = 12000


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                          capture_output=True, check=True).stdout


def _chunks(revision: str, paths: list[str]) -> dict[str, str]:
    chunks: dict[str, str] = {}
    for path in paths:
        source = _git("show", f"{revision}:{path}")
        tree = ast.parse(source, filename=path)
        lines = source.splitlines(keepends=True)
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if not getattr(node, "end_lineno", None):
                continue
            text = "".join(lines[node.lineno - 1:node.end_lineno])
            # The model has an 8192-token ceiling.  A few orchestration
            # functions are much larger, so a bounded prefix is an explicit
            # benchmark/index policy, never an accidental allocator failure.
            chunks[f"{path}#{node.name}"] = f"# {path}#{node.name}\n{text[:MAX_CHUNK_CHARS]}"
    return chunks


def load_goldset(path: Path = GOLDSET) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("candidate_paths"), list):
        raise ValueError("code goldset requires schema=1 and candidate_paths")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("code goldset requires cases")
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
            rows.append({"id": case["id"], "target": target, "rank": rank,
                         "top": ordered[0][0], "top_score": ordered[0][1]})
        else:
            score = ordered[0][1] if ordered else 0.0
            negative_scores.append(score)
            rows.append({"id": case["id"], "target": None, "top": ordered[0][0] if ordered else None,
                         "top_score": score})
    min_positive_top_score = min(row["top_score"] for row in rows if row["target"] and row["rank"] == 1)
    return {
        "positive_n": len(positive_ranks),
        "recall_at_1": sum(rank <= 1 for rank in positive_ranks) / len(positive_ranks),
        "recall_at_5": sum(rank <= 5 for rank in positive_ranks) / len(positive_ranks),
        "recall_at_10": sum(rank <= 10 for rank in positive_ranks) / len(positive_ranks),
        "mrr": sum(1 / rank for rank in positive_ranks) / len(positive_ranks),
        "negative_n": len(negative_scores),
        "negative_max_score": max(negative_scores, default=None),
        "negative_median_score": statistics.median(negative_scores) if negative_scores else None,
        "negative_false_alarm_rate_at_weakest_top1": (
            sum(score >= min_positive_top_score for score in negative_scores) / len(negative_scores)
            if negative_scores else 0.0
        ),
        "rows": rows,
    }


def _coderank(path: str, texts: list[str], *, query: bool) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError("CodeRankEmbed runtime is unavailable") from error
    model = SentenceTransformer(path, local_files_only=True, trust_remote_code=True)
    payload = [QUERY_PREFIX + text if query else text for text in texts]
    return [list(map(float, row)) for row in model.encode(payload, normalize_embeddings=True,
                                                            show_progress_bar=False, batch_size=4)]


def _bge(texts: list[str]) -> list[list[float]]:
    result = [embeddings.embed_text(text, model=embeddings.model_identity("bge-m3")) for text in texts]
    if any(vector is None for vector in result):
        raise RuntimeError("BGE-M3 is unavailable; no score is emitted")
    return [vector for vector in result if vector is not None]


def run(model_path: str, revision: str = "HEAD") -> dict:
    goldset = load_goldset()
    revision = _git("rev-parse", revision).strip()
    chunks = _chunks(revision, goldset["candidate_paths"])
    targets = {case["target"] for case in goldset["cases"] if case.get("target")}
    missing = sorted(targets - set(chunks))
    if missing:
        raise ValueError("goldset targets missing from revision: " + ", ".join(missing))
    docs = [chunks[key] for key in sorted(chunks)]
    keys = sorted(chunks)
    queries = [case["query"] for case in goldset["cases"]]
    started = time.perf_counter()
    bge_docs = _bge(docs)
    bge_queries = _bge(queries)
    bge_seconds = time.perf_counter() - started
    started = time.perf_counter()
    code_docs = _coderank(model_path, docs, query=False)
    code_queries = _coderank(model_path, queries, query=True)
    code_seconds = time.perf_counter() - started
    return {
        "schema": 1,
        "git_commit": revision,
        "goldset_sha256": hashlib.sha256(GOLDSET.read_bytes()).hexdigest(),
        "candidate_count": len(keys),
        "chunking": {"max_chars": MAX_CHUNK_CHARS,
                     "truncated_chunks": sum(len(text) >= MAX_CHUNK_CHARS for text in chunks.values())},
        "model": {"id": "nomic-ai/CodeRankEmbed", "license": "MIT", "dimension": len(code_docs[0]),
                  "query_prefix": QUERY_PREFIX, "model_revision": Path(model_path).name},
        "bge_m3": {"model": embeddings.model_identity("bge-m3"), "dimension": len(bge_docs[0]),
                   "seconds": round(bge_seconds, 3),
                   "metrics": evaluate(goldset["cases"], dict(zip(keys, bge_docs)), bge_queries)},
        "coderankembed": {"seconds": round(code_seconds, 3),
                          "metrics": evaluate(goldset["cases"], dict(zip(keys, code_docs)), code_queries)},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", default=os.environ.get("BRAINLEHR_CODE_MODEL_PATH", ""))
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not args.model_path:
        raise SystemExit("--model-path or BRAINLEHR_CODE_MODEL_PATH is required")
    result = run(args.model_path, args.revision)
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
