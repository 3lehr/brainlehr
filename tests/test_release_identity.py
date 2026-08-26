from pathlib import Path

from kern.release_identity import identity


def test_identity_is_local_deterministic_and_fingerprints_artifact(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("fixture = '1'\n", encoding="utf-8")
    artifact = tmp_path / "fixture.whl"
    artifact.write_bytes(b"artifact")
    kwargs = dict(schema="s1", api="a1", event="e1", deploy="d1",
                  compatibility={"min": "s1", "max": "s2"},
                  canary={"percent": 5}, rollback={"strategy": "previous"})
    first = identity(tmp_path, artifact=artifact, **kwargs)
    second = identity(tmp_path, artifact=artifact, **kwargs)
    assert first == second
    assert first["artifact"]["sha256"]
    assert first["locks"] == ["uv.lock"]
    assert first["coverage_gaps"] == []
    assert first["identity"] == {"schema": "s1", "api": "a1", "event": "e1", "deploy": "d1"}


def test_missing_lock_is_explicit_gap_and_no_network(tmp_path: Path):
    result = identity(tmp_path)
    assert result["network"] == "disabled"
    assert "lockfile_missing" in result["coverage_gaps"]
    assert result["artifact"] is None
