import hashlib
import json
import subprocess
from pathlib import Path

from messungen.sealed_retrieval_document_views import view
from messungen.sealed_retrieval_v3_collector import hash_report
from messungen.sealed_retrieval_v5_collector import collect, resolve_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_v4_cases_reproduce_source_view_without_model_or_encode():
    manifest = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v4.json").read_text())
    corpus = json.loads((ROOT / manifest["corpus"]["path"]).read_text())
    seen = set()
    for case in corpus["cases"]:
        key = (case["repository"], case["document_path"])
        if key in seen:
            continue
        seen.add(key)
        source = subprocess.run(["git", "-C", manifest["repository_roots"][key[0]], "show",
                                 f"{corpus['repositories'][key[0]]['commit']}:{key[1]}"],
                                text=True, capture_output=True, check=True).stdout
        assert all(view(source, arm) for arm in manifest["arms"])


def test_v4_v5_pointer_manifests_resolve_and_hash_mismatch_fail_closed():
    raw = {"schema": 6, "case_count": 15, "test_runs": 1}
    for version in (4, 5):
        manifest = json.loads((ROOT / f"tests/fixtures/sealed_code_retrieval_v{version}.json").read_text())
        resolved = resolve_manifest(manifest)
        assert resolved["schema"] == 3 and len(resolved["cases"]) == 15
        good = collect(manifest, raw, raw_sha256=hash_report(raw))
        assert "sealed_manifest" not in good["missing"]
        bad = {**manifest, "corpus": {**manifest["corpus"], "sha256": "0" * 64}}
        failed = collect(bad, raw, raw_sha256=hash_report(raw))
        assert failed["status"] == "FAIL" and failed["missing"] == ["sealed_manifest"]
