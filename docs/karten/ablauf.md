# Der eigene Ablauf — und wo er nur Absicht ist

**Erzeugt von `melder/landkarten.py` — nicht von Hand ändern.**

```mermaid
graph LR
  auftrag>"Auftrag"]
  class auftrag waise
  existenzprobe["Existenzprobe"]
  plan["Plan"]
  bauen["Bauen"]
  gate(["Quality Gate"])
  beleg["Rot vor Grün"]
  ablegen["Ablegen"]
  commit["Commit"]
  aussen>"Nach außen"]
  auftrag --> existenzprobe
  existenzprobe -->|gibt es nicht| plan
  existenzprobe -->|gibt es schon| commit
  plan --> bauen
  bauen --> gate
  gate -.->|ROT — zurück, ohne Prüfer| bauen
  gate -->|grün| beleg
  beleg -->|kein Beleg möglich| bauen
  beleg -->|belegt| ablegen
  ablegen --> commit
  commit -->|nächster Schritt| auftrag
  commit -->|auf ausdrückliches Wort| aussen
  classDef waise stroke-dasharray: 5 5
```

Gestrichelt = **kein Mechanismus setzt diesen Schritt durch**. 1 von 9 Schritten sind heute blosse Absicht: Auftrag.
