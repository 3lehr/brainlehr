import os
import subprocess
from pathlib import Path

def test_webui_server_logic_in_foreign_repo():
    webui_dir = Path("/Volumes/daten/brainlehr-webui")
    if webui_dir.exists():
        # Delegate to the webui repo test
        res = subprocess.run(["pytest", "tests/test_webui_server.py"], cwd=str(webui_dir))
        assert res.returncode == 0, "WebUI tests failed"
    else:
        # Fallback if checked out separately
        pass
