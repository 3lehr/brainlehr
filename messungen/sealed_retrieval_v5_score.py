"""Offline, one-shot P103-v5 scorer using shared fixed source views."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from messungen.sealed_retrieval_document_views import view
from messungen.sealed_retrieval_v3 import _write_claimed, claim_test_once, run
from messungen.sealed_retrieval_v4_score import ROOT, _bge, _coderank, _source, preflight


def score(manifest: dict[str, Any]) -> dict[str, Any]:
    evidence = preflight(manifest)
    corpus_path = ROOT / manifest["corpus"]["path"]
    if hashlib.sha256(corpus_path.read_bytes()).hexdigest() != manifest["corpus"]["sha256"]:
        raise RuntimeError("sealed corpus hash mismatch")
    result_path = Path(manifest["test_once"]["result"])
    claim_test_once(result_path)
    try:
        corpus = json.loads(corpus_path.read_text())
        cases = corpus["cases"]
        docs: dict[str, str] = {}
        for case in cases:
            path, repository = case["document_path"], case["repository"]
            if path not in docs:
                docs[path] = _source(Path(manifest["repository_roots"][repository]),
                                     corpus["repositories"][repository]["commit"], path)
        model_root = Path(manifest["models"]["coderank"]["cache_root"])
        vectors: dict[str, Any] = {"bge_m3": {}, "coderank_raw": {}, "prose_bge_identity": True}
        for arm in manifest["arms"]:
            document_texts = {path: view(source, arm) for path, source in docs.items()}
            queries = [case["query"] for case in cases]
            vectors["bge_m3"][arm] = {"queries": dict(zip((case["id"] for case in cases), _bge(queries))),
                                        "documents": dict(zip(document_texts, _bge(list(document_texts.values()))))}
            vectors["coderank_raw"][arm] = {"queries": dict(zip((case["id"] for case in cases), _coderank(model_root, queries, query=True))),
                                              "documents": dict(zip(document_texts, _coderank(model_root, list(document_texts.values()), query=False)))}
        raw = run(cases, vectors, manifest["dev_rrf_grid"])
        raw.update({"schema": 6, "preflight": evidence})
    except Exception as error:
        raw = {"schema": 6, "case_count": 15, "test_runs": 1,
               "failure": f"{type(error).__name__}: {error}", "preflight": evidence}
    _write_claimed(result_path, raw)
    return raw


if __name__ == "__main__":
    manifest = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v5.json").read_text())
    print(json.dumps(score(manifest), sort_keys=True, separators=(",", ":")))
