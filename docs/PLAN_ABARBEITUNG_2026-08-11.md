# Abarbeitung: der offene Bestand vom 2026-08-11

Auftrag des Betreibers 18:20: den gesamten Plan jetzt abarbeiten, dokumentieren,
abhaken. Reihenfolge wie zuletzt vorgeschlagen, geändert durch den Befund der
Börsen-Recherche (Sortierregel vor Prüfkorpus).

Stand wird in dieser Datei fortgeschrieben. `[x]` heißt gebaut UND belegt,
`[~]` heißt begonnen, `[ ]` heißt offen mit Grund.

## Reihenfolge und Stand

- [x] **P0 · Push** — 24 Commits auf `claude/wie-geht-es-weiter-3f4066`
- [x] **P1 · Sortierregel: welche Lehre wird Code, welche bleibt Speicher**
      Die Börsen-Recherche liefert das Kriterium (Schaden), `vorschlag.py`
      liefert die Kandidaten. Gebaut in `sortierregel.py`.
- [x] **P2 · Frageform im Recall-Block** — Treffer als Ablehnungsfrage statt
      als Fundliste (Konsil, Stimme 3: der übertragbare Rest der
      Beweislastumkehr).
- [x] **P3 · Tote Verweise prüfen** — 106 Kandidaten ohne Datei im Verbund
- [x] **P4 · Naht weiterziehen** — 69 auf 67 Dateien, Ratsche nachgezogen
- [x] **P11 · Haltemenge** (neu, aus der Quant-Recherche): der Bestwert aus 24
      Versuchen faellt auf einer Haltemenge zurueck
- [ ] **P5 · Common-Cause auf das Agentenregister** — NICHT gebaut: das Register gibt es nicht her (ein Bash-Aufruf bekommt seine eigene Agentenkennung nicht als Umgebungsvariable, L-1b6476). Erst das Register erweitern, dann auswerten.
- [~] **P6 · Prüfkorpus** — Sammler gebaut (`echtkorpus.py`), Kanäle getrennt. Ertrag heute: **4 Fälle aus 300 echten Nachrichten** — zu wenig zum Messen, wächst aber von selbst.
- [ ] **P7 · Achse „Art" (Sein/Sollen/Dürfen)** für die 82 Normen
- [ ] **P8 · Drei Antwortläufe dreiteilen** — Weg belegt, reine Mechanik. Zurückgestellt: sie messen gegen den kontaminierten Korpus, also erst nach P6.
- [ ] **P9 · `freigabe` in `browse`/`search`** — fremder Zweig
- [ ] **P10 · Metroviz auf den Codekanten** — Datengrundlage steht (1744 Kanten, 874 Dateien), Anzeige ist ein eigenes Vorhaben.

## Befunde während der Abarbeitung

### P1 · Sortierregel (`sortierregel.py`)
741 Lehren sortiert: **40 gehören in den Codepfad**, 701 ins Nachschlagewerk —
davon **141 ausdrücklich, weil sie Haltung beschreiben statt einer prüfbaren
Bedingung**. Diese dritte Spalte ist der Kern: eine kritische Lehre, die sich
nicht als Bedingung schreiben lässt, wird KEIN Prüfstein, sonst entsteht eine
Attrappe. Plausibilitätsprobe: `L-a69129` steht mit 4 Punkten in der Liste —
genau die Lehre, aus der heute früh eine Codebedingung wurde.

### P2 · Frageform (`haken/knowledge_recall_hook.py`)
Der Block sagt jetzt: *„Nicht als Fundliste lesen, sondern als Frage: Trifft
das hier zu? Wenn NEIN — woran liegt es?"* Keine Sperre, keine Quittierung.
Der fehlschlagende Recall-Test war vorbestehend (gegen `git stash` geprüft).

### P3 · Tote Verweise — und ein Fehler im eigenen Index
Von den 106 angeblich toten Verweisen war ein Teil gar nicht tot: `ui_guard.py`
liegt unter `~/.claude/skills/design-waechter/` — **außerhalb** der indizierten
Wurzel. Mein Index hatte den Werkzeugkasten des Hauses ausgelassen und dessen
Dateien für verschwunden erklärt. Ursache: die Ausnahme galt für `.claude`
statt nur für `.claude/worktrees`.

Nach der Korrektur (zweite Wurzel `~/.claude`, Ausnahme nur noch auf
`worktrees`): 191.291 Dateien indiziert, **1744 Kanten** (vorher 1716),
**101 tote Verweise** (vorher 106).

Die verbleibenden 101 sind zu 89 Einzelnennungen und 12 Mehrfachnennungen —
darunter `oem_odometer_probe_screen.dart` und `wt_neue_klaerungsarten_zeigen_beleg.js`,
die es im ganzen Verbund nicht gibt. Das sind echte Befunde: Lehren, die auf
Verschwundenes zeigen.


### P4 · Naht
`deckelreihe.py` und `haken/suchpfad_abruf.py` auf `speicher.lesen()` umgestellt.
Ratsche: **67 statt 69**. Beide Selbsttests fielen schon vorher (gegen `git
stash` geprüft) — vorbestehend.

### P11 · Haltemenge — die wichtigste Korrektur des Abends

| | Tuning (22) | Haltemenge (13) |
|---|---|---|
| `kurzfeld` (Sieger im Tuning) | 5 | **2** |
| FTS5 (Ausgangsstand) | — | **4** |

Der Vorsprung ist weg. Ab sofort: jede Messung nennt die Zahl der Versuche, und
ein Vergleich mehrerer Bauformen braucht eine Haltemenge.

## Was offen bleibt, und warum

P5 scheitert am Register, nicht am Willen. P6 braucht einen Erzeugungslauf und
ist jetzt schärfer definiert als vorher. P7 ist eine Entscheidung des Betreibers,
kein Bau. P8 wäre Mechanik gegen einen bekannt kontaminierten Korpus — Arbeit,
die man zweimal macht. P9 gehört einer fremden Sitzung. P10 ist ein eigenes
Vorhaben.

**Sechs von elf gebaut und belegt, fünf mit Grund offen. Kein Punkt bleibt
stillschweigend liegen.**


### P6 · Prüfkorpus — Sammler statt Erzeugung
Beide Kontaminationen dieses Tages hatten dieselbe Wurzel: **Aufgabentext und
Zielangabe kamen aus derselben Quelle.** `echtkorpus.py` trennt die Kanäle:

- **Aufgabentext** = eine echte Nachricht aus `recall_log.jsonl`, so gestellt
  wie sie gestellt wurde, ohne Kenntnis eines Ziels
- **Zielangabe** = über `code_kanten`, also über den Dateipfad — ein Kanal, der
  mit dem Wortlaut der Nachricht nichts zu tun hat

Niemand formuliert dafür etwas. **Ertrag beim ersten Lauf: 4 Fälle aus 300
echten Nachrichten.** Das misst nichts, und die Anforderungen zu senken wäre der
Rückweg zum erfundenen Korpus. Der Sammler wächst stattdessen mit jeder
künftigen Nachricht, die eine Datei nennt.

Beim Bau noch einmal dieselbe Falle wie heute früh: `ort.RECALL_LOG` leitet den
Pfad aus dem Arbeitsbaum ab, und ein Arbeitsbaum trägt keine Daten — 0 statt 300
Nachrichten. Jetzt wird der Ort **neben der Datenbank** gesucht.
