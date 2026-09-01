# Brainlehr-Abschlussplan für Qwen3.8 in Hermes Agent

Stand: 2026-08-27. Dieser Plan ist ein Ausführungsplan zum einzigen normativen
Katalog `docs/REQUIREMENTS_BRAINLEHR.md`, kein zweiter Lastenkatalog. Bei einem
Widerspruch gilt die betroffene `BDW-*`-Zeile. `AI_HANDOFF.md` ist technische
Historie und darf keinen Produktstatus überstimmen.

## Teilplan-Navigation und Kontextwechsel

Qwen liest diesen Masterplan nur in Phase 00 vollständig. Danach arbeitet es
nur noch den im Laufstate benannten Teilplan ab; der Masterplan wird nicht
erneut geladen. Jeder Qwen-Teilplan endet mit einem Abschlussgate, aktualisiert
den kleinen JSON-Laufstate und verwendet im frischen Kontextfenster wieder
bytegleich `docs/qwen_abschluss/STARTPROMPT_STABLE.md`.

1. `docs/qwen_abschluss/00_BOOTSTRAP_OMLX_GRENZE.md`
2. `docs/qwen_abschluss/01_KATALOG_GRAPH_P60_P62.md`
3. `docs/qwen_abschluss/02_P42_ANALYZER_OSS.md`
4. `docs/qwen_abschluss/03_ALLE_MUST_P67.md`
5. `docs/qwen_abschluss/04_HERMES_ZWEI_REPOS.md`
6. `docs/qwen_abschluss/05_PAKET_DIFF_UEBERGABE.md`
7. `docs/qwen_abschluss/06_CODEX_ENDABNAHME.md` — ausschließlich Codex.

Ein Kontextwechsel ist nur erlaubt, wenn das Teilplan-Gate terminal PASS oder
terminal FAIL ist. Veränderliche Candidate-HEADs und Verdicts stehen niemals im
Startprompt, sondern ausschließlich in
`/Volumes/daten/brainlehr-qwen-run/state.json`. Chattext wird nicht gespeichert;
übertragen werden nur technische IDs, Hashes, knappe Evidenz, Verdicts und Gaps.

## 0. Auftrag und Ergebnisgrenze

Qwen baut aus dem aktuellen verifizierten Git-Stand Kandidaten-Commits. Codex
führt danach die unabhängige Endvalidierung, Eigentumsprüfung, Live-DB-Freigabe,
koordinierten Neustart und gegebenenfalls den privaten Push aus.

Qwen meldet deshalb niemals `FINAL PASS`, sondern höchstens `CANDIDATE PASS`.
Ein Gate ist nur Kandidat, wenn sein roter Test vorher scheiterte, der grüne
Test danach bestand und der exakte Befehl samt Ergebnis vorliegt.

Ausgangspunkte:

- Brainlehr: `/Volumes/daten/Begod2026/brainlehr`, Branch
  `brainlehr/b4-ausweis`, verifizierter HEAD `640ceca7`.
- Hermes-Adapter: `/Volumes/daten/Begod2026/hermes-brainlehr`.
- Lokaler Hermes-Host: `/Users/lehrmacbook/.hermes/hermes-agent`; nur testen
  und dokumentieren, niemals mit Adapter-Commits vermischen oder upstream
  pushen.
- Brainlehr-Produktiv-DB, Backups und MCP sind wegen P67 eingefroren. Qwen
  arbeitet nur mit `tmp_path`, frischen Test-DBs oder ausdrücklich erzeugten
  Kopien. Kein `project_ensure`, `project_context`, `project_change`, Recall,
  Checkpoint, Vacuum oder direkter Produktiv-DB-Zugriff.
- `bge-m3:latest`, 1024 Dimensionen, bleibt aktiver Basiskanal.
- P103 V9 ist gemessenes H0: CodeRank lieferte null einzigartige Treffer und
  keine strikte RRF-Verbesserung. CodeRank/RRF bleiben inaktiv; V4-V9 werden
  weder wiederholt noch nachgetuned, das Modell nicht erneut geladen/pullt.
- P2-Dashboardarbeit bleibt ausgeschlossen. Eine 3D-Projektion wird nur als
  späteres, messbares P2-Pilotgate spezifiziert.

## 1. Harte Verbote

Qwen darf niemals:

1. Nutzeränderungen, untracked Dateien, Datenbanken, Backups, Korpora,
   Receipts, Wissen, Quellen oder Capsule-Historie löschen, verschieben,
   überschreiben, stage-en oder in einen Commit kopieren.
2. `git add -A`, `git add .`, `git commit -a`, `git reset --hard`,
   `git checkout --`, `git clean`, rekursives `rm` oder Force-Push verwenden.
3. einen historischen Checkpoint erfinden oder schließen. Der alte Name
   `brainlehr-vibecoding-20260826-pause1` lieferte zuletzt null.
4. Recall-Aussagen, Katalogstatus oder Agentenberichte als Primärbeleg nutzen.
5. freie AI-Kommentare schreiben. Default ist `NONE`; erlaubt ist nur ein vom
   vorhandenen Validator akzeptierter, revisionsgebundener `brainlehr:link`.
   Vorhandene menschliche Kommentare bleiben bytegleich.
6. CodeRank aktivieren, Vektoren konkatenieren, Kosinuswerte zwischen Modellen
   mischen oder eine Graphkante aus einem Embedding-Treffer erfinden.
7. Graphify als Abhängigkeit einbauen. Es ist nur nichtnormativer Zeuge.
8. P2-/Dashboardpfade anfassen.
9. pushen. Qwen erzeugt höchstens lokale, atomare Kandidaten-Commits.
10. gleichzeitig Qwen/OMLX und ein weiteres großes ML-Modell laden.

Stoppe nur bei einem nicht selbst lösbaren Blocker oder exakt `es wird ernst`.
Ein roter Test ist kein Blocker: Ursache finden, kleinsten Root-Cause-Fix bauen,
erneut prüfen.

## 2. Arbeitsform für ein schwächeres Modell

Qwen arbeitet immer nur an einer Karte. Jede Karte umfasst höchstens zwei
Produktdateien plus fokussierte Tests und Dokumentstatus.

Für jede Karte exakt diese Schleife:

1. Lies die vollständige betroffene `BDW-*`-Zeile und alle genannten ACs.
2. Verifiziere den Ist-Stand mit `rg`; lies jeden direkten Aufrufer der zu
   ändernden Funktion. Keine Änderung nach Dateiname-Raten.
3. Erfasse `git status --short` und notiere die erlaubten Pfade der Karte.
4. Schreibe genau den kleinsten roten Positiv-/Negativtest.
5. Führe nur diesen Test aus und belege, dass er aus dem richtigen Grund rot ist.
6. Implementiere den kleinsten gemeinsamen Root-Cause-Fix.
7. Führe den roten Test, direkte Geschwistertests und eine Gegenprobe aus.
8. Prüfe `git diff --check` und `git diff -- <erlaubte Pfade>`.
9. Stage ausschließlich explizite Pfade. Prüfe danach zwingend:

   ```bash
   git diff --cached --name-status
   git diff --cached --numstat
   git diff --cached
   ```

10. Enthält der Index einen fremden Pfad/Hunk: nicht committen, Index nur für
    die selbst gestagten Pfade wieder leeren, Ursache dokumentieren.
11. Commit nach `git-ai-handoff`: Warum, Verifikation,
    `AI-Assisted-By: Qwen3.8 via Hermes Agent`, Agentpfad.
12. Danach `git show --stat --oneline HEAD` und geänderte Zeilenzahl gegen die
    erwartete Karte prüfen.
13. Im Bericht nur: Karte, Commit, Red-Befehl, Green-Befehl, Ergebnis, Restgap.

Keine Sammelrefaktoren. Keine neuen Frameworks. Standardbibliothek und bereits
vorhandene Module zuerst. Ein Fehler in einem gemeinsamen Pfad wird einmal im
gemeinsamen Pfad behoben, nicht in jedem Aufrufer.

## 3. Kontext- und Zustandsdisziplin

Nur in Phase 00 einmal vollständig lesen:

1. `AI_HANDOFF.md`
2. `docs/REQUIREMENTS_BRAINLEHR.md`
3. diesen Plan
4. `AGENTS.md`, falls im Arbeitsbaum vorhanden

In jedem Fenster ist die Ladefolge fest:

1. bytegleiches `docs/qwen_abschluss/STARTPROMPT_STABLE.md`;
2. unverändertes `docs/qwen_abschluss/BOOTSTRAP_STABLE.md`;
3. `/Volumes/daten/brainlehr-qwen-run/state.json` plus Schema;
4. genau der in `next_phase_path` benannte Teilplan.

Danach nie den ganzen Bestand erneut laden. Pro Karte nur:

- eine BDW-Zeile,
- direkt genannte Tests/Produktdateien,
- direkte Aufrufer,
- höchstens die letzte relevante Handoff-Notiz.

Brainlehr-Recall bleibt bis zur P67-Freigabe aus. Qwen speichert keine Prompts,
Transkripte oder Thinking-Texte. Dauerhaft sind nur Requirement-ID, Commit,
Testbefehl, Hash, Verdict und offener Gap.

Nach jeder Phase Laufstate auf technische Fakten begrenzen:

```text
phase / candidate HEADs / evidence / verdict / exact gaps / next phase /
open MUST IDs / cache metrics / DB mode / push status
```

## 4. Hermes-/OMLX-Startgate

Primärbefund: `/Users/lehrmacbook/.hermes/config.yaml` enthält bereits:

```yaml
model:
  default: Qwen3.8-27B-MLX-4bit
  provider: omlx
  context_length: 262144
  base_url: http://localhost:8010/v1
```

Der alte Fehler mit 49.152 Token beweist deshalb nicht, dass der Wert fehlt;
er beweist, dass der laufende Pfad ihn damals nicht wirksam übernommen hat.
Qwen ändert `context_length` nicht blind.

Startgate in dieser Reihenfolge:

1. Prüfe, dass OMLX genau ein großes Modell führt und keine CodeRank-MPS-
   Auswertung läuft.
2. Prüfe `/v1/models`, ohne Schlüssel oder vollständige Konfiguration
   auszugeben. Modellname muss exakt `Qwen3.8-27B-MLX-4bit` sein.
3. Führe im lokalen Hermes-Host die fokussierten Context-Resolver-Tests aus,
   insbesondere `tests/test_ctx_halving_fix.py` und Tests zur expliziten
   `model.context_length`-Priorität.
4. Belege, dass der Resolver bei genau dieser Konfiguration `262144` liefert
   und den Serverwert `49152` nicht über den expliziten Wert stellt.
5. Erst wenn 3 und 4 grün sind: Hermes kontrolliert neu starten. Vorher PID und
   Startzeit notieren; danach neue PID/Startzeit und Agent-Init belegen.
6. Einen leeren Agentstart und einen kurzen Tool-Call ausführen. PASS nur wenn
   Init ohne 64K-Fehler gelingt und der angezeigte/effective Context mindestens
   64K ist.
7. Bei Speicher-/Thermalproblemen nicht den Kontextwert fälschen. Nur einen
   großen Modellprozess, Batch 1, einen Worker; freien Speicher, Swapout und
   Throttle beobachten. Bei Swapout-Anstieg, Throttle oder freiem RAM unter
   25 Prozent abbrechen und als Ressourcen-Gap melden.

Dieses Gate verändert weder Brainlehr-DB noch Adapter-Repository.

## 5. Ausgangsaudit und sichere Baugrenze

Qwen führt zuerst read-only aus:

```bash
cd /Volumes/daten/Begod2026/brainlehr
git rev-parse HEAD
git status --short
git diff --cached --name-status
git diff --cached --numstat
git remote -v

cd /Volumes/daten/Begod2026/hermes-brainlehr
git rev-parse HEAD
git status --short
git diff --cached --name-status
git diff --cached --numstat
git remote -v

cd /Users/lehrmacbook/.hermes/hermes-agent
git rev-parse HEAD
git status --short
```

Erwartung: nichts gestaged. Abweichung ist ein Gate-Fail, kein Anlass zum
Leeren des Index.

Der gemischte Hauptworktree bleibt Schutzobjekt. Neue Implementierung erfolgt
bevorzugt in einem separaten Git-Worktree unter `/Volumes/daten`, basierend auf
dem verifizierten HEAD. Vorhandene untracked Dateien des Hauptworktrees werden
nicht gelesen oder kopiert, um vermeintliche Agentenarbeit nicht versehentlich
als Eigentum zu übernehmen. Kandidaten-Commits bleiben auf einem lokalen
`qwen/`-Branch; Codex entscheidet später über Cherry-pick.

## 6. Katalogledger: keine MUST-Zeile vergessen

Qwen erzeugt keine zweite Requirements-Liste. Es prüft jede Tabellenzeile des
Root-Katalogs und führt ein abgeleitetes Ledger außerhalb des Katalogs.

Für jede `MUSS`- und `MUSS-NICHT`-Zeile:

- `PASS`: Primärtest erneut gegen aktuellen Kandidaten-HEAD ausführen.
- `TEILWEISE`, `FAIL`, `NOT RUN`: tatsächliches AC lesen und Karte anlegen.
- `DEFERRED`/`PILOT`: Defer-Gate selbst prüfen. Nur akzeptieren, wenn Trigger,
  Owner und Aktivierungsbedingung belegt sind; sonst FAIL.
- historische Handoff-PASS-Aussage bei abweichender Produktgate-Zelle ignorieren.

Mindestbefehl:

```bash
python3 -m pytest -q tests/test_requirements_brainlehr.py
rg -n '^\| BDW-' docs/REQUIREMENTS_BRAINLEHR.md
rg -n 'TEILWEISE|FAIL|NOT RUN|DEFERRED|PILOT|CONFLICT' docs/REQUIREMENTS_BRAINLEHR.md
```

Jede verbleibende Nicht-PASS-Zeile erhält: exaktes AC, Testbefehl, aktuelles
Verdict, kleinste nächste Probe. Keine pauschale Aussage „alle Gates grün“.

## 7. Priorisierte Karten

### Karte A — Katalog- und Testdrift

Ziel: Katalog, Gate-Tests und aktuelle Primärevidenz widersprechen sich nicht.

Betroffene stabile IDs: `BDW-P99`, `BDW-P100`, `BDW-P101`, `BDW-P102`,
`BDW-P103`, `BDW-P104`.

- P99-P104 gegen aktuelle Produktdateien und fokussierte Tests verifizieren.
- P103 auf V9 PASS/H0 binden: raw
  `0d08110a4ba249ee2a080dd32154b3ce02de355206333ec02e9247cf382ef954`,
  collector
  `dbda275582eb179ea0a439f6009903578e8d94953e26cc8a323f89763e3f8626`.
- Alte Tests, die weiterhin `NOT IMPLEMENTED`, V5 oder `H0 undecided`
  verlangen, sind rot zu aktualisieren; nicht Produktstatus zurückdrehen.
- Kein erneuter Score-Lauf.

### Karte B — P60 fail-closed Graphpersistenz

Graphify ist nur Zeuge für ein nützliches Muster: ein vollständiger Graph darf
nicht durch einen partiellen/kleineren oder unlesbaren Lauf still überschrieben
werden. Brainlehr implementiert dies im vorhandenen Graphspeicher, ohne neue
Abhängigkeit.

Red-Tests:

1. vorhandener Graph N Knoten, neuer unvollständiger Graph kleiner als N:
   Write wird abgewiesen, Originalbytes bleiben gleich;
2. vorhandener nichtleerer, unlesbarer Graph: fail closed;
3. simulierter Abbruch vor atomarem Replace: Original bleibt lesbar;
4. explizit verifizierte legitime Löschung/Tombstone bleibt möglich;
5. Backup/Restore bindet Schema, Revision und Hash.

Suche zuerst den gemeinsamen Schreibpfad in `kern/graph_envelope_store.py` und
alle Aufrufer. Kein zweiter Store, kein Graphify-Import.

### Karte C — P34/P35/P40/P47/P62 struktureller Retrievalkanal

Bestehende Wahrheit bleibt ein revisionsgebundener typisierter Graph. Er ist
der strukturelle dritte Kanal neben BGE-M3 und einem derzeit inaktiven
CodeRank-Kandidaten.

Pflichtinvarianten:

- BGE liefert semantische Kandidaten; Graph liefert nur belegte Pfade/Kanten.
- CodeRank bleibt deaktiviert.
- Fusion findet nur über bounded Treffer-/Kontextlisten statt, niemals über
  Vektorkonkatenation oder erfundene Kanten.
- `query`, `path`, `explain` liefern ausgewählte Teilgraphen lazy und
  budgetiert; stale Revision, unbekannte Kante und Budgetende bleiben Gap.
- `EXTRACTED`, `INFERRED`, `AMBIGUOUS/GAP`, `OBSERVED` bleiben visuell und
  maschinell unterscheidbar.
- Über einer Größenkappe wird ein Community-/Subsystemgraph gezeigt, nicht der
  Vollgraph in den Browser gedrückt.

Vor Neubau mit `rg` prüfen, welche dieser Funktionen bereits P35/P40/P47/P98
abdecken. Nur fehlende Invariante ergänzen. Kein neues UI-Framework.

3D ist P2 und bleibt NOT RUN. Späteres Pilotgate: dieselbe Graph-ID, Revision
und Hash; Z-Achse kodiert fachlich entweder Wirkungskettenstufe oder
Evidenz-/Zeitlage, nie dekorative Zufallstiefe; 2D- und Tastaturfallback;
Humanvergleich misst Pfadfindungszeit, Fehlpfade und Verständnis gegen 2D.

### Karte D — P42 Wahrheitskonflikt

`.brainlehr.json`, Registry, Code und Tests müssen dieselbe Wahrheit sagen.
SCIP/Semgrep/tree-sitter sind nur callable, wenn registrierter realer Runner,
Version, Hash, Sandbox und ein erfolgreicher Lauf vorliegen. Bounded
Runner-Evidenz und `planned/non-callable` dürfen nicht gleichzeitig als
Produktstatus bestehen.

Red-Test zuerst: Konfiguration behauptet callable, obwohl Tool/Runner/Attest
fehlt, oder umgekehrt. Ergebnis ist entweder sauber registriert und messbar
oder sichtbar planned/gap. Keine stille Promotion.

### Karte E — alte Nicht-PASS-Gates einschließlich P67

Nicht nur P71-P104 prüfen. Besonders P04, P05, F05, P42 und jede weitere vom
Ledger gefundene MUST/MUST-NOT-Zeile gegen ihr tatsächliches AC ausführen.

P67 bleibt Kandidat, solange die Produktiv-DB eingefroren ist. Qwen darf:

- alle DB-Gates auf frischen/temporären Datenbanken ausführen;
- Trigger-SQL nach Schemaänderungen in `sqlite_master` prüfen;
- Paket-, Pfad-, Datenschutz-, Restore- und Korruptionsnegativtests ausführen.

Qwen darf nicht:

- die echte DB öffnen, migrieren, checkpointen, vacuumen oder über MCP lesen;
- Backups verändern;
- den Freeze selbst aufheben.

Codex übernimmt später den unabhängigen Live-P67-Audit.

### Karte F — zwei Repositories und Hermes-Grenzen

Brainlehr und `hermes-brainlehr` sind getrennte Commitreihen.

Adapterpflicht:

- `README.md`, `brainlehr_provider.py`, `tests/test_provider.py` als eigene
  Adaptergrenze prüfen;
- Python 3.11, 3.12 und 3.13: jeweils erwartete Matrix ausführen;
- Fake-Transport: foreground genau ein Recall; cron, oneshot, background,
  subagent und unknown null Brainlehr-Writes;
- Built-in Hermes Memory und Brainlehr-Provider getrennt;
- empty/timeout/error sichtbar; Retry erzeugt keine Duplikate;
- keine Prompts, Transkripte, Rohcode oder Secrets persistieren.

Lokaler Acht-Dateien-Hermes-Kompatibilitätspatch:

- nur separat testen und Hash/Dateiliste dokumentieren;
- niemals in Adaptercommit kopieren;
- niemals upstream pushen;
- Context-Resolver-Fix muss expliziten `model.context_length` respektieren.

### Karte G — OSS-Finalisten

Nichtnormative Zeugen explizit klassifizieren:

- OpenSpec und Spec Kit: Zeugen/Testfrontends, niemals Normquelle;
- Graphify: Zeuge für query/path/explain, Provenienzvisualisierung,
  Community-Aggregation und fail-closed Graph-Overwrite; keine Dependency;
- GUAC, Syft/Grype, DevLake/GrimoireLab: je `integriert`, `gemessener Gap`
  oder `DEFERRED mit erfülltem Defer-Gate`;
- Größe allein ist kein Ablehnungsgrund.

Jede Klassifikation nennt offizielle Primärquelle, Version/Revision, gemessene
lokale Lücke und betroffene BDW-ID. Marketingbenchmarks sind kein PASS-Beleg.

## 8. Kombinierte Verifikation

Erst wenn alle Einzelkarten grün/kandidaten-grün sind:

1. fokussierte P71-P104-Suite;
2. alle Katalog-/Plan-/Handoff-Invarianztests;
3. vollständige deterministische CPU-Suite auf frischer temporärer DB;
4. alle explizit isolierten System-/Live-Fixtures, niemals Produktiv-DB;
5. Hermes-Adaptermatrix 3.11/3.12/3.13;
6. Paketbau offline;
7. Installation von Wheel und sdist in frische Umgebungen;
8. Import-/CLI-/MCP-Schema-Smoke ohne Produktiv-DB;
9. Karten/Currentness und allowlisted Public Export gegen Fixtures;
10. Pfad-/Secret-/Prompt-/Transcript-Leakscan;
11. Eigentums- und Diffgrenze beider Repositories.

Paketbeispiel, vorhandene Projektbefehle bevorzugen:

```bash
python3 -m pytest -q
python3 -m pytest -q tests/test_paketbau.py
uv build --offline
git diff --check
```

Ein Full-Suite-Fehler wird klassifiziert: echter Regressionstest, externe
Voraussetzung, P2-ausgeschlossen oder kontaminierte Umgebung. Kein `xfail`,
Skip oder Allowlist nur zum Grünmachen.

## 9. Kandidaten-Commits

Commitreihenfolge:

1. Katalog-/Gate-Testdrift;
2. P60 Graphpersistenz;
3. fehlende strukturelle Graphinvariante, nur falls wirklich fehlend;
4. P42 Wahrheitsabgleich;
5. je altem Nicht-PASS-Gate eine kleine Root-Cause-Karte;
6. Brainlehr Paket-/Handoff-/Currentness-Evidenz;
7. getrennte Hermes-Adaptercommits.

Keine Commitserie darf P2, Produktiv-DB, Backups, Korpora, fremde untracked
Dateien oder lokale Hermes-Hostpatches enthalten.

Nach jedem Commit:

```bash
git show --stat --oneline HEAD
git status --short
```

Qwen pusht nicht. Codex validiert später jeden Commit aus einem frischen
Checkout, prüft `git diff --cached --numstat`, Handoff, Paketinstallation,
Remote-Privacy und erst danach einen privaten Push mit Fetch/Remote-HEAD-
Gegenprobe.

## 10. Übergabeformat an Codex

Qwen liefert genau diese Tabelle, ohne Erfolgserzählung:

| Feld | Inhalt |
|---|---|
| Candidate branch/HEAD | exakte Hashes je Repo |
| Commits | Hash, BDW-IDs, Pfade, Zeilenzahl |
| Red evidence | exakter Befehl und erwarteter Fehler |
| Green evidence | exakter Befehl, Count, Dauer |
| Full suite | PASS/FAIL mit erstem echten Fehler |
| Package | Wheel/sdist SHA-256 und Install-Smoke |
| Hermes | effektiver Kontext, PID/Startzeit, 3.11-3.13-Matrix |
| DB | `UNTOUCHED/FROZEN` |
| CodeRank | `H0/INACTIVE/NOT RERUN` |
| BGE-M3 | Modell/Digest/1024d/active |
| Protected material | unveränderte Pfadklassen |
| Remaining MUST | jede ID, kein Sammelbegriff |
| Push | `NOT DONE` |

Abschlussformulierung von Qwen:

```text
CANDIDATE PASS oder CANDIDATE FAIL.
Kein FINAL PASS; unabhängige Codex-Validierung und P67-Livefreigabe stehen aus.
```

## 11. Copy-paste-Startprompt für Hermes/Qwen

Immer den vollständigen, unveränderten Inhalt von
`docs/qwen_abschluss/STARTPROMPT_STABLE.md` senden. Keine Phase, keinen HEAD und
keinen Abschlussblock anfügen. Diese wechselnden Daten stehen im validierten
Laufstate und werden erst nach dem stabilen Präfix geladen.
