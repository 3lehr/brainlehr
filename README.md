# Brainlehr

Kleiner, lokaler Wissensspeicher mit einer JSON-RPC-Schnittstelle über Standard-Ein-/Ausgabe.

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
