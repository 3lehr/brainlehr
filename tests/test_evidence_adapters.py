"""Contract tests for normalizing external analyzer records.

Fixtures are synthetic and carry stable revisions so adapters cannot silently
drop provenance while converging on Brainlehr's compact record shape.
"""

import json
from pathlib import Path

import pytest

from kern.evidence_adapters import normalize_record


FIXTURES = Path(__file__).parent / "fixtures" / "evidence_adapters"


@pytest.mark.parametrize("kind", ["tree_sitter", "scip", "joern", "otlp", "semgrep"])
def test_normalized_record_has_common_identity_and_provenance(kind):
    payload = json.loads((FIXTURES / {"tree_sitter": "tree_sitter_js.json", "scip": "scip.json", "joern": "joern_cpg.json", "otlp": "otlp.json", "semgrep": "semgrep.json"}[kind]).read_text())
    record = normalize_record(kind, payload)
    assert set(record) >= {"kind", "revision", "source", "nodes", "edges", "provenance"}
    assert record["kind"] == kind
    assert record["revision"] == payload["revision"]
    assert record["source"] == payload["source"]
    assert record["provenance"]["fixture"] is True
    assert record["nodes"] and all("id" in node for node in record["nodes"])
    assert all({"type", "from", "to"} <= set(edge) for edge in record["edges"])


def test_normalization_is_deterministic_and_rejects_unknown_kind():
    payload = json.loads((FIXTURES / "scip.json").read_text())
    assert normalize_record("scip", payload) == normalize_record("scip", payload)
    with pytest.raises(ValueError, match="unsupported analyzer"):
        normalize_record("unknown", payload)


def test_otlp_drops_untrusted_attributes_and_keeps_timing_metadata():
    record = normalize_record("otlp", {"source": "otlp", "revision": "r1", "resourceSpans": [{
        "scopeSpans": [{"spans": [{"spanId": "a", "name": "build",
            "attributes": [{"key": "secret", "value": {"stringValue": "do-not-store"}}],
            "startTimeUnixNano": 10, "endTimeUnixNano": 20}]}]}]})
    node = record["nodes"][0]
    assert node["name"] == "build" and node["startTimeUnixNano"] == 10
    assert "secret" not in str(record)
