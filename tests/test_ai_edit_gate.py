from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from kern.ai_edit_gate import build_manifest, validate_manifest
from kern.anchor_registry import Anchor, AnchorRegistry


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> tuple[Path, AnchorRegistry, str]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "app.py").write_text("# human note\nVALUE = 1\n", encoding="utf-8")
    _git(root, "add", "app.py")
    _git(root, "commit", "-qm", "base")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                              check=True, capture_output=True, text=True).stdout.strip()
    registry = AnchorRegistry.empty(revision).register(
        Anchor.create("src:app", revision, "P99", ()))
    return root, registry, revision


def _manifest(repo: Path, registry: AnchorRegistry, revision: str) -> dict:
    return build_manifest(repo, registry=registry, accepted_anchor_ids=["src:app"],
                          base_revision=revision)


def test_ai_owned_flow_returns_hash_only_and_binds_staged_content(repo):
    root, registry, revision = repo
    (root / "app.py").write_text(
        '# human note\n# brainlehr:link {"anchor_id":"src:app","revision":"%s"}\nVALUE = 2\n'
        % revision, encoding="utf-8")
    _git(root, "add", "app.py")
    manifest = _manifest(root, registry, revision)
    result = validate_manifest(manifest, root, registry=registry)
    assert result["status"] == "PASS"
    assert set(result) == {"status", "receipt_sha256"}
    assert re.fullmatch(r"[0-9a-f]{64}", result["receipt_sha256"])


@pytest.mark.parametrize("bad", [
    ("# freeform AI explanation\n", None),
    ('# brainlehr:link {"anchor_id":"invented","revision":"%s"}\n', "revision"),
    ('# brainlehr:link {"anchor_id":"src:app","revision":"%s"}\n', "stale"),
])
def test_ai_owned_flow_rejects_invalid_or_stale_comments(repo, bad):
    root, registry, revision = repo
    template, kind = bad
    text = template % ("b" * 40 if kind == "stale" else revision) if "%s" in template else template
    (root / "app.py").write_text(text + "VALUE = 2\n", encoding="utf-8")
    _git(root, "add", "app.py")
    manifest = _manifest(root, registry, revision)
    with pytest.raises(ValueError):
        validate_manifest(manifest, root, registry=registry)


def test_human_comment_change_is_rejected_but_unmarked_human_flow_is_unchanged(repo):
    root, registry, revision = repo
    (root / "app.py").write_text("# human changed\nVALUE = 2\n", encoding="utf-8")
    _git(root, "add", "app.py")
    manifest = _manifest(root, registry, revision)
    manifest["human_comment_inventory_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="human comment"):
        validate_manifest(manifest, root, registry=registry)

    # Generic, non-AI-owned operation remains outside this gate.
    assert validate_manifest(None, root, registry=registry) == {"status": "bypass"}


def test_manifest_is_strict_and_rejects_secret_or_self_proof_fields(repo):
    root, registry, revision = repo
    (root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    _git(root, "add", "app.py")
    manifest = _manifest(root, registry, revision)
    for key, value in (("secret", "do-not-copy"), ("self_proof", True), ("evidence", "PASS")):
        candidate = json.loads(json.dumps(manifest))
        candidate[key] = value
        with pytest.raises(ValueError):
            validate_manifest(candidate, root, registry=registry)
