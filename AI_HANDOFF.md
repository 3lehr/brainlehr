# AI-Handoff

## 2026-08-24T00:00:00+02:00 — fix(config): require Python 3.11 in shipped MCP templates

- Dateien: `.mcp.json`, `integrations/hermes/config.template.yaml`, `README.md`, `tests/test_smoke.py`.
- Warum: `pyproject.toml` verlangt Python 3.11+, während die ausgelieferten Vorlagen das auf macOS häufig noch 3.9 umfassende `python3` starteten und damit beim Laden von `knowledge_mcp_server.py` scheiterten.
- Verifiziert: `python3 -m pytest -q -p no:cacheprovider tests`; `python3 tools/privacy_check.py`. Die drei vorherigen direkten Tests importierten seit der API-Umstellung nicht mehr vorhandene Hilfsfunktionen (`open_db`, `add_node`, `call`); sie pruefen nun die aktuelle Schema-, Governance-, Kanten- und Annahmen-API. Die Claude-Hooks riefen dieselbe entfernte Helper-API auf und nutzen nun die bestehenden direkten Funktionen; der bestehende Profiltest nutzte ebenfalls die veraltete Variable `BRAINLEHR_TOOL_PROFILE` und das alte JSON-RPC-Fehlerformat, der Prompt-Test übersah das aktuelle Feld `recommendation`. Sie pruefen nun den aktuellen Vertrag.
- Entscheidung: Keine `__future__.annotations`-Symptomkorrektur für Python 3.9; das würde den deklarierten, weiter gültigen Mindestvertrag verschleiern.
- AI-Assisted-By: ChatGPT Codex (`/root/terra_hermes_fresh_clone_audit`)

## 2026-08-17T13:18:49+02:00 — feat(mcp): add prompt-invariance clients

- Dateien: `kern/prompt_invarianz.py`, MCP-Dispatch und Tests, README/Feature-Matrix/AI-Entscheidung, ChatGPT- und Hermes-Vorlagen.
- Warum: Claude bleibt primärer vollständiger stdio-Client; ChatGPT und Hermes erhalten dieselbe deterministische Prompt-Invarianz mit minimaler Werkzeugfreigabe. OpenAI Secure MCP Tunnel übernimmt den authentifizierten HTTPS-Transport ohne öffentlichen Brainlehr-Ingress.
- Verifiziert: `python3 -m pytest -q -p no:cacheprovider tests` → 8 bestanden; `python3 tools/privacy_check.py` → Exit 0; `tunnel-client --version` → 0.0.11; temporäres `tunnel-client init` erfolgreich; `doctor` lehnt ohne Runtime-Key erwartungsgemäß ab.
- Restrisiko: Der echte OpenAI-Tunnel ist noch nicht aktiv, weil `tunnel_id`, Runtime-API-Key und ChatGPT Developer Mode nur im Betreiberkonto verfügbar sind. Keine Zugangsdaten wurden gelesen oder gespeichert.
- Nächster Test: Betreiber setzt den Runtime-Key direkt im Terminal; danach `tunnel-client doctor --profile brainlehr-chatgpt --explain`, verwalteten Runtime-Status prüfen und in ChatGPT genau die zwei freigegebenen Werkzeuge listen/aufrufen.
