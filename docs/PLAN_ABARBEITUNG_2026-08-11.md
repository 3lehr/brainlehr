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
- [x] **P4 · Naht weiterziehen** — Dateien von eigener Verbindung auf
      `speicher.py` umstellen, Ratsche nachziehen
- [ ] **P5 · Common-Cause auf das Agentenregister** — siehe Befund unten
- [ ] **P6 · Prüfkorpus, der nicht aus Lehrentexten erzeugt ist**
- [ ] **P7 · Achse „Art" (Sein/Sollen/Dürfen)** für die 82 Normen
- [ ] **P8 · Die drei restlichen Antwortläufe dreiteilen**
- [ ] **P9 · `freigabe` in `browse`/`search`** — fremder Zweig
- [ ] **P10 · Metroviz auf den Codekanten**

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
