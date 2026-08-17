import json, os, subprocess, sys, tempfile

def run(name, payload, env):
    return subprocess.run([sys.executable, f"integrations/claude/hooks/{name}.py"], input=json.dumps(payload), text=True, capture_output=True, check=True, env=env)

def test_capture_then_recall():
    with tempfile.TemporaryDirectory() as d:
        env={**os.environ,"BRAINLEHR_DB":os.path.join(d,"store.sqlite")}
        run("capture", {"learning":"Synthetic reusable practice"}, env)
        out=run("recall", {"prompt":"reusable"}, env)
        assert "Synthetic reusable practice" in json.loads(out.stdout)["additionalContext"]
