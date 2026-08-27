import hashlib
import json
import os
import subprocess
from pathlib import Path

from messungen.sealed_retrieval_v6_launcher import score_command


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path("/Volumes/daten/p103-v4-runtime/bin/python")


def test_detached_style_module_preflight_is_ready_before_lock(tmp_path):
    assert RUNTIME.is_file()
    manifest = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v5.json").read_text())
    manifest["schema"] = 6
    for key, path in {"scorer": "messungen/sealed_retrieval_v6_score.py",
                      "launcher": "messungen/sealed_retrieval_v6_launcher.py"}.items():
        manifest[key] = {"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
    manifest["test_once"] = {"state": "sealed_not_evaluated", "mode": "O_EXCL",
                             "result": str(tmp_path / "result.json"), "lock": str(tmp_path / "result.json.lock")}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    env = {**os.environ, "PYTHONPATH": str(ROOT)}
    completed = subprocess.run([*score_command(str(RUNTIME)), "--preflight", "--manifest", str(manifest_path)],
                               cwd=ROOT, env=env, text=True, capture_output=True, check=True)
    assert completed.stdout.strip() == "READY_BEFORE_LOCK"
    assert not Path(manifest["test_once"]["result"]).exists()
    assert not Path(manifest["test_once"]["lock"]).exists()
