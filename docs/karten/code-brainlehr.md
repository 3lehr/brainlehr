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
  kern["kern"]
  knowledge_mcp_server["knowledge_mcp_server"]
  melder["melder"]
  messungen["messungen"]
  migrationen["migrationen"]
  pflege["pflege"]
  pruefstand["pruefstand"]
  runs["runs"]
  schnellstart["schnellstart"]
  schreibpruefstand["schreibpruefstand"]
  spikes["spikes"]
  tests["tests"]
  berichte -->|1| haken
  berichte -->|1| knowledge_mcp_server
  brainlehr -->|1| knowledge_mcp_server
  haken -->|7| knowledge_mcp_server
  haken -->|1| melder
  kern -->|6| haken
  kern -->|24| knowledge_mcp_server
  melder -->|2| haken
  melder -->|6| knowledge_mcp_server
  messungen -->|1| kern
  messungen -->|5| knowledge_mcp_server
  migrationen -->|7| knowledge_mcp_server
  pflege -->|2| kern
  pflege -->|2| knowledge_mcp_server
  pruefstand -->|1| knowledge_mcp_server
  runs -->|1| kern
  schnellstart -->|1| knowledge_mcp_server
  schreibpruefstand -->|4| knowledge_mcp_server
  tests -->|2| brainlehr
  tests -->|4| haken
  tests -->|14| kern
  tests -->|81| knowledge_mcp_server
```

Ein Kasten ist ein Verzeichnis, die Zahl an der Kante sagt, wie viele Dateien diesen Weg gehen. 18 Module, 22 Verbindungen.
