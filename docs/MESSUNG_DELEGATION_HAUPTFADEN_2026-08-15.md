# Messung: Wann baut der Hauptfaden selbst, wann delegiert er?

Erzeugt 2026-08-15T08:27:01+0200. Auslöser: Betreiber beanstandete
2026-08-15T07:05:00+0200, es werde zu oft selbst gebaut, "es passiert immer
wieder". Das ist als Behauptung geprüft, nicht als Vorgabe übernommen.

Sieht der Code/die Datenlage anders aus als hier beschrieben: an den Code/die
Rohdaten halten, Abweichung melden.

## Quellen

- Sitzungsprotokolle: `~/.claude/projects/-Volumes-daten-Begod2026-brainlehr*/*.jsonl`,
  22 Dateien, Zeitraum 2026-08-08T08:20:01Z bis 2026-08-15T06:19:25Z.
- Agentenregister: `/Volumes/daten/Begod2026/hub/laufzeit/agent-register.jsonl`,
  602 Zeilen gesamt, brainlehr-Anteil 264 `file`-Ereignisse, Zeitraum
  2026-08-14T08:45:52 bis 2026-08-15T08:24:57 (Ort per
  `agent_register_ort.pfad()` erfragt, nicht geraten).
- Bestehende Auto-Memory: `delegation-pro-schritt-geprueft-summe-bezahlt.md`.
- Wissensspeicher (`lesson_query`, `knowledge_search`): kein bestehender
  Eintrag deckt die hier gemessenen Befunde ab (Nachbarschaft: L-c41320,
  L-0bb2e5, L-53eeda — alle zu Durchsetzungslücken der Kaskaden-Regel, nicht
  zum Direktbau-Muster selbst).

## Befund 1 — JSONL-Zählung unterschätzt Delegation strukturell

Aus den 22 Sitzungsprotokollen (Hauptfaden-Sicht, `parentUuid`-Kette
rekonstruiert, `isSidechain` ist in dieser Umgebung durchgängig `false`/fehlt
und daher untauglich als Unterscheidungsmerkmal):

- Direkte `Edit`+`Write`+`MultiEdit` vom Hauptfaden: 733 + 359 + 0 = **1092**.
- `Agent`-Starts vom Hauptfaden: **420** (plus 12 verschachtelte Agent-in-Agent-Starts).
- `run_in_background`: 255× nicht gesetzt (Standard = Hintergrund), 96× explizit
  `true`, 81× explizit `false` — **rund 81 % aller Agent-Starts laufen im
  Hintergrund.**
- Innerhalb der lokal inline sichtbaren Subagenten-Teilbäume (nur die
  synchronen, `run_in_background:false`-Fälle sind überhaupt als Kette im
  selben Protokoll auffindbar): **0** `Edit`/`Write`/`MultiEdit`-Aufrufe über
  alle 22 Dateien.

Das ist kein Beleg dafür, dass Subagenten nie bauen. Es ist der Beleg, dass
das lokale JSONL-Protokoll die tatsächliche Werkzeugspur von
Hintergrund-Agenten **nicht enthält** — nur deren Abschluss-Ereignis
(`tool_result`) erscheint im Hauptfaden-Protokoll. Eine Zählung, die sich auf
JSONL allein stützt, würde "der Hauptfaden baut praktisch alles selbst"
melden — und läge falsch, weil sie die unsichtbare Mehrheit der Agentenarbeit
ausblendet. Deshalb: Befund 2 zählt stattdessen das Agentenregister, das
Datei-Anfassungen unabhängig vom Vordergrund/Hintergrund-Status protokolliert.

## Befund 2 — Registerbasiert: 39 % der Dateianfassungen sind delegiert, mit Tagesschwankung

Register, `ev=file`, Pfad enthält `/brainlehr` (264 Ereignisse,
2026-08-14T08:45 bis 2026-08-15T08:24, rund 24 Stunden):

| Rolle | Ereignisse | Eindeutige Dateien |
|---|---|---|
| orchestrator | 162 | 60 |
| subagent | 102 (60× `general-purpose`, 42× `implementer`) | 47 |

Pro Tag aufgeschlüsselt:

| Tag | orchestrator | subagent | Anteil delegiert |
|---|---|---|---|
| 2026-08-14 | 150 | 69 | 31 % |
| 2026-08-15 (bis 08:24, also grösstenteils NACH der Beanstandung um 07:05) | 12 | 33 | **73 %** |

**Das ist der Befund, der der Ausgangsbehauptung widerspricht bzw. sie
einschränkt:** Im kurzen Fenster nach der Beanstandung überwiegt Delegation
deutlich (33 von 45 Dateianfassungen). Einschränkung der Aussagekraft: das
Fenster ist nur gut anderthalb Stunden lang und deckt damit nicht den
Zeitraum ab, den die Beanstandung eigentlich meinte (die Tage/Sitzungen
davor, für die kein Register-Datenbestand mehr vorliegt — die JSONL-Zählung
aus Befund 1 ist für diesen längeren Zeitraum die einzige Quelle, und sie
zeigt keinen Rückgang der `Agent`-Starts über die Woche).

## Befund 3 — Direktbau ist überwiegend Nacharbeit NACH Delegation, nicht statt Delegation

8 Dateien wurden im Register-Zeitraum von BEIDEN Rollen angefasst. Für die 4
mit den meisten Ereignissen wurde die zeitliche Reihenfolge geprüft:

| Datei | Muster |
|---|---|
| `haken/regelwechsel.py` | subagent 5× (10:37–11:30) → orchestrator 1× (11:37, 7 Min. später) |
| `kern/domaene.py` | subagent 3× (21:55) → orchestrator 2× (22:01, 6 Min. später) |
| `kern/normachsen.py` | subagent 4× (11:28–11:30) → orchestrator 3× (11:38–16:10) |
| `tests/test_satzwache.py` | subagent 4× (23:22–23:24) → orchestrator 1× (23:28, 4 Min. später) |

In allen 4 geprüften Fällen: Subagent zuerst, Orchestrator-Anfassung danach,
Abstand 4–10 Minuten. Das ist das Muster "Subagent baut, Orchestrator
korrigiert/schliesst ab" — nicht "Orchestrator baut statt zu delegieren".
Stichprobe, kein Vollbeweis (nur 4 von 8 Überschneidungs-Dateien geprüft),
aber konsistent in alle 4 Richtungen gleich.

## Befund 4 — Wo tatsächlich ausschliesslich der Orchestrator baute

Dateien mit Anfassung NUR durch `orchestrator` (kein `subagent`-Ereignis im
Register-Zeitraum), absteigend:

`STAND.md` (35×, Status-/Koordinationsdokument), `kern/dokumentdienst.py`
(19×), `melder/pruefer.py` (13×), `docs/PLAN_OPENLEHR_2026-08-14.md` (8×),
`docs/PLAN_GESAMT_2026-08-13.md` (6×), `tests/test_alle_selftests.py` (5×),
zwei ADR-Dateien (4×, 3×), `haken/worktree_identitaet.py` (3×), zwei weitere
Testdateien und eine `spikes/`-Datei (je 2×), `requirements.txt` (2×).

Status-/Plan-/ADR-Dateien sind Entscheidungsdokumente des Orchestrators
selbst — Direktbau dort ist keine unterlassene Delegation. Die zwei Fälle,
die als echter Code-Direktbau ohne jede Subagenten-Beteiligung gelten:
`kern/dokumentdienst.py` (19 Anfassungen) und `melder/pruefer.py` (13
Anfassungen). Diese zwei sind die konkreten Kandidaten, an denen die
Beanstandung zutrifft — nicht am Gesamtbild.

## Zu Frage 3 — Kosten selbst gebaut vs. delegiert

Nicht seriös aus den lokalen Protokollen beantwortbar. Grund: Hintergrund-
Agenten (≈ 81 % aller Starts, Befund 1) haben keine lokal gespeicherte
Werkzeugspur, also auch keine lokal messbaren Tokenzahlen — ihre Kosten
laufen serverseitig, sind aber hier nicht einsehbar. Die einzige lokal
messbare Grösse (Hauptfaden-Tokens über 7 Tage: 9,32 Mrd., davon 9,20 Mrd.
`cache_read_input_tokens`, nur 22,1 Mio. `output_tokens`) zeigt vor allem:
Der dominante Kostentreiber des Hauptfadens ist das wiederholte Einlesen des
wachsenden Kontexts bei jedem Zug, nicht die Entscheidung Edit-selbst-vs-
delegieren. Ein sauberer Pro-Aufgabe-Vergleich (selbst gebaut ↔ delegiert)
würde eine Zuordnung "diese Tokens gehören zu dieser abgeschlossenen
Teilaufgabe" voraussetzen, die aus den vorliegenden Daten nicht rekonstruierbar
ist. **Ungemessen — keine Grössenordnung wird hier behauptet.**

## Zu Frage 4 — Mechanisierbare Bedingung

Die Stelle, an der die Regel heute gebrochen würde: `hub/laufzeit/agent-
register.jsonl` wird bereits von zwei Haken gelesen
(`hub/scripts/agent_reuse_guard_hook.py`, `hub/scripts/quality_gate_hook.py`),
aber keiner davon prüft das Verhältnis orchestrator:subagent oder erkennt
einen "kalten Direktbau" (erste Anfassung einer Datei in der laufenden
Sitzung ist ein `orchestrator`-`Edit`/`Write`, ohne dass zuvor in derselben
Sitzung ein `Agent`-Start protokolliert wurde). Ein Haken liesse sich dort
ansetzen: bei jedem `file`-Ereignis mit `rolle=orchestrator` und einer Datei
ausserhalb der in Befund 4 genannten Dokument-Muster (`STAND.md`,
`docs/PLAN_*`, `docs/adr/*`) prüfen, ob in derselben `session` bereits ein
`start`-Ereignis mit `rolle=subagent` vorausging. Fehlt es, ist das ein
"kalter Direktbau" — genau das Muster, das Befund 3 als Ausnahme (Nacharbeit
nach Delegation) von der Regel unterscheidet. Nicht vorgeschlagen: ein
Blocker. Aus L-cd95a1 und L-c41320 ist belegt, dass PreToolUse-Blocker bei
falscher Annahme über den Hook-Input flottenweit fehlschlagen und dass ein
durchsetzendes Werkzeug seine Regelquelle nennen muss, sonst überlebt es
selbst eine abgelöste Regel. Ein zählendes/meldendes Signal (z. B. in
`melder/`) ist der risikoärmere erste Schritt.

## Zur Auto-Memory-Notiz "delegation-pro-schritt-geprueft-summe-bezahlt"

Ihre These — die Prüfung "soll ich delegieren?" laufe pro Werkzeugaufruf statt
pro Vorhaben — ist aus den Protokollen selbst nicht direkt nachweisbar (das
ist ein Aussage über internes Vorgehen, keine beobachtbare Grösse in JSONL
oder Register). Indirekt eingeschränkt wird aber ihre zugespitzte Formulierung
"greift deshalb strukturell nie": Befund 2 zeigt 39 % delegierte
Dateianfassungen über 24 Stunden, an einem Tag sogar 73 %. "Nie" ist zu stark;
"ungleichmässig, mit Tagen deutlich unter dem Zielbild" ist die durch die
Daten gedeckte Fassung.
