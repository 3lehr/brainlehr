# Herkunftskette — woraus ein Knoten entstand

Stand 2026-08-13T08:05:00+0200. Aufgabe 73, mit bindender Kopplung an Aufgabe 78.

## Der gemessene Ist-Stand

| | Befund |
|---|---|
| `abgeleitet_von` gefüllt | **1 von 2165** — ein einziger echter Fall (`cb56f7d1` → `db0a448b`) |
| Kanten insgesamt | `aehnlich_bedeutung` **5814**, `lesson_mentions_file` 43, `analogous_to` 10, `supports` 5, `constrains` 3 |
| Lehren mit `node_path` | 122 von 833 |
| Knoten mit Sitzungskennung | 256 von 2165 (12 %) |

**Rückwirkend belegbar** (Verweis steht wörtlich im Text des Knotens):

| Quelle | Knoten |
|---|---|
| nennen eine existierende Lehre `L-xxxxxx` | 83 |
| nennen einen existierenden Knoten (8 hex) | 56 |
| beides | 14 |
| **zusammen, ohne Doppelzählung** | **125** von 2165 = 5,8 % |

## Die Entscheidung, die vor dem Füllen steht: Spalte oder Kante

**A — Die Spalte `abgeleitet_von` füllen.** Abgelehnt. Sie trägt **einen**
Vorgänger. Abgeleitetes Wissen hat fast immer mehrere — der eine belegte Fall
im Bestand ist die Ausnahme, nicht die Regel. Und sie ist ein zweiter Ort für
eine Tatsache, für die es bereits eine Tabelle gibt.

**B — Kantentyp `abgeleitet_von` in `knowledge_relations` (gewählt).**
Beliebig viele Vorgänger, ein Ort, und die Graphabfrage funktioniert schon.
Die Spalte wird danach **entfernt**, nicht stehengelassen — eine Spalte, die
dasselbe schlechter kann, wird beim nächsten Lesen für den Wahrheitsort
gehalten.

**C — Beides.** Abgelehnt ohne Diskussion: zwei Orte für eine Tatsache, die
auseinanderlaufen, sobald einer gepflegt wird.

**Nebenwirkung, die für B spricht:** Der Kantenbestand ist zu 99 %
`aehnlich_bedeutung` — dicht in der Dimension „sieht ähnlich aus", leer in der
Dimension „hängt voneinander ab". Ein Abhängigkeitstyp ist genau das, was dem
Graphen fehlt, und er entsteht hier nebenbei.

## Zwei Quellen, und ihr Verhältnis ist der Kern des Plans

**Vorwärts, die eigentliche Quelle:** `knowledge_add` hält beim Schreiben fest,
was in dieser Sitzung vorher gelesen wurde. Das ist der einzige Moment, in dem
die Herkunft ohne Raten bekannt ist.

**Rückwirkend, exakt aber klein:** die 125 Knoten mit wörtlichem Verweis. Sie
sind **nicht** die Lösung, sondern die **Positivkontrolle** — an ihnen muss sich
das Verfahren messen lassen, bevor irgendjemand ihm etwas glaubt.

**Was ausdrücklich NICHT gemacht wird:** die übrigen ~2040 Knoten über
Sitzungsnähe oder Ähnlichkeit „auffüllen". Nur 12 % tragen überhaupt eine
Sitzungskennung, und eine geratene Herkunft ist schlechter als eine leere: Ein
leeres Feld sagt „unbekannt", ein falsch gefülltes sagt „belegt". Der Preis ist,
dass die Spalte lange dünn bleibt. Das ist der richtige Preis.

## Bindende Kopplung an Aufgabe 78

Beide Aufgaben ändern **dieselbe Funktion** — `knowledge_add` soll beim
Schreiben (a) nach inhaltlich nahen Knoten suchen und (b) die Herkunft
festhalten. Zwei Agenten in derselben Funktion verlieren garantiert Arbeit.

**Reihenfolge: 78 zuerst.** Die Dublettenerkennung sucht ohnehin vor dem
Schreiben nach nahen Knoten — genau die Suche, aus der die Herkunftskandidaten
fallen. Andersherum müsste sie zweimal gebaut werden.

## Woran sich Erfolg misst

- **Rot vor grün an den 125:** Ein Lauf über den Bestand muss aus ihnen Kanten
  erzeugen. Vorher 1 Herkunftsangabe, nachher mindestens 125 Kanten.
- **Negativfall:** Ein Knoten ohne jeden Verweis darf **keine** Kante bekommen.
  Ein Verfahren, das überall etwas findet, findet nichts.
- **Grenzwert:** Ein Text, der eine Zeichenkette im Format `L-xxxxxx` nennt, die
  es **nicht** gibt, erzeugt keine Kante — und wird gemeldet, nicht verschluckt.
- **Die Spalte `abgeleitet_von` ist danach weg**, nicht nur unbenutzt.
