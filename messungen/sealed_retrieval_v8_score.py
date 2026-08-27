"""P103-v8 scorer: V7 resource policy with an explicit schema-eight envelope."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from messungen.sealed_retrieval_document_views import view
from messungen.sealed_retrieval_v3 import _write_claimed, claim_test_once
from messungen.sealed_retrieval_v8_runner import run
from messungen.sealed_retrieval_v4_score import MODEL_FILES, ROOT, _source, preflight, sha256
from messungen.sealed_retrieval_v7_launcher import RESOURCE_ENV
from messungen.sealed_retrieval_v7_score import _bge, _coderank

RESOURCES = {"device": "mps", "batch_size": 1, "workers": 1, "tokenizers_parallelism": False,
             "omp_threads": 1, "mkl_threads": 1, "openblas_threads": 1, "veclib_maximum_threads": 1}
RUNTIME = {"python": "/Volumes/daten/p103-v4-runtime/bin/python", "torch": "2.13.0",
           "ollama": "loopback", "coderank_prefix": "search_query: "}


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema") != 8 or manifest.get("resources") != RESOURCES or manifest.get("runtime") != RUNTIME:
        raise RuntimeError("sealed V8 manifest policy mismatch")
    for key in ("runner", "source_views", "collector", "scorer", "launcher"):
        item, path = manifest.get(key, {}), None
        path = ROOT / item.get("path", "")
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item.get("sha256"):
            raise RuntimeError(f"sealed {key} hash mismatch")
    corpus = ROOT / manifest["corpus"]["path"]
    if hashlib.sha256(corpus.read_bytes()).hexdigest() != manifest["corpus"]["sha256"]:
        raise RuntimeError("sealed corpus hash mismatch")
    model = manifest["models"]["coderank"]
    if model.get("files") != MODEL_FILES or {name: sha256(Path(model["cache_root"]) / name) for name in MODEL_FILES} != MODEL_FILES:
        raise RuntimeError("CodeRank file binding mismatch")


def ready(manifest: dict[str, Any]) -> dict[str, Any]:
    validate_manifest(manifest)
    if Path(sys.executable) != Path(RUNTIME["python"]) or any(os.environ.get(key) != value for key, value in RESOURCE_ENV.items()):
        raise RuntimeError("V8 runtime resources not enforced")
    import torch
    if not torch.backends.mps.is_available():
        raise RuntimeError("MPS unavailable")
    return preflight(manifest)


def score(manifest: dict[str, Any]) -> dict[str, Any]:
    evidence = ready(manifest)
    result_path = Path(manifest["test_once"]["result"])
    claim_test_once(result_path)
    try:
        corpus = json.loads((ROOT / manifest["corpus"]["path"]).read_text())
        cases, docs = corpus["cases"], {}
        for case in cases:
            path, repository = case["document_path"], case["repository"]
            if path not in docs:
                docs[path] = _source(Path(manifest["repository_roots"][repository]), corpus["repositories"][repository]["commit"], path)
        vectors: dict[str, Any] = {"bge_m3": {}, "coderank_raw": {}, "prose_bge_identity": True}
        for arm in manifest["arms"]:
            texts, queries = {path: view(source, arm) for path, source in docs.items()}, [case["query"] for case in cases]
            vectors["bge_m3"][arm] = {"queries": dict(zip((case["id"] for case in cases), _bge(queries))), "documents": dict(zip(texts, _bge(list(texts.values()))))}
            root = Path(manifest["models"]["coderank"]["cache_root"])
            vectors["coderank_raw"][arm] = {"queries": dict(zip((case["id"] for case in cases), _coderank(root, queries, query=True))), "documents": dict(zip(texts, _coderank(root, list(texts.values()), query=False)))}
        raw = run(cases, vectors, manifest["dev_rrf_grid"])
        raw.update({"schema": 8, "preflight": evidence})
    except Exception as error:
        raw = {"schema": 8, "case_count": 15, "test_runs": 1, "failure": f"{type(error).__name__}: {error}", "preflight": evidence}
    _write_claimed(result_path, raw)
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "tests/fixtures/sealed_code_retrieval_v8.json")
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
