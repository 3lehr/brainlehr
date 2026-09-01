from kern.project_context import witness_envelope
from kern.release_distribution_provenance import as_evidence_witness, distribution_provenance


ARTIFACT = "a" * 64


def test_distribution_channels_remain_distinct_and_project_to_p98():
    results = [distribution_provenance(
        artifact_sha256=ARTIFACT, target=f"{channel}-target",
        published_revision="r1", release_revision="r1", channel=channel)
        for channel in ("local", "private", "public")]
    assert [result["status"] for result in results] == ["PASS", "PASS", "PASS"]
    assert [result["distribution"]["channel"] for result in results] == [
        "local", "private", "public"]
    assert len({result["provenance_sha256"] for result in results}) == 3
    witness = as_evidence_witness(results[1], witness_id="p84-private")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_distribution_missing_or_mismatched_evidence_never_claims_publish():
    missing = distribution_provenance(
        artifact_sha256=None, target=None, published_revision="r1",
        release_revision="r1", channel="public")
    assert missing["status"] == "UNKNOWN"
    assert missing["coverage_gaps"] == [
        "artifact_evidence_missing", "distribution_target_missing"]
    assert "published" not in missing
    mismatch = distribution_provenance(
        artifact_sha256=ARTIFACT, target="private-target", published_revision="r2",
        release_revision="r1", channel="private")
    assert mismatch["status"] == "FAIL"


def test_distribution_rejects_blank_target_and_revisions():
    result = distribution_provenance(
        artifact_sha256=ARTIFACT, target=" ", published_revision=" ",
        release_revision=" ", channel="local")
    assert result["status"] == "UNKNOWN"
    assert result["coverage_gaps"] == [
        "distribution_target_missing", "published_revision_missing",
        "release_revision_missing"]
