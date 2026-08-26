from kern.dependency_evidence import evidence, read_manifests


def test_local_manifests_become_scoped_sorted_nodes():
    nodes = read_manifests("tests/fixtures/dependency_slice")
    assert [(n["name"], n["version"], n["scope"]) for n in nodes] == [
        ("numpy", "1.26.4", "runtime"), ("pytest", "8", "test"),
        ("requests", "2.31", "runtime"), ("ruff", "0.6.9", "runtime")]


def test_evidence_is_deterministic_and_delta_has_rollback_metadata():
    current = read_manifests("tests/fixtures/dependency_slice")
    candidate = [dict(node, version="2.32" if node["name"] == "requests" else node["version"])
                 for node in current]
    result = evidence("tests/fixtures/dependency_slice", current=current, candidate=candidate)
    assert result["network"] == "disabled"
    assert result["delta"] == [{"name": "requests", "scope": "runtime", "from": "2.31", "to": "2.32"}]
    assert result["rollback"]["required"] is True
    assert result["sha256"] == evidence("tests/fixtures/dependency_slice", current=current, candidate=candidate)["sha256"]
