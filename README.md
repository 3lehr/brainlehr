# Brainlehr

> **Öffentliche Preview (Alpha).** Dieser Branch ist eine frische, datenfreie Vorschau; er ersetzt weder den privaten Betrieb noch behauptet er vollständige Funktionsparität.

Lokaler Wissensspeicher mit einer JSON-RPC-Schnittstelle über Standard-Ein-/Ausgabe, primär für Claude MCP. Implementiert sind Knoten, Suche, Beziehungen, Annahmen, Freigabe/Rücknahme, Lehren, Statistik sowie neutrale Claude Recall-/Capture-Hooks. Die maschinenlesbare [Funktionsmatrix](docs/FEATURE_MATRIX.json) nennt weitere noch zu generalisierende Engine-Funktionen.

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

```sh
python3 -m pytest -q -p no:cacheprovider tests
python3 tools/privacy_check.py
```

Der Privacy-Check ist ein technischer Schutz, keine DSGVO- oder Compliance-Zusage.
