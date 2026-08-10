#!/usr/bin/env python3
"""
test_agent_compliance.py — Validates .agent.md, .instructions.md and copilot-instructions.md
across Begod2026, AKA2026, and BEBETTER.

Erstellt: 2026-03-25T16:50:00+01:00
Usage: pytest tests/test_agent_compliance.py -v
       pytest tests/test_agent_compliance.py -v -m smoke
"""

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import re
from pathlib import Path

import pytest
import yaml

# ─── Configuration ──────────────────────────────────────────────────────

PROJECTS = {
    "begod": Path("/Volumes/daten/Begod2026/hub"),
    "aka": Path("/Volumes/daten/AKA2026"),
    "bebetter": Path("/Volumes/daten/BEBETTER"),
}

MAX_COPILOT_INSTRUCTIONS_LINES = 500
MAX_INSTRUCTIONS_LINES = 200
MAX_AGENT_DESCRIPTION_LINES = 100


# ─── Helpers ────────────────────────────────────────────────────────────

EXCLUDE_DIRS = {
    "_legacy", ".worktrees", "node_modules", "build", ".dart_tool",
    ".nosync", "_LOCAL_CACHE.nosync", ".build", "Pods",
}


def find_files(project_path: Path, pattern: str) -> list[Path]:
    results = []
    for f in project_path.rglob(pattern):
        if not any(part in EXCLUDE_DIRS or part.endswith(".nosync") for part in f.parts):
            results.append(f)
    return sorted(results)


def parse_frontmatter(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter from a file. Returns (frontmatter_dict, body)."""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {"_parse_error": True}
    return fm, parts[2]


# ─── Fixtures ───────────────────────────────────────────────────────────

def collect_instructions_files():
    """Collect all .instructions.md files across all projects (canonical only)."""
    items = []
    seen = set()
    for name, path in PROJECTS.items():
        canonical = path / ".github" / "instructions"
        if canonical.is_dir():
            for f in sorted(canonical.glob("*.instructions.md")):
                if f.name not in seen:
                    items.append(pytest.param(f, name, id=f"{name}:{f.name}"))
                    seen.add(f.name)
    return items


def collect_agent_files():
    """Collect all .agent.md files across all projects (canonical only)."""
    items = []
    seen = set()
    for name, path in PROJECTS.items():
        agents_dir = path / ".github" / "agents"
        if agents_dir.is_dir():
            for f in sorted(agents_dir.glob("*.agent.md")):
                if f.name not in seen:
                    items.append(pytest.param(f, name, id=f"{name}:{f.name}"))
                    seen.add(f.name)
    return items


def collect_copilot_instructions():
    """Collect copilot-instructions.md files."""
    items = []
    for name, path in PROJECTS.items():
        ci = path / ".github" / "copilot-instructions.md"
        if ci.exists():
            items.append(pytest.param(ci, name, id=f"{name}:copilot-instructions"))
    return items


# ─── Tests: Instructions Files ──────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.agent
@pytest.mark.parametrize("filepath,project", collect_instructions_files())
class TestInstructionsCompliance:

    def test_has_yaml_frontmatter(self, filepath, project):
        """Every .instructions.md must start with valid YAML frontmatter."""
        fm, _ = parse_frontmatter(filepath)
        assert "_parse_error" not in fm, f"Invalid YAML frontmatter in {filepath.name}"

    def test_has_apply_to(self, filepath, project):
        """Every .instructions.md must have an applyTo field."""
        fm, _ = parse_frontmatter(filepath)
        assert "applyTo" in fm, f"Missing 'applyTo' in {filepath.name}"

    def test_apply_to_not_too_broad(self, filepath, project):
        """applyTo should not be '**' unless it's a meta/governance file."""
        fm, _ = parse_frontmatter(filepath)
        apply_to = fm.get("applyTo", "")
        if apply_to == "**":
            meta_names = ["orchestration", "governance", "bridge", "token", "git", "session"]
            is_meta = any(m in filepath.stem.lower() for m in meta_names)
            if not is_meta:
                pytest.fail(f"{filepath.name}: applyTo='**' is too broad. Use a specific glob pattern.")

    def test_line_count_reasonable(self, filepath, project):
        """Instructions files should not exceed max lines."""
        lines = filepath.read_text(encoding="utf-8", errors="replace").count("\n")
        assert lines <= MAX_INSTRUCTIONS_LINES, (
            f"{filepath.name} has {lines} lines (max {MAX_INSTRUCTIONS_LINES})")


# ─── Tests: Agent Files ─────────────────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.agent
@pytest.mark.parametrize("filepath,project", collect_agent_files())
class TestAgentCompliance:

    def test_has_frontmatter(self, filepath, project):
        """Every .agent.md must have valid YAML frontmatter."""
        fm, _ = parse_frontmatter(filepath)
        assert "_parse_error" not in fm, f"Invalid YAML frontmatter in {filepath.name}"

    def test_has_description(self, filepath, project):
        """Agent files must have a description field."""
        fm, _ = parse_frontmatter(filepath)
        assert fm.get("description"), f"Missing 'description' in {filepath.name}"

    def test_body_not_empty(self, filepath, project):
        """Agent files must have actual content in the body."""
        _, body = parse_frontmatter(filepath)
        assert len(body.strip()) > 50, f"{filepath.name}: body is too short or empty"


# ─── Tests: copilot-instructions.md ─────────────────────────────────────

@pytest.mark.smoke
@pytest.mark.parametrize("filepath,project", collect_copilot_instructions())
class TestCopilotInstructions:

    def test_line_count(self, filepath, project):
        """copilot-instructions.md must stay under max lines for token efficiency."""
        lines = filepath.read_text(encoding="utf-8", errors="replace").count("\n")
        assert lines <= MAX_COPILOT_INSTRUCTIONS_LINES, (
            f"{project}: copilot-instructions.md has {lines} lines (max {MAX_COPILOT_INSTRUCTIONS_LINES})")

    def test_no_duplicate_sections(self, filepath, project):
        """Check for obviously duplicated sections (same heading twice)."""
        text = filepath.read_text(encoding="utf-8", errors="replace")
        headings = re.findall(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
        seen = set()
        for h in headings:
            h_lower = h.strip().lower()
            assert h_lower not in seen, f"Duplicate heading '{h}' in {project}/copilot-instructions.md"
            seen.add(h_lower)


# ─── Tests: MCP Configuration ───────────────────────────────────────────

@pytest.mark.smoke
class TestMCPConfig:

    @pytest.mark.parametrize("project,path", [
        ("begod", PROJECTS["begod"]),
        ("aka", PROJECTS["aka"]),
        ("bebetter", PROJECTS["bebetter"]),
    ])
    def test_mcp_json_valid(self, project, path):
        """Each project must have a valid .vscode/mcp.json."""
        mcp_file = path / ".vscode" / "mcp.json"
        assert mcp_file.exists(), f"{project}: .vscode/mcp.json not found"
        data = json.loads(mcp_file.read_text())
        assert "servers" in data, f"{project}: mcp.json missing 'servers' key"

    @pytest.mark.parametrize("project,path", [
        ("begod", PROJECTS["begod"]),
        ("aka", PROJECTS["aka"]),
        ("bebetter", PROJECTS["bebetter"]),
    ])
    def test_knowledge_mcp_configured(self, project, path):
        """Each project must have the shared knowledge-mcp server."""
        mcp_file = path / ".vscode" / "mcp.json"
        data = json.loads(mcp_file.read_text())
        assert "knowledge-mcp" in data["servers"], (
            f"{project}: knowledge-mcp not configured in mcp.json")


# ─── Tests: Settings.json ───────────────────────────────────────────────

@pytest.mark.smoke
class TestVSCodeSettings:

    @pytest.mark.parametrize("project,path", [
        ("begod", PROJECTS["begod"]),
        ("aka", PROJECTS["aka"]),
        ("bebetter", PROJECTS["bebetter"]),
    ])
    def test_max_requests_set(self, project, path):
        """Each project should have chat.agent.maxRequests configured."""
        settings = path / ".vscode" / "settings.json"
        assert settings.exists(), f"{project}: .vscode/settings.json not found"
        data = json.loads(settings.read_text())
        assert "chat.agent.maxRequests" in data, (
            f"{project}: chat.agent.maxRequests not set")

    @pytest.mark.parametrize("project,path", [
        ("begod", PROJECTS["begod"]),
        ("aka", PROJECTS["aka"]),
        ("bebetter", PROJECTS["bebetter"]),
    ])
    def test_instructions_locations_set(self, project, path):
        """Each project should have chat.instructionsFilesLocations configured."""
        settings = path / ".vscode" / "settings.json"
        data = json.loads(settings.read_text())
        assert "chat.instructionsFilesLocations" in data, (
            f"{project}: chat.instructionsFilesLocations not set")
