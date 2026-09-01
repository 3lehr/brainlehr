import subprocess
from pathlib import Path

import pytest

from kern.cross_repo_impact import as_evidence_witness, cross_repo_impact
from kern.project_context import witness_envelope


def _repo(path: Path, name: str) -> str:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README").write_text(name, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README"], check=True)
    subprocess.run(["git", "-C", str(path), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", name], check=True)
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def test_registered_cross_repo_contract_has_transitive_impact_and_p98_witness(tmp_path: Path):
    a, b, c = (tmp_path / name for name in ("a", "b", "c"))
    rev_a, rev_b, rev_c = (_repo(path, path.name) for path in (a, b, c))
    projects = {"a": {"revision": rev_a}, "b": {"revision": rev_b}, "c": {"revision": rev_c}}
    links = [{"producer_project": "a", "consumer_project": "b", "contract_id": "api", "producer_revision": rev_a, "consumer_revision": rev_b},
             {"producer_project": "b", "consumer_project": "c", "contract_id": "api", "producer_revision": rev_b, "consumer_revision": rev_c}]
    result = cross_repo_impact(projects, links, changed_project="a", changed_revision=rev_a)
    assert result["status"] == "PASS"
    assert result["impacted"] == [{"project_id": "b", "distance": 1, "via_contract": "api"}, {"project_id": "c", "distance": 2, "via_contract": "api"}]
    witness = as_evidence_witness(result, witness_id="p80-a")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_unregistered_or_stale_counterpart_never_becomes_impact_proof():
    projects = {"a": {"revision": "a1"}, "b": {"revision": "b1"}}
    stale = cross_repo_impact(projects, [{"producer_project": "a", "consumer_project": "b", "contract_id": "api", "producer_revision": "a1", "consumer_revision": "old"}], changed_project="a", changed_revision="a1")
    assert stale["status"] == "UNKNOWN" and "registered_contract_edge_stale" in stale["coverage_gaps"]
    assert cross_repo_impact(projects, [], changed_project="x", changed_revision="x1")["coverage_gaps"] == ["changed_project_unregistered"]
    with pytest.raises(ValueError, match="bounded"):
        cross_repo_impact(projects, [], changed_project="../x", changed_revision="x1")
