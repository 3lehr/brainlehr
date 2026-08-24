import tempfile
import json
import sqlite3
from pathlib import Path

from knowledge_mcp_server import ensure_schema


def test_schema_initializes():
    with tempfile.NamedTemporaryFile(suffix=".sqlite") as file:
        db = sqlite3.connect(file.name)
        ensure_schema(db)
        assert db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='knowledge_nodes'").fetchone()


def test_shipped_mcp_templates_require_supported_python():
    root = Path(__file__).resolve().parents[1]
    assert json.loads((root / ".mcp.json").read_text())["mcpServers"]["brainlehr"]["command"] == "python3.11"
    assert 'command: "python3.11"' in (root / "integrations/hermes/config.template.yaml").read_text()
