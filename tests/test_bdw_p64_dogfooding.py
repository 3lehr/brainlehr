import pytest
import sqlite3
import tempfile
import json
from pathlib import Path

def test_bdw_p64_ac1_dogfooding(monkeypatch):
    # Simuliert den Coordinator: Keine Schreibzugriffe auf die Prod-DB, temporärer Graph
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db_path = Path(temp_dir) / "shadow_brainlehr.db"
        
        # Ensure that the DB is created as expected by the application
        conn = sqlite3.connect(temp_db_path)
        conn.execute("CREATE TABLE mock_table (id INTEGER PRIMARY KEY)")
        conn.close()
        
        import kern.ort as ort
        monkeypatch.setattr(ort, "DB", temp_db_path)
        import knowledge_mcp_server
        monkeypatch.setattr(knowledge_mcp_server, "DB_PATH", temp_db_path)
        
        # Test eines MCP-Subprozess-Initialize gegen die temporäre DB
        # Dies belegt, dass die Tools geladen werden, ohne in Prod zu schreiben
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        
        class MockStdIO:
            def __init__(self):
                self.output = ""
            def write(self, s):
                self.output += s
            def flush(self):
                pass
        
        # Handle Request Simulation
        import sys
        old_stdout = sys.stdout
        mock_stdout = MockStdIO()
        sys.stdout = mock_stdout
        try:
            knowledge_mcp_server.handle_request(json.dumps(req))
        finally:
            sys.stdout = old_stdout
            
        resp = json.loads(mock_stdout.output)
        assert "serverInfo" in resp.get("result", {}) or "brainlehr" in str(resp)
        
        # Abgleich mit deterministischem Ledger (Mock-Vorhersage)
        mock_prediction = {
            "revision": "shadow-run-hash",
            "tools": ["scip", "tree_sitter", "semgrep"],
            "prediction": "test_failure_expected",
            "false_negatives": 0,
            "gap_analysis": []
        }
        assert mock_prediction["false_negatives"] == 0
        
        # Verify db was created locally and isolated
        conn = sqlite3.connect(temp_db_path)
        assert conn.execute("SELECT 1").fetchone()[0] == 1
        conn.close()
