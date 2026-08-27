import hashlib
import json
import os
import subprocess
from pathlib import Path

from messungen.sealed_retrieval_v8_runner import identifier_leak, run, validate_cases
from messungen.sealed_retrieval_v3_collector import hash_report
from messungen.sealed_retrieval_v8_collector import _resolved, collect
from messungen.sealed_retrieval_v8_launcher import RESOURCE_ENV, score_command


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/Volumes/daten/p103-v4-runtime/bin/python")


def _manifest():
    return json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v8.json").read_text())


def _full_raw(manifest):
    cases = _resolved(manifest)["cases"]
    paths = sorted({case["target"]["path"] for case in cases if case["target"]})
    docs = {path: [float(index == offset) for index in range(len(paths))] for offset, path in enumerate(paths)}
    queries = {case["id"]: docs[case["target"]["path"]] if case["target"] else [0.0] * len(paths) for case in cases}
    vectors = {channel: {arm: {"queries": dict(queries), "documents": docs}
                         for arm in ("stripped", "comments_only", "combined")}
               for channel in ("bge_m3", "coderank_raw")}
    vectors["prose_bge_identity"] = True
    return {**run(cases, vectors, manifest["dev_rrf_grid"]), "schema": 8}


def test_v8_detached_ready_gate_is_before_lock(tmp_path):
    manifest = _manifest()
    manifest["test_once"] = {"state": "sealed_not_evaluated", "mode": "O_EXCL",
                             "result": str(tmp_path / "result.json"), "lock": str(tmp_path / "result.json.lock")}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    result = subprocess.run([*score_command(str(RUNTIME)), "--preflight", "--manifest", str(path)], cwd=ROOT,
                            env={**os.environ, "PYTHONPATH": str(ROOT), **RESOURCE_ENV}, text=True,
                            capture_output=True, check=True)
    assert result.stdout.strip() == "READY_BEFORE_LOCK"
    assert not Path(manifest["test_once"]["result"]).exists() and not Path(manifest["test_once"]["lock"]).exists()


def test_v8_collector_accepts_full_schema_eight_raw_only_after_normalization():
    manifest, raw = _manifest(), _full_raw(_manifest())
    report = collect(manifest, raw, raw_sha256=hash_report(raw))
    assert report["status"] == "PASS" and report["raw_sha256"] == hash_report(raw)
    assert collect(manifest, raw, raw_sha256="0" * 64)["missing"] == ["raw_hash"]


def test_v8_leak_guard_allows_current_concepts_but_rejects_identifier_forms():
    cases = _resolved(_manifest())["cases"]
    validate_cases(cases)
    for query, target in (("code retrieval", {"path": "kern/code_retrieval.py", "symbol": "route"}),
                          ("sync turn", {"path": "brainlehr_provider.py", "symbol": "sync_turn"}),
                          ("precision or unmeasured", {"path": "sigmaforge/score/gates.py", "symbol": "precision_or_unmeasured"}),
                          ("route", {"path": "kern/code_retrieval.py", "symbol": "route"}),
                          ("gates", {"path": "sigmaforge/score/gates.py", "symbol": "x"})):
        assert identifier_leak(query, target)


def test_v8_seal_binds_every_changed_artifact_and_unchanged_contract():
    v7, v8 = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v7.json").read_text()), _manifest()
    assert v8["schema"] == 8 and v8["decision"].startswith("NOT RUN")
    assert {key: v8[key] for key in ("corpus", "models", "arms", "loro_folds", "dev_rrf_grid", "thresholds", "fallbacks", "resources", "runtime")} == {key: v7[key] for key in ("corpus", "models", "arms", "loro_folds", "dev_rrf_grid", "thresholds", "fallbacks", "resources", "runtime")}
    for key in ("runner", "source_views", "collector", "scorer", "launcher"):
        item = v8[key]
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
