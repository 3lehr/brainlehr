from kern import analyzer_registry


def test_registry_marks_missing_runner_as_explicit_gap(monkeypatch):
    monkeypatch.setattr(analyzer_registry, "executable", lambda _kind: None)
    result = analyzer_registry.run("joern", ["fixture"], revision="r1")
    assert result["status"] == "coverage_gap"
    assert "unavailable" in result["coverage_gaps"][0]


def test_registry_runs_explicit_local_version_command():
    result = analyzer_registry.run("tree_sitter", ["--version"], revision="r1")
    assert result["status"] == "completed"
    assert "stdout" not in result and "stderr" not in result
    assert len(result["output"]["stdout_sha256"]) == 64
    assert result["sandbox"]["environment"] == "allowlist"
    assert result["coverage_gaps"] == ["network isolation is not enforced by this host"]
