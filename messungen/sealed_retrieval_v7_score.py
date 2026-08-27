"""P103-v7: one-resource CodeRank score after a no-encode readiness gate."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Sequence

from messungen.sealed_retrieval_document_views import view
from messungen.sealed_retrieval_v3 import _write_claimed, claim_test_once, run
from messungen.sealed_retrieval_v4_score import ROOT, _source, preflight
from messungen.sealed_retrieval_v7_launcher import RESOURCE_ENV


def ready(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate seal, MPS availability, and bounded resources without a lock/encode."""
    if manifest.get("schema") != 7:
        raise RuntimeError("P103-v7 manifest schema required")
    for key in ("runner", "source_views", "collector", "scorer", "launcher"):
        item = manifest.get(key, {})
        path = ROOT / item.get("path", "")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            raise RuntimeError(f"sealed {key} hash mismatch")
    corpus = ROOT / manifest["corpus"]["path"]
    if hashlib.sha256(corpus.read_bytes()).hexdigest() != manifest["corpus"]["sha256"]:
        raise RuntimeError("sealed corpus hash mismatch")
    resources = manifest.get("resources")
    expected = {"device": "mps", "batch_size": 1, "workers": 1,
                "tokenizers_parallelism": False, "omp_threads": 1, "mkl_threads": 1,
                "openblas_threads": 1, "veclib_maximum_threads": 1}
    if resources != expected:
        raise RuntimeError("sealed V7 resource policy mismatch")
    if manifest.get("runtime") != {"python": "/Volumes/daten/p103-v4-runtime/bin/python",
                                   "torch": "2.13.0", "ollama": "loopback",
                                   "coderank_prefix": "search_query: "}:
        raise RuntimeError("sealed V7 runtime binding mismatch")
    if Path(sys.executable) != Path(manifest["runtime"]["python"]) or any(
            os.environ.get(key) != value for key, value in RESOURCE_ENV.items()):
        raise RuntimeError("V7 runtime resources not enforced")
    import torch
    if not torch.backends.mps.is_available():
        raise RuntimeError("MPS unavailable")
    return preflight(manifest)


def _bge(texts: Sequence[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/embed",
            data=json.dumps({"model": "bge-m3:latest", "input": text, "keep_alive": 0}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=60) as response:
            vector = json.loads(response.read().decode())["embeddings"][0]
        if len(vector) != 1024:
            raise RuntimeError("BGE-M3 dimension mismatch")
        vectors.append([float(value) for value in vector])
    return vectors


def _coderank(root: Path, texts: Sequence[str], *, query: bool) -> list[list[float]]:
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(1)
    model = SentenceTransformer(str(root), local_files_only=True, trust_remote_code=True, device="mps")
    try:
        vectors = model.encode(["search_query: " + text if query else text for text in texts],
                               normalize_embeddings=True, show_progress_bar=False, batch_size=1)
        if any(len(vector) != 768 for vector in vectors):
            raise RuntimeError("CodeRank dimension mismatch")
        return [[float(value) for value in vector] for vector in vectors]
    finally:
        del model
        gc.collect()
        torch.mps.empty_cache()


def score(manifest: dict[str, Any]) -> dict[str, Any]:
    evidence = ready(manifest)
    result_path = Path(manifest["test_once"]["result"])
    claim_test_once(result_path)
    try:
        corpus = json.loads((ROOT / manifest["corpus"]["path"]).read_text())
        cases = corpus["cases"]
        docs: dict[str, str] = {}
        for case in cases:
            path, repository = case["document_path"], case["repository"]
            if path not in docs:
                docs[path] = _source(Path(manifest["repository_roots"][repository]),
                                     corpus["repositories"][repository]["commit"], path)
        vectors: dict[str, Any] = {"bge_m3": {}, "coderank_raw": {}, "prose_bge_identity": True}
        for arm in manifest["arms"]:
            document_texts = {path: view(source, arm) for path, source in docs.items()}
            queries = [case["query"] for case in cases]
            vectors["bge_m3"][arm] = {"queries": dict(zip((case["id"] for case in cases), _bge(queries))),
                                      "documents": dict(zip(document_texts, _bge(list(document_texts.values()))))}
            model_root = Path(manifest["models"]["coderank"]["cache_root"])
            vectors["coderank_raw"][arm] = {"queries": dict(zip((case["id"] for case in cases), _coderank(model_root, queries, query=True))),
                                             "documents": dict(zip(document_texts, _coderank(model_root, list(document_texts.values()), query=False)))}
        raw = run(cases, vectors, manifest["dev_rrf_grid"])
        raw.update({"schema": 7, "preflight": evidence})
    except Exception as error:
        raw = {"schema": 7, "case_count": 15, "test_runs": 1,
               "failure": f"{type(error).__name__}: {error}", "preflight": evidence}
    _write_claimed(result_path, raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "tests/fixtures/sealed_code_retrieval_v7.json")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    ready(manifest)
    if args.preflight:
        print("READY_BEFORE_LOCK")
        return 0
    print(json.dumps(score(manifest), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
