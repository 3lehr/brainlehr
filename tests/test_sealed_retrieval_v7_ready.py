import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from messungen.sealed_retrieval_v7_launcher import RESOURCE_ENV, score_command
from messungen.sealed_retrieval_v7_score import ready


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/Volumes/daten/p103-v4-runtime/bin/python")


def test_v7_mps_resource_preflight_is_ready_before_lock(tmp_path):
    assert RUNTIME.is_file()
    manifest = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v6.json").read_text())
    manifest["schema"] = 7
    for key, path in {"scorer": "messungen/sealed_retrieval_v7_score.py",
                      "launcher": "messungen/sealed_retrieval_v7_launcher.py"}.items():
        manifest[key] = {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
    manifest["resources"] = {"device": "mps", "batch_size": 1, "workers": 1,
                             "tokenizers_parallelism": False, "omp_threads": 1, "mkl_threads": 1,
                             "openblas_threads": 1, "veclib_maximum_threads": 1}
    manifest["runtime"] = {"python": str(RUNTIME), "torch": "2.13.0", "ollama": "loopback",
                           "coderank_prefix": "search_query: "}
    manifest["test_once"] = {"state": "sealed_not_evaluated", "mode": "O_EXCL",
                             "result": str(tmp_path / "result.json"), "lock": str(tmp_path / "result.json.lock")}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    completed = subprocess.run([*score_command(str(RUNTIME)), "--preflight", "--manifest", str(manifest_path)],
                               cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT), **RESOURCE_ENV},
                               text=True, capture_output=True, check=True)
    assert completed.stdout.strip() == "READY_BEFORE_LOCK"
    assert not Path(manifest["test_once"]["result"]).exists()
    assert not Path(manifest["test_once"]["lock"]).exists()


@pytest.mark.parametrize("field, value", (("device", "cpu"), ("batch_size", 2), ("omp_threads", 2)))
def test_v7_rejects_a_resource_policy_deviation_before_lock(field, value):
    manifest = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v7.json").read_text())
    manifest["resources"][field] = value
    with pytest.raises(RuntimeError, match="resource policy"):
        ready(manifest)
