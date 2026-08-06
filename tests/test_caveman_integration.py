"""TDD-Tests fuer Caveman-Integration (Begod2026)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "begod/scripts"
sys.path.insert(0, str(SCRIPTS))

import caveman_compress as cc  # type: ignore  # noqa: E402


@pytest.fixture(scope="module")
def policy() -> cc.Policy:
    return cc.load_policy()


# --- Policy ---------------------------------------------------------------

def test_policy_file_exists():
    assert cc.POLICY_PATH.exists(), "caveman_policy.json fehlt"


def test_policy_loads_and_is_valid_json(policy: cc.Policy):
    errors = cc.validate_policy(policy)
    assert errors == [], f"Policy ungueltig: {errors}"


def test_policy_has_required_principles(policy: cc.Policy):
    principles = " ".join(policy.raw.get("principles", []))
    assert "P-CM-1" in principles
    assert "P-CM-2" in principles
    assert "Original IMMER" in principles


def test_policy_denies_legal_paths(policy: cc.Policy):
    for path in [
        "begod/knowledge/legal/dsgvo.md",
        "docs/recht/urteil-bvg-2024.md",
        "infra/din/normen-uebersicht.md",
        "begod/knowledge/apps/akademia/VERFASSUNG.md",
        "begod/SYSTEM_PROTOCOLS.md",
        ".github/copilot-instructions.md",
        "begod/agents/jesus-guide.agent.md",
        "begod/knowledge/konsil/konsil-2026-04-29.json",
        "begod/knowledge/meta/schema.json",
    ]:
        denied, pat = policy.is_denied(path)
        assert denied, f"Pfad sollte denied sein: {path}"
        assert pat


def test_policy_allows_session_handoffs(policy: cc.Policy):
    for path in [
        "docs/sessions/akademia/2026-04-29-handoff.md",
        "X-postfach/eingang/research-2026-04-29.md",
        "_ANALYSE/BESTANDSAUFNAHME_BERICHT.md",
        "CAVEMAN_INTEGRATION_BERICHT.md",
    ]:
        denied, _ = policy.is_denied(path)
        assert not denied, f"Pfad sollte erlaubt sein: {path}"


def test_policy_disables_wenyan(policy: cc.Policy):
    assert "VERBOTEN" in policy.raw["modes"]["wenyan"]


def test_policy_default_intensity_is_lite(policy: cc.Policy):
    assert policy.raw.get("intensity_default") == "lite"


def test_policy_is_opt_out(policy: cc.Policy):
    assert policy.raw.get("activation_default") == "on"
    assert policy.raw.get("activation_mode") == "opt-out"


def test_policy_has_format_preference(policy: cc.Policy):
    fmt = policy.raw.get("file_format_preference", {})
    assert fmt.get("knowledge_prose") == "md"
    assert fmt.get("structured_records") == "json-min"


def test_reasoning_models_default_off(policy: cc.Policy):
    overrides = policy.raw.get("model_overrides", {})
    assert overrides.get("claude-opus-4.7", {}).get("default_intensity") == "off"
    assert overrides.get("o3", {}).get("default_intensity") == "off"


# --- Kompression: Schutzregionen -----------------------------------------

def test_code_blocks_preserved():
    text = "Run the test now.\n\n```python\nx = a + b  # the sum\n```\n"
    out, stats = cc.compress_text(text, level="full")
    assert "```python\nx = a + b  # the sum\n```" in out
    assert stats["ratio"] >= 0


def test_inline_code_preserved():
    text = "Use the `useMemo` hook to avoid the re-render."
    out, _ = cc.compress_text(text, level="full")
    assert "`useMemo`" in out


def test_urls_preserved():
    text = "See https://example.com/path?q=1 for the details."
    out, _ = cc.compress_text(text, level="full")
    assert "https://example.com/path?q=1" in out


def test_paths_preserved():
    text = "Edit the file ./begod/scripts/nav_lookup.py and the config."
    out, _ = cc.compress_text(text, level="full")
    assert "./begod/scripts/nav_lookup.py" in out


# --- Kompression: Recht/Norm-Schutz --------------------------------------

@pytest.mark.parametrize("legal_text", [
    "Gemaess Art. 6 DSGVO ist die Verarbeitung rechtmaessig.",
    "BGB \xc2\xa7 433 regelt den Kaufvertrag.",
    "DIN EN ISO 9001 fordert dokumentierte Prozesse.",
    "BVerfG, Beschluss vom 12.03.2024, Az. 1 BvR 123/24.",
    "SGB V regelt die gesetzliche Krankenversicherung.",
])
def test_legal_content_skipped(legal_text: str):
    out, stats = cc.compress_text(legal_text, level="full")
    assert stats.get("skipped") is True
    assert stats.get("reason") == "legal_content_detected"
    assert out == legal_text


# --- Kompression: Filler-/Pleasantry-Removal ------------------------------

def test_filler_removed():
    text = "This is just really basically a simple test."
    out, _ = cc.compress_text(text, level="lite")
    assert "just" not in out.lower()
    assert "really" not in out.lower()
    assert "basically" not in out.lower()


def test_german_filler_removed():
    text = "Das ist eigentlich grundsaetzlich nur eine kleine Aenderung."
    out, _ = cc.compress_text(text, level="lite")
    assert "eigentlich" not in out.lower()
    assert "grundsaetzlich" not in out.lower()


def test_pleasantry_removed():
    text = "Sure! I'd be happy to help with that.\nThe issue is X."
    out, _ = cc.compress_text(text, level="lite")
    assert not out.lower().startswith("sure")


def test_compression_ratio_lite_at_least_some():
    text = (
        "This is just basically really a fairly simple example. "
        "It would be good to make sure to consider the implications. "
        "In order to verify, you could really just run the test."
    )
    out, stats = cc.compress_text(text, level="lite")
    assert stats["ratio"] > 0.05, f"Mindestens 5% Reduktion erwartet, war {stats['ratio']}"
    assert len(out) < len(text)


def test_full_drops_articles():
    text = "The user opens a connection to the database."
    out, _ = cc.compress_text(text, level="full")
    assert " the " not in out.lower()
    assert " a " not in out.lower()


def test_invalid_level_raises():
    with pytest.raises(ValueError):
        cc.compress_text("text", level="ultra")
    with pytest.raises(ValueError):
        cc.compress_text("text", level="wenyan")


# --- CLI-Integration ------------------------------------------------------

def test_cli_status_runs(capsys):
    rc = cc.main(["--status"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["wenyan_enabled"] is False


def test_cli_policy_test_passes(capsys):
    rc = cc.main(["--policy-test"])
    assert rc == 0


def test_cli_blocks_denied_path(tmp_path: Path, monkeypatch, capsys):
    # Datei in einem denied-Pfad simulieren
    legal = REPO_ROOT / "begod/knowledge/legal"
    legal.mkdir(parents=True, exist_ok=True)
    target = legal / "_test_caveman_block.md"
    target.write_text("Some prose here.\n", encoding="utf-8")
    try:
        rc = cc.main([str(target)])
        assert rc == 2
    finally:
        if target.exists():
            target.unlink()


def test_cli_compress_and_restore(tmp_path: Path):
    # Allowlist-Pfad nutzen: docs/sessions
    sessions = REPO_ROOT / "docs/sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    target = sessions / "_test_caveman_compress.md"
    original_text = (
        "# Session Notes\n\n"
        "This is just basically a really simple session note. "
        "It would be good to make sure to verify the assumptions.\n"
    )
    target.write_text(original_text, encoding="utf-8")
    backup = target.with_name(target.stem + ".original.md")
    try:
        rc = cc.main([str(target), "--level", "lite"])
        assert rc == 0
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == original_text
        new_content = target.read_text(encoding="utf-8")
        assert len(new_content) < len(original_text)

        rc2 = cc.main([str(target), "--restore"])
        assert rc2 == 0
        assert target.read_text(encoding="utf-8") == original_text
    finally:
        if target.exists():
            target.unlink()
        if backup.exists():
            backup.unlink()


# --- Instructions/Prompt-Files Smoke -------------------------------------

def test_caveman_instructions_exists():
    p = REPO_ROOT / ".github/instructions/caveman.instructions.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "OPT-IN" in text
    assert "Wenyan" in text and "DEAKTIVIERT" in text
    assert "DSGVO" in text


def test_caveman_prompt_exists():
    p = REPO_ROOT / ".github/prompts/caveman.prompt.md"
    assert p.exists()
