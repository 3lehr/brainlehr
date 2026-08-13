# ADR-005 · Von vier W-Fragen bekommt genau eine ein Feld

Stand 2026-08-13T21:50:00+0200 · Aufgabe 75 · Status: entschieden

## Die Messung, die alles andere entscheidet

Füllstand über 2181 Knoten, heute erhoben:

| Feld | Art | gefüllt |
|---|---|---|
| `source` | **Pflicht** | 100,0 % |
| `freigabe` | **Pflicht** | 100,0 % |
| `anlass` | **Pflicht** | 100,0 % |
| `norm_entschieden_von` · `norm_entschieden_grund` | freiwillig | 12,0 % |
| `gilt_ab` | freiwillig | 3,8 % |
| `gilt_bis` | freiwillig | 0,1 % |
| `abgeleitet_von` (Spalte) | freiwillig | 0,0 % |
| `norm_entschieden_belegart` | freiwillig | 0,0 % |

**Der natürliche Versuch steckt in `anlass`.** In der Aufgabenbeschreibung vom
selben Tag stand es mit **85 %** — damals halbpflichtig. Heute steht es bei
**100 %**. Dazwischen liegt nur eines: Es wurde Pflicht.

Damit ist die Bauregel nicht mehr Behauptung, sondern gemessen an einem
Feld, das den Übergang selbst gemacht hat: **Ein Feld wird gefüllt, weil es
Pflicht ist, nicht weil es nützlich ist.** Alle sieben freiwilligen Felder
liegen unter 12 %, vier davon bei null.

## Die Entscheidung je Frage

### 1 · Woran erkennt man, dass es falsch ist — **kein eigenes Feld**

Eine Falsifikationsbedingung gibt es nur für Sätze, die etwas behaupten. Ein
Gesetzeswortlaut, ein Zitat, ein Nachschlagewerk-Eintrag hat keine. Ein
Pflichtfeld an dieser Stelle würde in drei Vierteln des Bestands mit einer
Verlegenheitsformel gefüllt — und eine Verlegenheitsformel ist schlimmer als
eine Leerstelle, weil sie Vollständigkeit vortäuscht.

Sie gehört in den Text, und zwar an den Anfang des Befunds.

### 2 · Wie sicher — **Feld, und zwar Pflicht**

`herkunftsart` mit vier Werten: `gemessen` · `fremdberichtet` · `abgeleitet` ·
`plausibel`.

Diese Frage ist die einzige der vier, die auf **jeden** Knoten anwendbar ist —
auch auf ein Zitat (fremdberichtet) und auf einen Gesetzestext (fremdberichtet).
Sie kostet beim Schreiben eine Sekunde und beantwortet die Frage, die heute
mehrfach Schaden angerichtet hat: Der Unterschied zwischen „33 von 205
gemessen" und „der Nachbar veröffentlicht 63 Prozent" ist die halbe Wahrheit
eines Satzes. Mehrfach wurde heute eine Zahl aus einem Agentenbericht wie eine
eigene Messung weitergetragen.

### 3 · Für welche Menge gilt es — **kein eigenes Feld**

Der Geltungsbereich ist bei den meisten Knoten „alles" und damit leer.
Ein Pflichtfeld erzeugt hier „gilt allgemein" in Serie. Er gehört in den
**ersten Satz der Zusammenfassung**, wo er den Satz überhaupt erst wahr macht.

### 4 · Was hängt daran — **kein Feld, eine Abfrage**

Belegt an echten Daten: Die Gegenrichtung ist über `knowledge_relations`
bereits beantwortbar, 229 Kanten vom Typ `abgeleitet_von`. Beispiel: vier
Knoten leiten sich von `L-47cd16` ab, vier von `L-352afa`.

**Nebenbefund, der eine eigene Aufgabe verdient:** `abgeleitet_von` existiert
**zweimal** — als Spalte in `knowledge_nodes` (1 von 2181 gefüllt, faktisch
tot) und als Kantentyp (229 Kanten, lebendig). Zwei Orte für dieselbe Aussage,
und der eine täuscht Leere vor, wo der andere Daten hat.

## Was bewusst nicht getan wird, samt Preis

- **Keine vier Felder.** Preis: Drei der vier Fragen bleiben Disziplin statt
  Mechanik. Grund: Die Messung oben sagt, dass genau das nicht funktioniert —
  aber ein Feld, das nicht überall anwendbar ist, kann nicht Pflicht werden,
  und freiwillig wäre es tot. Die Wahl ist nicht zwischen Feld und Disziplin,
  sondern zwischen einem gefüllten Feld und vier leeren.

## Die Sperre, die den Einbau bestimmt

**Ein neues Pflichtfeld, per Datenbank-Trigger erzwungen, blockiert laufende
Sitzungen.** Genau das ist heute passiert: Der `norm_art`-Trigger wies jeden
deutschen Plural ab und legte fremde Sitzungen lahm, weil MCP über stdio
bedeutet, dass jeder Klient seinen eigenen Serverprozess startet und es keinen
zentralen Neustart gibt.

Daraus die bindende Reihenfolge für `herkunftsart`:
1. Spalte anlegen mit Vorgabewert — kein Trigger. Alte Aufrufer laufen weiter.
2. Der Schreibpfad füllt sie, wo er es weiß.
3. Erst wenn der Bestand hoch genug ist, wird sie erzwungen — und die
   installierte Fassung des Triggers wird danach gelesen, nicht die Datei.

## Woran sich Erfolg misst

`herkunftsart` erreicht binnen einer Woche einen Füllstand über 90 % — wie
`source`, `freigabe` und `anlass` — statt unter 12 % wie jedes freiwillige
Feld. Wird es das nicht, war die Bauregel falsch und die Entscheidung ist zu
widerrufen.

## Aufträge, fertig zum Übergeben

| | |
|---|---|
| **Tabu für alle Schritte** | Kein Trigger, der schreibende Aufrufe abweist, solange fremde Sitzungen laufen. `~/.claude/` und `app/` bleiben unberührt. |

### Schritt A · `herkunftsart` als Spalte mit Vorgabewert

| | |
|---|---|
| **Darf ändern** | `schema.sql`, `kern/` (Schreibpfad), `tests/` |
| **Fakten** | Vier Werte: `gemessen`, `fremdberichtet`, `abgeleitet`, `plausibel`. Füllstand freiwilliger Felder heute: 12 %, 3,8 %, 0,1 %, 0,0 %, 0,0 %. Füllstand der Pflichtfelder: 100 %. `anlass` stieg von 85 % auf 100 %, als es Pflicht wurde. |
| **Abnahme** | Ein Schreibvorgang ohne `herkunftsart` läuft weiterhin durch (alte Aufrufer, laufende Sitzungen) und setzt den Vorgabewert. Rot-Probe: ein Aufruf mit unzulässigem Wert wird abgewiesen und nennt die vier erlaubten. Negativfall: ein Aufruf mit gültigem Wert speichert ihn unverändert. Grenzwert: leerer String — er ist nicht dasselbe wie fehlend und muss entschieden und geprüft sein. |
| **Einsatz** | Der Unterschied zwischen gemessen und fremdberichtet ist heute mehrfach verlorengegangen; eine Agentenzahl wurde als eigene Messung weitergetragen. |

### Schritt B · Die tote Spalte `abgeleitet_von` auflösen

| | |
|---|---|
| **Darf ändern** | `kern/`, `tests/`, `schema.sql` |
| **Fakten** | Spalte `knowledge_nodes.abgeleitet_von`: 1 von 2181 gefüllt. Kantentyp `abgeleitet_von` in `knowledge_relations`: 229 Kanten. Zwei Orte für dieselbe Aussage. |
| **Abnahme** | Die eine gefüllte Zeile wird als Kante übernommen, danach ist die Spalte nachweislich leer und wird entfernt oder ausdrücklich als stillgelegt gekennzeichnet. Rot-Probe: Vor dem Umzug findet eine Abfrage über die Kanten diesen einen Fall NICHT, danach schon. Negativfall: Die 229 vorhandenen Kanten bleiben unverändert. |
| **Einsatz** | Eine Spalte bei 0,0 % neben einer Kantentabelle mit 229 Einträgen meldet Leere, wo Daten liegen — und der Prüfer meldet sie seit Tagen als „gebaute Regel ohne Wirkung". |

**Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.**
