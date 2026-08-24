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
                response = json.loads(process.stdout.readline())
                assert response["id"] == request["id"]
                if request["id"] == 2:
                    assert {"knowledge_add", "prompt_invarianz_planen"} <= {tool["name"] for tool in response["result"]["tools"]}
        finally:
            process.terminate(); process.wait(timeout=5)


def test_prompt_only_profile_is_default_deny():
    with tempfile.TemporaryDirectory() as directory:
        env = {**os.environ, "BRAINLEHR_DB": os.path.join(directory, "store.sqlite"), "BEGOD_KNOWLEDGE_PROFIL":"prompt-invariance"}
        process = subprocess.Popen([sys.executable, "knowledge_mcp_server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
        try:
            requests = (
                {"jsonrpc":"2.0","id":1,"method":"tools/list"},
                {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"prompt_invarianz_planen","arguments":{"task_type":"rangfolge","security":True}}},
                {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"knowledge_search","arguments":{"query":"x"}}},
            )
            responses = []
            for request in requests:
                process.stdin.write(json.dumps(request) + "\n"); process.stdin.flush()
                responses.append(json.loads(process.stdout.readline()))
            assert [tool["name"] for tool in responses[0]["result"]["tools"]] == ["prompt_invarianz_planen", "prompt_invarianz_pruefen"]
            assert json.loads(responses[1]["result"]["content"][0]["text"])["profile"] == "strong"
            assert responses[2]["result"]["isError"] is True
            assert json.loads(responses[2]["result"]["content"][0]["text"])["grund"] == "profil:prompt-invariance"
        finally:
            process.terminate(); process.wait(timeout=5)
