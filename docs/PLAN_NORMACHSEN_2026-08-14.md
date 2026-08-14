# Drei Achsen zu Ende bringen, eine tote Spalte klären

Stand 2026-08-14T13:30:00+0200. Vier Betreiberentscheidungen vom selben Tag,
alle vier auf Vorlage mit Empfehlung getroffen. Dieser Plan setzt sie um.

**Wortlaut der Entscheidungen**, weil zwei davon von der Empfehlung abweichen:

- Normachse 3: „Wert an der Herkunft" (Empfehlung übernommen).
- Normachse 2: „Dürfen und können scheinen mir wichtige Eigenschaften zu sein.
  Wenn dem so ist, entscheide du, ansonsten Sein und Sollen, erster Vorschlag."
- Gegenprobe-Altlast: „Als nicht rekonstruierbar abschließen" (Empfehlung).
- Token-Spalten: „Offen lassen, wir sind ein offenes System, wollen sogar
  vielleicht einen eigenen Klienten bauen. Außerdem, vielleicht kann Cloud das
  morgen doch — Hermes sollte dazu jetzt schon in der Lage sein."

## Kennungen: NA1–NA3, und warum dieser Plan hier nicht bleiben darf

Nachgetragen 2026-08-14 auf einen Befund der Grundarchitektur-Sitzung
(`L-30be01`): Abschnittskennungen kollidieren quer über die Pläne. Gemessen
mit deren Prüfgriff — `S1`, `S2`, `S3` bezeichnen je drei verschiedene Dinge,
und **„Schritt N" steht in zwölf Plandateien**. Dieser Plan war einer davon:
er kam mit eigener Zählung ab 1 neben `PLAN_GESAMT_2026-08-13.md` zu liegen,
statt eine Linie darin zu werden — genau der Fehler, den die Lehre beschreibt.

Bis zur Einhängung tragen die Schritte darum das Präfix `NA` (frei geprüft,
0 Treffer über alle `docs/*.md`). Das ist eine Notlösung, keine Korrektur:
**dieser Plan gehört als Linie in den Gesamtplan.** Getan wird das nicht
jetzt — die Grundarchitektur-Sitzung hält `PLAN_GESAMT_2026-08-13.md` gerade
und hängt dort Linie D und E ein; zwei Sitzungen in derselben Datei verlieren
garantiert Arbeit.

## Der gemessene Ist-Stand

| | Zahl | Quelle |
|---|---|---|
| Normen (Rang gesetzt, nicht zurückgezogen) | 85 | `knowledge_nodes` |
| davon mit `norm_art` | **2** (beide `sein`) | dito |
| Normen fremder Herkunft, am Quelltext erkannt | 3 | `kern/normachsen.py` |
| Ergebnisdateien ohne Gegenprobe-Vermerk | 83, davon 78 alt | `hub/scripts/gegenprobe_faellig.py` |
| `access_log`-Zeilen mit Tokenzahl | **0** von 12722 | `kern/tokenkosten.py` |
| Tokenzeilen in Hermes (`session_model_usage`) | 30, 41 022 641 Eingabe | `~/.hermes/state.db` |

## Was sich beim Nachsehen als schon entschieden herausstellte

**Normachse 2 brauchte gar keine Entscheidung.** `_is_spannung` in
`kern/knowledge_lint.py` nennt Sein/Sollen/Dürfen wörtlich im Docstring
(Auftrag 2026-08-07/08, Knoten `dd367fd1`), und `schema.sql` erzwingt den
Wertebereich `('sein','sollen','duerfen')` seit Auftrag 95 per Trigger
(`knowledge_nodes_norm_art_check_bi`/`_bu`). Die Frage war falsch gestellt:
es fehlt keine Taxonomie, es fehlt die Befüllung.

**Zum „Können" trotzdem eine Begründung**, weil der Betreiber danach gefragt
hat und die Antwort sonst wie Übergehen aussieht. Es zerfällt in zwei Dinge,
die verschieden behandelt gehören:

- *Fähigkeit* („der Emulator kann einen GATT-Server") ist eine
  Tatsachenaussage, also `sein`. Nichts geht verloren.
- *Kann-Vorschrift* im Rechtssinn (Ermessen, neben Muss und Soll) ist kein
  Modus, sondern ein **Verbindlichkeitsgrad** — und den trägt `norm_rang`.
  Genau diese Spalte ist bereits doppelt belegt (Rangmaßstab Buckeberg gegen
  Direktiven-Skala des hub, Knoten zur Verwalterwahl). Ein zweites Mal
  Grad-Semantik hineinzumischen wäre derselbe Fehler mit anderem Namen.

## Die Alternativen, und warum sie ausscheiden

**Für Achse 2 — Massenbefüllung aller 85 Normen zuerst.** Abgelehnt: Eine
Klassifikation von 85 Sätzen durch eine Maschine ist eine Behauptung, keine
Messung, und sie wäre am nächsten Tag durch neue Normen wieder unvollständig.
`PLAN_RECHTSRAUM_2026-08-13.md` Schritt 1 nennt deshalb die **Schranke am
Schreibweg** als Abnahme, nicht den Bestand. Erst wenn nichts Neues mehr ohne
Art hereinkommt, lohnt der Altbestand — dieselbe Reihenfolge wie bei UTC
(Erzeuger vor Bestand), die dort binnen Minuten acht übersehene Schreiber
gefunden hat.

**Für Achse 3 — eigene Spalte `unabaenderlich`.** Vom Betreiber abgelehnt.
Preis der gewählten Variante: die Angabe steht in einem Textfeld statt in
einem Ja/Nein-Feld und ist damit schwerer abzufragen. Gewinn: kein Schemawechsel,
und die 85 bestehenden Normen brauchen keinen Wert.

**Für die Token-Spalten — entfernen.** Vom Betreiber abgelehnt, mit einem
Grund, der trägt: das System soll offen bleiben und einen eigenen Klienten
bekommen können. Eine Spalte zu löschen, die morgen befüllbar wird, ist
teurer als sie leer zu lassen.

## Der Befund, der die Token-Frage verschiebt

Hermes misst tatsächlich, und zwar genau die vier gesuchten Größen
(`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`,
dazu Kosten). **Aber die Körnung passt nicht:** `session_model_usage` zählt je
**Sitzung und Modell**, `access_log.tokens_*` will je **Aufruf**.

Das ist kein Detail, sondern entscheidet die Bauform. Aus 30 Sitzungszeilen
lassen sich 12722 Aufrufzeilen nicht rekonstruieren — jede Verteilung wäre
erfunden. Wer die Sitzungssumme in die Aufrufspalte schreibt, erzeugt genau
die Sorte Zahl, die später niemand mehr als Schätzung erkennt.

## Reihenfolge, und wo sie bindend ist

1. **A3 · Herkunftswert** (klein, unabhängig).
2. **Altlast Gegenprobe** (unabhängig, mechanisch).
3. **Token · nur messen und festhalten**, nicht bauen.

Alle drei dürfen nebeneinander laufen.

**Nicht in diesem Plan, aber davor fällig: A2, die Schranke am Schreibweg.**
Sie steht ausformuliert in `docs/PLAN_RECHTSRAUM_2026-08-13.md`, Schritt 1,
und wird hier bewusst nicht verdoppelt — zwei Fassungen desselben Auftrags
laufen auseinander, sobald eine angefasst wird. Bindend ist nur, dass sie
**vor** einer Befüllung des Altbestands kommt (UTC-Beleg: ohne Erzeugersperre
ist der Bestand eine Momentaufnahme).

## Was bewusst nicht getan wird, samt Preis

- **Keine Massenklassifikation der 85 Normen.** Preis: Achse 2 bleibt vorerst
  stumm für den Altbestand, der Melder meldet weiter. Grund oben.
- **Keine Aufrufzeilen-Tokenzahlen aus Hermes-Sitzungssummen.** Preis: die
  Spalten bleiben leer. Grund: jede Verteilung wäre erfunden.
- **Keine Altersgrenze für Gegenproben.** Der Betreiber hat den Einzelabschluss
  gewählt; eine Regel hätte künftig auch prüfbare Fälle verschwiegen.

## Woran sich Erfolg misst

- **A3:** Der Melder `kern/normachsen.py` meldet die drei Gesetzesnormen nicht
  mehr als offenen Punkt, sondern findet den Wert vor. Negativfall: eine
  eigene Hausregel bekommt ihn **nicht**.
- **A2:** Rot vor grün — ein neuer Knoten, der ein fremdes Gesetz zitiert, wird
  ohne `norm_art` abgewiesen oder gemeldet; vorher lief er durch. Negativfall:
  eine eigene Regel ohne fremdes Zitat läuft unverändert. Grenzwert: die
  `offen`en Knoten werden nicht angefasst.
- **Altlast:** `gegenprobe_faellig.py` nennt danach nur noch die Läufe, deren
  Gegenprobe wirklich noch jemand fahren kann — gezählt, nicht angenommen.
- **Token:** Der Körnungsbefund steht als Knoten im Speicher, nicht nur hier.

## Aufträge, fertig zum Übergeben

**Für alle gleichermaßen:** Arbeitsort `/Volumes/daten/Begod2026/brainlehr`,
Zweig `brainlehr/b4-ausweis`. Zuerst `CLAUDE.md`, dann dieser Plan. „Sieht der
Code anders aus als hier beschrieben, halte dich an den Code und melde die
Abweichung." Kein `git add -A`, kein Push, kein `git stash`. Committen mit
expliziter Pfadliste. Datenbanknamen über `kern/speicher`.

### NA1 · A3, Herkunftswert für fremde Normen — **erledigt** (`c9482c6`)

| | |
|---|---|
| **Darf ändern** | `kern/normachsen.py`, dazu Tests |
| **Tabu zusätzlich** | `schema.sql`, `knowledge_mcp_server.py`, `melder/` |
| **Fakten** | `fremdnormen()` erkennt fremde Herkunft heute schon am `source`-Text (`FREMDE_QUELLE`, Treffer `gesetz`/`BGBl`) und findet 3 Knoten. Der Wert wird an derselben Stelle festgehalten, an der er erkannt wird — nicht neu geraten. |
| **Abnahme** | Rot vor grün an einem der drei echten Knoten. Negativfall: eine Hausregel ohne Gesetzesbezug bekommt keinen Wert. Grenzwert: ein `source`, das das Wort „Gesetz" nur in der Prosa trägt, ohne Fundstelle — dieser Fall wird benannt, nicht stillschweigend mitgenommen. |

### NA2 · Altlast Gegenprobe abschließen — **erledigt** (`1aedf27`, Korrektur folgt)

| | |
|---|---|
| **Darf ändern** | nur Beistelldateien unter `runs/` |
| **Tabu zusätzlich** | jede Ergebnisdatei selbst, jeder Melder |
| **Fakten** | 83 offene Fälle, davon 78 älter als heute. `melder/rasterblick.py` hat mit `verlust_vermerken` bereits den richtigen Mechanismus: er behauptet **keine** Zahl, sondern hält fest, dass der Blick nicht mehr befragbar ist. |
| **Abnahme** | Nach dem Lauf nennt der Melder nur noch Läufe, deren Gegenprobe fahrbar ist. Kein Vermerk trägt eine erfundene Kennzahl — stichprobenweise geöffnet und nachgesehen, nicht am Exit-Code abgelesen. |

### NA3 · Token, nur festhalten — **erledigt** (Knoten `e504b10c` ergänzt)

| | |
|---|---|
| **Darf ändern** | nichts im Code |
| **Fakten** | Hermes `~/.hermes/state.db`, Tabelle `session_model_usage`: 30 Zeilen, 41 022 641 Eingabe-Token, 249 850 Ausgabe-Token, mit `cache_read_tokens`/`cache_write_tokens`. Körnung Sitzung×Modell gegen `access_log` je Aufruf. |
| **Abnahme** | Der Körnungsbefund liegt als Knoten im Speicher und ist über eine Suche nach „Token" auffindbar. Die vier Spalten bleiben, kommen aber **nicht** auf die Ausnahmeliste des Prüfers — sie sollen weiter gemeldet werden, denn sie sind ein echter offener Punkt und kein Fehlalarm. |
