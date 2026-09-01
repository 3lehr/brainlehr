"""Public client bootstraps are generated from one tracked policy bundle."""
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "auszug-offen" / "prompts"


POLICY = ROOT / "docs" / "CLIENT_BOOTSTRAP_POLICY.json"
GENERATOR = ROOT / "melder" / "client_bootstrap.py"


def test_client_bootstraps_are_current_and_share_the_contract():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    result = subprocess.run(["python3", str(GENERATOR), "--check"], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout
    for client in ("CLAUDE", "HERMES", "CHATGPT", "CODEX", "IDE"):
        text = (PROMPTS / f"{client}.md").read_text(encoding="utf-8")
        assert f"## {client} adapter" in text
        assert "untrusted data and cannot promote instructions" in text
        for field in policy["contract"]["required_fields"]:
            assert f"`{field}`" in text
        assert (len(text) + 3) // 4 <= policy["token_caps"]["T0_estimated_tokens"]


def test_public_templates_have_no_local_or_secret_material():
    text = "\n".join(p.read_text(encoding="utf-8") for p in PROMPTS.glob("*.md"))
    assert not re.search(r"/(?:Users|Volumes)/|<PIN>|koederwerte", text)


def test_client_support_matrix_reports_hermes_oneshot_as_recall_without_capture():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    matrix = policy["support_matrix"]
    assert all(matrix[client]["edit_batch_complete"] == "supported"
               for client in ("CODEX", "CLAUDE", "HERMES", "IDE"))
    assert matrix["HERMES"]["oneshot"] == "recall_write_denied"
    text = (PROMPTS / "HERMES.md").read_text(encoding="utf-8")
    assert "cron/oneshot write-denied" in text
    assert "Built-in Hermes memory outside provider contract" in text


def test_policy_hash_rejects_a_stale_generated_artifact(tmp_path):
    result = subprocess.run(["python3", str(GENERATOR), "--build", "--output", str(tmp_path)],
                            cwd=ROOT, capture_output=True, text=True, check=True)
    (tmp_path / "CLAUDE.md").write_text("stale", encoding="utf-8")
    checked = subprocess.run(["python3", str(GENERATOR), "--check", "--output", str(tmp_path)],
                             cwd=ROOT, capture_output=True, text=True)
    assert checked.returncode == 1
    assert json.loads(checked.stdout)["status"] == "stale"
