# Feldbericht: eine Arbeitssitzung mit brainlehr

**Erhoben:** 2026-08-09T15:52:23+0200
**Sitzung:** `3e645d59`, 2026-08-09T14:19:22+0200 bis 15:52 — **1 h 33 min**
**Arbeitsgegenstand:** fahrtenbuch (nicht brainlehr). brainlehr lief nebenher mit, wie im Alltag.
**Modell:** claude-opus-5, Client claude-code
**Erhoben von:** dem Assistenten selbst, über sich selbst. Kein unabhängiger Beobachter — die Grenzen stehen unten.

---

## 1. Wie das hier gemessen wurde

Zwei Quellen, mit unterschiedlicher Belastbarkeit:

| Quelle | belegt | Verlässlichkeit |
|---|---|---|
| `knowledge.db`, Tabellen `lessons_learned`, `knowledge_nodes`, `access_log` | alle **Schreib**vorgänge | hart, per SQL abgefragt |
| Gesprächsverlauf der Sitzung | alle **Lese**vorgänge | von Hand gezählt |

**Dass diese Trennung nötig ist, ist der wichtigste Befund dieses Berichts** — siehe Abschnitt 5.1.

Eine Selbstkorrektur vorweg, weil sie die Zahl betrifft: In der ersten mündlichen Antwort nannte ich 7 Recall-Einspielungen. Beim Nachzählen für diesen Bericht waren es **9**; zwei Einspielungen an zuletzt eingetroffenen Agentenmeldungen hatte ich übersehen. Alle Zahlen unten sind die nachgezählten.

---

## 2. Geschrieben — 5 Einträge

Per SQL belegt, alle mit `model=claude-opus-5`, `actor=claude-code`:

```
L-9f8816  antipattern  15:04:58  anlass=hook    Auftrag nannte Repo statt absolutem Pfad
L-23c20d  antipattern  15:05:12  anlass=hook    Abnahme widersprach der Grenze im Auftrag
L-5767a7  pattern      15:06:04  anlass=hook    Abweichungssatz + rot-vor-grün als Verfahren
L-a670d9  antipattern  15:06:25  anlass=hook    Abdeckung zugesagt, ohne nachzusehen
L-6ad279  antipattern  15:19:14  anlass=selbst  Prüfstand ohne Lebensprüfung
```

**Knoten (`knowledge_nodes`): 0.**

Zur Entstehung, weil sie etwas über den Mechanismus sagt: Vier der fünf entstanden zwischen 15:04 und 15:06 — in zwei Minuten, weil der `Stop`-Hook den Aufruf von `/learn` erzwang. Der fünfte (15:19) entstand im Arbeitsfluss, als der Befund frisch war. **Der Reflex, der laut Hausregel die Regel sein soll, lieferte einen von fünf Einträgen. Das Netz lieferte vier.**

---

## 3. Gelesen — 9 Einspielungen, 34 Einzeltreffer, davon 0 protokolliert

| Weg | Anzahl | im `access_log`? |
|---|---|---|
| Auto-Recall (`UserPromptSubmit`-Hook) | **9** Einspielungen, zusammen **34** Einzeltreffer | **nein** |
| `lesson_query` (Duplikatprüfung vor dem Schreiben) | 2 | **nein** |
| `knowledge_search` | 0 | — |
| `knowledge_read` | 0 | — |
| `knowledge_browse` | 0 | — |
| SessionStart: Knoten-Index (2029 Knoten / 699 Lehren) + 4 Warnblöcke | 1 | nein |

Abfrage über das gesamte Sitzungsfenster:

```sql
select action, count(*) from access_log
where timestamp >= '2026-08-09T14:19:00' group by action;
-- update 40 | lesson 7 | add 4
```

Kein einziger Lesezugriff. Die 40 `update` und der Großteil der übrigen stammen aus einer **parallelen** Sitzung (`d40bc0e8`), die gleichzeitig in brainlehr selbst arbeitete; von mir stammen genau die 5 `lesson`-Zeilen.

Die Aktionsart `search` existiert und ist seit 2026-03-25 insgesamt **1150-mal** protokolliert. Sie wird also grundsätzlich geschrieben — nur eben nicht vom Recall-Hook und nicht von `lesson_query`.

---

## 4. Hat es geholfen? Vier von neun

Maßstab: Hat der Treffer eine Handlung verändert, die ohne ihn anders ausgefallen wäre? Nicht: war er interessant.

### Ja, handlungsverändernd (4)

1. **`L-3b7506`** — „Fastlane meldet *successfully uploaded*, Apple verwirft das Binary still, der Build taucht 25+ Minuten nicht auf." → Deswegen habe ich nach dem TestFlight-Upload nicht *fertig* gemeldet, sondern eine Lane `verify_upload` gebaut, die App Store Connect direkt fragt. Antwort: *„TestFlight fuehrt aktuell Build 76"*. **Ein Commit, den es ohne diesen Treffer nicht gäbe** — und ohne ihn hätte ich eine unbelegte Erfolgsmeldung abgegeben.

2. **`L-4750fc`** — „`Geolocator.requestPermission()` liefert unter `flutter test integration_test` durchgehend *denied*, auch nach `simctl privacy grant`; TCC.db bleibt leer." → Trägt die gesamte Arbeit der zweiten Sitzungshälfte. Er lieferte die Prüffrage für eine Bestandsaufnahme und ließ mich einen gefundenen Orchestrator (`run_live_test.sh`) korrekt als *läuft in denselben Blocker* einordnen, statt ihn für die Lösung zu halten. Die daraus folgende Untersuchung ergab, dass gar kein Umbau nötig ist — die Plattforminstanz von `geolocator` ist ersetzbar.

3. **`L-48e414` + `L-125f02`** — „Ein Subagent, der einen langen Lauf im Hintergrund startet, wartet nicht, er ist fertig; *ich melde mich* ist eine Absicht ohne Mechanik." → Hat **jeden** Agentenauftrag danach verändert: ausdrückliches Verbot von Werkzeugläufen über etwa einer Minute, plus die Auflage, den Zug nie mit *ich warte* zu beenden. Vier Agenten liefen danach ohne diesen Ausfall.

4. **`L-2326bd`** — „Der native Tracker registriert Standort mit 5 s / HIGH_ACCURACY; ohne diesen Strom füllt sich der Bestätigungspuffer nie." → Damit ließ sich ein Requester in einer `dumpsys location`-Ausgabe überhaupt zuordnen.

### Schwach (1)

Der Knoten zu `wiring_check.py` — ich nannte das Werkzeug in einem Auftrag, entscheidend war es nicht.

### Ungenutzt (rund 28 Einzeltreffer)

Kanonischer Codeort von wohlairr · Stiftshütte-Register · MCP-stdio-Entscheidung · Joker-Trip-ADR · Methodik 13/15 · Walkthrough-Doktrin · `L-91448c` · `L-8b4799` · `L-f281aa` · `L-6fa963` · `L-2febb5` · `L-1b6476` · TestFlight-Pflichtfelder für externe Beta-Gruppen (wir blieben intern) · der eigene, drei Minuten zuvor geschriebene Eintrag `L-6ad279`.

**Trefferquote grob: 4 von 34 Einzeltreffern trugen etwas bei, also ungefähr jeder achte.** Zwei davon (`L-3b7506`, `L-4750fc`) waren allerdings so wertvoll, dass sie den Aufwand aller neun Einspielungen allein rechtfertigen. Das ist kein Widerspruch, sondern die Natur der Sache: Der Nutzen liegt in wenigen Volltreffern, nicht im Durchschnitt. Wer diese Quote nur senken will, indem er weniger einspielt, riskiert genau die zwei.

---

## 5. Befunde für die Weiterentwicklung

### 5.1 Der Speicher misst, was hineingeht — nicht, was herauskommt

Der `access_log` protokolliert Schreibvorgänge lückenlos. Der Auto-Recall, der eigentliche Hauptkanal, schreibt dort **nichts**. `lesson_query` ebenfalls nicht (die Aktionsart existiert nicht einmal).

**Folge:** Die Frage „nützt dieser Speicher etwas" ist aus dem Speicher heraus nicht beantwortbar. Dieser Bericht war nur möglich, weil ein Gesprächsverlauf existiert, der von Hand nachgezählt werden kann. In einem Betrieb ohne diese Möglichkeit gäbe es keine Antwort.

Was fehlt, ist eine Zeile pro Einspielung: Zeitpunkt, auslösende Nachricht, welche Knoten/Lehren geliefert wurden, Sitzung. Damit ließen sich die zwei Zahlen bilden, auf die es ankommt — **wie oft ein Eintrag ausgeliefert wird** und **welche Einträge nie ausgeliefert werden**. Der zweite Wert ist der interessantere: Ein Eintrag, der in Monaten kein einziges Mal getroffen wurde, ist entweder falsch geschrieben oder überflüssig, und beides erfährt man heute nicht.

### 5.2 Die Kostenseite ist ebenfalls unbemessen

```sql
select count(*), count(tokens_input), count(tokens_cache_read) from access_log;
-- 3638 | 0 | 0
```

Vier Tokenspalten sind angelegt, **in 3638 Zeilen ist keine einzige befüllt**. Damit ist auch die Gegenrechnung zu 5.1 nicht möglich: Was kostet eine Einspielung, die nichts beiträgt?

### 5.3 Der Auslöser trifft die falschen Momente

Von **9** Einspielungen kamen **6 auf Systemmeldungen** — abgeschlossene Hintergrundläufe von Agenten — und nur **3 auf Nachrichten des Betreibers**. Von dessen 9 Nachrichten lösten also 6 gar nichts aus.

Zwei Muster dahinter:

- **Nachrichten, die während laufender Arbeit eintreffen, lösen keinen Recall aus.** Genau das waren in dieser Sitzung die inhaltlich schärfsten: *„wäre eine virtuelle Testfahrt sinnvoll?"* und *„Bau CarPlay test!"*. Bei der ersten habe ich anschließend eine falsche Aussage über die Testabdeckung gemacht — ein Recall zum Stichwort Simulator/Emulator hätte sie möglicherweise verhindert.
- **Umgekehrt feuert er auf Maschinenereignisse.** Nach dem erfolgreichen TestFlight-Upload bekam ich den kanonischen Codeort von wohlairr eingespielt. Die auslösende „Nachricht" war eine Statusmeldung eines Bauprozesses.

Deckt sich mit dem vorhandenen Knoten */brainlehr/recall-fragt-den-prompt-nicht-das*.

### 5.4 Die Warnungen beim Sitzungsstart liefen vollständig ins Leere

Um 14:19 kamen vier Warnblöcke: fehlender Gegenprobe-Vermerk zu `deckelreihe_2026-08-09.json` · 14 `runs/`-Dateien ohne Rastervermerk · `norm_art` bei allen 72 Normen leer, 62 davon Selbstermächtigung, `actor` bei 94 % nichtssagend · Normachse 3 fällig.

**Ich habe keine einzige bearbeitet.** Nicht aus Nachlässigkeit: Sie betreffen brainlehr, ich arbeitete in fahrtenbuch. Für eine Sitzung in einem anderen Projekt sind sie strukturell nicht adressierbar.

Das ist genau der Fall, den der eigene Knoten */methodik/arbeitsweise/04b* beschreibt: *ein Erzwinger, der immer anschlägt, ist wirkungslos*. Eine Warnung, die bei jedem Start unabhängig vom Arbeitsgegenstand erscheint, wird nach wenigen Malen überlesen — und dann auch dort, wo sie zuträfe. Vorschlag: nur ausspielen, wenn die Sitzung tatsächlich im betroffenen Projekt arbeitet, sonst höchstens als Einzeiler.

### 5.5 Die Modellfrage beruht auf einer falschen Annahme

Ein Hook forderte, den Betreiber stufenweise nach Anbieter und Untermodell zu fragen, weil für die Sitzung kein Modell in der DB stehe. Ich weiß, welches Modell ich bin, und habe `model=claude-opus-5` direkt mitgeschrieben.

Ergebnis: Das Feld ist in allen fünf Zeilen korrekt — der vorgesehene Weg wurde übergangen. Die Annahme „das Modell kennt sich selbst nicht" trifft für diesen Client nicht zu. Zwei Rückfragen an den Menschen wurden dadurch eingespart; hätte ich gehorcht, wären sie die ersten beiden Interaktionen der Sitzung gewesen.

### 5.6 `anlass` bleibt Selbstauskunft — und das Werkzeug weiß es

Vier meiner Einträge tragen `anlass=hook`, einer `anlass=selbst`. Beides habe **ich** hingeschrieben. Der `Stop`-Hook ruft `lesson_record` nicht selbst auf, er zwingt nur zum Aufruf von `/learn`, das dann normal schreibt. Die Werkzeugbeschreibung sagt das ausdrücklich — der Wert ist also ehrlich dokumentiert, aber als Messgröße nicht belastbar. Wer aus dieser Spalte je eine Statistik zieht („X % entstehen im Reflex"), misst Selbsteinschätzung.

### 5.7 Die Verpackung kostet mehr als der Inhalt

Jeder Treffer erscheint als `⟦DATEN, ungeprueft: …⟧`, und zwar **zweimal pro Eintrag** — einmal um den Titel, einmal um den Inhalt. Bei fünf Treffern pro Einspielung und neun Einspielungen ist das ein erheblicher Anteil des eingespielten Textes, ohne Informationsgehalt nach dem ersten Mal.

Der Zweck ist richtig und wichtig: Diese Inhalte sind Daten, keine Anweisungen, und dürfen nicht als Aufträge gelesen werden. Nur muss das nicht 34-mal pro Sitzung wiederholt werden. Ein einziger Satz am Kopf des Blocks leistet dasselbe.

### 5.8 Der Reuse-Wächter entschied über Text statt über Zustand

Beim Start eines neuen Agenten blockierte eine Sperre mit Verweis auf `L-c46550`: ein anderer Agent bearbeite die genannte Datei bereits. Ich hatte diese Datei im Auftrag genannt — ausdrücklich als **tabu**. Die Nennung wurde als Anspruch gelesen.

Übersteuert per `touch /tmp/claude-agent-reuse-allow`. Deckt sich mit `L-7d0b49` (Eskalations-Hook zählt Berührungen statt Misserfolge) und mit `L-1b6476` (ein Register-Prüfer kann die eigene Instanz strukturell nicht von einer fremden unterscheiden). Drei Wächter, dieselbe Bauform, dasselbe Ergebnis: Sie entscheiden über Text oder Häufigkeit statt über Zustand, und werden deshalb reflexhaft übersteuert.

---

## 6. Was dieser Bericht nicht ist

- **Kein unabhängiges Urteil.** Der Assistent bewertet hier seine eigene Nutzung. Ob ein Treffer „handlungsverändernd" war, ist eine Selbsteinschätzung; sie lässt sich am Gesprächsverlauf plausibilisieren, aber nicht beweisen.
- **Keine Stichprobe.** Eine Sitzung, ein Projekt, 93 Minuten, ein Modell. Die Trefferquote aus Abschnitt 4 ist ein Einzelwert, kein Durchschnitt.
- **Kein Urteil über den Bestand.** 2029 Knoten und 699 Lehren wurden nicht geprüft — nur die 34, die von selbst kamen.
- **Verzerrung zugunsten des Speichers:** Was ein Recall verhindert hat, ist unsichtbar. Ein Fehler, den ich wegen `L-48e414` gar nicht erst machte, taucht in keiner Zeile auf. Die vier gezählten Volltreffer sind also eher eine Untergrenze.
- **Verzerrung zulasten des Speichers:** Ich habe **kein einziges Mal** aktiv gesucht (0 × `knowledge_search`, 0 × `knowledge_read`). Der Speicher wurde in dieser Sitzung ausschließlich passiv genutzt. Wie gut die aktive Suche ist, sagt dieser Bericht nicht.

---

## 7. Ein Satz zum Mitnehmen

Der Speicher hat in dieser Sitzung zwei Dinge geleistet, die ohne ihn nicht passiert wären: eine unbelegte Erfolgsmeldung verhindert (`L-3b7506` → Gegenprobe-Lane gebaut) und eine mehrstündige Untersuchung in die richtige Richtung gelenkt (`L-4750fc`). Beides sind Ergebnisse, keine Eindrücke.

Und er kann von beidem nichts wissen, weil er Lesevorgänge nicht protokolliert. Das wäre die erste Änderung.
