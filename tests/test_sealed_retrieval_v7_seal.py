import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v7_seal_binds_resources_and_unchanged_experiment_contract():
    v6 = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v6.json").read_text())
    v7 = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v7.json").read_text())
    assert v7["schema"] == 7 and v7["decision"].startswith("NOT RUN")
    assert {key: v7[key] for key in ("corpus", "models", "arms", "loro_folds", "dev_rrf_grid", "thresholds", "fallbacks")} == {key: v6[key] for key in ("corpus", "models", "arms", "loro_folds", "dev_rrf_grid", "thresholds", "fallbacks")}
    assert v7["resources"] == {"device": "mps", "batch_size": 1, "workers": 1,
                               "tokenizers_parallelism": False, "omp_threads": 1, "mkl_threads": 1,
                               "openblas_threads": 1, "veclib_maximum_threads": 1}
    assert v7["runtime"] == {"python": "/Volumes/daten/p103-v4-runtime/bin/python", "torch": "2.13.0",
                             "ollama": "loopback", "coderank_prefix": "search_query: "}
    for key in ("runner", "source_views", "collector", "scorer", "launcher"):
        item = v7[key]
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
