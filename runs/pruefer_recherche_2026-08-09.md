# Recherche: Wo blieb der Skeptiker? (2026-08-09T08:14:36+0200)

Anlass (Betreiber): "begod entstand zuerst in einer VS-Code-Umgebung, damals hat sich
z.B. autonom der Skeptiker-Agent gemeldet und auf Dogmen hingewiesen. Sowas passiert
nun gar nicht mehr, obwohl wir viel mehr Datenpunkte haben."

Nur gelesen. Nichts geaendert, nichts angelegt, nichts committet ausser dieser Datei.

---

## Raster: wo gesucht, was ausgelassen

Durchsucht:
- `/Volumes/daten/Begod2026/stiftshuette/begod/agents/` (Top-Level, 62 Dateien) und die
  Unterordner `afrika/ amerika/ antarktis/ europa/ openhood/ ozeanien/` (22 weitere)
- `/Volumes/daten/Begod2026/stiftshuette/begod/AGENTS.md`
- `/Volumes/daten/Begod2026/stiftshuette/begod/knowledge/agents/agent-index.json` (75 registrierte Agenten)
- `/Volumes/daten/Begod2026/stiftshuette/.vscode/` (nur `mcp.json`, kein `settings.json`,
  keine Tasks/Automations)
- `grep -ril skeptiker` ueber ganz `/Volumes/daten/Begod2026/` (alle Baeume, nicht nur stiftshuette)
- `/Volumes/daten/Begod2026/stiftshuette/begod/knowledge/apps/ideenfinder/` (Case-Kontext,
  Prompt-Datei, Konsil-Workflow-Skill)
- `git log --follow` auf die zwei ideenfinder-Dateien, in denen "Skeptiker" vorkommt
- `/Volumes/daten/Begod2026/brainlehr/knowledge.db` (nur lesend, sqlite3) — Spalten
  `norm_entschieden_von`, `norm_art`, vollstaendiges Schema von `knowledge_nodes`
  inkl. aller Trigger
- `/Volumes/daten/Begod2026/brainlehr/normachsen.py` und `gegenprobe.py` (Volltext)

Bewusst ausgelassen:
- Die Agenten der Kontinent-Unterordner (afrika/amerika/antarktis/europa/ozeanien) wurden
  nur als Dateiliste erfasst, nicht einzeln gelesen — keiner davon heisst oder rollt wie
  ein Skeptiker (Namen: parity-guard, benchmark-richter, dsp-ingenieur, latenz-waechter,
  mir-wissenschaftler, ble-kommunikations-ingenieur, diagnose-richter,
  fahrzeug-sicherheitswaechter, fuzzing-architekt, hardware-limit-waechter,
  lade-analytiker, obd2-experte, usb-protokoll-experte, plugin-richter,
  theme-architekt, wp-security-experte, evaluations-waechter,
  fortbildungs-experte, obd2-expert, carving-ingenieur, forensik-experte,
  integritaets-waechter, nas-gateway-ingenieur).
- Kein Blick in `/Volumes/daten/Begod2026/afrika/` oder `/Volumes/daten/Begod2026/archive/`
  (Treffer beim grep, aber andere Baeume/Snapshots — ausserhalb des Auftrags "stiftshuette").
- Keine Volllektuere von `hub/shared-knowledge/` — nicht Teil des Auftrags (der zeigt auf
  brainlehr/knowledge.db).
- Die vier Beispielzahlen aus Frage 3 (n=2-Kennzahl, Plan mit acht Abschnitten) wurden
  NICHT neu erhoben, wie im Auftrag vorausgesetzt — nur die beiden anderen (62/72,
  72/72 ohne Art) wurden gegen die DB nachgerechnet, weil sie sich in einem Statement
  pruefen liessen, das ohnehin gestellt werden musste.

---

## Frage 1 — Bestandsaufnahme

`begod/agents/` (Top-Level) enthaelt 62 `.agent.md`-Dateien, dazu 22 in den
Kontinent-/Domain-Unterordnern — macht die vom `agent-index.json` gezaehlten
75 registrierten Agenten (plus ein paar undokumentierte). Nicht alle einzeln
durchgegangen; als Zahl: rund 70 Rollen, ganz ueberwiegend BAUEND (Dev, Store,
Global-Querschnitt, Domain-Spezialisten wie DSP/OBD2/BLE).

PRUEFENDE Rollen (widersprechen, hinterfragen, Dogmen benennen — nicht nur
pruefen ob etwas FUNKTIONIERT, sondern ob es RICHTIG oder NOETIG ist):

- **spaghetti-monster** (`begod/agents/spaghetti-monster.agent.md`) — Red Team /
  Devils Advocate, Anti-Dogma, Buerokratie-Scan gegen das eigene Agentensystem.
  Der naechste Verwandte zum erinnerten "Skeptiker".
- **sokrates-review** (`begod/agents/sokrates-review.agent.md`) — stellt nur
  Fragen, gibt nie Antworten, bei Code-Reviews.
- **pivot-richter** (`begod/agents/pivot-richter.agent.md`, Jeftah) — erkennt
  Sackgassen/Diminishing Returns, empfiehlt Methodenwechsel statt Weitermachen.
- **verfassungsgericht** (`begod/agents/verfassungsgericht.agent.md`) —
  Judikative, Veto-Recht, prueft gegen die eigene Verfassung.
- **hippokrates-safety** (`begod/agents/hippokrates-safety.agent.md`) — Veto bei
  Schaden, unabhaengig vom fachlichen Gate.
- **evangelist** (`begod/agents/evangelist.agent.md`, Markus) — externer
  Code-Reviewer, schreibt explizit "das Gute UND das Schlechte, ohne Schnoerkel".
- **blauhelme** (`begod/agents/blauhelme.agent.md`, Simeon) — Krisen-Intervention,
  stoppt Weiterbau bis Stabilisierung.
- **archaeologe** (`begod/agents/archaeologe.agent.md`, Kaleb) — graebt externes
  Wissen aus (Urteile, Studien, Prior Art) statt intern zu behaupten.
- **benchmark-richter-global** (`begod/agents/benchmark-richter-global.agent.md`)
  — Regressions-Waechter gegen Baselines/Schwellwerte.
- **heiliger-geist** (`begod/agents/heiliger-geist.agent.md`) — Prozessreibung,
  veraltete Templates, Inkonsistenzen aufdecken.
- **prophet** (`begod/agents/prophet.agent.md`, Amos) — meldet wenn Meta-Arbeit
  die eigentliche Produktarbeit ueberwiegt.

Kein Treffer fuer einen Agenten namens "skeptiker" — weder als Datei noch als
Eintrag im `agent-index.json` (75 Eintraege durchsucht, keiner heisst so).

---

## Frage 2 — Der Mechanismus (belegt)

**Ergebnis: kein "Skeptiker"-Agent existiert je als eigenstaendige, registrierte
Rolle. "Skeptiker-Duo" ist ein FESTER SCHRITT in einer einzigen, von Hand
gestarteten Pipeline — kein autonomer Ausloeser.**

Beleg — Fundstelle:
- `begod/knowledge/apps/ideenfinder/prompts/start-case-ideen.prompt.md` Zeile 9:
  "Pipeline: problem-scout (...) -> ideen-bewerter (...) -> Konsil (6 Experten
  parallel) -> **Skeptiker-Duo** -> ideen-bewerter (Top 3) -> ...". Frontmatter
  der Datei: `agent: "jesus-guide"` — eine VS-Code-Copilot-Chat-**Prompt-Datei**,
  die der Nutzer explizit aufruft (Slash-Prompt), nicht etwas, das von selbst
  feuert.
- `begod/knowledge/apps/ideenfinder/skills/konsil-workflow.md` Zeile 39-41:
  "3. Skeptiker-Duo prueft die Konsil-Ergebnisse -> Negativer Skeptiker:
  Kill-Kriterien ... -> Positiver Skeptiker: Gegen-Check". Auch das ist Schritt 3
  einer sechsstufigen Pipeline, die per Definition erst nach Schritt 1+2 laeuft.
- Weder unter `begod/agents/` noch in `agent-index.json` (75 Eintraege) gibt es
  eine Datei/einen Eintrag "skeptiker" — der Skeptiker ist NIE als
  eigenstaendiger, wiederverwendbarer Agent gebaut worden, sondern nur als
  Rollenbezeichnung innerhalb dieser einen Case-Pipeline.
- `git log --follow` auf beide Dateien zeigt genau einen Commit:
  `f96ada4ed 2026-02-23 "feat(ideenfinder): Case/Skills/Prompt aus Datenplatte
  isoliert importiert"` — der Skeptiker-Schritt kam fertig aus einem Import,
  keine Historie eines Hooks, der ihn spaeter automatisiert haette.
- `.vscode/` im stiftshuette-Baum enthaelt nur `mcp.json` (MCP-Server-Verdrahtung
  fuer begod-mcp/xcode-mcp/android-mcp) — kein `settings.json`, keine Tasks, kein
  Scheduler, nichts, das eine Chat-Rolle automatisch anstoesst.

Zusaetzlicher, wichtiger Fund (nicht verwechseln mit dem echten Mechanismus):
Mehrere der "pruefenden" Agenten (spaghetti-monster, luther-refactoring,
heiliger-geist, hippokrates-safety, polizei, tool-agent) tragen im eigenen
Frontmatter/Kopf eine Zeile wie:

```
ACTIVATION: Proaktiv bei Gruppen-Denken, unbewiesenen Annahmen,
"das ist offensichtlich"-Momenten.          (spaghetti-monster.agent.md, Zeile 9)
ACTIVATION: Automatisch bei Pflege-relevanten Features ...
                                             (hippokrates-safety.agent.md, Zeile 9)
```

Das ist KEIN Hook, kein Cron, keine Codezeile mit Bedingung — es ist ein
FLIESSTEXT-Hinweis in der Rollendefinition, den (in der VS-Code-Umgebung) das
jeweils orchestrierende Modell beim Lesen der Agentendatei selbst auslegen und
befolgen musste ("Proaktiv" = das Modell entscheidet aus eigenem Ermessen,
diesen Agenten jetzt zu rufen, ueber das VS-Code-Copilot-Tool `agent`). Es gibt
keine Infrastruktur (kein SessionStart/PostToolUse-Aequivalent), die das
erzwingt. Diese Prosa-Konvention erklaert vermutlich das allgemeine Gefuehl
"da hat sich mal was von selbst gemeldet" — aber sie ist NICHT der Mechanismus
hinter dem konkret erinnerten Skeptiker-Fall, denn fuer "Skeptiker" gibt es gar
keine solche Datei mit ACTIVATION-Zeile. Der Skeptiker-Fall selbst lief ueber
den von Hand gestarteten Case-Workflow.

**Kurzfassung: Kein automatischer Ausloeser gefunden. Der Skeptiker wurde
gerufen — als Pflichtschritt einer von Hand gestarteten Pipeline (VS-Code-Prompt-
Datei), nicht durch einen Hook oder eine Regel, die unabhaengig vom Nutzer
gefeuert haette.**

---

## Frage 3 — Uebertragung: messbare Ausloesebedingungen

Bauform uebernommen von `normachsen.py`/`gegenprobe.py`: reine SQL-/Text-Zaehlung,
STILL bis eine Schwelle ueberschritten ist, kein Urteil ueber die Guete der
Messung selbst, Negativfall im Selftest mitgefuehrt.

Gegengeprueft an der DB (nur die zwei Zahlen, die sich in einem Statement
pruefen liessen):

```sql
SELECT norm_entschieden_von, COUNT(*) FROM knowledge_nodes
WHERE norm_rang IS NOT NULL AND zurueckgezogen=0 GROUP BY norm_entschieden_von;
--  (leer)                 5
--  claude-code/opus-5    62
--  unbekannt              5
SELECT norm_art, COUNT(*) FROM knowledge_nodes
WHERE norm_rang IS NOT NULL AND zurueckgezogen=0 GROUP BY norm_art;
--  NULL                  72
```

Bestaetigt: 62 von 72 Normen der Maschine zugeschrieben, 72 von 72 ohne Art.
Die zweite Zahl (Art) wird bereits von `normachsen.py::stumme_achse` gemeldet —
dafuer braucht es keinen neuen Melder, der existiert. Fuer die erste Zahl
(Selbstzuschreibung) gibt es noch keinen.

### Vorschlag A — Selbstzuschreibungs-Quote bei Normentscheidungen

Messung (reines SQL, kein Text-Raten):
```sql
SELECT norm_entschieden_von, COUNT(*) c
FROM knowledge_nodes
WHERE norm_entscheidung IN ('norm_befristet','norm_unbefristet')
GROUP BY norm_entschieden_von;
```
Ausloeser: ein einzelner Akteur haelt >= 80% aller Entscheidungen UND dessen
Name matcht das KI-Muster (`%claude%|%gpt%|%opus%|%sonnet%|...`, dasselbe
Muster wie im bestehenden DB-Trigger `knowledge_nodes_normrang_herkunft_bi`,
nur dort nur fuer Rang 1/2 und nur beim Schreiben gepflegt) UND n >= 20
(Mindestbestand, sonst kippt das Verhaeltnis durch einen einzigen Nachtrag).

Fehlklasse, der das nachgeht: eine Norm wird faktisch nie von einem Menschen
entschieden, obwohl die DB-Trigger das nur fuer Rang 1/2 erzwingen — bei allen
anderen Raengen kann die Maschine unwidersprochen durchentscheiden (genau der
62-von-72-Fall).
Kosten eines Fehlalarms: gering. Reine Zaehlung, keine Interpretation von
Text. Einziges Risiko: am Projektanfang, wenn ein Mensch noch keine Zeit hatte
nachzuziehen — deshalb die n>=20-Schwelle, keine Bewertung vor ausreichendem
Bestand.

### Vorschlag B — generischer "stumme Spalte"-Melder (verallgemeinert MELDER 1 aus normachsen.py)

`normachsen.py` musste von Hand gebaut werden, NACHDEM ein Mensch bemerkt hatte,
dass `norm_art` zu 100% NULL ist. Das ist selbst ein Fall von "der Skeptiker hat
es nicht gefunden, der Betreiber schon". Ein generischer Melder braucht dafuer
keine Handarbeit pro Spalte:

```sql
SELECT 'norm_art' AS spalte, COUNT(*) n, SUM(norm_art IS NULL) leer FROM knowledge_nodes WHERE norm_rang IS NOT NULL
UNION ALL
SELECT 'norm_entschieden_grund', COUNT(*), SUM(norm_entschieden_grund IS NULL OR TRIM(norm_entschieden_grund)='')
FROM knowledge_nodes WHERE norm_entscheidung != 'offen'
-- usw. fuer jede Spalte, die als "wirkt aber leer" bekannt ist oder neu dazukommt
```
Ausloeser: jede Spalte mit definiertem Zweck (Kommentar im Schema oder in einer
Regel referenziert, z.B. `_is_spannung` liest `norm_art`), deren Fuellgrad bei
> N Datensaetzen bei 0% liegt.

Fehlklasse: eine gebaute Regel, die im Quelltext wie ein Schutz aussieht, aber
nichts unterscheidet, weil ihre Datengrundlage nie gefuellt wurde — exakt das,
was `norm_art` war, bevor es jemand bemerkte. Ein genereller Melder faengt das
naechste Mal auch Spalten, die niemand einzeln beobachtet.
Kosten eines Fehlalarms: gering bis mittel. Manche Spalten sind gewollt selten
gefuellt (z.B. `zurueckgezogen_grund` bei wenigen Ruecknahmen) — der Melder
braucht eine Ausschlussliste fuer Spalten, deren Leere selbst der Normalfall
ist, sonst meldet er staendig Rauschen und wird ueberlesen (dasselbe Argument,
das `normachsen.py --melder` fuer sich selbst schon macht: "ein Melder, der bei
jedem Start dasselbe sagt, faellt nach drei Tagen aus").

### Vorschlag C — Kennzahl auf kleiner Basis, als Aussage behandelt

Messung (Text-Heuristik in der Art von `_paare()` aus `gegenprobe.py`, aber
angewandt auf `knowledge_nodes.summary`/`content` und `lessons_learned`):
Regex auf Muster wie `(\d+)\s*(von|/|aus)\s*(\d+)` bzw. Prozentzahlen im Text,
verglichen mit dem erkannten Nenner. Ausloeser: Nenner < 10 UND der Satz
enthaelt ein verallgemeinerndes Wort ("zeigt", "belegt", "beweist", "immer",
"nie", "in der Regel") in derselben Zeile.

Fehlklasse: ein Befund aus n=2 wird sprachlich wie ein belastbares Ergebnis
behandelt (der genannte n=2-Fall).
Kosten eines Fehlalarms: am hoechsten von den dreien — echte, vollstaendige
Kleinst-Grundgesamtheiten ("2 von 2 Ozeanien-Domain-Agenten haben Vetorecht")
sind kein Fehler, nur weil der Nenner klein ist. Ohne das Verallgemeinerungswort
in der Bedingung waere die Falsch-Positiv-Quote untragbar; selbst damit bleibt
es eine Heuristik, keine Messung wie A oder B — genau die Grenze, die
`gegenprobe.py` selbst zieht: es kann pruefen, ob die Datei sich selbst
widerspricht, nicht ob die Messung klug war.

**Nicht vorgeschlagen (zu unsicher fuer einen Melder):** die vierte
Beispiel-Fehlklasse aus dem Auftrag — eine Nummerierung von Planabschnitten,
die eine Abhaengigkeit suggeriert — laesst sich nur ueber Fliesstext-Heuristik
pruefen (numerierte Ueberschriften ohne Abhaengigkeits-Vokabular in der Naehe).
Das waere reine Textform-Erkennung ohne Bezug zum tatsaechlichen Inhalt und
haette absehbar eine sehr hohe Fehlalarmquote — genau die Sorte Pruefung, die
laut `gegenprobe.py`s eigenem Vorbehalt ("NICHT geprueft: ob die Messung die
richtige Frage stellte") kein Skript leisten sollte, ohne mit einem Menschen
gegenzupruefen.

---

## Melde-Zusammenfassung

Dateiname: `runs/pruefer_recherche_2026-08-09.md`

Pruefende Rollen mit Datei (Kernliste): spaghetti-monster
(`begod/agents/spaghetti-monster.agent.md`), sokrates-review
(`begod/agents/sokrates-review.agent.md`), pivot-richter
(`begod/agents/pivot-richter.agent.md`), verfassungsgericht
(`begod/agents/verfassungsgericht.agent.md`), hippokrates-safety
(`begod/agents/hippokrates-safety.agent.md`), evangelist
(`begod/agents/evangelist.agent.md`), blauhelme
(`begod/agents/blauhelme.agent.md`), archaeologe
(`begod/agents/archaeologe.agent.md`), benchmark-richter-global
(`begod/agents/benchmark-richter-global.agent.md`), heiliger-geist
(`begod/agents/heiliger-geist.agent.md`), prophet
(`begod/agents/prophet.agent.md`).

Frage 2: Kein automatischer Ausloeser gefunden. "Skeptiker-Duo" existiert nur
als Pflichtschritt 3 einer sechsstufigen, von Hand per VS-Code-Prompt-Datei
gestarteten ideenfinder-Pipeline (`start-case-ideen.prompt.md` +
`konsil-workflow.md`) — kein eigener Agent, kein Hook, kein Cron. Die
"ACTIVATION: Proaktiv"-Zeilen anderer pruefender Agenten sind Fliesstext fuer
das orchestrierende Modell, keine erzwungene Automatik, und betreffen den
Skeptiker-Fall nicht direkt.

Drei tragfaehigste Ausloesebedingungen: (A) Selbstzuschreibungs-Quote bei
Normentscheidungen (reines SQL, n-Schwelle haelt Rauschen klein), (B)
generischer Melder fuer Spalten mit 0%-Fuellgrad trotz definiertem Zweck
(verallgemeinert den bereits gebauten Art-Melder), (C) Kennzahl-auf-kleiner-
Basis per Regex mit Verallgemeinerungswort-Bedingung (schwaecher, aber noch
vertretbar). Die vierte Beispiel-Fehlklasse (Nummerierung als Abhaengigkeit)
wurde bewusst NICHT als Melder vorgeschlagen — zu hohe Fehlalarmquote fuer
eine reine Textform-Heuristik.
