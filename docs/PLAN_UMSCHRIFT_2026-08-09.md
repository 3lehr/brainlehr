# Plan: Was koennte der Abruf, wenn jeder Knoten sauber geschrieben waere?

Stand 2026-08-09T13:40:00+0200. Frage des Betreibers: liegt der Abrufrueckstand
an den historisch gewachsenen Knoten? Statt brainlehr in einer Sandbox neu
aufzubauen (siehe Verworfene Wege) wird die Obergrenze an genau den 20
Zielknoten des Pruefkorpus gemessen.

## Ist-Stand, gemessen

- Abrufguete auf der Betriebs-DB und auf der Arbeitskopie identisch: **LESSON 4/15, NODE 3/20**.
- Textmenge sagt nichts ueber den Rang: Spearman **-0,12** (n=20).
- Alter sagt nichts: Treffer wie Fehlschlaege liegen zwischen 01. und 07.08.
- Einziges erkennbares Muster: alle drei Node-Treffer tragen Eigennamen
  (Verwalterwahl, Brennertausch, EFBE) — die paraphrasiert der Korpus nicht.
- 101 von 384 Knoten des Arbeitsbestands (26 %) haben keinen `content`.

## Ablauf, Reihenfolge bindend

1. Arbeitskopie der DB (`scratchpad/probe.db`), Nulllinie darauf gemessen: 7/35. **Erledigt.**
2. Die 20 Zielknoten exportiert (`los1.json`, `los2.json`). **Erledigt.**
3. Zwei Subagenten schreiben je 10 Knoten um — **blind**, siehe Voraussetzung.
4. Umschriften in die Arbeitskopie schreiben, Vektoren fuer genau diese 20 neu.
5. Erneut messen. Erst danach wird ueber die Betriebs-DB entschieden.

## Die Voraussetzung, ohne die die Messung wertlos ist

Der umschreibende Agent darf `runs/pruefkorpus.jsonl` **nicht** sehen und nicht
wissen, dass es einen Pruefkorpus gibt. Sonst schreibt er die erwartete Antwort
in den Knoten und die Messung misst sich selbst. Er bekommt nur den Knoten und
die Schreibregeln.

## Negativkontrolle, eingebaut

Die 15 Lehren bleiben unangetastet. `LESSON` muss nach dem Lauf **4/15** sein.
Aendert sich diese Zahl, hat der Eingriff mehr veraendert als die 20 Knoten und
die ganze Messung ist zu verwerfen — nicht nur der NODE-Wert.

## Was bewusst nicht getan wird, und der Preis

- **Kein Neuaufbau in der Sandbox.** Wer Knoten und Fragen vom selben Modell
  bauen laesst, misst die Aehnlichkeit zweier Ausgaben, nicht Abruf. Preis: wir
  erfahren nichts darueber, wie ein von Grund auf methodisch gebauter Bestand
  sich verhaelt — nur, was Umschreiben am echten Bestand bringt.
- **Kein Schreiben in die Betriebs-DB** vor dem Ergebnis. Preis: ein
  Kopierschritt und der Zwang, den Lauf spaeter zu wiederholen.
- **Die 101 Knoten ohne `content` bleiben unberuehrt.** Sie sind eine eigene
  Baustelle, kein Teil dieser Frage.

## Woran sich Erfolg misst

NODE steigt von 3/20 messbar an, waehrend LESSON bei 4/15 bleibt. Bleibt NODE
bei 3/20, ist die Schreibseite als Hebel widerlegt und der Rest der Arbeit
gehoert auf die Anfrageseite (Umformulierung durch ein Modell).

## Ergebnis, 2026-08-09T14:10:00+0200

`runs/umschrift_ergebnis_2026-08-09.json`, Texte in
`runs/umschrift_neu1|neu2|knoten_ist_2026-08-09.json`.

| Arm | Zeichen/Knoten (Median) | NODE Kanal AUS | NODE Kanal AN |
|---|---:|---:|---:|
| Ist | 2537 | 3/20 | 4/20 |
| nur Laenge verdoppelt | 5075 | 4/20 | 5/20 |
| **umgeschrieben** | 3257 | **10/20** | **13/20** |

Gesamt ueber alle 35 Faelle: 7/35 → 14/35 → 17/35.

**Der Kontrollarm entscheidet die Frage.** Er traegt MEHR Text als die Umschrift
(5075 gegen 3257 Zeichen) und bringt fast nichts (4/20). Es ist die
Schreibweise, nicht die Menge — und damit ist auch der fruehere Befund
bestaetigt, dass Textmenge und Rang nicht zusammenhaengen (Spearman -0,12).

**Negativkontrolle gehalten:** LESSON bleibt im Umschrift-Arm 4/15 in beiden
Kanalzustaenden. Im Laengen-Arm faellt LESSON bei angeschaltetem zweiten Kanal
auf 3/15 — aufgeblaehte Knoten verdraengen Lehren aus der GEMEINSAMEN
Kandidatenliste. Wer Knoten aufblaeht, schadet den Lehren.

**Was diese Messung nicht sagt:** ob 20 umgeschriebene Knoten in einem Bestand
von 384 dieselbe Wirkung haben wie 384 umgeschriebene. Die 20 konkurrieren hier
gegen 364 unveraenderte — bei vollstaendiger Umschrift steigt auch die
Konkurrenz. Die Zahl ist ein Beleg fuer die Richtung, keine Prognose fuer den
Endstand.

**Offen, Betreiberentscheidung:** die Umschrift auf den echten Bestand
anwenden. Reichweite: 384 Knoten des Arbeitsbestands, davon 101 ohne `content`.
Kosten sind Subagenten-Laeufe, kein Betriebsrisiko — geschrieben wird zuerst
wieder auf einer Kopie.

## Zwei Nebenbefunde, gemessen statt vermutet

- `build_embeddings.py` achtet `BEGOD_KNOWLEDGE_DB` nicht (fest verdrahtetes
  `DB_PATH`, Zeile 36) — genau die Fehlerklasse, vor der `haken/ort.py` im
  eigenen Docstring warnt. Fuer diesen Lauf umgangen, nicht behoben.
- Die Herkunftsschranke (`knowledge_nodes_normrang_herkunft_bu`) greift auch
  beim UPDATE und hat zwei Direktiven-Knoten geschuetzt. Auf der Messkopie
  abgeklemmt und wieder gesetzt; in der Betriebs-DB unberuehrt.
