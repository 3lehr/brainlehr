# Code-Struktur: brainlehr

**Erzeugt von `melder/landkarten.py` — nicht von Hand ändern.**

```mermaid
graph LR
  app["app"]
  aufsaetze["aufsaetze"]
  berichte["berichte"]
  brainlehr["brainlehr"]
  fremdclient["fremdclient"]
  haken["haken"]
  integrations["integrations"]
  kern["kern"]
  knowledge_mcp_server["knowledge_mcp_server"]
  korpora["korpora"]
  melder["melder"]
  messungen["messungen"]
  migrationen["migrationen"]
  pflege["pflege"]
  pruefstand["pruefstand"]
  runs["runs"]
  schnellstart["schnellstart"]
  schreibpruefstand["schreibpruefstand"]
  sicherungen["sicherungen"]
  spikes["spikes"]
  tests["tests"]
  tool["tool"]
  berichte -->|1| haken
  berichte -->|2| kern
  berichte -->|1| knowledge_mcp_server
  brainlehr -->|1| knowledge_mcp_server
  haken -->|7| knowledge_mcp_server
  haken -->|1| melder
  kern -->|6| haken
  kern -->|28| knowledge_mcp_server
  knowledge_mcp_server -->|2| kern
  knowledge_mcp_server -->|1| sicherungen
  melder -->|2| haken
  melder -->|6| knowledge_mcp_server
  messungen -->|6| kern
  messungen -->|20| knowledge_mcp_server
  migrationen -->|7| knowledge_mcp_server
  pflege -->|2| kern
  pflege -->|2| knowledge_mcp_server
  pruefstand -->|1| knowledge_mcp_server
  runs -->|1| kern
  schnellstart -->|1| knowledge_mcp_server
  schreibpruefstand -->|4| knowledge_mcp_server
  tests -->|2| berichte
  tests -->|2| brainlehr
  tests -->|6| haken
  tests -->|32| kern
  tests -->|108| knowledge_mcp_server
  tests -->|1| melder
  tests -->|2| sicherungen
  tool -->|1| knowledge_mcp_server
```

Ein Kasten ist ein Verzeichnis, die Zahl an der Kante sagt, wie viele Dateien diesen Weg gehen. 22 Module, 29 Verbindungen.
