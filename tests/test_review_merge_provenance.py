import subprocess

from kern.project_context import witness_envelope
from kern.review_merge_provenance import as_evidence_witness, review_merge_provenance


def test_review_merge_provenance_separates_approval_gap_and_reject(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "change.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "change.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "reviewed change"], cwd=repo, check=True)
    reviewed = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    subprocess.run(["git", "commit", "--allow-empty", "-qm", "merge"], cwd=repo, check=True)
    merge = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()

    approved = review_merge_provenance(
        reviewed_revision=reviewed, review_role="independent-reviewer",
        review_result="approved", merge_commit=merge, merge_revision=reviewed)
    assert approved["status"] == "PASS"
    assert set(approved["review"]) == {"revision", "role", "result", "independent"}
    assert "prompt" not in str(approved).lower() and "review_text" not in approved["review"]
    witness = as_evidence_witness(approved, witness_id="p83-review")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}

    assert review_merge_provenance(
        reviewed_revision=reviewed, review_role="reviewer", review_result="approved",
        merge_commit=merge, merge_revision=reviewed, stale=True)["status"] == "UNKNOWN"
    assert review_merge_provenance(
        reviewed_revision=reviewed, review_role="reviewer", review_result="approved",
        merge_commit=merge, merge_revision=reviewed, independent=False)["status"] == "UNKNOWN"
    assert review_merge_provenance(
        reviewed_revision=reviewed, review_role="reviewer", review_result="rejected",
        merge_commit=merge, merge_revision=reviewed)["status"] == "FAIL"
    assert review_merge_provenance(
        reviewed_revision=reviewed, review_role="reviewer", review_result="approved",
        merge_commit=merge, merge_revision=merge)["status"] == "FAIL"


def test_review_merge_provenance_rejects_blank_identity():
    result = review_merge_provenance(
        reviewed_revision=" ", review_role=" ", review_result="approved",
        merge_commit=" ", merge_revision=" ")
    assert result["status"] == "UNKNOWN"
    assert result["coverage_gaps"] == [
        "merge_commit_missing", "review_role_missing", "revision_missing"]
