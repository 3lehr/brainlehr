import json
import os
import subprocess
import sys
import tempfile


def test_stdio_lifecycle():
    with tempfile.TemporaryDirectory() as directory:
        env = {**os.environ, "BRAINLEHR_DB": os.path.join(directory, "store.sqlite")}
        process = subprocess.Popen([sys.executable, "knowledge_mcp_server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        try:
            for request in ({"jsonrpc":"2.0","id":1,"method":"initialize"}, {"jsonrpc":"2.0","id":2,"method":"tools/list"}, {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"knowledge_add","arguments":{"title":"Synthetic","summary":"Synthetic"}}}):
                process.stdin.write(json.dumps(request) + "\n"); process.stdin.flush()
                assert json.loads(process.stdout.readline())["id"] == request["id"]
        finally:
            process.terminate(); process.wait(timeout=5)
