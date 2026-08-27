"""The opt-in AI-edit boundary must ship as one explicit archive unit."""
from __future__ import annotations

import pathlib
import tarfile
import tomllib
import zipfile

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = (
    "kern/ai_comment_policy.py", "kern/ai_edit_gate.py",
    "tool/ai_edit_gate.py", "tool/ai_project_boundary.py",
    "docs/CLIENT_BOOTSTRAP_POLICY.json", "melder/client_bootstrap.py",
)


def test_manifest_boundary_is_explicit_in_both_package_lists():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    build = config["tool"]["hatch"]["build"]
    assert set(build["targets"]["sdist"]["only-include"]) == set(build["targets"]["wheel"]["force-include"])
    assert all(path in build["targets"]["wheel"]["force-include"] for path in REQUIRED)


@pytest.mark.skipif(__import__("importlib.util", fromlist=["util"]).find_spec("hatchling") is None,
                    reason="hatchling unavailable")
def test_manifest_boundary_is_in_wheel_and_sdist(tmp_path):
    from hatchling.builders.sdist import SdistBuilder
    from hatchling.builders.wheel import WheelBuilder

    wheel = next(iter(WheelBuilder(str(ROOT)).build(directory=str(tmp_path))))
    sdist = next(iter(SdistBuilder(str(ROOT)).build(directory=str(tmp_path))))
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
    with tarfile.open(sdist) as archive:
        sdist_names = archive.getnames()
    for path in REQUIRED:
        assert any(name.endswith(path) for name in wheel_names)
        assert any(name.endswith(path) for name in sdist_names)
