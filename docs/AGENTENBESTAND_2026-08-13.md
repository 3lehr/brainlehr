# Agenten und Fähigkeiten dreier Generationen

Stand 2026-08-13T08:40:00+0200. Auf Betreiberfrage: Welche Fertigkeiten und
Agenten fehlen brainlehr heute, verglichen mit begod und Begod2026?

Erhoben von einem lesenden Agenten, **danach in den Kernzahlen selbst
nachgeprüft**. Drei seiner Angaben waren falsch und stehen unten korrigiert —
das ist der Grund, warum die Nachprüfung nicht optional ist.

## Generation 1 — die alte Platte `/Volumes/daten/begod`

**Dort liegt kein Agentensystem.** Der ganze Pfad enthält ein einziges
Verzeichnis `home/`, darin ausschließlich Signier- und Zugangsmaterial. Selbst
nachgesehen, einschließlich versteckter Einträge.

Das beantwortet die Vermutung, das historische Regelwerk könne noch auf der
alten Platte liegen: **nicht dort.** Es liegt in der Stiftshütte.

## Generation 2 — Stiftshütte `/Volumes/daten/Begod2026/stiftshuette`

**Korrigierte Zahlen** (der Agent meldete 58; das war nur das Wurzelverzeichnis):

| | |
|---|---|
| `.agent.md`-Dateien insgesamt | **81** |
| davon in `begod/agents/` selbst | 58 |
| in Kontinent-Unterordnern | amerika 8, afrika 5, ozeanien 4, antarktis 3, europa 2, openhood 1 |
| `agent-index.json` → `agents` | **75** Einträge |
| `agent-index.json` → `routing_matrix` | **77** Zeilen |

**Drei Zahlen für einen Bestand — 81 Dateien, 75 Indexeinträge, 77
Routingzeilen.** Keine stimmt mit einer anderen überein. Der Index ist gepflegt,
nicht erzeugt; genau die Bauform, die brainlehr an anderer Stelle abgeschafft
hat (Selbstbeschreibung erzeugen statt pflegen).

### Die tragenden Rollen, mit ihrem Auslöser

Der Auslöser ist das Interessante, nicht die Beschreibung.

| Name | Tut | Ausgelöst durch |
|---|---|---|
| jesus-guide | Absicht verstehen, an die richtige Rolle weiterleiten | jeder Auftrag, nach Tor 0 |
| wissens-scout (Elisa) | liefert von sich aus passendes Wissen zur Aufgabe | Tor 0.5, bei jedem neuen Auftrag |
| **spaghetti-monster** | Rotes Team gegen Verzettelung — **zwei** Standbeine: verworrener Code *und* verworrener Prozess | „proaktiv bei Gruppendenken, unbewiesenen Annahmen, ‚das ist offensichtlich'-Momenten"; Pflichttor 4b |
| heiliger-geist | Meta-Verbesserung, Stimmigkeitsprüfung | „ungefragt bei Prozessreibung"; **Pflicht bei jedem Sitzungsende** |
| hippokrates-safety | Vetorecht im Pflege-/Sicherheitskontext | vor dem Entwicklungsschritt |
| hermes-extern | wählt ein fremdes KI-System und formuliert den Prompt | ausdrücklicher Aufruf |

### Drei Mechanismen, die von selbst liefen

| Name | Bauform | Takt |
|---|---|---|
| Focus Guardian | **eigener Betriebssystemprozess** (`os.fork()`, eigene PID, SIGTERM-Behandlung), erhöht einen Dringlichkeitszähler für offene Fragen und schreibt ihn in eine Datei | alle 10 Minuten, Schwelle 30, Eskalation 60 |
| Telegram-Brücke | eigener Dienst, meldet Aktionen und Fragen **nach außen** in drei Kanäle und liest einen Eingangskanal zurück | Abfrage alle 3–60 Sekunden |
| Agent-Live-Ansicht | eigener Reiter der Desktop-Anwendung, zeigt live mit, was die KI gerade schreibt | dauerhaft |

Fähigkeiten: `begod-doctor`, `chronist`, `deep-research`, `knowledge-scout`.
Rollenbilder: `architect_reviewer`, `compliance_guardian`, `default_coder`,
`rubber_duck_debugger`.

## Generation 3 — heute

| Ort | Bestand |
|---|---|
| `~/.claude/agents/` | 1 — `compliance` |
| `buckeberg/.claude/agents/`, `hub/.claude/agents/` | je 15, identisch |
| `<repo>/.github/agents/` in 26 Repos | je 3, überall dieselbe Schablone |
| `fahrtenbuch/.claude/skills/` | 3 |
| `~/.claude/skills/` | ~84 Einträge, davon rund 60 Verweise auf ein Fremdpaket; **7 eigene**: `abwesend`, `cavelehr`, `design-waechter`, `papernetz`, `pause`, `synergien`, `ux-walkthrough` |
| **`brainlehr/.claude/`** | `launch.json`, `settings.json`, `worktrees/` — **kein `agents/`, kein `skills/`** |

**Korrektur einer Falschaussage des Berichts:** Er meldete,
`aufsaetze/agenten.py` erwarte Agentendefinitionen unter
`brainlehr/.claude/agents/` und finde sie nicht. Nachgesehen: Das Skript sucht
in `hub/.claude/agents` und `~/.claude/agents`. Es erwartet dort **nichts** und
vermisst folglich auch nichts.

## Was es damals gab und heute nicht

- **Das Rollenbild als Ganzes.** 81 benannte Rollen mit Toren, Vetorang und
  Weiterleitung gegen heute 1 eigenen Agenten in der Heimatablage.
- **Rollen, die sich ungefragt melden.** `spaghetti-monster` und
  `heiliger-geist` waren so gebaut: einer proaktiv gegen Verzettelung, einer
  verpflichtend am Sitzungsende. Heute meldet sich nichts von selbst.
- **Ein Prozess, der die Zeit im Blick behält.** Der Focus Guardian zählte
  hoch, solange eine Frage offen blieb.
- **Ein Weg nach außen.** Die Telegram-Brücke erreichte den Betreiber, ohne
  dass er im Gespräch sein musste.

## Was heute existiert und damals nicht

- `aufsaetze/agenten.py` — wertet die **tatsächliche Nutzung** von Agenten aus
  dem Laufzeitregister aus. Die Stiftshütte hatte `analyze_agent_gaps.py`, das
  Definitionen vergleicht. Der Unterschied ist genau der zwischen *was ist
  definiert* und *was wird benutzt*.
- Sieben eigene, projektübergreifende Fähigkeiten ohne Vorläufer.
- Das schlanke Einzeldateiformat mit Kopfdaten statt der alten `.agent.md`-Form.

## Die beiden Erinnerungen des Betreibers

**„Es meldete sich unaufgefordert etwas im Gespräch."** — **Teilweise
bestätigt, aber anders gebaut als erinnert.** Es gab drei Mechanismen, und
**keiner** war ein Unteragent, der im selben Kontextfenster das Wort ergreift:
ein eigener Betriebssystemprozess, der in eine Datei schrieb, die beim nächsten
Start gelesen wurde (Abfrage, kein Dazwischenrufen) · ein Dienst, der nach außen
meldete · eine eigene Fensteransicht. Die Erinnerung an das Erlebnis stimmt, die
an die Bauform nicht.

**„Ein Spaghettimonster warnte vor Verzetteln."** — **Bestätigt, unter fast
demselben Namen.** `begod/agents/spaghetti-monster.agent.md`, „Fliegendes
Spaghetti-Monster (Rotes Team)". Bemerkenswert ist seine zweite Hälfte: Es prüfte
nicht nur Code, sondern den **Prozess** — mit Regeln wie *„Agentenkette länger
als vier für eine Entscheidung → Vereinfachung prüfen"* und *„Agent ohne Auslöser
in fünf Sitzungen → Abschaltkandidat"*. Es hatte **kein Veto, nur Hinweisrecht.**

Diese zweite Regel ist der eigentliche Fund. Sie ist genau der Melder, der
diese Nacht zwölfmal von Hand gefunden werden musste: *gebaut, laufend, ohne
Auslöser.* Es gab ihn schon.
