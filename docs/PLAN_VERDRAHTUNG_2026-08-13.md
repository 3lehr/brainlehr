# Verdrahten, ohne fremde Sitzungen zu treffen

Stand 2026-08-13T03:40:00+0200. Aufgabe 44, und zugleich der Weg für Aufgabe 55.

## Der gemessene Ist-Stand

| | Befund |
|---|---|
| `haken/existenzpruefung.py` | vorhanden, liest die letzte eigene Antwort, sucht Existenz-Verneinungen, fragt den Bestand |
| Verdrahtet | **nein** — 0 Treffer in `~/.claude/settings.json` |
| Bauform | braucht `transcript_path`, druckt nur bei Treffern, fällt bei eigenem Fehler offen aus (`except: pass`, `exit 0`) |
| Selbsttest | **keiner** — `--selftest` erzeugt keine Ausgabe |
| Projekteigene Ablage | `brainlehr/.claude/settings.json` **existiert nicht** — das war Ursache 3 der Messung „warum greifen die Regeln nicht" |

## Die Alternativen

**A — In `~/.claude/settings.json` eintragen.** Abgelehnt. Das wirkt sofort auf
**alle** Sitzungen des Betreibers, auch die in fahrtenbuch und openlehr. In
diesem Verbund hat ein so eingetragener Wächter schon einmal in allen parallel
laufenden Sitzungen jeden Subagenten geblockt — wegen **einer** ungeprüften
Annahme über sein Eingabefeld.

**B — Projekteigene `brainlehr/.claude/settings.json` (gewählt).** Wirkt nur
in diesem Repo. Schließt nebenbei die dritte gemessene Ursache: Dieses Projekt
hat bis heute keine eigene Regelablage.

**C — Gar nicht verdrahten.** Abgelehnt: Ein Haken, der nirgends hängt, zählt
als keiner. Genau das ist heute an `ui_guard.py` und `push_guard.py` gemessen
worden.

## Drei Auflagen, alle aus gemessenen Fehlern

1. **Fällt bei eigenem Fehler offen aus.** Ist gebaut — bleibt so und wird
   geprüft, nicht angenommen.
2. **Beide Richtungen belegt, bevor er scharf geht:** eine Verneinung, die
   melden **muss**, und eine gewöhnliche Antwort, die **schweigen** muss. Ein
   Signal, das nur in eine Richtung ausschlagen kann, ist keine Messung.
3. **Er urteilt nicht.** Ein Treffer heißt „dazu gibt es etwas", nicht „du hast
   dich geirrt". Steht schon im Modulkopf und bleibt.

## Was bewusst nicht getan wird, samt Preis

- **Keine Änderung an `~/.claude/settings.json`.** Preis: Andere Projekte
  bekommen den Haken nicht. Gewinn: keine Wirkung auf laufende fremde
  Sitzungen. Übertragen wird erst, wenn er sich hier bewährt hat.
- **Kein Blockieren.** Der Haken meldet und hält niemanden auf.

## Woran sich Erfolg misst

- Beide Richtungen vorgeführt, nicht behauptet.
- Der Haken hat danach einen **Selbsttest** — heute hat er keinen.
- `git status` zeigt keine Änderung an `~/.claude/settings.json`.
