import json

from kern.dependency_evidence import evidence, lock_delta, read_manifests


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


def test_locked_sbom_delta_has_hashes_consumers_and_no_network(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\ndependencies=['requests==2.31']\n[dependency-groups]\ntest=['pytest==8']\n",
        encoding="utf-8")
    (tmp_path / "uv.lock").write_text(
        "[[package]]\nname='brainlehr'\nversion='0'\n[[package]]\nname='requests'\nversion='2.31'\n",
        encoding="utf-8")
    sbom = tmp_path / "supply.spdx.json"
    sbom.write_text(json.dumps({"packages": [{"name": "requests", "versionInfo": "2.31",
                                                "licenseConcluded": "Apache-2.0"}]}), encoding="utf-8")
    current = read_manifests(tmp_path)
    candidate = [dict(node, version="2.32") if node["name"] == "requests" else node for node in current]
    result = evidence(tmp_path, current=current, candidate=candidate, sbom=sbom,
                      advisory={"status": "clean", "source": "osv-fixture", "network": "explicit"},
                      consumers={"requests": ["tests/test_client.py"]})
    assert result["network"] == "disabled"
    assert result["inputs"]["lock_sha256"] and result["inputs"]["sbom_sha256"]
    assert result["lock_nodes"] == [{"name": "requests", "version": "2.31", "scope": "transitive", "source": "uv.lock"}]
    assert result["sbom"] == [{"name": "requests", "version": "2.31", "license": "Apache-2.0", "source": "supply.spdx.json"}]
    assert result["consumers"] == {"requests": ["tests/test_client.py"]}
    assert result["rollback"] == {"required": True, "basis": "restore_previous_manifest"}


def test_pinned_lock_delta_binds_real_consumer_and_rollback(tmp_path):
    old = tmp_path / "old.uv.lock"
    new = tmp_path / "new.uv.lock"
    old.write_text("[[package]]\nname='pycrdt'\nversion='0.14.3'\n", encoding="utf-8")
    new.write_text("[[package]]\nname='pycrdt'\nversion='0.14.4'\n", encoding="utf-8")
    result = lock_delta(old, new, {"pycrdt": ["kern/dokument.py", "kern/teilnehmer.py"]})
    assert result["network"] == "disabled"
    assert result["changes"] == [{"name": "pycrdt", "from": "0.14.3", "to": "0.14.4",
                                   "consumers": ["kern/dokument.py", "kern/teilnehmer.py"]}]
    assert result["rollback"] == {"required": True, "command": "restore_previous_lock"}
    assert result["current"]["sha256"] and result["candidate"]["sha256"] and result["sha256"]
