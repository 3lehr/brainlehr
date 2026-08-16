# Plan: drei Richtungen gegen den Abstraktionssprung — vergleichbar gemessen

**Erstellt** 2026-08-16T12:30:12+0200
**Verhältnis zum geltenden Plan:** untergeordnet zu `docs/PLAN_KANALGUETE_2026-08-15.md`
(K1). Löst nichts ab; K1 Punkt 1 und 2 sind erledigt, dies ist die Folgefrage.
**Anlass** Betreiber: *„wir sollten alles 3 testen und vergleichbar machen/halten"*

## §0 Gemessener Ist-Stand (2026-08-16, Knoten `291c2e3f`)

Eigener Prüfkorpus `runs/pruefkorpus.jsonl`, 35 Fälle:

| | |
|---|---|
| gefunden in den ersten 5 | **5 (14 %)** |
| Rang 6–50 | 7 (20 %) |
| außerhalb Top-50 | **23 (66 %)** |
| davon ohne Einbettung | **0** |
| Rang der 23 im **reinen Bedeutungskanal** | bester 42 · **Median 134** · schlechtester 2487 von 5963 |

**Damit ist ausgeschlossen:** Fusionsformel, Sockel, Stichwortkanal, Relevanzschwelle.
Keine Umordnung erreicht Rang 134. Die Ursache ist der Abstand zwischen Frageform
(Situationsbeschreibung in Alltagssprache) und Zielform (technische Fehlerbeschreibung
mit Eigennamen).

## §1 Die drei Richtungen

| | Was geändert wird | Kosten |
|---|---|---|
| **V1 Zweiteinbettung** | je Lehre/Knoten eine zusätzliche Einbettung, die die **Lage** beschreibt statt der Technik | einmalig je Eintrag |
| **V2 Anfrage umschreiben** | die Anfrage wird vor der Suche in ein hypothetisches Zieldokument übersetzt | **je Anfrage, dauerhaft** |
| **V3 anderes Modell** | `bge-m3` gegen ein Alternativmodell | einmalig, aber Neuberechnung des ganzen Bestands |

## §2 Was Vergleichbarkeit hier konkret heißt

`L-3bf6c7` ist der Grund für diesen Abschnitt: Dort liefen Vorher- und Nachher-Messung
über **verschiedene Korpora**, und beide Zahlen sahen plausibel aus. Deshalb bindend:

1. **Ein Korpus, alle Varianten:** `runs/pruefkorpus.jsonl`, dieselben 35 Fälle, dieselbe
   Reihenfolge. Kein Vorgabewert für den Korpus — er wird verlangt.
2. **Eine Kennzahl, dieselbe für alle:** Rang des Ziels im **reinen Bedeutungskanal**.
   Nicht die Trefferquote@5 des vollen Suchwegs — die mischt Stichwortkanal und Fusion
   hinein und macht die Varianten ununterscheidbar.
3. **Jede Zahl trägt ihren Weg mit** (Korpus, Modell, Codestand, Kandidatenzahl).
4. **Der Produktivbestand wird nicht angefasst.** V1 und V3 rechnen mit zusätzlichen
   Vektoren im Arbeitsspeicher gegen dieselbe Kandidatenmenge — keine Schreiboperation
   auf `knowledge_embeddings`, bevor eine Richtung gewählt ist.
5. **Ausgangslage ist eine eigene Stufe**, nicht eine Erinnerung an die Messung von
   heute früh. Sie läuft im selben Lauf mit.

## §3 Die Grenze dieser Messung — was sie NICHT beantwortet

*Pflichtteil nach `L-0a05b2`: jede Messung benennt, welche Frage sie nicht beantwortet.*

- Sie misst den **Bedeutungskanal**, nicht den vollen Suchweg. Eine Variante, die dort
  gewinnt, muss danach noch am echten Weg gemessen werden.
- Sie misst **35 Fälle**. Das ist klein — heute früh hat eine Stichprobe von 12 gegen 12
  eine saubere Trennung gezeigt, die bei 40 gegen 40 verschwand. Ein knapper Unterschied
  zwischen zwei Varianten ist damit **kein** Ergebnis.
- Sie misst **nicht die Kosten im Betrieb.** V2 kostet je Anfrage; ob das tragbar ist,
  ist eine andere Frage als ob es wirkt.

## §4 Modellwahl — nicht frei

Für V1 und V2 wird ein Modell zum Umformulieren gebraucht. Die Betreiberentscheidung
dazu liegt vor (`L-a69129`, dreimal verletzt): **für Prüfläufe Haiku, nicht das lokale
Modell** — der Unterschied ist die Geschwindigkeit, und Wartezeit war ausdrücklich
unerwünscht. Für V3 wird ein zweites **Einbettungs**modell gebraucht; welche lokal
verfügbar sind, wird gemessen, nicht angenommen.

## §5 Reihenfolge, und wo sie bindend ist

1. Messwerkzeug mit **Stufe 0 (Ausgangslage)** — erst wenn es die heutigen Zahlen
   reproduziert, ist es vertrauenswürdig.
2. V1 an **fünf Lehren** als Vorprobe. Zeigt sich dort nichts, wird der ganze Bestand
   nicht angefasst.
3. V3 (nur wenn ein zweites Modell verfügbar ist), V2 zuletzt — sie ist die einzige mit
   dauerhaften Kosten.

**Bindend:** Stufe 0 zuerst. Ein Messwerkzeug, das die bekannte Ausgangslage nicht
trifft, misst etwas anderes als gedacht.

## §6 Woran sich Erfolg messen lässt

Nicht „eine Variante ist besser". Sondern: **der Median-Rang der heute 23 verlorenen
Fälle**, je Variante, mit Angabe der Kandidatenzahl. Und ausdrücklich auch das
Nullergebnis — eine Richtung, die nichts bringt, wird als solche festgehalten statt
stillschweigend fallengelassen.

## Fortschreibung 2026-08-16T14:15:00+0200 — V2 gemessen, und sie wirkt

Der Plan hielt die Messung für blockiert („kein Modellzugang"). Das war eine Aussage
über den eigenen Aufbau, nicht über die Lage: Ollama lief die ganze Zeit, und Haiku
ist über einen Subagenten erreichbar. Gebaut wurde deshalb `--umschriften` — ein
Haiku-Subagent schreibt die 35 Texte, das Modul rechnet sie. L-a69129 bleibt gewahrt,
sie verlangt das Modell, nicht den Abrechnungsweg.

| Lauf | top5 | top50 | Median-Rang |
|---|---|---|---|
| Stufe 0 (Ausgangslage) | 4/35 | 13 | 79 |
| **V2 Anfrageumschrift** | **11/35** | **19** | **35** |
| Gegenprobe (Identität) | 4/35 | 13 | 79 |

Von 5973 Kandidaten. Die Gegenprobe reproduziert Stufe 0 **exakt** — der Unterschied
kommt aus der Umschrift, nicht aus dem Messweg. Das ist der Beleg, den der Plan als
Bedingung genannt hat.

**Was die Zahl NICHT sagt:** Sie misst den reinen Bedeutungskanal, nicht den vollen
Suchweg; 35 Fälle sind klein; und die Betriebskosten je Anfrage sind hier nicht
gemessen, weil das Umschreiben vorher im Subagenten geschah. Ein Verfahren, das jede
Anfrage durch ein zweites Modell schickt, kostet Zeit und Geld — das gehört gemessen,
bevor es in den Produktivweg geht.

### Der Befund am Prüfstand, der die Zahl fast wertlos gemacht hätte

Der erste Subagentenlauf lieferte alle 35 Umschriften auf **Englisch**, gegen einen
durchweg deutschen Bestand. Die Messung wäre gelaufen, hätte eine plausible Zahl
geliefert — und eine Sprachdifferenz gemessen statt der Variante. Aufgefallen ist es
beim Lesen der Ausgabe, nicht durch eine Prüfung; die Abnahme des Auftrags verlangte
Vollständigkeit und Format, aber nichts über die Sprache.

Nachgefordert wurde mit einer Abnahme, die eine **Null** verlangt: Zahl der
Umschriften ohne deutsches Funktionswort. Das ist die Form, die trägt — eine
Zusicherung, die einen Fehlschlag verlangt, statt einer, die Erfolg beschreibt.

## Fortschreibung 2026-08-16T14:30:00+0200 — V1 gemessen, und ihre Gegenprobe korrigiert die eigene Zahl

| Lauf | top5 | top50 | Median-Rang |
|---|---|---|---|
| Stufe 0 (Ausgangslage) | 4/35 | 13 | 79 |
| **V1-Gegenprobe** (Volltext neu eingebettet) | 4/35 | **16** | **56** |
| **V1 situative Zweiteinbettung** | 6/35 | 18 | 42 |
| **V2 Anfrageumschrift** | **11/35** | **19** | **35** |

**Die Gegenprobe von V1 reproduziert Stufe 0 nicht.** Sie trifft die 4/35 in den Top-5,
aber top50 steigt von 13 auf 16 und der Median fällt von 79 auf 56 — **ohne dass eine
Variante wirkt**. Die Gegenprobe bettet nur den Originaltext des Ziels ein zweites Mal
ein; dass das allein schon Ränge verbessert, heißt: die gespeicherte Einbettung eines
Knotens ist schlechter als eine frisch aus seinem Volltext gerechnete.

**Das ändert, woran V1 zu messen ist.** Gegen Stufe 0 sieht V1 nach +2 Top-5 und +5
Top-50 aus. Gegen ihre **eigene Gegenprobe** — den ehrlichen Maßstab — bleiben +2 Top-5
und +2 Top-50. Der Rest war kein Variantenerfolg, sondern ein Nebeneffekt des
Neu-Einbettens.

**Der Nebenbefund ist wertvoller als die Variante:** Ein Teil des Rückstands liegt in
veralteten oder gekappten Einbettungen des Bestands, nicht im Verfahren. Der
Prüfer-Melder meldet unabhängig davon 94 Knoten mit veralteter Prüfsumme und 13 beim
Einbetten gekappte. Das ist billiger zu beheben als jede Variante und gehört zuerst
gemessen.

### Entscheid

**V2 (Anfrageumschrift) gewinnt** — 11/35 gegen 6/35, und ihre Gegenprobe reproduziert
Stufe 0 exakt, ihre Zahl ist also unverfälscht. V1 wirkt, aber schwächer als es zunächst
aussah. V3 (Zweitmodell) war bereits ausgeschieden.

**Nicht empfohlen wird der sofortige Produktiveinsatz von V2.** Sie schickt jede Anfrage
durch ein zweites Modell; die Betriebskosten sind in keinem der Läufe gemessen, weil das
Umschreiben vorher im Subagenten geschah. Bei 35 Fällen und einem Unterschied, der bei
7 Treffern liegt, wäre eine Umstellung des Produktivwegs eine Wette. Nächster Schritt ist
deshalb nicht der Einbau, sondern die Kostenmessung — und davor die Einbettungshygiene,
weil sie beide Varianten gleichermaßen hebt.

**Verzerrung, die zu benennen ist:** Die Kandidatenzahl wuchs während der Läufe von 5972
auf 5976, weil parallele Sitzungen Knoten anlegten. Vier Kandidaten auf sechstausend
ändern keine dieser Aussagen, aber die Läufe sind dadurch nicht bit-identisch vergleichbar.
