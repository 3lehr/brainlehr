# Code-Struktur: hub

**Erzeugt von `melder/landkarten.py` — nicht von Hand ändern.**

```mermaid
graph LR
  X_postfach["X-postfach"]
  apps["apps"]
  begod["begod"]
  docs["docs"]
  hooks["hooks"]
  infra["infra"]
  laufzeit["laufzeit"]
  revert_design["revert_design"]
  scripts["scripts"]
  tests["tests"]
  toolbox["toolbox"]
  tools["tools"]
  update_vis["update_vis"]
  laufzeit -->|3| apps
```

Ein Kasten ist ein Verzeichnis, die Zahl an der Kante sagt, wie viele Dateien diesen Weg gehen. 13 Module, 1 Verbindungen.
