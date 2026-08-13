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

## Aufträge, fertig zum Übergeben

**Für alle Aufträge gleichermaßen gilt:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis` — ein
Startverzeichnis unter `.claude/worktrees/` ist ein alter Stand. Zuerst
`CLAUDE.md` lesen, dann diesen Plan. „Sieht der Code anders aus als hier
beschrieben, halte dich an den Code und melde die Abweichung." Kein `git add
-A`, kein Push, kein `git stash`. Committen mit expliziter Pfadliste
(`git commit -- pfad1 pfad2`), weil mehrere Agenten im selben Baum arbeiten.
Volle Suite **im Vordergrund** mit `timeout=600000` — sie braucht rund 230
Sekunden. Datenbanknamen nie fest verdrahten, immer über `kern/speicher`.
Schreibende Läufe **nicht** parallel zu einem Suitelauf starten: `knowledge.db`
war deswegen schon zweimal stundenlang für jeden Schreiber gesperrt
(`L-f3edbf`).

### Schritt 1 · Kantentyp statt Spalte, rückwirkend an 125 Fällen belegt

| | |
|---|---|
| **Darf ändern** | ein neues Werkzeug unter `kern/` für den Rückwärtslauf, dazu sein Test |
| **Tabu zusätzlich** | `knowledge_mcp_server.py` und `schema.sql` — die gehören Schritt 2, und zwei Agenten in derselben Funktion verlieren Arbeit |
| **Fakten** | `abgeleitet_von` ist bei 1 von 2165 Knoten gesetzt. Kanten: `aehnlich_bedeutung` 5814, `lesson_mentions_file` 43, `analogous_to` 10, `supports` 5, `constrains` 3. Rückwirkend belegbar: 83 Knoten nennen eine existierende Lehre `L-xxxxxx`, 56 einen existierenden Knoten (8 hex), 14 beides — zusammen 125. |
| **Abnahme** | Rot vor grün: vorher 1 Herkunftsangabe, nachher mindestens 125 Kanten. Negativfall: ein Knoten ohne jeden Verweis bekommt **keine** Kante — ein Verfahren, das überall etwas findet, findet nichts. Grenzwert: eine Zeichenkette im Format `L-xxxxxx`, die es nicht gibt, erzeugt keine Kante und wird **gemeldet**, nicht verschluckt. |

### Schritt 2 · Vorwärts beim Schreiben, gemeinsam mit Aufgabe 78

| | |
|---|---|
| **Darf ändern** | `knowledge_mcp_server.py` (`knowledge_add`), `schema.sql`, dazu die Tests dieser Funktion |
| **Tabu zusätzlich** | das Werkzeug aus Schritt 1 — es ist dann fertig und wird nur noch gelesen |
| **Fakten** | Nur 256 von 2165 Knoten tragen überhaupt eine Sitzungskennung (12 %). `lesson_record` prüft vor dem Schreiben auf Ähnlichkeit, `knowledge_add` an keiner Stelle. Bekannte Falle `L-183517`: `lesson_record` legt die Zeile an und meldet die Ähnlichkeit **danach** — das erzwingt drei Aufrufe. Beim Knoten gehört die Prüfung **vor** das Schreiben. |
| **Abnahme** | Rot vor grün an der belegten Reihe: Der dritte Achsen-Knoten muss beim Anlegen die beiden älteren als Hinweis erhalten. Ein Verfahren, das genau diesen Fall nicht findet, ist nicht gebaut. Negativfall: ein inhaltlich neuer Knoten erzeugt **keinen** Hinweis. |

### Schritt 3 · Die Spalte entfernen

| | |
|---|---|
| **Darf ändern** | `schema.sql`, alle lesenden Stellen der Spalte, deren Tests |
| **Tabu zusätzlich** | nichts Weiteres — dieser Schritt läuft allein, weil er Struktur ändert |
| **Fakten** | Der eine gefüllte Fall ist `cb56f7d1` → `db0a448b`. Er muss vorher als Kante vorliegen, sonst geht die einzige echte Angabe verloren. |
| **Abnahme** | Rot vor grün: Ein Test, der die Spalte liest, ist vorher grün und nachher rot — und wird mit entfernt. Der Fall `cb56f7d1` ist danach als Kante auffindbar, gezählt statt angenommen. |
