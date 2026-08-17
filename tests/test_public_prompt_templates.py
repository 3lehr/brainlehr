"""Public Claude/Hermes templates share one immutable prompt contract."""
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "auszug-offen" / "prompts"


def _shared(text: str) -> str:
    match = re.search(r"## Shared rules\n\n(.*?)\n## ", text, re.S)
    assert match, "template lacks the shared rules block"
    return match.group(1)


def test_claude_and_hermes_share_exact_prompt_rules():
    claude = (PROMPTS / "CLAUDE.md").read_text(encoding="utf-8")
    hermes = (PROMPTS / "HERMES.md").read_text(encoding="utf-8")
    assert _shared(claude) == _shared(hermes)
    assert "Claude anchor" in claude and "Hermes anchor" in hermes


def test_public_templates_have_no_local_or_secret_material():
    text = "\n".join(p.read_text(encoding="utf-8") for p in PROMPTS.glob("*.md"))
    assert not re.search(r"/(?:Users|Volumes)/|<PIN>|koederwerte", text)

