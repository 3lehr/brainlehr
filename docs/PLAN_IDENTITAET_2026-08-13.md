# Wer bin ich, was ist mein Ziel — und warum es heute nirgends steht

Stand 2026-08-13T11:20:00+0200. Betreiberfrage: Gehört die Definition — wer bin
ich, was ist mein Ziel, warum machen wir das — nicht in **jeden Arbeitsbaum** und
an **jede Abfrage**?

Sie ist dieselbe Frage wie „brainlehr soll mehr sein als Vibecoding". Ohne einen
Zweck, der mitreist, ist jede Ausweitung auf buckeberg, openlehr, Akademie oder
Stadtwerke nur ein weiterer Bestand im selben Topf.

## Der gemessene Ist-Stand

**Eigene Identitätsdatei je Repo:**

| Repo | `CLAUDE.md` |
|---|---|
| hub | 143 Zeilen |
| buckeberg | 77 |
| openlehr | 42 |
| fahrtenbuch | 30 |
| **brainlehr** | **fehlt** |

Ausgerechnet das System, das über Regeln und Wissen wacht, ist das einzige ohne
eigene Beschreibung.

**In den Arbeitsbäumen:** fünf geprüft — `CLAUDE.md` **0 von 5**,
`.claude/settings.json` **0 von 5**.

Das schließt zugleich eine Frage, die heute früh offen blieb. Die
projekteigene `settings.json` wurde im Hauptbaum angelegt; **jedes** gemessene
Stop-Ereignis lief aber mit einem Arbeitsbaum als Verzeichnis. Sie war dort nie
vorhanden. Die Existenzprüfung lief nicht, weil die Regelablage nicht mitreist —
nicht, weil projekteigene Ablagen grundsätzlich nicht wirken.

**An der Abfrage** existiert bereits die Gegenrichtung:
`_zweckprojektion_sichtbar` filtert Treffer nach Zweck. Der Zweck **filtert**
also — er wird nur nirgends **genannt**. Ein Filter, dessen Kriterium im
Ergebnis nicht auftaucht, ist nicht überprüfbar.

## Die Gefahr, die diesen Plan begrenzt

Ein Zwecktext, der in jeden Prompt gespritzt wird, **wird Tapete**. Der
Wissens-Abruf ist der Beleg: Er kommt bei jeder Nachricht und wird regelmäßig
übergangen — dafür existiert eine eigene Notiz. Wer Identität als weiteren
Fließtext einspielt, baut die vierzehnte Erscheinungsform von „gebaut, laufend,
wirkungslos".

**Daraus die Leitlinie: Identität muss mechanisch wirken, nicht dastehen.**
Prüffrage vor jedem Teilschritt: *Was geht kaputt, wenn sie fehlt?* Ist die
Antwort „nichts, es liest sie nur niemand", ist der Schritt falsch zugeschnitten.

## Die Alternativen

**A — Ein Zwecktext, überall eingespielt.** Abgelehnt: siehe oben. Er kostet
Kontext bei jeder Nachricht und ist an keiner Stelle prüfbar.

**B — Identität als Datei, die beim Anlegen eines Arbeitsbaums mitkommt, plus
Zweck als benanntes Feld der Abfrage (gewählt).** Beides ist **zählbar**: Die
Datei ist da oder nicht; der Zweck steht im Ergebnis oder nicht.

**C — Nur die Repo-Datei nachziehen.** Zu wenig: Sie erklärt, wer wir sind, und
beantwortet nicht, wonach ein einzelner Abruf gefiltert hat.

## Die vier Fragen, die jede Instanz beantwortet

Die **Form** ist gemeinsam, die **Antworten** sind es nicht — das ist der Kern
für die Ausweitung über Vibecoding hinaus:

1. **Wer fragt hier?** (Rolle und Rechte — der Ausweis beantwortet das bereits.)
2. **Worüber wird hier Wissen geführt?** (Gegenstand: Code · Rechtslage · Steuer
   · Lehre · Netz.)
3. **Was ist ein Treffer wert?** Ein falscher Rechtssatz kostet anders als ein
   falscher Funktionsname. **Diese Frage entscheidet über Schwellen** — und
   heute gibt es sie nicht, weshalb eine Schwelle für alle Domänen gilt.
4. **Was darf nach außen?** (Freigabe — die Achse existiert, ist aber leer.)

Frage 3 ist die, die am meisten kostet, wenn sie fehlt: Sie ist der Grund, warum
`0,65` heute für Rechtsfragen und Codefragen derselbe Wert ist.

## Was bewusst nicht getan wird, samt Preis

- **Keine Zweckdefinition für fremde Domänen erfinden.** Akademie und
  Stadtwerke haben noch kein Einsatzgebiet; eine ausgedachte Antwort auf Frage 2
  wäre geraten und würde später für gemessen gehalten. Preis: Der Rahmen bleibt
  vorerst für zwei Domänen gefüllt, nicht für vier.
- **Keine Schwellen je Domäne, bevor Frage 3 beantwortet ist.** Preis: `0,65`
  gilt weiter überall. Gewinn: keine zweite geratene Zahl im Abruf, nachdem
  gerade eine ausgebaut wurde.
- **Kein Eintrag in `~/.claude/settings.json`.** Die Wirkung auf parallele
  Sitzungen bleibt ausgeschlossen.

## Woran sich Erfolg misst

- **Zählbar statt gefühlt:** Arbeitsbäume mit Identitätsdatei steigen von **0
  von 5**. Ein Arbeitsbaum ohne sie wird gemeldet, nicht geduldet.
- **Der Abruf nennt den Zweck**, nach dem er gefiltert hat — dann lässt sich ein
  Fehlfilter überhaupt erkennen.
- **Die Probe auf die Tapete:** Wird die Identitätsdatei entfernt, muss etwas
  **messbar** anders laufen. Passiert nichts, ist der Schritt gescheitert, auch
  wenn die Datei überall liegt.

## Aufträge, fertig zum Übergeben

**Für alle Aufträge gleichermaßen gilt:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`. Zuerst
`CLAUDE.md` in `~/.claude/` lesen, dann diesen Plan. „Sieht der Code anders aus
als hier beschrieben, halte dich an den Code und melde die Abweichung." Kein
`git add -A`, kein Push, kein `git stash`. Committen mit expliziter Pfadliste.
Volle Suite im Vordergrund mit `timeout=600000`. Datenbanknamen über
`kern/speicher`.

### Schritt 1 · Die eigene Beschreibung, erzeugt statt gepflegt

| | |
|---|---|
| **Darf ändern** | `brainlehr/CLAUDE.md` (neu), das erzeugende Skript unter `melder/`, dessen Test |
| **Tabu zusätzlich** | `~/.claude/CLAUDE.md`, alle fremden Repos, `knowledge_mcp_server.py`, `schema.sql` |
| **Fakten** | brainlehr hat als einziges Repo keine eigene `CLAUDE.md` (hub 143, buckeberg 77, openlehr 42, fahrtenbuch 30 Zeilen). `melder/selbstbeschreibung.py` erzeugt bereits eine Fähigkeitsbeschreibung **aus dem Bestand** — diese Bauform wird weiterverwendet, nicht danebengestellt. |
| **Abnahme** | Die Datei wird **erzeugt**, nicht getippt: Ändert sich der Bestand, ändert sich die Datei. Als Test: eine Fähigkeit entfernen → die Datei nennt sie nicht mehr. Negativfall: unveränderter Bestand erzeugt byteweise dieselbe Datei (sonst rauscht jeder Lauf einen Commit). |

### Schritt 2 · Meldung statt Duldung im Arbeitsbaum

| | |
|---|---|
| **Darf ändern** | einen Melder unter `melder/`, angehängt an einen **bereits laufenden** Haken, dazu Tests |
| **Tabu zusätzlich** | `~/.claude/settings.json`, `haken/auszug_nachziehen.py` (hält bereits den Kantenlauf) |
| **Fakten** | 0 von 5 Arbeitsbäumen haben `CLAUDE.md` oder `.claude/settings.json`. Jedes der 949 gemessenen Stop-Ereignisse lief mit einem Arbeitsbaum als Verzeichnis, nie im Hauptbaum. Belegt laufende Haken: `haken/antwort_abruf.py --stop`, `haken/knowledge_capture_hook.py`, `melder/wissensverlauf.py`. |
| **Abnahme** | Der Melder schlägt **gegen den heutigen Arbeitsbaum** an — er hat keine Identitätsdatei. Negativfall: im Hauptbaum schweigt er. Grenzwert: Datei vorhanden aber leer zählt als fehlend, und das wird geprüft, nicht angenommen. |

### Schritt 3 · Der Abruf nennt seinen Zweck

| | |
|---|---|
| **Darf ändern** | `knowledge_mcp_server.py` an der Stelle der Ergebnisausgabe, dessen Tests |
| **Tabu zusätzlich** | `_zweckprojektion_sichtbar` selbst — die Filterlogik bleibt unverändert, nur ihr Kriterium wird sichtbar gemacht |
| **Fakten** | `_zweckprojektion_sichtbar` filtert an mindestens sechs Stellen (Suche, Blättern, Lesen). Aufgabe 22 hat bereits einmal aufgedeckt, dass sie nicht überall greift. |
| **Abnahme** | Rot vor grün: Ein Abruf, der wegen des Zwecks etwas ausgelassen hat, weist das vorher **nicht** aus und nachher schon — mit Zahl, nicht mit Text. Negativfall: Ein Abruf ohne Auslassung erzeugt **keine** Zusatzzeile, sonst ist es Rauschen statt Auskunft. |
