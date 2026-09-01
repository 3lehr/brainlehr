import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_joern_runner_redacts_code_and_binds_revision():
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    result = subprocess.run(["python3", "tool/joern_cpg.py", "--source",
                             "tests/fixtures/evidence_adapters/joern_cpg_input.c", "--revision", revision],
                            cwd=ROOT, capture_output=True, text=True, timeout=30, check=True)
    record = json.loads(result.stdout)
    assert record["revision"] == revision and record["nodes"] and record["edges"]
    assert "CODE" not in result.stdout and "secret" not in result.stdout.lower()
    assert record["sandbox"]["network"] == "sandbox-exec deny network"
    assert record["coverage_gaps"] == ["sandbox-exec profile permits host filesystem paths required by JVM"]


def test_joern_sandbox_profile_denies_a_socket_probe():
    probe = "import socket; socket.create_connection(('127.0.0.1', 9), timeout=1)"
    result = subprocess.run(["/usr/bin/sandbox-exec", "-p", "(version 1) (allow default) (deny network*)",
                             "python3", "-c", probe], capture_output=True, text=True, timeout=5)
    assert result.returncode != 0
