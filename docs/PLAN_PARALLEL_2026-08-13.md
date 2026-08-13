# Was gleichzeitig laufen kann — Aufteilung nach Dateibesitz

Stand 2026-08-13T01:15:00+0200. Anlass: Betreiberauftrag, die offenen Aufgaben
gleichzeitig und selbständig abzuarbeiten.

## Die Regel, nach der aufgeteilt wird

**Nach Dateien trennen, nicht nach Themen.** Zwei Agenten in derselben Datei
verlieren garantiert Arbeit. Jeder Auftrag nennt ausdrücklich, welche Dateien
andere gerade halten.

Zweite Regel, die hier bindet: **Reihenfolge erzwingen, wo eine Änderung die
andere entwertet.** Eine Messung des Abrufs, die parallel zu einem Umbau des
Abrufs läuft, misst einen Zustand, den es danach nicht mehr gibt.

## Der gemessene Ist-Stand

**VERALTET, korrigiert 2026-08-13T21:05.** Der Satz stand hier als
Ist-Stand: 64 Aufgaben, 28 erledigt. Es sind inzwischen **107 Aufgaben, 71
erledigt** — die Wellen unten stimmen inhaltlich weiter, der Nenner nicht.

Und die tragende Erkenntnis kam nach diesem Plan: **Was seriell aussieht, ist
es oft nur, weil das Werkzeug sich seine Arbeit selbst holt.** Die S12-Lose
schienen eine Kette, weil `--lose` selbst greift, was noch unbehandelt ist —
zwei Agenten haetten dieselben Knoten gefasst. Mit `--ab` sind sie
ueberschneidungsfrei (nachgemessen: 100 Eintraege, 100 verschieden). Vorab
erzeugte Lose machen aus 55 Schritten elf Runden zu je fuenf.

Die Regel dahinter, allgemeiner als der Fall: Bevor eine Aufgabe als seriell
gilt, pruefen, ob die Reihenfolge aus der SACHE stammt oder aus der
Selbstbedienung des Werkzeugs. Nur die erste bindet.

Alter Stand: 64 Aufgaben, 28 erledigt. Von den offenen sind **5 Entscheidungen des
Betreibers** (7, 20, 23, 29, 31), **3 warten auf Wachstum oder einen Plan**
(4, 8, 14) und **2 liegen im fremden Repo hub** (50, 60, 61 teilweise).

Suite: 994 grün, 2 übersprungen, 11 xfail, 0 rot.

## Welle 1 — fünf Aufträge, überschneidungsfrei

| | Aufgaben | Besitzt diese Dateien | Warum getrennt |
|---|---|---|---|
| **A** | 62 + 63 | `melder/`, `haken/antwort_abruf.py`, neue Datei in `kern/` | Nenner und Kanarienvogel sind dieselbe Frage — der Vogel liefert dem Nenner B seine Unterscheidung |
| **B** | 36 + 38 | `knowledge_mcp_server.py` | Beide sind Zugriffsfragen an derselben Datei; zwei Agenten dort wäre der klassische Verlust |
| **C** | 46 | `messungen/echtkorpus.py`, `messungen/trichter_fragen.py` | Satzart-Erkennung, berührt keine der anderen |
| **D** | 42 | **nur neue Dateien** unter `messungen/` und `runs/` | **Bindend: darf `haken/` NICHT ändern** — sonst misst der Versuch einen Zustand, den A gerade umbaut |
| **E** | 57 + 58 | `docs/` | Reine Dokumentenarbeit, kollidiert mit nichts |

**Tabu für alle:** `app/`, `entscheidungen.html`, `berichte/`, `pflege/`,
sowie die Dateien der fremden Sitzung (`messungen/messlauf_abrufguete_v2.py`,
`migrationen/lauf_titelverteidiger_2026-08-08.py`, `NODE_INDEX.md`,
`antwort_treffer.json`, `auszug/`, `bereinigung_log.jsonl`,
`runs/messlauf_abrufguete_v2.json`).

## Welle 2 — erst danach, und warum

| Aufgaben | Grund für die Reihenfolge |
|---|---|
| 35 (Kalibrierbremse), 39 (zweiter Anfragevektor) | Beide bauen an `haken/knowledge_recall_hook.py` — der Datei, die Welle 1 misst |
| 44, 55 (Verdrahtung) | Beide ändern `~/.claude/settings.json`. Eine blockierende Wache mit ungeprüfter Annahme hat in diesem Verbund schon einmal **alle** Subagenten in **allen** parallelen Sitzungen lahmgelegt — das läuft allein und mit beiden Richtungen belegt |
| 59 (Ablation über 205) | Läuft 12 bis 20 Minuten. Gehört **nicht** in einen Subagenten, sondern selbst gestartet |
| 64 (Caveman gegen Antwort-Abruf) | Braucht den Nenner aus Aufgabe 62 |
| 37, 40, 41 | Nach der Okkultation — deren Ergebnis entscheidet, ob ein Abrufmonitor das Richtige anzeigt |

## Was bewusst nicht parallelisiert wird, samt Preis

- **Nicht mehr als fünf gleichzeitig.** Preis: langsamer. Grund: Jeder Agent
  kostet beim Abschluss eine Prüfung durch mich — Suite fahren, Zuschreibungen
  gegen die Historie halten, committen. Fünf ungeprüfte Berichte sind
  schlechter als drei geprüfte.
- **Kein Agent auf `~/.claude/settings.json` in dieser Welle.** Preis:
  Aufgabe 44 und 55 warten. Grund steht oben.
- **Keine Aufgabe, die ein fremdes Repo ändert.** 50, 60 und 61 betreffen den
  hub; dort wird nichts im Vorbeigehen geändert.

## Woran sich Erfolg misst

- Nach jeder Welle: Suite grün ohne Rücklauf gegenüber 994.
- `git status` zeigt keine Datei, die zwei Aufträgen zugleich gehörte.
- Jede Zahl aus einem Agentenbericht wird vor dem Weitertragen selbst geprüft.
- Jede Aufgabe wird nur mit einem Beleg auf `completed` gesetzt, der vorher
  rot war — sonst bleibt sie offen mit einem Satz, was fehlt.
