# Brainlehr

> **Public Alpha.** Dieser Main-Stand ist eine frische, datenfreie Veröffentlichung; er ersetzt weder den privaten Betrieb noch behauptet er vollständige Funktionsparität.

Lokaler Wissensspeicher mit einer JSON-RPC-Schnittstelle über Standard-Ein-/Ausgabe, primär für Claude MCP. Implementiert sind Knoten, Suche, Beziehungen, Annahmen, Freigabe/Rücknahme, Lehren, Statistik, neutrale Claude Recall-/Capture-Hooks und agentneutrale Prompt-Invarianz für Claude, ChatGPT und Hermes. Die maschinenlesbare [Funktionsmatrix](docs/FEATURE_MATRIX.json) nennt weitere noch zu generalisierende Engine-Funktionen.

## Schnellstart

```sh
python3 schnellstart.py
python3 knowledge_mcp_server.py
```

`schnellstart.py` erstellt eine lokale Beispieldatenbank. Diese Datei ist absichtlich nicht versioniert.

## Entwicklung

```sh
python3 -m pytest -q -p no:cacheprovider tests
python3 tools/privacy_check.py
```

Die öffentliche Ausgabe enthält ausschließlich Quellcode, Tests und allgemeine Dokumentation. Betriebsdaten, Exportdaten und interne Arbeitsnotizen gehören nicht in dieses Repository.

Für Claude: `integrations/claude/settings.template.json` mit eigenen lokalen Pfaden kopieren; die Hook-Vorlagen liegen unter `integrations/claude/hooks/`.

Für ChatGPT bleibt derselbe stdio-MCP lokal. Der [offizielle Secure-MCP-Tunnel](integrations/chatgpt/README.md) stellt den authentifizierten HTTPS-Transport bereit und exponiert im Profil `prompt-invariance` ausschließlich die beiden Vergleichswerkzeuge. Hermes nutzt ebenfalls stdio; eine minimale [Konfigurationsvorlage](integrations/hermes/config.template.yaml) liegt bei.

Prompt-Invarianz wird nur für Bewertungen, Rangfolgen und Entscheidungen aktiviert: normal `light`, bei gemeinsamen, irreversiblen, sicherheits-, Datenmodell- oder Automationsfolgen `strong`. Faktensuche, Extraktion, Ausführung und Tests bleiben `off`. Das gilt unabhängig von der App: Anbieter-Rankings in Buckenberg nutzen sie; Brainlehr-, Openlehr- oder Fahrtenbuch-Coding nur bei einer echten Architektur- oder Produktentscheidung, nicht bei jedem Edit oder Testlauf.

```sh
python3 -m pytest -q -p no:cacheprovider tests
python3 tools/privacy_check.py
```

Der Privacy-Check ist ein technischer Schutz, keine DSGVO- oder Compliance-Zusage.
