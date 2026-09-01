import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parent / "fixtures" / "multilingual_code"
MANIFEST = json.loads((ROOT / "manifest.json").read_text())


@pytest.mark.parametrize("fixture", MANIFEST["fixtures"], ids=lambda item: item["language"])
def test_multilingual_fixture_is_parseable_and_has_three_symbols(fixture, tmp_path):
    path = ROOT / fixture["file"]
    text = path.read_text()
    assert len(fixture["symbols"]) == 3
    assert all(symbol in text for symbol in fixture["symbols"])
    command = fixture["parser_command"].split()
    if not shutil.which(command[0]):
        pytest.skip(f"{command[0]} unavailable")
    if fixture["language"] == "typescript":
        run = command + [str(path)]
    elif fixture["language"] == "rust":
        run = command + [str(path), "-o", str(tmp_path / "rust_fixture")]
    elif fixture["language"] == "java":
        run = command + ["-d", str(tmp_path), str(path)]
    elif fixture["language"] == "go":
        run = command + ["-o", str(tmp_path / "go_fixture"), str(path)]
    elif fixture["language"] == "swift":
        run = command + [str(path), "-o", str(tmp_path / "swift_fixture")]
    elif fixture["language"] == "dart":
        run = command + [str(path)]
    else:
        run = command + [str(path)]
    env = os.environ.copy()
    # Host TMPDIR may point at a removed volume directory.  Compilers need a
    # writable temporary directory; keep all outputs inside pytest's fixture.
    for name in ("TMPDIR", "TMP", "TEMP"):
        env[name] = str(tmp_path)
    if fixture["language"] == "python":
        env["PYTHONPYCACHEPREFIX"] = str(tmp_path / "pycache")
    result = subprocess.run(run, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
