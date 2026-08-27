import hashlib
import json
from pathlib import Path

from messungen.sealed_retrieval_v3_collector import hash_report
from messungen.sealed_retrieval_v8_collector import collect
from test_sealed_retrieval_v8 import _full_raw


ROOT = Path(__file__).resolve().parents[1]


def test_v9_binds_monitor_and_actual_corpus_collector_preflight():
    seal = json.loads((ROOT / "tests/fixtures/sealed_code_retrieval_v9.json").read_text())
    assert seal["decision"].startswith("NOT RUN") and seal["monitor"]["abort"]["free_pct_lt"] == 25
    for key in ("runner", "source_views", "collector", "scorer", "launcher", "monitor"):
        item = seal[key]
        assert hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    raw = _full_raw(seal)
    assert collect(seal, raw, raw_sha256=hash_report(raw))["status"] == "PASS"
