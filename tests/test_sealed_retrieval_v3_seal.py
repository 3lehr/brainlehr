import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / "tests/fixtures/sealed_code_retrieval_v3.json"


def test_v3_seal_binds_unmodified_corpus_runner_collector_models_and_lock():
    seal = json.loads(SEAL.read_text())
    assert seal["schema"] == 3 and seal["decision"].startswith("NOT RUN")
    for key in ("corpus", "runner", "collector"):
        item = seal[key]
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert seal["models"]["bge"]["digest"] == "7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab"
    assert seal["models"]["coderank"]["sha256"].startswith("827529")
    assert seal["arms"] == ["stripped", "comments_only", "combined"] and seal["loro_folds"] == 3
    assert seal["test_once"]["mode"] == "O_EXCL" and seal["test_once"]["state"] == "sealed_not_evaluated"
