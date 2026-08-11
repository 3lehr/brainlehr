# S12, zweiter Anlauf — 2026-08-11T23:40:00+0200

Der erste Anlauf steht seit dem 2026-08-09 auf AUS: zwei billige Stufen
verbesserten nichts, die teure wurde nie gebaut. Dieser Plan baut nicht die
teure, sondern zeigt, dass die Frage falsch gestellt war.

## Ist-Stand, gemessen

| | Zahl | Quelle |
|---|---|---|
| Prüffälle, kontaminationsfrei | 78 (aus 2518 eindeutigen Nachrichten) | `runs/echtkorpus_2026-08-11T2300.json` |
| davon Fragen / Aufträge | 6 / 72 | ebenda |
| Nulllinie Abrufgüte | 15 von 35 | Gesamtplan |
| Stichwortkanal, eigener Beitrag | 0 gerettete Fälle über 6 Gewichte | Gesamtplan |
| Neuformulierung von 20 Zielknoten | 3 → 10 von 20, mit zweitem Kanal 13 | Knoten `b4238789` |
| Kontrollarm reine Textverdopplung | 4 von 20 | ebenda |

Die letzten beiden Zeilen sind der Grund für diesen Plan. Der größte gemessene
Sprung im ganzen Haus kam **nicht** aus einer Änderung am Abruf, sondern aus
einer Änderung am Text. Und der Kontrollarm schließt die naheliegende
Erklärung aus: es liegt nicht an der Menge der Zeichen.

## Die drei Wege, und warum zwei ausscheiden

**Weg 1 — Anfrage per Modellaufruf umschreiben.** Der Stand der Technik
(HyDE). Ausgeschieden, aber nicht aus dem alten Grund: Ein Modellaufruf je
Prompt trifft **jede** Sitzung, auch die 18,3 %, die den Haltepunkt gar nicht
erreichen, und die Mehrheit der Prompts, für die es nichts zu finden gibt. Der
Preis fällt immer an, der Nutzen nur manchmal.

**Weg 2 — die echte Antwort als Suchanfrage** (Vorschlag des Betreibers,
`L-33aae1`). Kostet keinen zusätzlichen Modellaufruf, weil die Antwort ohnehin
entsteht. Ausgeschieden für **diesen** Schritt, nicht grundsätzlich: Die
Antwort liegt erst vor, wenn die Arbeit getan ist. Als Abruf **vor** der
Antwort ist sie unbrauchbar; als Werkzeug, um den Speicher hinterher zu
verknüpfen, ist sie stark — das ist ein eigener Schritt und gehört auf die
Kantenlinie, nicht hierher.

**Weg 3 — den Bestand in die Sprache der Frage bringen.** Gewählt. Er hat als
einziger eine gemessene Wirkung im eigenen Haus, er kostet **einmal** statt je
Prompt, und er wirkt auf allen drei Lesewegen zugleich, auch auf dem
Pfadschlüssel.

## Was gebaut wird

Die drei Schreibregeln aus `b4238789`, angewandt auf den Bestand:
Titel benennt die Sache statt ihrer Herkunft · Zusammenfassung trägt die
Kernaussage statt einer Verwaltungsformel · Volltext nennt jeden Begriff
mehrfach und unterschiedlich.

Erzeugt wird das je Knoten einmal, mit einem nicht-lokalen Modell (Rolle
`erzeugen`, Modellsperre gilt). Der alte Text bleibt stehen — die neue Fassung
tritt **neben** ihn, nicht an seine Stelle. Grund: Eine Neuformulierung, die
den Sachgehalt verschiebt, wäre sonst nicht mehr auffindbar, und der
Prüfspruch hinge an einem Text, den es nicht mehr gibt.

## Die Falle, an der dieser Plan scheitern würde

Der Korpus enthält 78 Fälle, deren Ziele bekannt sind. Formuliert man **diese**
Zielknoten neu und misst dann an ihnen, misst man sich selbst — genau das
Tuning-Maximum, das heute schon einmal zurückgenommen wurde.

Deshalb bindend: Der Bestand wird in zwei Hälften geteilt, **bevor** irgendein
Text entsteht. Eine Hälfte wird neu formuliert, die andere nicht. Gemessen wird
an beiden. Die Zahl, die zählt, ist die Differenz — und die Hälfte ohne
Behandlung ist die Positivkontrolle, die sagt, ob überhaupt etwas gemessen
wurde.

## Reihenfolge, und wo sie bindend ist

1. Teilung des Bestands und Festschreiben der Zuordnung. **Vor** allem anderen,
   sonst ist die Trennung nachträglich behauptet statt hergestellt.
2. Messung der Ausgangslage getrennt je Hälfte. Sind die Hälften schon vorher
   unterschiedlich gut, ist die spätere Differenz wertlos.
3. Neuformulierung nur der behandelten Hälfte.
4. Messung, getrennt je Hälfte, mit denselben Deckeln wie im Betrieb (10/7).

## Was bewusst nicht getan wird

Kein Modellaufruf je Prompt. Keine Änderung an Verschmelzung, Gewichten oder
Deckeln in diesem Schritt — sonst misst man zwei Dinge und liest das Ergebnis
als eines. Keine Neuformulierung der Lehren; sie tragen mit `description`,
`root_cause`, `resolution`, `prevention` bereits vier Textfelder und sind damit
ein anderer Fall.

## Woran sich Erfolg messen lässt

Die behandelte Hälfte gewinnt gegenüber der unbehandelten, gemessen an
denselben 78 Fällen, mit Nenner je Hälfte. Gewinnt sie nicht, ist das ein
Ergebnis und wird als solches festgehalten — die Neuformulierung wird dann
nicht ausgerollt, und `b4238789` bekommt einen Widerspruch angehängt.

Die Gegenrichtung ist ausdrücklich vorgesehen: Verliert die behandelte Hälfte,
ist die Erklärung nicht „falsch umgesetzt", sondern zuerst „die Regeln aus
`b4238789` galten für 20 handverlesene Knoten und tragen nicht über den
Bestand".
