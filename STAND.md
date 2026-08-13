# STAND brainlehr — 2026-08-13T23:20:00+0200

**Haerteste Zahl:** 85,5 % des Wissensabrufs erreichen die Sitzung nicht (11 Einspielungen, 155749 Byte erzeugt, 22528 angekommen; sichtbar 2/14, 3/10, 6/15). Ein Glied im Kanal kappt auf 2 KB und meldet Byte statt Treffer (`L-e61d18`). Punkt 1: der Hook bleibt INNERHALB der Grenze und benennt das Weglassen. Zweite, getrennte Ursache: MIN_HITS=3 gattert auf der Anfrageseite, kurze Zurufe bekommen gar nichts (282 von 1923).

**Entschieden:** ADR-006 (DB-Schema als Quelle der Form, Python Grundsprache, andere Sprachen LESEN das Schema) · ADR-007 (zwei Schichten: brainlehr kann nein sagen, openlehr nicht) · `open*` ist der INSTANZ-Namensraum, buckeberg wird openWEG erst bei Veroeffentlichung, die Schicht braucht einen Namen ausserhalb `open*`. Plan: `docs/PLAN_GRUNDARCHITEKTUR_2026-08-13.md`. Gemessen dabei: der „offene Nerv" war zur Haelfte keiner — `Fundstelle.swift` dekodiert nur, `Rangfolge.swift`/`kern/rangfolge.py` war ein Namens-Fehlalarm; uebrig bleibt ein Feldvertrag, heute schon gebrochen (Python 13 Felder, Swift 12, `weitere` kommt nie an).

**Halb gebaut, NICHTS gelaufen:** Feldvertrag — `--vertrag`, `app/Resources/fundstelle_vertrag.json`, `FundstelleVertragTests.swift`. Python-Test fehlt, keine Rot-Probe. Nicht als erledigt lesen.

**Falle + offen:** Aus guter Bauform auf Wirksamkeit geschlossen und einen Import empfohlen, den zwei Plaene laengst abgelehnt hatten (`L-dd35c1`) — vor jedem „wir sollten X uebernehmen" erst in `docs/` greppen. Beim Betreiber: Name der Schicht · Ja zum Neubau der Steuerinstanz · Besetzung des Opus-Konsils.
