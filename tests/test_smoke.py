import tempfile
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from knowledge_mcp_server import ensure_schema
from haken.ort import _ermittle_db


def test_schema_initializes():
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as file:
        db = sqlite3.connect(file.name)
        ensure_schema(db)
        assert db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge_nodes'").fetchone()


def test_shipped_mcp_templates_require_supported_python():
    root = Path(__file__).resolve().parents[1]
    assert json.loads((root / ".mcp.json").read_text())["mcpServers"]["brainlehr"]["command"] == "python3.11"
    assert 'command: "python3.11"' in (root / "integrations/hermes/config.template.yaml").read_text()


def test_legacy_db_remains_a_fallback_without_forced_rename(tmp_path, capsys):
    legacy = tmp_path / "knowledge.db"
    legacy.touch()
    assert _ermittle_db(tmp_path, None, None) == legacy
    assert "Legacy-Fallback" in capsys.readouterr().err


def test_mcp_starts_without_fcntl():
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys\n"
            "sys.modules['fcntl'] = None\n"
            "import knowledge_mcp_server as server\n"
            "assert server.fcntl is None\n"
            "with server._write_lock(): pass\n",
        ],
        cwd=root,
        check=True,
    )
