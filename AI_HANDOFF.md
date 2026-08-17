# AI-Handoff

## 2026-08-17T13:18:49+02:00 — feat(mcp): add prompt-invariance clients

- Dateien: `kern/prompt_invarianz.py`, MCP-Dispatch und Tests, README/Feature-Matrix/AI-Entscheidung, ChatGPT- und Hermes-Vorlagen.
- Warum: Claude bleibt primärer vollständiger stdio-Client; ChatGPT und Hermes erhalten dieselbe deterministische Prompt-Invarianz mit minimaler Werkzeugfreigabe. OpenAI Secure MCP Tunnel übernimmt den authentifizierten HTTPS-Transport ohne öffentlichen Brainlehr-Ingress.
- Verifiziert: `python3 -m pytest -q -p no:cacheprovider tests` → 8 bestanden; `python3 tools/privacy_check.py` → Exit 0; `tunnel-client --version` → 0.0.11; temporäres `tunnel-client init` erfolgreich; `doctor` lehnt ohne Runtime-Key erwartungsgemäß ab.
- Restrisiko: Der echte OpenAI-Tunnel ist noch nicht aktiv, weil `tunnel_id`, Runtime-API-Key und ChatGPT Developer Mode nur im Betreiberkonto verfügbar sind. Keine Zugangsdaten wurden gelesen oder gespeichert.
- Nächster Test: Betreiber setzt den Runtime-Key direkt im Terminal; danach `tunnel-client doctor --profile brainlehr-chatgpt --explain`, verwalteten Runtime-Status prüfen und in ChatGPT genau die zwei freigegebenen Werkzeuge listen/aufrufen.
