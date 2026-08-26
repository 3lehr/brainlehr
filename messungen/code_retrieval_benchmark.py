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
BATCH_SIZE = 4
CODE_MATRIX_IDS = frozenset({"en_prose_to_python", "de_prose_to_python", "code_signature_to_python"})


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
    args = parser.parse_args()
    if not args.model_path:
        raise SystemExit("--model-path or BRAINLEHR_CODE_MODEL_PATH is required")
    encoded = json.dumps(run(args.model_path, args.revision), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
