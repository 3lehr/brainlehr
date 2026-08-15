# Startprompt — brainlehr, Plan abarbeiten

*Für ein frisches Kontextfenster. Alles ab „ANFANG DES PROMPTS" kopieren.*

Erzeugt am 2026-08-15T21:00:00+0200, weil der Vorgängerfaden seit 05:44 lief und
neben brainlehr auch Steuerrecht, ein Videotranskript, Namensfragen und
Vertrauenseinstellungen verhandelt hat. Der Kontext war voll und vermischt.

---

## ANFANG DES PROMPTS

Lies zuerst `~/.claude/CLAUDE.md`, dann `CLAUDE.md`, dann `STAND.md`, dann
`docs/PLAN_GESAMT_2026-08-13.md` (die Fortschreibungen am Ende zuerst).

**Arbeitsort** `/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`.
**27 Commits liegen lokal und sind nicht gepusht.** Push nur auf ausdrückliches
Wort; der `pre-push`-Wächter ist seit dem 2026-08-15 scharf und geprüft.
**Bestand: 4932 Knoten** — jede ältere Messzahl gilt für 2217 und ist **nicht**
vergleichbar.

### Was du zuerst tust

**Existenzprobe vor jedem Bauauftrag.** Am 2026-08-15 wurden **fünfmal** Agenten
auf bereits Gebautes angesetzt (`L-229bb2`) — jedes Mal, weil dem Plan geglaubt
wurde statt dem Repo. Such nach der **Sache**, nicht nach der Kennung:
`git log --all --grep=`, und
`python3 /Volumes/daten/Begod2026/hub/scripts/symbolindex.py <begriff>` sucht nach
Tätigkeit statt nach Dateinamen.

Und in **jeden** Agentenauftrag gehört der Satz, der in allen fünf Fällen gerettet
hat: *„Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung."*

### Die offenen Linien, nach Wert geordnet

**K1 — die Verschmelzung.** `docs/PLAN_KANALGUETE_2026-08-15.md` samt
Fortschreibung. Zwei Schritte wurden gebaut, gemessen und **verworfen**: Schritt 1
ohne Effekt, Schritt 2 verschlechtert alles und verfehlt den Leitfall. Der Code
liegt unverdrahtet in `kern/embeddings.py`, Vorgabe `None` ist byte-identisch zur
alten Formel.
**Was stattdessen dran ist, in dieser Reihenfolge:**
1. **Den Sockel messen.** In `_fuse_with_keyword_floor()` sättigt etwas, wodurch
   der **echte** Suchweg eine Änderung an `rrf_fuse` strukturell nicht sieht. Diese
   Datei stand auf der Tabu-Liste des letzten Auftrags — der Fehler wohnt
   vermutlich genau dort.
2. **Die Relevanzschwelle.** Die Falschmeldequote steht bei **40/40 in jeder
   Stufe**: Das System hat keinen Abschneidepunkt und kann *„dazu habe ich nichts"*
   nicht ausdrücken. Deshalb ist jede Trefferquote dieses Hauses zweideutig.
3. **Die Formel zuletzt**, und erst nach einer Verteilungsmessung — nicht aus der
   Rechnung eines Einzelfalls (`L-9e4ce3`).

**I5/I6 — ADR-020 Schritt 2 und 3.** Die 12 schreibenden, dann die 13 lesenden
MCP-Werkzeuge werden Klienten des Dienstes. Vorbedingung erfüllt: Der HTTP-Umweg
kostet gemessen 0,3–1,1 ms. **Blocker ist nicht das Tempo**, sondern dass niemand
den Dienst startet — LaunchAgent liegt fertig unter `dienst/`, ist aber nicht
geladen (eine Handbewegung des Betreibers).

**96 — `melder/schemastand.py`** hat keinen Auslöser; das Ereignis `FileChanged`
kommt in **keiner** der beiden Einstellungsdateien vor. Echt offen.

**H12 — Blaupause statt Herauslösung.** Einzige noch offene Zeile der Linie H.

**Der Prüfer am Haltepunkt** gegen nackte Zahlen über zählbare Dinge — angeregt,
nicht entschieden. Bauform wie `normbezug.py`/`existenzpruefung.py`.
**Anlass:** Sechs Zahlenangaben des Assistenten waren am 2026-08-15 falsch, alle
zählbar (11 statt 79 Läufe, 15 statt 334 Kennungen, 91 statt 96 Module, 56 statt
53 Fundstellen, „dreizehn wirkungslose Mechanismen" unbelegt).

### Fünf Fallen, alle am 2026-08-15 gemessen

1. **Es gibt ZWEI Einstellungsdateien** — `~/.claude/settings.json` und die
   repo-eigene `.claude/settings.json`. Wer eine liest, misst falsch; das ist an
   einem Tag in beide Richtungen passiert (`L-ca836f`).
2. **Ein Arbeitsbaum ist ein Schnappschuss.** Er kopiert `.claude/` beim Anlegen
   und danach nie wieder. Deshalb hat die Wache gegen das Beiseitelegen von
   Änderungen in der Sitzung, in der sie gebaut wurde, **nie existiert**.
   Behoben, aber die Klasse bleibt.
3. **Nackte Zahlen als Plankennungen** kollidieren mit Zahlen im Fließtext.
   `82`, `83`, `87` waren **Phantomkennungen** — gar keine Aufgaben (`L-58d434`).
4. **„Gebaut" ist nicht „wirksam".** Die beherrschende Fehlerklasse dieses Hauses.
   Der Plan führt dafür seit dem 2026-08-15 eine eigene Kategorie.
5. **Der Wissensabruf erreicht die Agenten nicht.** `knowledge_recall_hook.py`
   hängt nur an `UserPromptSubmit`, kostet gemessen 6,0 s. Ein verengter Abruf am
   Agentenstart wurde gebaut, gemessen (76 % / 94 % / 35 % Fehlalarm je Variante)
   und **wieder abgenommen** — die Information steckt nicht in den Ankern
   (`58919208`).

### Werkzeuge, die es seit dem 2026-08-15 gibt und die niemand kennt

`melder/abrufwirkung.py` (Verlauf mit Rücknahme) · `melder/agentendauer.py`
(Schätzung gegen Messung) · `kern/planstatus.py` (sieben Zustände, Belegpflicht per
DB-Trigger, erreicht 37 von 39 Planknoten) · `messungen/okkultation_richter.py`
(mechanischer Richter, Leck und Voreingenommenheit strukturell ausgeschlossen).
**Alle vier sind NICHT verdrahtet.**

### Was NICHT hierher gehört

Alles zu openlehr, zur Steuerdomäne und zum atelier läuft in einem eigenen Fenster
— dafür gibt es `docs/STARTPROMPT_OPENLEHR_ATELIER_2026-08-15.md`. Nicht doppelt
anfassen.

### Beim Delegieren

Sonnet-Subagenten, Caveman Ultra, Vordergrund mit `timeout=600000`. In jeden
Auftrag: die Schätzung des Auftraggebers (Dauer, Token, Werkzeugaufrufe) — die
Messreihe läuft seit dem 2026-08-15 und hat drei Datenpunkte mit Abweichungen
zwischen −34 % und +88 %. Und: `git commit -- <pfad>`, nie `git add -A`; das
Beiseitelegen von Änderungen ist gesperrt, Ersatz ist `git show HEAD:<datei>`.

## ENDE DES PROMPTS
