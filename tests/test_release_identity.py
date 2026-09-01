from pathlib import Path

import subprocess

from kern.project_context import witness_envelope
from kern.release_identity import (artifact_manifest, as_evidence_witness, config_hash,
                                   deployment_gate, identity)


def _git_fixture(root: Path) -> tuple[str, str]:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "pyproject.toml"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=a@b", "-c", "user.name=a",
                    "commit", "-qm", "init"], check=True)
    revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    tree = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], text=True).strip()
    return revision, tree


def test_identity_is_local_deterministic_and_fingerprints_artifact(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("fixture = '1'\n", encoding="utf-8")
    artifact = tmp_path / "fixture.whl"
    artifact.write_bytes(b"artifact")
    sbom = tmp_path / "fixture.spdx.json"
    sbom.write_bytes(b'{"spdxVersion":"SPDX-2.3"}')
    kwargs = dict(schema="s1", api="a1", event="e1", deploy="d1",
                  compatibility={"min": "s1", "max": "s2"},
                  canary={"percent": 5}, rollback={"strategy": "previous"}, sbom=sbom,
                  signature={"status": "verified", "tool": "cosign"}, source_revision="abc123",
                  tool_versions={"build": "1.5"})
    first = identity(tmp_path, artifact=artifact, **kwargs)
    second = identity(tmp_path, artifact=artifact, **kwargs)
    assert first == second
    assert first["artifact"]["sha256"]
    assert first["locks"] == [{"path": "uv.lock", "sha256": first["locks"][0]["sha256"]}]
    assert first["coverage_gaps"] == []
    assert first["identity"] == {"schema": "s1", "api": "a1", "event": "e1", "deploy": "d1"}
    assert first["sbom"]["sha256"]
    assert first["provenance"]["source_revision"] == "abc123"


def test_missing_lock_is_explicit_gap_and_no_network(tmp_path: Path):
    result = identity(tmp_path)
    assert result["network"] == "disabled"
    assert "lockfile_missing" in result["coverage_gaps"]
    assert "signature_unverified" in result["coverage_gaps"]
    assert result["artifact"] is None


def test_incompatible_schema_blocks_canary_until_rollback_is_declared():
    current = {"schema": "1", "api": "1", "event": "1", "deploy": "blue"}
    candidate = {"schema": "2", "api": "1", "event": "1", "deploy": "green"}
    blocked = deployment_gate(current=current, candidate=candidate,
                              compatibility={"supported": {"schema": ["1"]}},
                              canary={"id": "canary-1", "result": "failed"}, rollback={})
    assert blocked["allowed"] is False
    assert blocked["coverage_gaps"] == ["incompatible_schema", "compatibility_missing_deploy", "rollback_missing"]
    rolled_back = deployment_gate(current=current, candidate=candidate,
                                  compatibility={"supported": {"schema": ["1", "2"], "api": ["1"], "event": ["1"], "deploy": ["blue", "green"]}},
                                  canary={"id": "canary-1", "result": "failed"},
                                  rollback={"strategy": "restore-previous-artifact", "result": "restored"})
    assert rolled_back["allowed"] is True


def test_artifact_manifest_binds_clean_source_variant_and_p98_witness(tmp_path: Path):
    revision, tree = _git_fixture(tmp_path)
    artifact = tmp_path.parent / "fixture-clean.whl"
    artifact.write_bytes(b"artifact")
    digest = __import__("hashlib").sha256(b"artifact").hexdigest()
    manifest = artifact_manifest(tmp_path, artifact=artifact, revision=revision, tree_hash=tree,
                                 config_sha256=config_hash(tmp_path), build_command=["build", "--wheel"],
                                 variant="release", launched_artifact_sha256=digest, launched_revision=revision)
    assert manifest["status"] == "PASS" and str(tmp_path) not in str(manifest)
    witness = as_evidence_witness(manifest, witness_id="w-p81", requirement_ids=["P81"],
                                  independence_group="build", lineage_id="fixture-release")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"pass": 1}


def test_artifact_manifest_rejects_tamper_dirty_source_and_variant_mismatch(tmp_path: Path):
    revision, tree = _git_fixture(tmp_path)
    artifact = tmp_path.parent / "fixture-tampered.whl"
    artifact.write_bytes(b"artifact")
    original = __import__("hashlib").sha256(b"artifact").hexdigest()
    original_config = config_hash(tmp_path)
    artifact.write_bytes(b"tampered")
    bad = artifact_manifest(tmp_path, artifact=artifact, revision=revision, tree_hash=tree,
                            config_sha256=config_hash(tmp_path), build_command=["build"], variant="debug",
                            launched_artifact_sha256=original, launched_revision=revision)
    assert "launched_artifact_mismatch" in bad["coverage_gaps"]
    (tmp_path / "pyproject.toml").write_text("changed", encoding="utf-8")
    dirty = artifact_manifest(tmp_path, artifact=artifact, revision=revision, tree_hash=tree,
                              config_sha256=original_config, build_command=["build"], variant="release")
    assert {"dirty_source", "config_hash_mismatch", "launched_identity_unobserved"} <= set(dirty["coverage_gaps"])


def test_artifact_manifest_keeps_variants_as_separate_subjects(tmp_path: Path):
    revision, tree = _git_fixture(tmp_path)
    rows = []
    for variant, payload in (("debug", b"debug"), ("release", b"release")):
        artifact = tmp_path.parent / f"fixture-{variant}.whl"
        artifact.write_bytes(payload)
        digest = __import__("hashlib").sha256(payload).hexdigest()
        rows.append(artifact_manifest(tmp_path, artifact=artifact, revision=revision, tree_hash=tree,
                                      config_sha256=config_hash(tmp_path), build_command=["build", variant],
                                      variant=variant, launched_artifact_sha256=digest, launched_revision=revision))
    assert [row["subject"]["variant"] for row in rows] == ["debug", "release"]
    assert rows[0]["subject"]["artifact_sha256"] != rows[1]["subject"]["artifact_sha256"]
