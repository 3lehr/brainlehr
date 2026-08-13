# Plan: Grundarchitektur — was entschieden ist und was daraus folgt

**Stand** 2026-08-13T23:06:29+0200
**Anlass** `docs/STARTPROMPT_GRUNDARCHITEKTUR_2026-08-13.md`, Betreiberauftrag
*„so war das nicht gedacht, denk gross! mir geht es um die grundarchitektur"*
**Verhältnis zu `PLAN_GESAMT_2026-08-13.md`** Dieser Plan ersetzt nichts. Der Gesamtplan
regelt die **Reihenfolge der Arbeit** (Linien A–E); dieser hier regelt, **wofür** sie gut
ist, und trägt die Befunde des Abends. Wo beide sich berühren, gilt der Gesamtplan.

---

## 0. EILMELDUNG — 85,5 % des Wissensabrufs erreichen die Sitzung nicht

Gemessen 2026-08-13T23:05 an dieser Sitzung, Betreiberfrage *„warum kommen hier die
brainlehr meldungen nicht mehr an?"*

| | |
|---|---|
| Einspielungen des Abrufs | 11 |
| erzeugt | **155 749 Byte** |
| angekommen | **22 528 Byte** (2 KB Vorschau je Stück) |
| **verloren** | **133 221 Byte = 85,5 %** |
| Einträge sichtbar | **2 von 14** · **3 von 10** · **6 von 15** |

**Zwei getrennte Ursachen, beide belegt:**

1. **Stumme Kappung im Kanal.** Übersteigt der eingespielte Block eine Größe, wird er in
   eine Datei geschrieben und durch eine 2-KB-Vorschau ersetzt. Die Meldung lautet
   „Output too large" — sie sagt **nicht**, dass neun Treffer weggelassen wurden. Der
   Abruf selbst arbeitet, brainlehr liefert; der Weg dazwischen verliert.
2. **`MIN_HITS = 3` gattert auf der Anfrageseite.** Ein Prompt mit weniger als drei
   verschiedenen Stichwörtern löst **gar keinen** Abruf aus, unabhängig vom Bestand
   (`haken/knowledge_recall_hook.py`, dort selbst dokumentiert: **282 von 1923** echten
   Betreiber-Prompts, 14,7 %). Belegter Fall an diesem Abend: *„was ist punkt 1?"* —
   kein einziger Treffer.

**Warum das schwer wiegt:** Linie 0 des Gesamtplans („brainlehr sagt") wurde gebaut, damit
der Betreiber die Trefferquote **im Gespräch mitsieht**, ohne Messlauf. Sie hat den ganzen
Abend über einen Kanal gemessen, von dem ein Siebtel ankam. Jede Aussage über die Güte des
Abrufs aus dieser Sitzung steht auf 14,5 % der Belege.

**Was zu tun ist — nicht mehr Größe, sondern Ehrlichkeit über die Grenze:**
Der Hook kennt seine Trefferzahl. Er muss **innerhalb** der Grenze bleiben und das
Weglassen **benennen** („15 Treffer, 6 eingespielt, 9 weggelassen"), statt einen zu großen
Block abzuliefern, den ein anderer stumm kappt. Ein kurzer vollständiger Block schlägt
einen langen gekappten. Dieselbe Regel wie überall heute: **kein stiller Fehlschlag.**

Der zweite Punkt ist eine **Abwägung, keine Panne** — `MIN_HITS = 3` ist gemessen und liegt
auf der Pareto-Front (Recall@5 0,141 bei Fehlalarm 0,000; MIN_HITS=2: 0,369 bei 0,033).
Er wird hier nur benannt, damit „kein Treffer" nicht als „nichts gefunden" gelesen wird.

---

## 1. Was entschieden wurde

### ADR-006 — eine Quelle für die Form, Python als Grundsprache
Datenbankschema ist die Quelle für Felder, Typen und Bedingungen. Python ist die
Grundsprache. Andere Sprachen sind erlaubt — Swift für die Oberfläche, Rust wo nötig — mit
**einer Bedingung: sie lesen das Schema, sie behaupten es nie neu.**

### ADR-007 — zwei Schichten
**brainlehr** = was gilt und ob es belegt ist. **openlehr** = was ein Mensch in seiner Lage
damit tun kann. Definition des Betreibers, wörtlich: *„vorgefertigtes valides ki wissen +
werkzeug um das wissen einzusetzen. in welcher form auch immer das werkzeug dann ist"*.

**Schichtgrenze ist Autorität, nicht Abstraktion:** brainlehr kann nein sagen (Freigabe,
Norm, Trigger, Melder), openlehr nicht. Daraus fällt die gemeinsame Dokumentbasis nach
openlehr. **Widerlegbar:** Findet sich ein Fall, in dem sie etwas verweigern *muss*, ist
sie eine eigene Schicht.

### Namensraum — durch `openWEG` entschieden
Betreiber: buckeberg wird bei Veröffentlichung **openWEG**. Damit ist `open*` der
**Instanz**-Namensraum. Folge: Die Schicht kann weder `open` heißen (Präfix jeder Instanz,
zudem ein Python-Builtin und nicht greppbar) noch `openlehr` (sähe selbst aus wie eine
Instanz). **Die Schicht braucht einen Namen außerhalb des `open*`-Musters; openlehr bleibt
als Instanz unverändert.** Der Schichtname ist offen — `lehrdesk` ist im Verbund frei
(null Treffer), aber als Schichtname nicht geprüft.

Nebenertrag: **buckeberg ist der Fall, openWEG ist das Werkzeug.** Der Fall trägt Namen
Dritter und bleibt privat; das Werkzeug ist die Form ohne den Fall. Die Freigabe-Achse,
angewandt auf ganze Projekte.

### Neubau statt Reparatur — Betreiberdirektive
*„keine dogmen! was nicht klappt wird nicht repariert sondern weggeschmießen"*, und dazu
die Anwendung: die Steuerinstanz wird neu gebaut.

**Die eine Bedingung, und sie ist kein Dogma, sondern das, was Wegwerfen billig macht:**
Weggeworfen wird der **Code**, nicht die **Entscheidungen**. Unter `docs/openlehr/` liegen
262 Beschlussdokumente. Ein Neubau, der sie mitentsorgt, verhandelt jede davon erneut.
Genau das ist die heute beschlossene Architektur, auf sich selbst angewandt: **Schicht 1
überlebt den Neubau von Schicht 2.** Erste Aufgabe des Neubaus ist deshalb nicht Code,
sondern die Beschlüsse nach brainlehr zu holen — sonst widerlegt der Neubau die Architektur
bei ihrer ersten Anwendung.

---

## 2. Gemessener Ist-Stand

### Der „offene Nerv" war zur Hälfte keiner
Der Startprompt nennt zwei Stellen doppelter Fachlogik. Nachgemessen:

| Behauptet | Gemessen |
|---|---|
| Fundstellen-Modell doppelt | **Nein.** `Fundstelle.swift` (97 Z.) dekodiert `POST /api/fundstelle`; `kern/fundstelle.py` (512 Z.) rechnet. Dienstgrenze. |
| Lesbarkeit doppelt | **Ja, bewusst.** Beide lesen `lesbarkeit.json`; die Formel ist fünf Zeilen, die Zahlen stehen einmal. |
| — | `AusweisProtokoll.swift` nennt sich selbst „reine Brücke zu `pflege/ausweis_helfer.py`". |
| — | **Fehlalarm aus Namensgleichheit:** `Rangfolge.swift` (Quellenanzeige) ≠ `kern/rangfolge.py` (Recall-Rangsignale). |

**Übrig bleibt der unerzwungene Feldvertrag** — und er ist **heute schon gebrochen**:
Python liefert 13 Felder, das Swift-Struct kennt 12. `weitere` kommt in der App nie an,
ohne dass es jemandem aufgefallen wäre.

### begod: das Regelsystem existiert, brainlehr weiß nichts davon
`hub/begod/protocols_index.json`: **44 Protokolle**, Tier-0 immer (7) / Tier-1 nach
Kontext (29) / Tier-2 nach Auslöser (8), je mit `triggers`, `depends_on`, `token_cost` und
Vetostufe (ABSOLUT 8 · STARK 21 · PFLICHT 14 · EMPFOHLEN 1).

**Gelesen von** `hub/scripts/init_worktree.py` und `hub/scripts/validate_agent_system.py`.
**Nicht gemessen:** ob Agenten die Protokolle zur Laufzeit tatsächlich laden.

Im Speicher stehen dazu **drei Seed-Knoten vom 25.03.** (`/agents`, `/agents/governance`,
`/begod`), deren `content` die eigene Zusammenfassung umschreibt. Sie nennen „Protokolle
P1–P40", ohne eines zu beschreiben.

**Defekt, neu und klein:** **P1** trägt `tier: 0` bei `tier_label: "tier-1"`, **P30**
`tier: 2` bei `tier_label: "tier-1"`. Wer das Zahlenfeld liest, lädt P1 immer; wer die
Beschriftung liest, nicht. Dieselbe Klasse wie der Feldvertrag, in der Datei, die die
Regeln des Verbunds verteilt.

**Kein Import daraus.** `hub/docs/PLAN_STIFTSHUETTE_UEBERNAHME_2026-08-08.md` hat das
entschieden, mit Grund: *„Wer von hier Merkmale übernimmt statt Disziplinen, importiert
diese Krankheit mit"* — sieben von dreizehn Datendateien der Stiftshütte haben keinen
Schreiber. `PLAN_GESAMT` übernimmt daraus genau **zwei Bauformen**: Bindung einer Regel an
einen Schritt, und Trennung von Grenzwert-Setzen und Durchsetzen. Dabei bleibt es.

---

## 3. Was die Fremdrecherche beiträgt (2026, nicht zehn Jahre alt)

**Der Grundgedanke ist belegt, aber mit anderer Begründung als der Startprompt gibt.**
Nicht „sechs Werkzeuge an einem Tag" — die teilen keine Bauform (`L-aa889c`) —, sondern:
**97,1 %** untersuchter MCP-Werkzeugbeschreibungen tragen mindestens einen Mangel, 56 %
„Unclear Purpose"; eine der sechs benannten Mängelklassen heißt **„Unstated Limitations"**
und ist wörtlich der Quick-Look-Fall (arXiv 2602.14878). Bessere Beschreibungen brachten
dort aber nur **+5,85 Prozentpunkte** bei **+67,46 %** Ausführungsschritten — Text allein
ist kein Hebel.

**Neu bauen heilt es nicht von selbst.** Die Analyse von Claude Code (arXiv 2604.14228)
führt als offenes Problem: *stille Fehlschläge, wenn Berechtigungsprüfungen Werkzeugaufrufe
unterdrücken*. brainlehrs eigene `freigabe`-Achse ist strukturell derselbe Fall.

**Es gibt jetzt einen fremden Maßstab für Frage 3.** LongMemEval-V2 (arXiv 2605.12493)
misst fünf Gedächtnisfähigkeiten an echten Agenten-Verläufen; die Kategorie
**„Umgebungs-Fallstricke"** ist brainlehrs Kerngeschäft (423 Antipatterns). Weltstand:
**48,3 %** (bestes System gesamt 74,9 %; naives RAG 40,1 %). Eigene Vergleichszahl:
**0 von 13** in der Klasse `lese`.

**Schreiben ist billig geworden, Belegen nicht.** Microsoft, Anfang 2026, Zehntausende
Ingenieure, vier Monate: Adoptierende mergen **~24 %** mehr Pull Requests (arXiv 2607.01418).
METR musste sein Messverfahren einstellen — Entwickler weigern sich, ohne KI zu arbeiten,
auch für 50 $/h. **Die Selbsteinschätzung ist wertlos:** gemessen −19 %, geschätzt +20 %.

**Vektoren finden, Struktur entscheidet — in vier Wissenschaften dasselbe Muster.**
Biologie: Protein-Sprachmodell findet Kandidaten, Foldseek prüft die Struktur. Chemie:
gelernte Einbettungen schlagen klassische Fingerabdrücke bei **activity cliffs** nicht —
*representation collapse*, zwei fast gleich aussehende Dinge sind im Raum nicht trennbar.
Recht: „legal-rational similarity" weicht von semantischer Ähnlichkeit ab; die besten
Verfahren legen Ereignisketten und Rollen unter festem Schema darüber. Code-Klone:
Einbettungen insgesamt am besten, AST/Graph gewinnt bei Typ 3 und 4; hybrid schlägt beides.

**Folge für den Code-Vektorraum:** Er hilft **jetzt schon** — als Kandidatensucher, nicht
als Richter. Meine frühere Absage („warten auf `71` und `80`") war zu grob: Diese Sperren
gelten für den **Abruf**. Ein Raum, der ein Analysewerkzeug speist und nie in den Recall
geht, berührt sie nicht.

`Rangfolge.swift` gegen `kern/rangfolge.py` ist ein activity cliff. Ein Ähnlichkeitsraum
hätte beide Fehlalarme dieses Abends reproduziert — mit einer Zahl daneben, die sie nach
Messung aussehen lässt.

---

## 4. Reihenfolge

| # | Was | Warum hier |
|---|---|---|
| **1** | **Abruf-Kappung ehrlich machen** (Abschnitt 0) | Solange 85,5 % stumm verloren gehen, ist jede Aussage über die Abrufgüte — und jede Arbeit, die sich auf eingespieltes Wissen stützt — auf einem Siebtel der Belege gebaut. Vor allem anderen. |
| **2** | **Feldvertrag `Fundstelle`** | Klein, und die Klasse ist an diesem Abend **zweimal** belegt (`weitere`; P1/P30). Vorlage `app/Resources/fundstelle_vertrag.json`, je ein Test in Python und Swift. |
| **3** | **Code-Raum vorbereiten** | Drei Festlegungen und ein Schlüssel — **kein Schema**: getrennter Raum (nicht `typ`-Spalte, wegen der 9→0-Messung) · Modellname ist Vektoridentität (Sperre `80`) · Schlüssel = Datei + Symbol + Commit, alle drei werden heute schon erzeugt (`codekanten.py`, `symbolindex.py`, `codestand.py`). Ohne Vektor sofort nützlich. |
| **4** | **P1/P30 in `protocols_index.json`** | Einzeiler, fremdes Repo, unabhängig. |

**Beim Betreiber, nicht bei mir:** der Name der Schicht · das Ja zum Neubau der
Steuerinstanz · ob buckeberg jetzt schon openWEG heißen soll.

**Der Gesamtplan bleibt vorrangig.** Seine Sperren gelten unverändert: `80` vor `69`,
`78` vor `73`, `89` vor jeder weiteren Abrufmessung, keine Abrufzahl nach außen solange
`71` offen ist.

---

## 5. Was bewusst nicht getan wird, samt Preis

- **Kein Regelwerk aus den 44 begod-Protokollen importieren.** Preis: Eine gute Bauform
  bleibt ungenutzt liegen. Grund: „Merkmale statt Disziplinen" ist die dokumentierte
  Krankheit des Vorgängersystems, und der Gesamtplan hat die Frage bereits entschieden.
- **Keine dreizehnte leere Spalte** für den Code-Raum. Vorbereitung heißt Festlegung und
  Schlüssel, nicht Schema. Preis: keiner — wenn der Raum nie kommt, war nichts umsonst.
- **Kein Codegenerator** für die zwei Sprachfassungen (ADR-006). Preis: die
  Lesbarkeitsformel bleibt zweimal.
- **Kein Weiterbau an der Mac-App.** Unverändert aus dem Startprompt.
- **Kein Vektorurteil über Doppelung.** Nur Kandidaten. Preis: Doppelungssuche braucht
  zusätzlich ein strukturelles Verfahren.

---

## 6. Woran sich Erfolg misst

- **Abruf:** Ein eingespielter Block nennt seine Trefferzahl und was er weglässt. Ein Block
  wird nie mehr stumm gekappt — nachweisbar an einer Anfrage, die mehr Treffer erzeugt als
  hineinpassen.
- **Feldvertrag:** Ein Feld in `kern/fundstelle.py` umbenennen lässt die Swift-Prüfung
  fallen. Vor dieser Arbeit fiel nichts, und `weitere` war seit jeher unbemerkt.
- **Schichtung:** Für jede neue Idee lässt sich in einem Satz sagen, ob sie brainlehr oder
  openlehr ist — über die Frage, ob sie etwas verweigern können muss.
- **Regelwerk:** Es entsteht aus den **zwei vorhandenen** Instanzen (openlehr/Steuer,
  buckeberg/WEG) und wird an einer dritten geprüft, nicht an ihnen erfunden.
- **Abrufgüte gegen fremden Maßstab:** die Kategorie „Umgebungs-Fallstricke" aus
  LongMemEval-V2, Weltstand 48,3 %. Erst nach `71` und `89`, und nicht nach außen davor.

---

## 7. Offene Fragen des Startprompts — Stand nach diesem Abend

| | Frage | Stand |
|---|---|---|
| 1 | Was ist brainlehr im Kern? | **Beantwortet** (ADR-007): die Schicht, die nein sagen kann — und die den Neubau der oberen überlebt. |
| 2 | Wo lebt die Fachlogik? | **Beantwortet** (ADR-006). Rest: der Feldvertrag. |
| 3 | Was heißt „von KI und Menschen bedienbar", und woran misst man es? | **Teilweise.** Bauform ist Literaturstand (eine Schnittstelle, zwei Ansichten). Abnahme: LongMemEval-V2 für das Gedächtnis; für Werkzeuge bleibt es eine **Baurichtlinie mit Selbsttest**, kein Prüfer über Fremdsoftware (`L-aa889c`). |
| 4 | Was muss eine Domäne mitbringen? | **Entsperrt.** Zwei Instanzen existieren; Entwurf liegt in `L-473ba2`. Noch nicht geschrieben. |
| 5 | Welche Plattformen? | **Offen**, und billiger geworden: Der Kern ist Python, die Plattformfrage betrifft nur die Oberfläche. |
| 6 | Kleinste zweite Domäne? | **Hinfällig** — es gibt bereits zwei. |
| 7 | Community-Gehirn: was fehlt? | **Kein Architekturthema.** Herkunft, Widerruf, Geltung sind Linie B und C des Gesamtplans, in bindender Reihenfolge. |
