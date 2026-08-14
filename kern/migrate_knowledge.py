#!/usr/bin/env python3
"""
Migrate existing knowledge files into the shared knowledge database.
Seeds the tree structure with root nodes and imports key files.

Erstellt: 2026-03-25T16:35:00+01:00
Usage: python3 migrate_knowledge.py
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
import zeitmarke  # Aufgabe 111: die eine Quelle fuer Zeitstempel
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# BEGOD_KNOWLEDGE_DB ueberschreibt den Pfad -- gleiches Muster wie
# knowledge_mcp_server.py::DB_PATH, sonst laesst sich dieses Skript nie gegen
# eine Testkopie fahren, ohne die Produktiv-DB anzufassen.
DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (_w / "brainlehr.db"))
BERLIN = ZoneInfo("Europe/Berlin")


def now_iso() -> str:
    return zeitmarke.jetzt()  # Aufgabe 111: UTC mit Z, eine Quelle


def add_node(conn, path, parent_path, title, summary, content="",
             project_id="shared", tags=None, source="", confidence=0.8):
    level = path.count("/") - 1
    node_id = str(uuid.uuid4())[:8]
    try:
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source, confidence, created_at, updated_at,
                norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'keine_norm', 'skript:migrate_knowledge.py', 'Struktur-/Sammelknoten, kein Normtext')""",
            (node_id, path, parent_path, project_id, title, summary, content,
             level, json.dumps(tags or []), source, confidence, now_iso(), now_iso())
        )
        return node_id
    except sqlite3.IntegrityError:
        return None  # Already exists


def seed_tree_structure(conn):
    """Create the root taxonomy nodes."""
    nodes = [
        # Level 0: Root categories
        ("/arch", None, "Architektur", "Architektur-Entscheidungen, Patterns und Systemdesign.", "shared", ["architecture"]),
        ("/ops", None, "Operations", "DevOps, Deployment, Docker, CI/CD Patterns.", "shared", ["devops"]),
        ("/frontend", None, "Frontend", "UI/UX, Design-Tokens, Komponenten, Barrierefreiheit.", "shared", ["frontend"]),
        ("/backend", None, "Backend", "Server, APIs, Datenbanken, WordPress.", "shared", ["backend"]),
        ("/agents", None, "Agent-System", "Agent-Konfig, Orchestrierung, MCP, Governance.", "shared", ["agents"]),
        ("/testing", None, "Testing", "Test-Strategien, pytest, Coverage, TDD Patterns.", "shared", ["testing"]),
        ("/lessons", None, "Lessons Learned", "Gesammelte Erfahrungen und Fehler-Patterns.", "shared", ["lessons"]),
        ("/tools", None, "Tools & Scripts", "CLI-Tools, MCP-Server, Automatisierung.", "shared", ["tools"]),

        # Level 1: Architecture sub-nodes
        ("/arch/mcp", "/arch", "MCP Server", "Model Context Protocol Server-Architektur und Patterns.", "shared", ["mcp"]),
        ("/arch/gate-system", "/arch", "Gate-System", "Gate-basierte Qualitätssicherung (-2 bis 10).", "shared", ["gates"]),
        ("/arch/knowledge-mgmt", "/arch", "Knowledge Management", "Wissens-DB, Baumstruktur, Token-Effizienz.", "shared", ["knowledge"]),
        ("/arch/token-economy", "/arch", "Token-Ökonomie", "Premium-Request-Multiplikatoren, Lazy-Loading, Context-Optimierung.", "shared", ["tokens"]),

        # Level 1: Agent sub-nodes
        ("/agents/governance", "/agents", "Governance", "Agenten-Hierarchie, Protokolle (P1-P40), Rollen.", "shared", ["governance"]),
        ("/agents/instructions", "/agents", "Instructions", "applyTo-Patterns, .instructions.md Best Practices.", "shared", ["instructions"]),
        ("/agents/mcp-tools", "/agents", "MCP Tools", "Tool-Design, Handler-Patterns, Security.", "shared", ["mcp"]),
        ("/agents/prompt-templates", "/agents", "Prompt Templates", ".prompt.md Workflow-Templates.", "shared", ["prompts"]),

        # Level 1: Frontend sub-nodes
        ("/frontend/design-tokens", "/frontend", "Design Tokens", "Farben, Typografie, Spacing, Motion-Tokens.", "shared", ["design"]),
        ("/frontend/accessibility", "/frontend", "Barrierefreiheit", "WCAG 2.2, ARIA, Kontraste, Screenreader.", "shared", ["a11y"]),
        ("/frontend/flutter", "/frontend", "Flutter", "Dart/Flutter Patterns, Plattform-Channels.", "shared", ["flutter"]),
        ("/frontend/web", "/frontend", "Web", "Astro, HTML, CSS, JavaScript, Tailwind.", "shared", ["web"]),

        # Level 1: Backend sub-nodes
        ("/backend/wordpress", "/backend", "WordPress", "WP-CLI, PHP, Plugins, Docker, 10-Phasen-Workflow.", "shared", ["wordpress"]),
        ("/backend/python", "/backend", "Python", "Scripts, FastAPI, SQLAlchemy Patterns.", "shared", ["python"]),
        ("/backend/database", "/backend", "Datenbank", "SQLite, PostgreSQL, Migration-Patterns.", "shared", ["database"]),

        # Level 1: Testing sub-nodes
        ("/testing/pytest", "/testing", "pytest", "pytest Config, Fixtures, Markers, Coverage.", "shared", ["pytest"]),
        ("/testing/agent-testing", "/testing", "Agent Testing", "Agent-Compliance-Tests, Instructions-Lint.", "shared", ["agent-testing"]),
        ("/testing/pre-commit", "/testing", "Pre-Commit", "Git-Hooks, Linting, Smoke-Tests.", "shared", ["pre-commit"]),

        # Level 1: Tools sub-nodes
        ("/tools/knowledge-mcp", "/tools", "Knowledge MCP", "Shared Knowledge MCP Server (browse/read/search/lesson).", "shared", ["mcp", "knowledge"]),
        ("/tools/lesson-recorder", "/tools", "Lesson Recorder", "CLI + MCP Tool für automatisches Fehler-Lernen.", "shared", ["lessons"]),

        # Project-specific root nodes
        ("/begod", None, "Begod2026", "Hub-Projekt: 14 Apps, 87 Agents, 8 Kontinente.", "begod", ["begod"]),
        ("/aka", None, "AKA2026", "Akademie-Projekt: 15 Apps, Zahnmedizin-Software.", "aka", ["aka"]),
        ("/bebetter", None, "BEBETTER", "Website-Rebuild-System: WordPress, Astro, Multi-Projekt.", "bebetter", ["bebetter"]),
    ]

    for path, parent, title, summary, proj, tags in nodes:
        add_node(conn, path, parent, title, summary, project_id=proj, tags=tags, source="seed")


def import_meta_optimization_findings(conn):
    """Import key findings from the meta-optimization research."""
    findings = [
        {
            "path": "/arch/token-economy/lazy-loading",
            "parent": "/arch/token-economy",
            "title": "applyTo Lazy-Loading",
            "summary": "VS Code lädt .instructions.md nur wenn die geöffnete Datei zum applyTo-Pattern passt. Ohne spezifisches Pattern (applyTo: '**') wird IMMER geladen — verschwendet Tokens.",
            "content": """## applyTo Lazy-Loading (GA seit VS Code 2025)

- `.instructions.md` mit YAML-Frontmatter `applyTo: "pattern"` werden nur geladen wenn die aktive Datei zum Glob-Pattern passt
- `applyTo: "**"` = wird IMMER geladen (wie copilot-instructions.md)
- `applyTo: "apps/myapp/**"` = wird NUR geladen wenn Agent in apps/myapp/ arbeitet
- Best Practice: Jede .instructions.md so spezifisch wie möglich scopen
- AKA2026 hatte 6/9 Dateien mit `**` → nach Fix auf spezifische Pfade: ~40-60% Token-Ersparnis pro Request

Quelle: Meta-Optimization Phase 1, Gemini Deep Research 2026-03-25""",
            "tags": ["tokens", "instructions", "applyTo", "lazy-loading"],
            "source": "meta-optimization-matrix-2026-03-25.md",
            "confidence": 0.99
        },
        {
            "path": "/arch/token-economy/premium-multipliers",
            "parent": "/arch/token-economy",
            "title": "Premium-Request-Multiplikatoren",
            "summary": "Claude Opus 4.6 kostet 3× pro Request, Haiku 0.33×, Sonnet 1×. Bei Pro+ Plan: 1500 Requests/Monat. Opus nur für komplexe Konsile nutzen.",
            "content": """## Premium Request Multipliers (Stand März 2026)

| Modell | Multiplikator | Einsatz |
|--------|---------------|---------|
| Claude Haiku 4.5 | 0.33× | Routine, Gates, Triage |
| Gemini 3 Flash | 0.33× | Schnelle Analysen |
| Claude Sonnet 4.5/4.6 | 1× | Standard-Arbeit |
| Claude Opus 4.5/4.6 | 3× | Komplexe Konsile |
| Claude Opus Fast | 30× | VERMEIDEN |

Pro Plan: 300/Monat, Pro+: 1500/Monat.
REGEL: Opus nur für Architektur-Konsile und komplexe Debugging-Sessions.""",
            "tags": ["tokens", "premium", "models", "cost"],
            "source": "deep-research-vscode-copilot-meta-optimization-2026_result.json",
            "confidence": 1.0
        },
        {
            "path": "/arch/mcp/server-design",
            "parent": "/arch/mcp",
            "title": "MCP Server Design Patterns",
            "summary": "stdio für lokale Server, Streamable HTTP für Shared. @mcp.tool() Decorator-Pattern. Max 15-20 Tools pro Server. sandboxEnabled für Security.",
            "content": """## MCP Server Design Patterns (März 2026)

### Transport
- **stdio**: Lokal, 1:1, isoliert. Für projektspezifische Tools.
- **Streamable HTTP**: Remote, skalierbar, Multi-Client. Für Shared Server.

### SDK
- Python SDK v1.26, TypeScript SDK v1.27.1
- `@mcp.tool()` Decorator für Tool-Registration
- Async ist Standard für I/O

### VS Code Integration
- `.vscode/mcp.json` pro Workspace
- `sandboxEnabled: true` für macOS/Linux Sandboxing
- Debugging via `dev`-Key

### Best Practices
- Max 15-20 Tools pro Server (Context Window)
- Read-Only Tools explizit markieren
- Destruktive Aktionen hinter User-Consent
- Pydantic für Input-Validierung""",
            "tags": ["mcp", "architecture", "patterns"],
            "source": "dr-mcp-architecture-2026_result.json",
            "confidence": 0.95
        },
        {
            "path": "/arch/knowledge-mgmt/tree-structure",
            "parent": "/arch/knowledge-mgmt",
            "title": "Baumstruktur-Wissens-DB",
            "summary": "SQLite + FTS5 mit Materialized Path. 3-4 Ebenen Tiefe. Agent navigiert mit browse→read in 2-3 Calls statt 15k Tokens Flat-Files.",
            "content": """## Knowledge DB Baumstruktur

### Warum
- 60+ JSON/MD Dateien flat = ~15.000 Tokens wenn alles geladen
- Baumstruktur: browse() gibt ~200 Tokens (nur Titel+Summary)
- read() gibt ~500 Tokens für einen Knoten
- 2-3 Calls statt Context-Flut

### Technologie
- SQLite + FTS5 (Full-Text Search)
- Materialized Path: `/shared/arch/mcp` (semantisch lesbar)
- 3-4 Ebenen optimal

### MCP Tools
- knowledge_browse(path) → Kinder (Titel+Summary)
- knowledge_read(id) → Volltext
- knowledge_search(query) → FTS5 Suche
- lesson_record() → Fehler-Learning
- lesson_query() → Lessons abfragen""",
            "tags": ["knowledge", "database", "sqlite", "tree"],
            "source": "dr-knowledge-db-tree-2026_result.json",
            "confidence": 0.95
        },
        {
            "path": "/testing/pytest/monorepo-setup",
            "parent": "/testing/pytest",
            "title": "Pytest Monorepo Setup",
            "summary": "pyproject.toml statt pytest.ini. Zentrales conftest.py mit shared Fixtures. Markers: smoke, integration, agent. Coverage via pytest-cov.",
            "content": """## Pytest Monorepo Setup

### Config
- pyproject.toml bevorzugt (alle 3 Projekte)
- [tool.pytest.ini_options] Section
- testpaths = ["tests", "scripts"]

### Fixtures (conftest.py)
- tmp_knowledge_db: Temporäre SQLite für Tests
- mock_mcp_server: MCP Server Mock
- sample_agent_config: Valide .agent.md

### Markers
- @pytest.mark.smoke — unter 1s, Pre-Commit
- @pytest.mark.integration — MCP, DB, Docker
- @pytest.mark.agent — Agent-Compliance
- @pytest.mark.slow — >10s

### Coverage
- pytest-cov für Monorepos
- Threshold: 60% für neue Dateien""",
            "tags": ["pytest", "testing", "monorepo"],
            "source": "dr-testing-learning-2026_result.json",
            "confidence": 0.9
        },
        {
            "path": "/lessons/reflexion-pattern",
            "parent": "/lessons",
            "title": "Reflexion-Pattern für Error-Learning",
            "summary": "Fehler → JSONL-Log → Pattern-Clustering → Regel-Generierung ab n≥3. Automatisch .instructions.md ergänzen wenn Pattern eskaliert.",
            "content": """## Reflexion-Pattern (Self-Learning)

### Flow
1. Fehler wird erkannt/berichtet
2. lesson_record() speichert in DB
3. Gleichartige Fehler werden automatisch geclustert (gleicher type+description)
4. Occurrences-Zähler inkrementiert
5. Ab n≥3: Status → 'escalated_to_rule'
6. Agent wird informiert: "Sollte zur Regel in .instructions.md werden"
7. Manuell oder via Script: Neue Regel erstellen

### Threshold
- n=1: Einmaliger Fehler, nur loggen
- n=2: Potenzielles Pattern, beobachten
- n≥3: Systematisches Problem → Regel generieren

### Quellen
- Reflexion Paper: arxiv.org/abs/2303.11366
- Praxis: In begod2026 copilot-instructions.md als "Fehler → Lesson → Gate → Regel" definiert""",
            "tags": ["learning", "errors", "reflexion", "automation"],
            "source": "dr-testing-learning-2026_result.json",
            "confidence": 0.85
        }
    ]

    for f in findings:
        add_node(conn, f["path"], f["parent"], f["title"], f["summary"],
                 f["content"], tags=f["tags"], source=f["source"], confidence=f["confidence"])


def main():
    print(f"Datenbank: {DB_PATH}")
    # Bewusst sqlite3.connect (nicht speicher.verbinde_bestand): dieses
    # Skript ist die Erstanlage selbst -- "Seeds the tree structure with
    # root nodes" --, es SOLL eine fehlende Datei anlegen.
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    print("🌳 Seeding Baumstruktur...")
    seed_tree_structure(conn)

    print("📥 Importiere Meta-Optimization Findings...")
    import_meta_optimization_findings(conn)

    conn.commit()

    # Stats
    total = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    by_level = conn.execute("SELECT level, COUNT(*) FROM knowledge_nodes GROUP BY level").fetchall()
    by_project = conn.execute("SELECT project_id, COUNT(*) FROM knowledge_nodes GROUP BY project_id").fetchall()

    print(f"\n✅ Knowledge DB bereit: {total} Knoten")
    print(f"   Ebenen: {dict(by_level)}")
    print(f"   Projekte: {dict(by_project)}")
    print(f"   DB: {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    main()
