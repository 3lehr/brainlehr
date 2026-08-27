import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / "tests/fixtures/sealed_code_retrieval_v4.json"


def test_v4_seal_binds_exact_local_coderank_files_and_rejects_placeholder_hash():
    seal = json.loads(SEAL.read_text())
    assert seal["schema"] == 4 and seal["decision"].startswith("NOT RUN")
    for key in ("corpus", "runner", "collector", "scorer"):
        item = seal[key]
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert hashlib.sha256((ROOT / seal["collector"]["v3_path"]).read_bytes()).hexdigest() == seal["collector"]["v3_sha256"]
    model = seal["models"]["coderank"]
    assert model["revision"] == "3c4b60807d71f79b43f3c4363786d9493691f8b1" and model["license"] == "MIT"
    assert all(len(value) == 64 and value != "827529" + "0" * 58 for value in model["files"].values())
    assert {name: hashlib.sha256((Path(model["cache_root"]) / name).read_bytes()).hexdigest() for name in model["files"]} == model["files"]
