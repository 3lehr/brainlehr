# AI-Handoff

## 2026-08-25T20:01:51+02:00 — docs(readme): publish an English product overview

- Dateien: `README.md`, `AI_HANDOFF.md`.
- Warum: Die öffentliche Startseite war deutsch und enthielt interne Audit- und Lizenzgeschichte sowie rechtfertigende Formulierungen. Sie ist nun eine englische Produktübersicht mit Fähigkeiten, Einstieg, Integrationen, Grenzen und genau zwei Kernabläufen.
- Verifiziert: `/Users/lehrmacbook/odysseus/odysseus/venv/bin/python -m pytest -q -p no:cacheprovider tests` → 15 bestanden; `/Users/lehrmacbook/odysseus/odysseus/venv/bin/python tools/privacy_check.py` → Exit 0; Sprach-/Linkprüfung, genau zwei Mermaid-Blöcke und `git diff --check` bestanden.
- Restrisiko: `knowledge_selbstauskunft` bleibt registriert, obwohl `kern/selbstauskunft.py` im Public-Export fehlt; die README nennt dies neutral als bekannte Grenze.
- Nächster Test: `kern/selbstauskunft.py` und dessen Paketaufnahme in einem eigenen, testgetriebenen Fix ergänzen.
- AI-Assisted-By: ChatGPT Codex (`/root`)

## 2026-08-25T19:52:35+02:00 — docs(readme): lead with verified capabilities

- Dateien: `README.md`, `AI_HANDOFF.md`.
- Warum: Die README begann mit Test-, Export- und Auditgeschichte, nannte nicht den heutigen Funktionsumfang und verwies auf zwei im Public-Repo fehlende Auszugspfade. Sie führt nun mit den belegten Speicher-, Such-, Geltungs-, Beziehungs-, Unsicherheits-, Schutz- und Betriebsfunktionen und zeigt genau zwei Kernabläufe als Mermaid-Flowcharts.
- Verifiziert: `python -m pytest -q -p no:cacheprovider tests` → 15 bestanden; `python tools/privacy_check.py` → Exit 0; zwei Mermaid-Blöcke und alle relativen README-Links geprüft; `git diff --check` → Exit 0.
- Restrisiko: `knowledge_selbstauskunft` ist registriert, aber im Public-Export fehlt `kern/selbstauskunft.py`; die README weist das aus, behoben wurde es in diesem Dokumentationsschritt nicht.
- Nächster Test: `kern/selbstauskunft.py` samt Paketliste und direktem Werkzeugtest in einem eigenen Fix ergänzen.
- AI-Assisted-By: ChatGPT Codex (`/root`)

## 2026-08-25T19:24:17+02:00 — fix(release): restore executable release checks

- Dateien: `.github/workflows/release.yml`, `knowledge_mcp_server.py`, `tests/test_smoke.py`, `AI_HANDOFF.md`.
- Warum: Der Release-Workflow verwies auf einen nie vorhandenen Einzeltest; zugleich verhinderte der unbedingte `fcntl`-Import jeden Serverstart unter Windows.
- Verifiziert: `python -m pytest -q -p no:cacheprovider tests` → 15 bestanden; `git diff --check` → Exit 0. Der neue Regressionstest simuliert den fehlenden `fcntl`-Import und durchlaeuft den No-op-Lockpfad.
- Restrisiko: Kein echter Windows-Lauf; GitHub Actions bleiben bis zur menschlichen Billing-Freigabe blind. PyPI v0.1.0 wurde nicht veraendert oder erneut ausgeloest.
- Naechster Test: Nach dem Billing-Unlock `workflow_dispatch` ausloesen und den vollstaendigen Tests-, Build- und Wheel-Erstlauf pruefen.
- AI-Assisted-By: ChatGPT Codex (`/root`)

## 2026-08-24T00:00:00+02:00 — fix(config): require Python 3.11 in shipped MCP templates

- Dateien: `.mcp.json`, `integrations/hermes/config.template.yaml`, `README.md`, `tests/test_smoke.py`.
- Warum: `pyproject.toml` verlangt Python 3.11+, während die ausgelieferten Vorlagen das auf macOS häufig noch 3.9 umfassende `python3` starteten und damit beim Laden von `knowledge_mcp_server.py` scheiterten.
- Verifiziert: `python3 -m pytest -q -p no:cacheprovider tests`; `python3 tools/privacy_check.py`. Die drei vorherigen direkten Tests importierten seit der API-Umstellung nicht mehr vorhandene Hilfsfunktionen (`open_db`, `add_node`, `call`); sie pruefen nun die aktuelle Schema-, Governance-, Kanten- und Annahmen-API. Die Claude-Hooks riefen dieselbe entfernte Helper-API auf und nutzen nun die bestehenden direkten Funktionen; der bestehende Profiltest nutzte ebenfalls die veraltete Variable `BRAINLEHR_TOOL_PROFILE` und das alte JSON-RPC-Fehlerformat, der Prompt-Test übersah das aktuelle Feld `recommendation`. Sie pruefen nun den aktuellen Vertrag.
- Entscheidung: Keine `__future__.annotations`-Symptomkorrektur für Python 3.9; das würde den deklarierten, weiter gültigen Mindestvertrag verschleiern.
- DB-Migration: `knowledge.db` bleibt ein lesbarer Legacy-Fallback. Der Hinweis fordert deshalb nicht mehr zum automatischen oder zwingenden Umbenennen auf; ein explizites `BRAINLEHR_DB` waehlt den Zielpfad.
- AI-Assisted-By: ChatGPT Codex (`/root/terra_hermes_fresh_clone_audit`)

## 2026-08-17T13:18:49+02:00 — feat(mcp): add prompt-invariance clients

- Dateien: `kern/prompt_invarianz.py`, MCP-Dispatch und Tests, README/Feature-Matrix/AI-Entscheidung, ChatGPT- und Hermes-Vorlagen.
- Warum: Claude bleibt primärer vollständiger stdio-Client; ChatGPT und Hermes erhalten dieselbe deterministische Prompt-Invarianz mit minimaler Werkzeugfreigabe. OpenAI Secure MCP Tunnel übernimmt den authentifizierten HTTPS-Transport ohne öffentlichen Brainlehr-Ingress.
- Verifiziert: `python3 -m pytest -q -p no:cacheprovider tests` → 8 bestanden; `python3 tools/privacy_check.py` → Exit 0; `tunnel-client --version` → 0.0.11; temporäres `tunnel-client init` erfolgreich; `doctor` lehnt ohne Runtime-Key erwartungsgemäß ab.
- Restrisiko: Der echte OpenAI-Tunnel ist noch nicht aktiv, weil `tunnel_id`, Runtime-API-Key und ChatGPT Developer Mode nur im Betreiberkonto verfügbar sind. Keine Zugangsdaten wurden gelesen oder gespeichert.
- Nächster Test: Betreiber setzt den Runtime-Key direkt im Terminal; danach `tunnel-client doctor --profile brainlehr-chatgpt --explain`, verwalteten Runtime-Status prüfen und in ChatGPT genau die zwei freigegebenen Werkzeuge listen/aufrufen.
