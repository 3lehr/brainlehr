"""P103-v2: validate the sealed, unscored retrieval fixture."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

from messungen.sealed_retrieval_v2 import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).parent / "fixtures" / "sealed_code_retrieval_v2.json"
SOURCE_ROOT = Path(os.environ.get("P103_SEAL_SOURCE_ROOT", ROOT.parent))
REPOS = {
    "brainlehr": ROOT,
    "hermes-brainlehr": SOURCE_ROOT / "hermes-brainlehr",
    "sigmaforge": SOURCE_ROOT / "sigmaforge",
}


def load_manifest():
    return json.loads(FIXTURE.read_text())


def git_bytes(repo: Path, object_name: str) -> bytes:
    return subprocess.run(
        ["git", "show", object_name], cwd=repo, check=True, capture_output=True
    ).stdout


def sha256(value: bytes | str) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def test_fixture_is_a_real_unscored_fifteen_case_seal():
    manifest = load_manifest()
    frozen = validate_manifest(manifest)
    assert frozen["schema"] == 2
    assert frozen["decision"] == "NOT RUN; BGE-only remains active"
    assert len(manifest["cases"]) >= 15
    for repo in manifest["repositories"]:
        rows = [case for case in manifest["cases"] if case["repository"] == repo]
        assert sum(case["expected"] == "target" for case in rows) >= 4
        assert any(case["expected"] == "no_hit" for case in rows)


def test_cases_have_balanced_languages_all_modalities_and_prose_control():
    cases = load_manifest()["cases"]
    languages = [case["query_language"] for case in cases]
    assert abs(languages.count("de") - languages.count("en")) <= 1
    assert {"code", "signature", "consumer", "error", "impact", "prose_control"} <= {
        case["modality"] for case in cases
    }


def test_source_revisions_licenses_documents_and_positive_proofs_are_exactly_bound():
    manifest = load_manifest()
    for name, source in manifest["repositories"].items():
        repo = REPOS[name]
        assert git_bytes(repo, "HEAD")
        assert sha256(git_bytes(repo, f"{source['commit']}:LICENSE")) == source["license_sha256"]
    for case in manifest["cases"]:
        repo = REPOS[case["repository"]]
        commit = manifest["repositories"][case["repository"]]["commit"]
        document = git_bytes(repo, f"{commit}:{case['document_path']}")
        assert sha256(document) == case["document_sha256"]
        assert sha256(case["query"]) == case["query_sha256"]
        if case["expected"] == "target":
            assert case["target"]["symbol"].encode() in document
            proof = git_bytes(repo, f"{commit}:{case['proof']['path']}")
            assert sha256(proof) == case["proof"]["sha256"]
            assert f"def {case['proof']['test']}(".encode() in proof


def test_annotation_arms_are_source_only_or_none_and_never_depend_on_the_query():
    arms = load_manifest()["annotation_arms"]
    assert {arm["annotation_source"] for arm in arms} <= {"source_comments_docstrings", "NONE"}
    assert all(arm["query_independent"] is True for arm in arms)


@pytest.mark.parametrize("mutation", [
    lambda case: case.__setitem__("query", case["target"]["symbol"]),
    lambda case: case.__setitem__("query", case["target"]["path"]),
    lambda case: case.__setitem__("proof", None),
])
def test_identifier_leaks_and_missing_positive_proofs_fail_closed(mutation):
    manifest = load_manifest()
    assert sha256((ROOT / "messungen" / "sealed_retrieval_v2.py").read_bytes()) == manifest["evaluator"]["sha256"]
    case = next(case for case in manifest["cases"] if case["expected"] == "target")
    mutation(case)
    if isinstance(case["query"], str):
        case["query_sha256"] = sha256(case["query"])
    with pytest.raises(ValueError):
        validate_manifest(manifest)


def test_test_once_loro_grid_fallback_and_operational_thresholds_are_frozen():
    manifest = load_manifest()
    assert len(manifest["loro_folds"]) == len(manifest["repositories"])
    assert len(manifest["dev_rrf_grid"]) > 1
    assert manifest["test_once"]["state"] == "sealed_not_evaluated"
    assert set(manifest["fallbacks"].values()) == {"bge_m3"}
    assert {"max_elapsed_seconds", "max_rss_bytes", "max_p95_latency_ms"} == set(manifest["operational_thresholds"])
