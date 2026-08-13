# Regelmechanik — 19 Abschnitte aus ~/.claude/CLAUDE.md, einzeln eingeordnet

Datum: 2026-08-13T03:31:32+0200
Commit bei Messung: 28b5c05 (Zweig brainlehr/b4-ausweis)
Messauftrag, kein Bauauftrag — nichts hier gebaut, nur eingeordnet.

## Frage und Trennlinie

Für jede der 19 Regeln in `~/.claude/CLAUDE.md`: Lässt sich eine Bedingung
benennen, die GENAU DANN fehlschlägt, wenn die Regel verletzt wird — ohne
Urteil, ohne Sprachmodell?

- **A** mechanisierbar, unverdrahtet — Bedingung benennbar, kein Mechanismus vorhanden.
- **B** mechanisierbar, Mechanismus vorhanden, aber nirgends angehängt.
- **C** verdrahtet — läuft, mit Beleg.
- **D** nicht mechanisierbar — braucht Urteil, begründet warum.

## Ausgangslage: was sich seit runs/regelgriff_2026-08-12.json geändert hat

Der Vorlauf vom 2026-08-12 (Commit ffc52b7) hatte dieselben 19 Abschnitte
bereits grob geclustert (2 verdrahtet / 2 Teilaspekt / 3 vorhanden-unverdrahtet
/ 1 „externes Plugin" / 11 ohne Mechanismus). Seither, laut Auftrag, wurde
GENAU EINE Regel verdrahtet: die Existenzprüfung hängt jetzt am `Stop`-Hook
einer neuen projekteigenen `.claude/settings.json` (Commit 24c2484), mit
einem Test, der den EINTRAG prüft (`tests/test_existenzpruefung_verdrahtung.py`).
Geprüft und bestätigt: der Hook zeigt auf `haken/existenzpruefung.py`, die
Datei existiert, der Test prüft exakt den Eintrag (nicht das Verhalten des
Hooks — das decken neun andere Testfälle in `tests/test_existenzpruefung.py`).

**Eine Korrektur zum Vorlauf, nicht nur eine Bestätigung:** Der Vorlauf hatte
„Caveman mode: always on" als über ein „externes Plugin" verdrahtet
eingeordnet. Das ist bei dieser Messung NICHT bestätigt worden — im Gegenteil:
`grep -i caveman ~/.claude/settings.json` und die Marketplace-Verzeichnisse
unter `~/.claude/plugins/marketplaces/` (nur `ponytail` und
`claude-plugins-official`) liefern null Treffer. Was tatsächlich als
`SubagentStart`-Hook feuert, ist `ponytail` (im eigenen Systemreminder dieser
Sitzung sichtbar: „PONYTAIL MODE ACTIVE"), nicht `caveman`. `caveman` liegt nur
als manuell aufrufbarer Skill unter `~/.claude/skills/caveman*` — kein
Hook-Eintrag in `~/.claude/settings.json`, keine Plugin-Registrierung. Die
Regel „ab der ersten Antwort jeder Sitzung, ohne Trigger" hat in DIESER
Sitzung nachweislich nicht selbständig gegriffen: Der Agent, der diesen
Auftrag bearbeitet, hat den Skill nicht von sich aus aufgerufen — genau der
Fall, den die Regel verbietet. Eingeordnet unten daher als **A**, nicht C.

## Einteilung, nach Aufwand sortiert (billig → teuer)

### Kostenlos — bereits verdrahtet (C)

**16. Nachsehen, bevor gefragt oder delegiert wird — C.**
Beleg: `.claude/settings.json` (projekteigen) registriert
`haken/existenzpruefung.py` am `Stop`-Hook; `tests/test_existenzpruefung_verdrahtung.py`
prüft den Eintrag (Datei liest `.claude/settings.json`, sucht `existenzpruefung.py`
im `Stop`-Kommando, prüft dass die Zieldatei existiert). Verhalten selbst
(Verneinungs-Erkennung + Bestandssuche) ist über neun weitere Testfälle in
`tests/test_existenzpruefung.py` abgesichert. Läuft bei jedem Session-Ende.

**4. BSI-Compliance Hard-Stops — C.**
Beleg: `hub/scripts/quality_gate_hook.py` ist am globalen `Stop`-Hook
registriert (`~/.claude/settings.json`, Zeile im `Stop`-Block) und enthält
ein Muster, das u. a. `crypt|secret|password|database|sqlite|migration`
erfasst (Zeile 53 der Datei) — schlägt bei jedem Sitzungsende auf
sicherheitsrelevante Muster an, unabhängig vom Projekt.

**10. Wissen festhalten & abrufen — C.**
Beleg: `haken/knowledge_recall_hook.py` am `UserPromptSubmit`-Hook,
`haken/knowledge_capture_hook.py` am `Stop`-Hook — beide in
`~/.claude/settings.json` eingetragen, beide liefen in dieser Sitzung
(Systemreminder-Injektion beim Prompt ist der laufende Beleg).

### Sehr billig — Mechanismus fertig, fehlt nur der Draht (B)

**5. WCAG 2.2 AA — B.**
Mechanismus vorhanden: `~/.claude/skills/design-waechter/ui_guard.py`,
laut eigener Beschreibung deterministisch. Fehlender Anhängepunkt bestätigt:
`grep -c ui_guard ~/.claude/settings.json` → 0 Treffer, keine Referenz in
irgendeinem Hook-Event. Anhängepunkt wäre `PostToolUse` mit Matcher
`Edit|Write` auf UI-tragende Dateiendungen (`.html`, `.dart`, `.tsx` je nach
Projekt) — exakt das Muster, das `hub/scripts/monolith_guard.py` schon für
Zeilenzahl fährt.

**9. Keine Entwicklerinformation in der Oberfläche — B.**
Derselbe Mechanismus wie oben (`ui_guard.py`, Regeln `selbsterklaerung` und
`maskierter-wert`), derselbe fehlende Draht. Ein Anhängepunkt deckt beide
Regeln ab, weil es dasselbe Skript ist.

### Billig — kleine, klar benennbare Bedingung, noch nicht gebaut (A)

**2. Datumsangaben ISO 8601 — A.**
Bedingung: eine `.md`-Datei (oder Fließtext-Feld) enthält ein Datum im Muster
`\b\d{4}-\d{2}-\d{2}\b`, dem NICHT unmittelbar `T\d{2}:\d{2}` folgt, außerhalb
von Codeblöcken/Dateinamen-Kontext. Ort: `PostToolUse`-Hook auf `Edit|Write`
für `*.md`, oder ein eigenständiger Test, der geänderte `.md`-Dateien gegen
das Muster prüft. Kein Sprachmodell nötig, reiner Regex.

**3. Caveman mode: always on — A** (Korrektur zum Vorlauf, siehe oben).
Bedingung: der `SubagentStart`- bzw. Sitzungsbeginn-Kontext enthält KEINEN
Caveman-Modus-Marker. Ort: exakt das Muster, das `ponytail` schon fährt (ein
`SubagentStart`-Hook-Eintrag, der einen Kontext-Block injiziert) — ließe sich
im selben Verzeichnis (`~/.claude/plugins/marketplaces/`) oder direkt als
`~/.claude/settings.json`-Hook nachbauen. Die Prüfung „wurde die Fähigkeit
aufgerufen" ist eine Ja/Nein-Bedingung, kein Urteil über den Text selbst.

**6. Aufträge an Agenten sind Schnappschüsse (Punkt 1: keine Zeilennummern als Adresse) — A.**
Bedingung: `tool_input.prompt` eines `Agent`/`Task`-Aufrufs enthält
`[Zz]eile\s+\d+` (oder `line\s+\d+`) OHNE ein vorangehendes Wort aus
`{etwa, ca\.?, ungefähr, rund}` im selben Satz. Ort: derselbe
`PreToolUse`-Matcher `Agent|Task`, an dem `hub/scripts/agent_model_guard.py`
und `hub/scripts/agent_reuse_guard_hook.py` bereits hängen — ein dritter
Eintrag am selben Punkt.

**18. „Es funktioniert" braucht Beleg (rot vor grün) — A.**
Bedingung: die eigene letzte Antwort enthält ein Erfolgs-Wort
(`funktioniert|behoben|jetzt klappt`) UND im selben Turn/derselben Sitzung
wurde keine Testdatei (`tests/*.py`) angelegt oder geändert (prüfbar über
`git diff --name-only` seit Sitzungsbeginn). Ort: `Stop`-Hook, baugleich zu
`haken/existenzpruefung.py` — dieselbe Technik (Verneinungs-/hier
Erfolgs-Muster in der letzten Antwort suchen), nur ein anderes Wortmuster
und eine zusätzliche Dateidiff-Prüfung.

**1. ALLES IST BETA / keine echten Daten — A, mit Einschränkung.**
Der Teilaspekt „keine Rückfrage der Art ‚sind das wirklich Echtdaten'" ist
mechanisierbar: Bedingung = eigene Antwort enthält ein Rückfrage-Muster wie
`(wirklich|sicher).{0,20}(echte?|produktiv).{0,10}daten` vor einer
Lösch-/Migrations-Aktion. Ort: `Stop`-Hook, dieselbe Technik wie oben. Der
zweite Teilaspekt — „Bestand ist NIE ein Argument, weder dafür noch
dagegen" — bleibt eine Bewertung, WARUM eine Entscheidung getroffen wurde,
nicht WAS geschrieben steht; das ist der D-Anteil dieser Regel (siehe unten,
nicht separat gezählt, weil die Regel als Ganzes hier unter A geführt wird,
mit dieser Einschränkung wörtlich benannt statt verschwiegen).

### Mittel — Bedingung klar, Bau aufwendiger oder mit Fehlalarmrisiko (A)

**7. Wie ein Agentenauftrag geschrieben wird — A (nur Strukturprüfung).**
Bedingung: `tool_input.prompt` eines `Agent`/`Task`-Aufrufs enthält NICHT
alle vier Schlüsselwörter `Fakten`, `Grenzen`, `Abnahme`, `Einsatz` als
Abschnittsüberschrift. Mechanisierbar, gleicher Hook-Ort wie Regel 6/19. Der
zweite Teil der Regel — „keine eigene Hypothese im Auftrag" — ist NICHT
mechanisierbar, weil er eine inhaltliche Bewertung verlangt (steht dort eine
Vermutung des Auftraggebers oder eine neutrale Messanweisung?); dieser
Teilaspekt bliebe D. Die Struktur-Prüfung allein ist aber schon ein
brauchbarer, unbeurteilter Fund.

**19. Plan vor Umsetzung — A.**
Bedingung: ein `Agent`/`Task`-Aufruf ODER eine Folge von `Edit`/`Write`
innerhalb einer Sitzung berührt mehr als eine Datei, UND kein
`docs/PLAN_*.md` wurde in derselben Sitzung neu angelegt oder geändert. Ort:
`PreToolUse`-Hook auf `Agent|Task` (Erweiterung von
`hub/scripts/agent_model_guard.py`), plus Zählung der bereits editierten
Dateien in der Sitzung. Bereits in Probe B von `runs/regelgriff_2026-08-12.json`
demonstriert, dass genau diese Bedingung heute NICHT geprüft wird (beide
existierenden Hooks am selben Matcher gaben exit 0, keine Warnung).

**15. Committen ohne Aufforderung — A (nur Sammelcommit-Heuristik, nicht der Kern).**
Bedingung: am `Stop`-Hook sind mehr als N (z. B. 3) Top-Level-Verzeichnisse
gleichzeitig unbereinigt geändert, ohne dass in der Sitzung ein Commit
stattfand. Das ist eine grobe, aber mechanisierbare Annäherung an das
explizit genannte Antipattern „Sammelcommit über Hunderte Dateien". Der
eigentliche Kern der Regel — „nach JEDEM abgeschlossenen Arbeitsschritt" —
verlangt eine Einschätzung, wann ein Schritt abgeschlossen ist; das bleibt
Urteil (D). `hub/scripts/commit_guard_hook.py` deckt heute nur die
Index-Kollision bei mehreren aktiven Agenten ab (bestätigt: Funktionen
`_blank_git_add`, `_blank_git_commit`, `_active_agents` — nichts davon prüft
Commit-Häufigkeit oder Themenmischung).

**14. Walkthrough-Doktrin — A (nur die drei statischen Prüfpunkte 1–3).**
Bedingung: eine geänderte `.py`/`.dart`-Datei im Kernpfad enthält
`datetime.now()`/`Date.now()`/`time.time()` NICHT als Parameter-Default,
sondern direkt im Funktionskörper; oder einen direkten HTTP-/IMAP-/DB-Aufruf
ohne erkennbare Interface-Schicht. Statische Grep-Prüfung, ähnlich
`hub/scripts/monolith_guard.py` (das bereits Zeilenzahl statisch prüft).
Punkte 4–7 der Doktrin (ehrliche Statusfelder, sprechende Fehler, keine
Außenwirkung im Testmodus, Debug-Control-API) verlangen jeweils eine
Bewertung des SEMANTISCHEN Verhaltens, nicht nur der Textform — die bleiben D.

**17. Zwei Ausgangszustände (frisch/gewachsen) — A, mit Aufwand.**
Bedingung: ein Commit ändert `schema.sql` oder eine Datei unter
`migrationen/`, UND `tests/` enthält für diesen Commit keinen Testfall, der
sowohl eine frisch angelegte als auch eine migrierte/bestehende DB als
Fixture verwendet (grep auf charakteristische Fixture-Namen wie
`frisch`/`leer` versus `migriert`/`bestand`). Mechanisierbar, aber
bezogen auf Namenskonventionen der Testdateien — brüchiger als die anderen
A-Fälle, weil er von Namensdisziplin abhängt statt von einem festen
Sprachmuster. Deshalb „mittel", nicht „billig".

**11. Testumgebung: handeln bis „es wird ernst" (die vier Ausnahmen) — A, mit Fehlalarmrisiko.**
Bedingung: ein Tool-Aufruf trifft eine der vier benannten Kategorien (Passwort-
/Zugangsdaten-Eingabe in ein Formularfeld, Nachricht an einen Menschen via
Messaging-/Mail-Tool, `git push` auf einen geschützten Branch, eine
Zahlungs-/Transfer-API) OHNE dass im Transcript zuvor eine explizite
Zustimmung des Betreibers zu GENAU dieser Aktion steht. Mechanisierbar über
eine Tool-Namens-/Muster-Liste am `PreToolUse`-Hook — analog zu
`hub/scripts/push_guard.py` (existiert bereits für den Haupt-Branch-Fall,
siehe unten) und `commit_guard_hook.py`. Als „mittel/teuer" statt „billig"
eingestuft, weil die Tool-Taxonomie (was zählt als „Nachricht an einen
Dritten") gepflegt werden muss und bei unvollständiger Liste falsch-negativ
wird — und eine unvollständige, aber lärmende Version schnell ignoriert wird
(vgl. Einsatz-Begründung des Auftrags: zwei Werkzeuge mit 73 % und 54 %
Fehlalarm).

**Nachrichtlich, kein eigener der 19 Abschnitte, aber Beleg für dieselbe
Fehlerklasse wie Regel 15/11:** `hub/scripts/push_guard.py` ist als
`git pre-push`-Hook geschrieben (nicht als Claude-Code-Hook) und prüft u. a.
Push auf `main`. Er ist in `brainlehr` NICHT installiert — geprüft:
`ls /Volumes/daten/Begod2026/brainlehr/.git/hooks/pre-push` → „No such file
or directory". Ein fertiger Mechanismus, der lokal nie an der Stelle hängt,
an der `git` ihn automatisch aufriefe. Kategorie B, wäre aber kein eigener
Abschnitt der 19 — nur als Beleg für die Kategorie „vorhanden, nicht
verdrahtet" mitgeführt.

### Nicht mechanisierbar (D)

**8. Abwesenheitsmodus ist die Voreinstellung — D.**
Die Regel verlangt, dass Agentenmeldungen „Arbeit auslösen, keine Ausgabe" —
das ist eine Bewertung des INHALTS jeder Chat-Nachricht (ist sie eine direkte
Antwort auf eine Frage, oder unaufgeforderte Prosa?), keine Textform lässt
sich dafür fest verdrahten, ohne jede Antwort auf eine echte Frage
fälschlich zu blockieren. Anders als bei Caveman (Regel 3) gibt es hier
keinen einzelnen Aufruf-Zeitpunkt, den man prüfen könnte — der Modus äußert
sich über die gesamte Sitzung verteilt in jeder einzelnen Antwort.

**12. Kurze Zustimmung ist eine Entscheidung — D.**
Ob eine vorangegangene Frage eines der vier Kriterien erfüllt (unumkehrbar,
hebt eine Regel auf, gilt über die Sitzung hinaus, Geld) ist eine inhaltliche
Einordnung der Frage, keine Textform. Der zweite Teil — wurde die Zustimmung
danach festgehalten — wäre zwar mechanisierbar (Prüfung auf einen
`knowledge_add`-Aufruf im selben Zeitfenster), aber ohne die Vorprüfung
„gehört diese Frage zu den vier Kriterien" bleibt jede Automatik entweder
bei jeder kurzen Zustimmung feuern (hoher Fehlalarm) oder gar nicht.

**13. Zweimal ist die Grenze, nicht dreimal — D.**
Erkennen, dass eine spätere Anfrage „dieselbe Sache zum zweiten Mal"
verlangt, verlangt einen semantischen Abgleich zweier möglicherweise anders
formulierter Anfragen über den Sitzungsverlauf hinweg — kein Textmuster
deckt Umformulierung ab, das ist genau die Aufgabe, für die man ein
Sprachmodell bräuchte, also per Definition der Trennlinie ausgeschlossen.

## Zusammenfassung, Nenner

19 von 19 Regeln eingeordnet.

| Kategorie | Anzahl | Regeln (Nummer laut Reihenfolge in CLAUDE.md) |
|---|---|---|
| A — mechanisierbar, unverdrahtet | 11 | 1, 2, 3, 6, 7, 11, 14, 15, 17, 18, 19 |
| B — mechanisierbar, vorhanden, nicht angehängt | 2 | 5, 9 |
| C — verdrahtet, mit Beleg | 3 | 4, 10, 16 |
| D — nicht mechanisierbar, Urteil nötig | 3 | 8, 12, 13 |
| **Summe** | **19** | 11 + 2 + 3 + 3 = 19 |

## Was NICHT eingeordnet werden konnte

Keine der 19 Regeln blieb unbewertet. Bei drei A-Regeln (1, 7, 14) deckt die
mechanisierbare Bedingung nur einen TEIL der Regel ab — der Rest ist
wörtlich als eigener D-Anteil benannt, statt ihn stillschweigend unter „A"
mitzuzählen. Das ist eine bewusste Vereinfachung der Zuordnungstabelle (eine
Zeile pro Regel, wie im Auftrag verlangt), keine verschwiegene Lücke — die
Einschränkung steht jeweils im Fließtext der Begründung.

Nicht Teil dieses Auftrags (aus dem Vorlauf `regelgriff_2026-08-12.json`
übernommen, hier nicht neu geprüft): die Einzelzuordnung der 83
`knowledge_nodes` mit gesetztem `norm_rang` und der 17 Abschnitte aus
`hub/CLAUDE.md` — beide waren im ursprünglichen Auftrag bereits explizit als
„nicht vertieft" ausgewiesen und lagen außerhalb des heutigen Auftrags
(„nur die 19 Abschnitte aus ~/.claude/CLAUDE.md").

## Kontrollen zu diesem Auftrag selbst

- `git status --short` vor und nach der Messung: identisch (siehe
  `runs/regelmechanik_2026-08-13.json`, Feld `arbeitsbaum_unveraendert`).
  Die 11 Zeilen stammen von fremdem WIP (`app/`, `NODE_INDEX.md`,
  `messungen/messlauf_abrufguete_v2.py` u. a.) — Tabu-Dateien dieses
  Auftrags, unangetastet.
- Volle Suite: `1080 passed, 2 skipped, 11 xfailed, 0 failed` in 197.58 s.
  Die im Auftrag genannte Ausgangslage („1035 passed, 2 skipped, 10 xfailed")
  bezog sich auf Commit ffc52b7 (2026-08-12); der aktuelle Stand 28b5c05 hat
  seither weitere Tests bekommen (u. a. `test_existenzpruefung_verdrahtung.py`)
  — die Differenz ist Zuwachs, keine Abweichung: 0 failed in beiden Fällen,
  keine Regression.
- Kein Produktivcode geändert — nur `docs/REGELMECHANIK_2026-08-13.md` und
  `runs/regelmechanik_2026-08-13.json` neu angelegt.
