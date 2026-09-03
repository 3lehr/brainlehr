# Code-Struktur: brainlehr

**Erzeugt von `melder/landkarten.py` — nicht von Hand ändern.**

```mermaid
graph LR
  app["app"]
  aufsaetze["aufsaetze"]
  berichte["berichte"]
  brainlehr["brainlehr"]
  build_aktion_korpus["build_aktion_korpus"]
  debug_all["debug_all"]
  debug_korpus["debug_korpus"]
  debug_quelle["debug_quelle"]
  debug_sample["debug_sample"]
  debug_search["debug_search"]
  debug_show["debug_show"]
  fix_db_fields["fix_db_fields"]
  fix_db_lessons["fix_db_lessons"]
  fix_db_nodes["fix_db_nodes"]
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
  debug_quelle -->|1| knowledge_mcp_server
  debug_search -->|1| knowledge_mcp_server
  haken -->|7| knowledge_mcp_server
  haken -->|1| melder
  kern -->|6| haken
  kern -->|29| knowledge_mcp_server
  knowledge_mcp_server -->|3| kern
  knowledge_mcp_server -->|1| sicherungen
  melder -->|2| haken
  melder -->|6| knowledge_mcp_server
  messungen -->|6| kern
  messungen -->|22| knowledge_mcp_server
  migrationen -->|2| kern
  migrationen -->|10| knowledge_mcp_server
  pflege -->|2| kern
  pflege -->|2| knowledge_mcp_server
  pruefstand -->|1| knowledge_mcp_server
  runs -->|1| kern
  schnellstart -->|1| knowledge_mcp_server
  schreibpruefstand -->|4| knowledge_mcp_server
  tests -->|2| berichte
  tests -->|2| brainlehr
  tests -->|6| haken
  tests -->|92| kern
  tests -->|118| knowledge_mcp_server
  tests -->|1| melder
  tests -->|23| messungen
  tests -->|2| sicherungen
  tests -->|1| tool
  tool -->|3| kern
  tool -->|1| knowledge_mcp_server
```

Ein Kasten ist ein Verzeichnis, die Zahl an der Kante sagt, wie viele Dateien diesen Weg gehen. 32 Module, 35 Verbindungen.
