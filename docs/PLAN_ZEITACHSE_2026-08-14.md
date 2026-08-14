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
