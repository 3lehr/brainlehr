"""Offline, one-shot P103-v4 scorer. No DB, index, network, or activation."""
from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import tokenize
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]
from messungen.sealed_retrieval_v3 import _write_claimed, claim_test_once, run  # noqa: E402

MODEL_FILES = {
    "model.safetensors": "827529bcd58aef0d9082e66eeff7e7d53a02f62bd005f841a26b3d3e2fb17ebe",
    "config.json": "5ff856a41d0f53ef2d74520627d464bd75c2efd8f26f381bd528654895c29b6c",
    "tokenizer.json": "91f1def9b9391fdabe028cd3f3fcc4efd34e5d1f08c3bf2de513ebb5911a1854",
    "tokenizer_config.json": "7809f768ee3614618b3f1b91dcbfab4f6a9d4b79fb1ad5d17feb65a7c1bb5b7a",
    "1_Pooling/config.json": "d02ebf56344d20f773449b15d0c10ee9a86a9178f3b3c9bfecb8b87d4350ce38",
}
PREFIX = "search_query: "


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preflight(manifest: Mapping[str, Any]) -> dict[str, Any]:
    test_once = manifest["test_once"]
    result = Path(test_once["result"])
    lock = Path(test_once["lock"])
    if result.exists() or lock.exists():
        raise RuntimeError("sealed result or lock already exists")
    model = manifest["models"]["coderank"]
    root = Path(model["cache_root"])
    observed = {name: sha256(root / name) for name in MODEL_FILES}
    if observed != MODEL_FILES or model.get("files") != MODEL_FILES:
        raise RuntimeError("CodeRank file binding mismatch")
    listing = subprocess.run(["ollama", "list"], text=True, capture_output=True, check=True).stdout
    if "bge-m3:latest    790764642607" not in listing:
        raise RuntimeError("BGE-M3 digest mismatch")
    return {"model_files": observed, "bge_digest": manifest["models"]["bge"]["digest"]}


def _docstring_lines(source: str) -> set[int]:
    tree = ast.parse(source)
    lines: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
            lines.update(range(body[0].lineno, body[0].end_lineno + 1))
    return lines


def view(source: str, arm: str) -> str:
    docstrings = _docstring_lines(source)
    comments, code = [], []
    rows = source.splitlines()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            comments.append(token.string)
        elif token.type not in (tokenize.ENCODING, tokenize.ENDMARKER, tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT) and token.start[0] not in docstrings:
            code.append(token.string)
    docs = [rows[number - 1] for number in sorted(docstrings)]
    if arm == "stripped":
        return " ".join(code)
    if arm == "comments_only":
        return "\n".join([*comments, *docs])
    if arm == "combined":
        return source
    raise ValueError("unknown arm")


def _source(repo: Path, commit: str, path: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], text=True,
                          capture_output=True, check=True).stdout


def _bge(texts: Sequence[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        request = urllib.request.Request("http://127.0.0.1:11434/api/embed",
            data=json.dumps({"model": "bge-m3:latest", "input": text, "keep_alive": "30m"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=60) as response:
            vector = json.loads(response.read().decode())["embeddings"][0]
        if len(vector) != 1024:
            raise RuntimeError("BGE-M3 dimension mismatch")
        vectors.append([float(value) for value in vector])
    return vectors


def _coderank(root: Path, texts: Sequence[str], *, query: bool) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as error:
        raise RuntimeError("CodeRank runtime unavailable: sentence_transformers") from error
    model = SentenceTransformer(str(root), local_files_only=True, trust_remote_code=True)
    vectors = model.encode([PREFIX + text if query else text for text in texts], normalize_embeddings=True,
                           show_progress_bar=False, batch_size=4)
    if any(len(vector) != 768 for vector in vectors):
        raise RuntimeError("CodeRank dimension mismatch")
    return [[float(value) for value in vector] for vector in vectors]


def score(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Acquire lock before first encode; leave failure sealed, never retry."""
    evidence = preflight(manifest)
    result_path = Path(manifest["test_once"]["result"])
    claim_test_once(result_path)
    try:
        corpus = json.loads((ROOT / manifest["corpus"]["path"]).read_text())
        cases = corpus["cases"]
        docs: dict[str, str] = {}
        for case in cases:
            path = case["document_path"]
            if path not in docs:
                repository = case["repository"]
                docs[path] = _source(Path(manifest["repository_roots"][repository]), corpus["repositories"][repository]["commit"], path)
        model_root = Path(manifest["models"]["coderank"]["cache_root"])
        vectors: dict[str, Any] = {"bge_m3": {}, "coderank_raw": {}, "prose_bge_identity": True}
        for arm in manifest["arms"]:
            document_texts = {path: view(source, arm) for path, source in docs.items()}
            query_texts = [case["query"] for case in cases]
            vectors["bge_m3"][arm] = {"queries": dict(zip((case["id"] for case in cases), _bge(query_texts))),
                                        "documents": dict(zip(document_texts, _bge(list(document_texts.values()))))}
            vectors["coderank_raw"][arm] = {"queries": dict(zip((case["id"] for case in cases), _coderank(model_root, query_texts, query=True))),
                                              "documents": dict(zip(document_texts, _coderank(model_root, list(document_texts.values()), query=False)))}
        raw = run(cases, vectors, manifest["dev_rrf_grid"])
        raw.update({"schema": 6, "preflight": evidence})
    except Exception as error:
        raw = {"schema": 6, "case_count": 15, "test_runs": 1, "failure": f"{type(error).__name__}: {error}", "preflight": evidence}
    _write_claimed(result_path, raw)
    return raw


if __name__ == "__main__":
    active = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v4.json").read_text())
    print(json.dumps(score(active), sort_keys=True, separators=(",", ":")))
