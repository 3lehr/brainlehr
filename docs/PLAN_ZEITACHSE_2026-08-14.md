# Zeit als Achse im Abruf — Schritt 1 von Aufgabe 88

Stand 2026-08-14T03:20:00+0200. Sperrt Aufgabe 104 (Rechtsdomäne WEG/Miete):
Rechtstexte bestehen aus „gilt seit / gilt bis", und der Speicher kann heute
keine der beiden Fragen beantworten.

## Der gemessene Ist-Stand

| | Zahl | Quelle |
|---|---|---|
| Knoten mit `created_at`/`updated_at` | 2184 von 2184 | eigene Zählung |
| Knoten mit `gilt_ab` | 83 | Aufgabe 88 |
| Knoten mit `gilt_bis` | 2 | Aufgabe 88 |
| Kanten mit Zeitbezug | 0 | Aufgabe 88 |
| Aufrufer von `kern/zeitfenster.py` im Abrufpfad | **0** | `grep` heute |

**Der Befund, der die Reihenfolge bestimmt:** `kern/zeitfenster.py` ist gebaut,
getestet und hat **keinen einzigen Aufrufer**. Es sitzt auf
`anfrage_erweiterung.treffer()` — einem anderen Weg als `knowledge_search()`.
Dreizehnte Instanz von „gebaut, laufend, wirkungslos" an einem Tag.

Die Geltungsachse dagegen ist **teilweise da**: `knowledge_search()` kennt
bereits `stichtag` und `nur_geltende` und stuft abgelaufene Normen zurück,
statt sie zu verstecken. Was fehlt, ist die **Entstehungszeit** — „letzte
Woche gemacht" ist eine andere Frage als „gilt bis X".

## Die Engstelle, und warum dort

Der Filter gehört in die Schleife, die Zeilen zu Treffern macht (dort, wo
`_geltung_status()` schon wirkt). Nicht in die FTS-Abfrage, nicht je Aufrufer.

**Alternativen und Ablehnungsgrund:**

- *In die SQL-WHERE-Klausel* — schneller, aber der Bedeutungskanal liefert
  seine Kandidaten getrennt an der FTS vorbei; ein WHERE dort filtert nur die
  Stichworthälfte und lässt die andere durch. Ein halb wirkender Filter ist
  schlimmer als keiner, weil das Ergebnis vollständig aussieht.
- *Je Aufrufer filtern* — dieselbe Fehlklasse wie L-44a838 (Engstelle
  umgangen). Es gibt drei Einstiege; zwei würden es vergessen.
- *Datum in den Einbettungstext aufnehmen und neu rechnen* — ausdrücklich
  verworfen, steht schon in Aufgabe 88: Ein Datum hat keine semantische Nähe
  zu einem anderen Datum, es hat einen **Abstand**. Als Text verrauscht es die
  Bedeutung. Metadaten gehören als Filter und als Kante in den Speicher, nie
  als Text in den Vektor.

## Die Entscheidung, die weh tut, und warum sie sichtbar wird

`kern/zeitfenster.py` schließt Lehren aus, sobald ein Zeitraum gesetzt ist —
weil nicht entschieden ist, welches Feld bei einer Lehre „gemacht" beantwortet
(`first_seen` und `last_seen` existieren beide). Das bleibt so; raten wäre
schlimmer.

**Aber es wird gezählt und genannt.** Eine Suche mit Zeitraum meldet, wie viele
Lehren sie aus diesem Grund fallen ließ. Eine stille Kürzung sieht in der
Antwort aus wie Vollständigkeit — und die fehlende Entscheidung bliebe für
immer unsichtbar, weil niemand vermisst, was er nie gesehen hat.

## Was bewusst nicht getan wird, samt Preis

- **Keine zeitlichen Kanten** (`folgt_auf`, `ersetzt`, `widerruft`). Preis: Der
  Graph bleibt eindimensional. Grund: Ohne gefüllte Geltung wären sie leer —
  Stufe 3 der Aufgabe, nicht Stufe 1.
- **Kein Füllen von `gilt_bis`.** Preis: „gilt bis X" bleibt unbeantwortbar.
  Grund: Erst muss geklärt sein, **wer** es setzt und **wann**; ein Feld, das
  niemand füllt, wird auch als Kante niemand füllen. Sonst entsteht die elfte
  leere Spalte.
- **Keine Vektor-Neuberechnung.** Grund siehe oben — Bauart, nicht Aufwand.

## Woran sich Erfolg messen lässt

- Eine Anfrage nach Inhalt **plus** Zeitraum liefert **vorher** dieselbe Menge
  wie ohne Zeitraum, **nachher** eine echte Teilmenge — an einem Fall, bei dem
  die Zeit den Ausschlag gibt.
- Negativfall: ein Zeitraum, der alles umfasst, ändert nichts.
- Grenzwert: je ein Knoten genau am Rand, einer davor, einer danach.
- Die Zahl der aus Zeitgründen fallengelassenen Lehren steht in der Antwort.

## Aufträge, fertig zum Übergeben

**Für alle gleichermaßen:** Arbeitsort `/Volumes/daten/Begod2026/brainlehr`.
Zuerst `CLAUDE.md` lesen, dann diesen Plan. „Sieht der Code anders aus als hier
beschrieben, halte dich an den Code und melde die Abweichung." Kein `git add
-A`, kein Push, kein `git stash`. Datenbanknamen über `kern/speicher`.

### Schritt 1 · Zeitfenster an die Engstelle von knowledge_search

| | |
|---|---|
| **Darf ändern** | `knowledge_mcp_server.py` (nur `knowledge_search`, die beiden Knoten-SELECTs darin und der `TOOLS`-Eintrag), dazu eine neue Testdatei unter `tests/` |
| **Tabu zusätzlich** | `kern/zeitfenster.py` (wird nur importiert, nicht geändert), `schema.sql`, `haken/` gesamt, `pruefstand/` gesamt, `kern/embeddings.py`, `kern/build_embeddings.py` |
| **Fakten** | `knowledge_search` kennt bereits `stichtag`/`nur_geltende` für die **Geltung**; neu ist die **Entstehungszeit**. Die Engstelle ist die Schleife, die `final_ids` zu Einträgen macht — dort wirkt `_geltung_status` schon. Beide Knoten-SELECTs liefern heute **kein** `created_at`; ohne es im SELECT filtert nichts. `kern/zeitfenster.im_zeitraum(zeitstempel, von, bis)` vergleicht in Tagesgranularität, Grenzen **inklusive**. Lehren tragen kein entschiedenes „gemacht"-Feld (`first_seen` und `last_seen` existieren beide) — sie fallen bei gesetztem Zeitraum heraus, und die Zahl der so verlorenen Lehren gehört als Feld in die Antwort. |
| **Abnahme** | Rot vor grün. Inhalt **plus** Zeitraum liefert vorher dieselbe Menge wie ohne, nachher eine echte Teilmenge. Negativfall: ein alles umfassender Zeitraum ändert nichts. Grenzwert: je ein Knoten genau am Rand, einer davor, einer danach. Die Zahl der aus Zeitgründen fallengelassenen Lehren steht in der Antwort und wird geprüft. Volle Suite grün. |

### Schritt 2 · Vorfrage zur Geltung beantworten, bevor gebaut wird

| | |
|---|---|
| **Darf ändern** | nur diese Plandatei und eine ADR unter `docs/adr/` |
| **Tabu zusätzlich** | jeder Produktivcode — dieser Schritt entscheidet, er baut nicht |
| **Fakten** | `gilt_bis` ist bei 2 von 2184 Knoten gesetzt, `gilt_ab` bei 83. Ein Feld, das niemand füllt, wird auch als Kante niemand füllen. Zu entscheiden ist ausschließlich: **wer** setzt es und **wann** — beim Schreiben, beim Import, durch einen Melder? |
| **Abnahme** | Eine ADR, die den Setzer benennt und den Auslöser. Ohne sie bleibt Schritt 3 gesperrt. Kein Code. |
