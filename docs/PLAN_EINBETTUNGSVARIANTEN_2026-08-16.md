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

 ist der Grund für diesen Abschnitt: Dort liefen Vorher- und Nachher-Messung
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
