"""P63 local dashboard: loopback-only, provenance-only and revision-bound."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kern"))
import impact_dashboard  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, check=True, text=True,
                          capture_output=True).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "repo"; repo.mkdir()
    _git(repo, "init", "-q"); _git(repo, "config", "user.email", "test@example.invalid"); _git(repo, "config", "user.name", "test")
    (repo / "provider.py").write_text("VALUE=1\n", encoding="utf-8")
    (repo / "consumer.py").write_text("import provider\n", encoding="utf-8")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "provider.py").write_text("VALUE=2\n", encoding="utf-8")
    _git(repo, "add", "."); _git(repo, "commit", "-qm", "change")
    return repo, base


def test_dashboard_is_loopback_single_instance_and_mode_gated(tmp_path, monkeypatch):
    repo, base = _repo(tmp_path)
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_STATE_DIR", str(tmp_path / "state"))
    assert impact_dashboard.start_for_mode("knowledge", repo, base) is None
    try:
        impact_dashboard.ImpactDashboard(repo, base, host="0.0.0.0")
        assert False, "non-loopback must fail"
    except ValueError: pass
    first = impact_dashboard.start_for_mode("code", repo, base)
    assert first and first.host == "127.0.0.1" and first.state_path.is_file()
    try:
        impact_dashboard.start_for_mode("mixed", repo, base)
        assert False, "same project may have one live dashboard"
    except RuntimeError: pass
    first.shutdown()
    assert not first.state_path.exists()


def test_dashboard_state_is_debounced_revision_bound_and_has_real_history(tmp_path, monkeypatch):
    repo, base = _repo(tmp_path)
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_STATE_DIR", str(tmp_path / "state"))
    dashboard = impact_dashboard.ImpactDashboard(repo, base)
    state = dashboard.state()
    assert state["status"] == "current"
    assert state["graph"]["source_revision"] == _git(repo, "rev-parse", "HEAD")
    assert state["timeline"] and {row["source"] for row in state["timeline"]} == {"git"}
    assert all("subject" not in row and "reason" not in row for row in state["timeline"])
    assert dashboard.state(required_hash="old")["status"] == "stale"
    assert dashboard.state()["status"] == "current"
    selected = dashboard.state(revision=base)
    assert selected["comparison"]["current"] is False
    page = dashboard.timeline_page(100)
    assert page["status"] == "current" and page["timeline"] == []


def test_dashboard_refreshes_committed_graph_and_append_only_receipt(tmp_path, monkeypatch):
    repo, base = _repo(tmp_path)
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_STATE_DIR", str(tmp_path / "state"))
    dashboard = impact_dashboard.ImpactDashboard(repo, base)
    before = dashboard.state()
    (repo / "provider.py").write_text("VALUE=3\n", encoding="utf-8")
    _git(repo, "add", "provider.py"); _git(repo, "commit", "-qm", "refresh")
    receipt = {"base": _git(repo, "rev-parse", "HEAD^"), "tree_hash": "safe-tree",
               "observed_at": "2026-08-26T00:00:00+00:00"}
    (repo / ".brainlehr-commit-acks.jsonl").write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    after = dashboard.state()
    assert after["graph"]["source_revision"] != before["graph"]["source_revision"]
    assert after["graph"]["content_hash"] != before["graph"]["content_hash"]
    assert any(row["source"] == "commit_ack" for row in after["timeline"])


def test_dashboard_working_overlay_is_hash_bound_and_excludes_unowned(tmp_path, monkeypatch):
    repo, base = _repo(tmp_path)
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_STATE_DIR", str(tmp_path / "state"))
    (repo / "provider.py").write_text("VALUE=3\n", encoding="utf-8")
    (repo / "owned.py").write_text("VALUE=4\n", encoding="utf-8")
    (repo / "private.txt").write_text("never show\n", encoding="utf-8")
    monkeypatch.setenv("BRAINLEHR_AGENT_OWNED_UNTRACKED", "owned.py")
    state = impact_dashboard.ImpactDashboard(repo, base).state()
    overlay = state["working_overlay"]
    assert overlay and overlay["overlay_hash"] and "provider.py" in overlay["changed_files"]
    assert overlay["owned_untracked_files"] == ["owned.py"]
    assert "private.txt" not in overlay["changed_files"]
    assert state["graph"]["analyzer"] == "working-overlay-v1"


def test_dashboard_http_refresh_and_safe_html(tmp_path, monkeypatch):
    repo, base = _repo(tmp_path)
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_STATE_DIR", str(tmp_path / "state"))
    dashboard = impact_dashboard.ImpactDashboard(repo, base).start()
    thread = threading.Thread(target=dashboard.serve_forever, daemon=True); thread.start()
    try:
        url = f"http://127.0.0.1:{dashboard.port}"
        page = urllib.request.urlopen(url + "/", timeout=3).read().decode()
        assert "Project detail" in page and "Evidence inspector" in page and "Content-Security-Policy" in page and "raw code" not in page.lower()
        state = json.loads(urllib.request.urlopen(url + "/state", timeout=3).read())
        assert state["status"] == "current" and state["graph"]["content_hash"]
        try:
            urllib.request.urlopen(url + "/state?hash=stale", timeout=3)
            assert False, "stale request must fail"
        except urllib.error.HTTPError as error:
            assert error.code == 409
    finally:
        dashboard.shutdown(); thread.join(timeout=2)


def _post(url: str, payload: dict, *, origin: str = "", capability: str = ""):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    request.add_header("Content-Type", "application/json")
    if origin: request.add_header("Origin", origin)
    if capability: request.add_header("X-Brainlehr-Capability", capability)
    return urllib.request.urlopen(request, timeout=3)


def test_dashboard_portfolio_uses_explicit_allowlist_only(tmp_path, monkeypatch):
    repo, base = _repo(tmp_path)
    other_parent = tmp_path / "other"; other_parent.mkdir()
    other, _other_base = _repo(other_parent)
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_PROJECTS", str(other))
    dashboard = impact_dashboard.ImpactDashboard(repo, base)
    first = dashboard.state()
    assert len(first["portfolio"]) == 2
    other_id = next(row["id"] for row in first["portfolio"] if row["label"] == other.name)
    selected = dashboard.state(project_id=other_id)
    assert selected["project_id"] == other_id and selected["project_label"] == other.name
    with pytest.raises(ValueError): dashboard.state(project_id="not-allowlisted")


def test_feedback_is_same_origin_append_only_proposal_never_canonical_write(tmp_path, monkeypatch):
    repo, base = _repo(tmp_path)
    monkeypatch.setenv("BRAINLEHR_DASHBOARD_STATE_DIR", str(tmp_path / "state"))
    dashboard = impact_dashboard.ImpactDashboard(repo, base).start()
    thread = threading.Thread(target=dashboard.serve_forever, daemon=True); thread.start()
    try:
        url = f"http://127.0.0.1:{dashboard.port}"
        state = json.loads(urllib.request.urlopen(url + "/state", timeout=3).read())
        payload = {"project_id": state["project_id"], "action": "correction", "target_ref": "node-1",
                   "old_summary": "old claim", "new_summary": "new claim", "source_ref": "commit:abc",
                   "reason": "verified correction"}
        for origin, capability in (("", state["feedback_capability"]),
                                   ("http://localhost:1", state["feedback_capability"]),
                                   (url, "wrong")):
            with pytest.raises(urllib.error.HTTPError) as error:
                _post(url + "/feedback", payload, origin=origin, capability=capability)
            assert error.value.code == 403
        with pytest.raises(urllib.error.HTTPError) as error:
            _post(url + "/feedback", {**payload, "reason": "x" * 5000}, origin=url,
                  capability=state["feedback_capability"])
        assert error.value.code == 400
        with pytest.raises(urllib.error.HTTPError) as error:
            _post(url + "/feedback", {**payload, "tool": "knowledge_update"}, origin=url,
                  capability=state["feedback_capability"])
        assert error.value.code == 400
        response = _post(url + "/feedback", payload, origin=url, capability=state["feedback_capability"])
        result = json.loads(response.read())
        assert result["status"] == "pending_review" and result["effect"] == "no canonical write"
        assert result["mcp_handoff"] == "knowledge_update" and result["role_capability"] == "not_attested_by_dashboard"
        latest = json.loads(urllib.request.urlopen(url + "/state", timeout=3).read())
        assert any(row["source"] == "feedback_proposal" and row["status"] == "pending_review"
                   for row in latest["timeline"])
        assert not list(repo.glob("*.db"))
        assert dashboard._feedback_path(repo).is_file()
        persisted = impact_dashboard.ImpactDashboard(repo, base).state()
        assert any(row["source"] == "feedback_proposal" and row["status"] == "pending_review"
                   for row in persisted["timeline"])
    finally:
        dashboard.shutdown(); thread.join(timeout=2)
