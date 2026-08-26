# Der Wissensbestand — Äste und ihre Verbindungen

**Erzeugt von `melder/landkarten.py` — nicht von Hand ändern.**

```mermaid
graph LR
  germanquad["germanquad<br/>2713"]
  nasa_llis["nasa-llis<br/>1638"]
  brainlehr["brainlehr<br/>338"]
  methodik["methodik<br/>174"]
  apps["apps<br/>112"]
  ops["ops<br/>94"]
  shared["shared<br/>56"]
  openlehr["openlehr<br/>46"]
  plaene["plaene<br/>17"]
  arch["arch<br/>16"]
  simulation_akademie_messaufbau_kein["simulation-akademie-messaufbau-kein<br/>15"]
  fahrtenbuch["fahrtenbuch<br/>9"]
  werkzeuge["werkzeuge<br/>8"]
  tools["tools<br/>8"]
  testing["testing<br/>8"]
  frontend["frontend<br/>7"]
  agents["agents<br/>7"]
  projects["projects<br/>6"]
  domaenen["domaenen<br/>5"]
  backend["backend<br/>4"]
  lessons["lessons<br/>3"]
  dokumente["dokumente<br/>3"]
  stadtwerke["stadtwerke<br/>2"]
  begod["begod<br/>2"]
  woanders["woanders<br/>1"]
  testdatenknoten_schreibrechtepruefung["testdatenknoten-schreibrechtepruefung<br/>1"]
  domaenenimporte["domaenenimporte<br/>1"]
  bebetter["bebetter<br/>1"]
  aka["aka<br/>1"]
  brainlehr ---|126| methodik
  brainlehr ---|36| openlehr
  apps ---|26| brainlehr
  apps ---|25| shared
  apps ---|24| methodik
  brainlehr ---|23| plaene
```

Zahl im Kasten = Knoten im Ast, Zahl an der Kante = Verbindungen zwischen zwei Ästen (ab 20, hoechstens 40 staerkste; 6 gezeigt).
