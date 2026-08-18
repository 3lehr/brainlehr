# Plan: Prüfstein zu `L-0e0ab6` — „Der Prüfstand ist nie die Wirklichkeit"

**Stand** 2026-08-18T06:05:00+0200
**Verhältnis zum geltenden Plan:** untergeordnet zu `docs/PLAN_GESAMT_2026-08-13.md`,
Sprintbezug S8 (Prüfer, die urteilen statt zählen). Kein Ablösen.

## Gemessener Ist-Stand

- `L-0e0ab6` hat **7 Vorkommen** und ist in `berichte/vorschlag.py --bericht` der
  oberste Prüfstein-Kandidat. Ein Prüfstein existiert nicht: die Kennung kommt in
  keiner `.py` des Repos vor.
- Die Lehre ist in `~/.claude/CLAUDE.md` bereits zur Regel eskaliert (vier Auflagen
  vor jedem Messlauf). Sie hat damit Text, aber keinen Mechanismus — genau die
  Bauform, gegen die brainlehr existiert.
- Heute, in dieser Sitzung, achtes Vorkommen in Miniatur (`L-234e85`): Ein rotes
  Gate war rot aus dem falschen Grund. **Gefangen hat es allein `strict=True`.**
- Bestand gemessen: 19 `xfail`-Fundstellen in `tests/`, davon **13 ohne
  `strict=True`**.

> **BERICHTIGT 2026-08-18T06:20:00+0200.** Diese beiden Zahlen sind falsch. Sie
> stammen aus `grep` über das *Wort* `xfail` und zählten Kommentare, Docstrings
> und Erwähnungen mit. Über den Syntaxbaum gemessen gibt es **7 echte Marker**,
> davon **einen ohne `strict=True`** — und der ist im eigenen Docstring
> ausdrücklich als gewollt begründet. Gemeldet hat das der ausführende Agent
> gegen meine Vorgabe; genau dafür steht der Satz „halte dich an den Code und
> melde die Abweichung" in jedem Auftrag. Der Plan behält seine Richtung: die
> Zahl war das Argument für die Dringlichkeit, nicht für die Engstelle. Aber sie
> war ein Messfehler derselben Klasse, gegen die dieser Prüfstein gebaut wird —
> ein Zählwerkzeug, das etwas anderes zählt als die Sache.

## Die Engstelle, und warum dort

Die sieben Vorkommen haben verschiedene Symptome (Harness strenger, großzügiger,
schmaler, sprachlich verschoben) und lassen sich **nicht** durch ein einziges
Prädikat erkennen — wer das versucht, baut einen Prüfer, der Vertrauen vortäuscht.

Gemeinsam ist ihnen der **Melder**, der sie tatsächlich gefangen hat: die Stelle,
an der ein erwartetes Rot plötzlich Grün ist. Genau das meldet `xfail(strict=True)`
und verschluckt das gewöhnliche `xfail`. Der Prüfstein sitzt deshalb dort — nicht
an der Lehre selbst, sondern an ihrem einzigen belegten Detektor.

## Was gebaut wird

Ein Prüfstein `tests/test_pruefstand_ehrlichkeit.py` mit zwei Prädikaten über
`tests/`:

- **A — kein stummes Rot.** Jede `pytest.mark.xfail`-Markierung trägt
  `strict=True` und ein `reason=`. Ohne `strict` wird ein XPASS nicht gemeldet,
  und damit fehlt der Melder, der heute als einziger anschlug.
- **B — kein rotes Gate ohne Positivfall.** Eine Testdatei, die ausschließlich aus
  `xfail`-Tests besteht, misst ihren eigenen Prüfstand: nichts belegt, dass der
  Prüffall bis zur gemessenen Stelle überhaupt durchkommt. Sie braucht mindestens
  einen nicht-`xfail`-Test.

## Alternativen, und warum verworfen

- **Statische Suche nach Mocks, die ein Feld fest verdrahten.** Verworfen: nicht
  entscheidbar ohne zu wissen, welche Fachlogik das Feld liest; erzeugt Rauschen
  und wird abgeschaltet.
- **Pflichtfeld „Weg der Erhebung" in jeder Datei unter `runs/`.** Verworfen:
  `melder/rasterblick.py` besetzt diese Familie bereits, und die 61 offenen
  Rastervermerke stammen aus fremden Sitzungen.
- **Nur eine Lint-Regel statt eines Tests.** Verworfen: es gibt keinen Linter im
  pre-push, aber `pytest` läuft ohnehin.

## Reihenfolge, bindend

1. Prüfstein schreiben, **rot** gegen den heutigen Bestand (13 Fundstellen ohne
   `strict`) — das Rot ist der Beleg, nicht die Behauptung.
2. Die 13 Fundstellen einzeln ansehen: `strict=True` nachtragen **oder**, wo ein
   Test bewusst nicht strikt sein soll, das mit Begründung ausnehmen. Fremde,
   uncommittete Testdateien bleiben unangetastet und werden gemeldet.
3. Erst danach grün.

## Was bewusst nicht getan wird

Der Prüfstein prüft **Bauform, nicht Wahrheit**: Wer `strict=True` schreibt und
die Probe nie fährt, kommt durch. Er verwandelt eine unsichtbare Unterlassung in
eine sichtbare Falschaussage — dieselbe erklärte Grenze wie bei
`melder/ablaufpflicht.py`, und mehr ist maschinell nicht zu haben.

## Woran sich Erfolg misst

Nicht an grünem Lauf, sondern an einer Zahl: Beim nächsten Vorkommen dieser Klasse
muss der Melder anschlagen, nicht der Betreiber fragen. Zwischenmaß heute:
`L-0e0ab6` wird von `berichte/vorschlag.py` nicht mehr als unbehandelter
Kandidat geführt, weil die Kennung im Prüfstein steht.
