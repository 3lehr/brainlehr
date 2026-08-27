import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v6_seal_binds_ready_gate_launcher_and_model_cache():
    seal = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v6.json").read_text())
    assert seal["schema"] == 6 and seal["decision"].startswith("NOT RUN")
    for key in ("corpus", "runner", "source_views", "collector", "scorer", "launcher"):
        item = seal[key]
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    model = seal["models"]["coderank"]
    assert {name: hashlib.sha256((Path(model["cache_root"]) / name).read_bytes()).hexdigest() for name in model["files"]} == model["files"]
