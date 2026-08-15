"""Rot-vor-gruen fuer haken/stash_guard_hook.py.

ANLASS: `git stash` wurde heute (2026-08-15) fuenfmal trotz Verbot in
CLAUDE.md aufgerufen -- eine Formulierung loest das nicht, es braucht eine
Stelle, an der der Aufruf SCHEITERT. Dieser Test ruft die Wache genauso auf,
wie PreToolUse sie aufruft (JSON auf stdin), und prueft beide Richtungen:
gefaehrliche Formen werden abgelehnt, harmlose durchgelassen.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "haken" / "stash_guard_hook.py"


def _run(command: str, env: dict | None = None) -> dict:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout.strip()
    return json.loads(out) if out else {}


def _denied(result: dict) -> bool:
    return (
        result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    )


def test_bare_stash_wird_abgelehnt():
    assert _denied(_run("git stash"))


def test_stash_push_wird_abgelehnt():
    assert _denied(_run("git stash push -m 'wip'"))


def test_stash_save_wird_abgelehnt():
    assert _denied(_run("git stash save"))


def test_stash_dash_u_wird_abgelehnt():
    assert _denied(_run("git stash -u"))


def test_stash_pop_wird_abgelehnt():
    assert _denied(_run("git stash pop"))


def test_stash_apply_wird_abgelehnt():
    assert _denied(_run("git stash apply"))


def test_ablehnung_nennt_ersatzweg():
    result = _run("git stash")
    grund = result["hookSpecificOutput"]["permissionDecisionReason"]
    assert "git show HEAD:" in grund
    assert "git checkout HEAD --" in grund


def test_verkette_befehl_wird_erkannt():
    assert _denied(_run("cd /tmp && git stash"))


def test_fuehrende_leerzeichen_werden_erkannt():
    assert _denied(_run("   git stash"))


def test_stash_list_wird_erlaubt():
    result = _run("git stash list")
    assert not _denied(result)


def test_stash_show_wird_erlaubt():
    result = _run("git stash show -p")
    assert not _denied(result)


def test_gewoehnlicher_status_wird_nicht_behindert():
    assert not _denied(_run("git status"))


def test_gewoehnlicher_commit_wird_nicht_behindert():
    assert not _denied(_run("git commit -m 'x' -- datei.py"))


def test_echo_mit_dem_wort_stash_wird_nicht_blockiert():
    assert not _denied(_run('echo "git stash"'))


def test_grep_nach_stash_wird_nicht_blockiert():
    assert not _denied(_run("grep -r 'git stash' ."))


def test_kein_bash_aufruf_laesst_durch():
    payload = {"tool_name": "Read", "tool_input": {"file_path": "x"}}
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_marker_override_erlaubt_einmalig():
    # Pfad wie MARKER in haken/stash_guard_hook.py -- bewusst woertlich,
    # nicht ueber tempfile.gettempdir() (das liefert auf macOS einen
    # anderen Pfad als das feste "/tmp/...", das die Wache tatsaechlich prueft).
    marker = Path("/tmp/claude-stash-guard-allow")
    marker.write_text("")
    try:
        assert not _denied(_run("git stash"))
        # Marker ist danach verbraucht -- zweiter Aufruf wird wieder abgelehnt.
        assert _denied(_run("git stash"))
    finally:
        marker.unlink(missing_ok=True)


def test_env_off_schaltet_die_wache_dauerhaft_ab():
    import os

    env = dict(os.environ, STASH_GUARD="off")
    assert not _denied(_run("git stash", env=env))
