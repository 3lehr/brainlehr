import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v5_seal_binds_fixed_execution_and_exact_model_cache():
    seal = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v5.json").read_text())
    assert seal["schema"] == 5 and seal["decision"].startswith("NOT RUN")
    for key in ("corpus", "runner", "source_views", "collector", "scorer"):
        item = seal[key]
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    model = seal["models"]["coderank"]
    assert model["revision"] == "3c4b60807d71f79b43f3c4363786d9493691f8b1" and model["license"] == "MIT"
    assert {name: hashlib.sha256((Path(model["cache_root"]) / name).read_bytes()).hexdigest() for name in model["files"]} == model["files"]
