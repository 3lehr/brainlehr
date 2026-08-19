# Plan: Gedächtnisarten episodisch/semantisch/prozedural — Aufgabe 104

Stand 2026-08-19T00:00:00+0200. Aufgabe 104 aus Linie K
(`docs/PLAN_GESAMT_2026-08-13.md:892`). Entwurfsauftrag — dieses Dokument
ändert kein Schema, keinen Code, keine Tests. Unterschritte heißen 104.1 ff.

Betroffene ACs, wörtlich aus `docs/REQUIREMENTS_BRAINLEHR.md:107-109`:

- `BDW-F01-AC1`: „Episoden bestehen Schreib-, Zeit-, Quellen-, Recall-,
  Korrektur- und Löschtest."
- `BDW-F02-AC1`: „Jeder verwendete Claim weist Quelle, Ableitung, Status und
  Korrekturpfad aus."
- `BDW-F03-AC1`: „Prozeduren sind von Fakten/Episoden getrennt und besitzen
  eigenen Freigabe- und Widerrufstest."

## 104.1 Gemessener Ist-Stand

Bestand (`sqlite3 "file:brainlehr.db?mode=ro" -readonly "SELECT count(*) FROM
knowledge_nodes;"` / `... lessons_learned;"`): **5172 Knoten, 1096 Lehren.**
Abweichung von den im Auftrag genannten 5170/1095: Drift von einem Tag
Betrieb, kein Widerspruch — genannt, damit niemand die alte Zahl fortträgt.

`knowledge_relations` (`SELECT relation_type, count(*) FROM
knowledge_relations GROUP BY relation_type ORDER BY 2 DESC;`): 10303 Kanten
gesamt, davon `aehnlich_bedeutung` 9981, `abgeleitet_von` 257, `loest_ab` 3
— stimmt mit den genannten „9976 Ähnlichkeitskanten, 3 Ablösungskanten" bis
auf dieselbe Tagesdrift überein.

### 104.1.1 Herkunftsspaltung, VOR jeder Stichprobe nötig

```
SELECT CASE
  WHEN path LIKE '/germanquad/%' THEN 'germanquad'
  WHEN path LIKE '/nasa-llis/%' THEN 'nasa-llis'
  ELSE 'sonst' END, count(*)
FROM knowledge_nodes GROUP BY 1;
```
→ germanquad 2713, nasa-llis 1637, sonst (= „eigen") 822. **84 % der
`knowledge_nodes`-Zeilen sind importierte Prüfkorpora** (Wikipedia-Auszüge,
NASA-Lessons-Learned), keine von brainlehr selbst erzeugte Aussage. Knoten
`096669de` legt den NASA-Bestand ausdrücklich als „Heuhaufen" für
Abrufmessungen fest, nicht als Aussagequelle. Die bestehende Spalte `gattung`
bildet diese Trennung bereits fast exakt ab:

```
SELECT gattung, CASE WHEN path LIKE '/germanquad/%' OR path LIKE '/nasa-llis/%'
  THEN 'corpus' ELSE 'eigen' END, count(*)
FROM knowledge_nodes GROUP BY 1,2;
```
→ `arbeitsbestand`/eigen 818, `nachschlagewerk`/corpus 4350,
`nachschlagewerk`/eigen 4. `gattung=arbeitsbestand` ist damit zu 818/822
= 99,5 % deckungsgleich mit „eigene Aussage". Eine Dreiteilung, die die
importierten Korpora mitzählt, würde die Zahlen der ersten Version verzerren
— **die Stichprobe für Schritt 104.1.2 zieht deshalb nur aus `gattung=
'arbeitsbestand'` bzw. `path NOT LIKE '/germanquad/%' AND path NOT LIKE
'/nasa-llis/%'`.**

### 104.1.2 Stichprobe, deterministisch und reproduzierbar

Nodes (eigen, n=32, Befehl:
`SELECT ... FROM knowledge_nodes WHERE path NOT LIKE '/germanquad/%' AND path
NOT LIKE '/nasa-llis/%' AND rowid % 27 = 1;` — 822/27≈30, Reststreuung ergab
32):

| Pfad | Art | Begründung |
|---|---|---|
| `/begod/neuen-app-worktree-bootstrappen` | **prozedural** | Titel „Prozedur:", enthält wörtliche Befehlsfolge (`git worktree add`, `init_worktree.py`) |
| `/methodik/arbeitsweise/der-plan-traegt-die-auftraege-selbst` | **prozedural** | schreibt vor, WIE ein Plan Aufträge tragen soll |
| `/methodik/direktiven/geht-nicht-ist-ein-zwischenstand-keine` | **prozedural** | Ablaufvorschrift „erst widerlegen, dann fragen" |
| `/apps/setfunk-technik-konsil-td1-td12-plan-ap` | **episodisch** | datierter Umsetzungsbericht 2026-07-24, welche Commits/Tests wann liefen |
| `/brainlehr/wettbewerbslage-2026-08-09-zwei-echte` | **episodisch** | datierte Rechercheergebnis-Momentaufnahme |
| `/methodik/direktiven/dringend-der-normbezugs-melder` | **episodisch** | datierter Einzelfund (§71 GEG, 2026-08-12) |
| `/arch` | **semantisch** | Definition, was der Bereich `/arch` ist |
| `/apps/fahrtenbuch/zweckwechsel-waehrend-der-fahrt-zaesur` | **semantisch** | Rechtsnorm (BFH-Urteil), zeitlos gültig bis Widerruf |
| `/ops/verwalterwahl-weg-im-buckeberg-zum-2027/rechtslage-die-jahresabrechnung-2026` | **semantisch** | Rechtslage aus § 28 Abs. 2 WEG |

Volle Liste unter `/private/tmp/.../scratchpad/sample_nodes_eigen.txt` dieser
Sitzung (32 Zeilen, id|path|title|summary). Auszählung: **semantisch 17
(53 %), episodisch 10 (31 %), prozedural 5 (16 %).**

Lessons (n=30, Befehl: `... FROM lessons_learned WHERE rowid % 37 = 1;`,
1096/37≈30):

| id | Art | Begründung |
|---|---|---|
| `L-14a742` | **episodisch** | „Erstes Auftreten 2026-07-23 03:32 … beim zweiten Auftreten 2026-07-23 08:20" — datiertes Ereignispaar |
| `L-ace7f0` | **episodisch** | „gemessen 2026-08-13", konkreter Feldfehler, konkreter Test |
| `L-b0e282` | **episodisch** | „Beinahefehler 2026-08-18, brainlehr" |
| `L-c903c3` | **prozedural** | generalisiertes Rezept „Lint-Regel verzeichnisweise staffeln", kein Datumsbezug |
| `L-1cb47c` | **prozedural** | nummerierte Schrittfolge 1–6, als Verfahren formuliert |
| `L-adb765` | **semantisch** | Aussage über Regex-Verhalten, zeitlos gültig |
| `L-645969` | **semantisch** | „Tags sind keine Durchsetzung." — Aussage über den Zustand des Systems |

Volle Liste unter `sample_lessons.txt` derselben Sitzung. Auszählung:
**episodisch 21 (70 %), prozedural 6 (20 %), semantisch 3 (10 %).**

### 104.1.3 Ergebnis der Messung

| Bestand | episodisch | semantisch | prozedural |
|---|---|---|---|
| `knowledge_nodes` (eigen, n=32) | 31 % | 53 % | 16 % |
| `lessons_learned` (n=30) | 70 % | 10 % | 20 % |
| **beide zusammen (n=62)** | **50 %** | **32 %** | **18 %** |

Keine Art erreicht 90 %. **Die Dreiteilung ist nicht per se nutzlos** — anders
als die Eingangsfrage unterstellt, ist der Bestand tatsächlich gemischt, auch
innerhalb einer einzigen Tabelle: `lessons_learned` ist strukturell bereits
episodisch (datiertes Ereignis, `first_seen`/`occurrences`) UND prozedural
(`prevention`-Feld) in ein und derselben Zeile verschränkt — das ist selbst
ein Befund (siehe 104.2).

## 104.2 Die Ablagefrage

Drei Alternativen, je mit Abruf- und Migrationskosten für 5172 Knoten/1096
Lehren:

**(a) Neue Spalte `gedaechtnisart` an `knowledge_nodes` (und/oder
`lessons_learned`), Werte `episodisch|semantisch|prozedural`, Bauform wie die
bestehende `gattung`-Spalte (`NOT NULL DEFAULT`, zwei `CHECK`-Trigger
`_bi`/`_bu`, `schema.sql:395-406` als Vorbild).**
- Abruf: ein `WHERE gedaechtnisart='prozedural'`-Filter reicht, FTS/Vektor-
  Index bleiben unverändert, keine neue Join-Kaskade.
- Migration: eine `UPDATE`-Kampagne über 5172 Zeilen, klassifiziert per
  Heuristik + Stichprobenkorrektur (siehe 104.1.2 als Startpunkt). Größtes
  Risiko: das Feld wird — wie `gattung` bei den vier `nachschlagewerk`/eigen-
  Ausreißern gezeigt hat — nie nachträglich sauber, weil niemand es beim
  Schreiben pflegt, wenn kein Trigger es erzwingt.
- Passt zur bestehenden Bauform des Repos (gleiche Lösung wie `gattung` und
  `freigabe`), kein neues Konzept.

**(b) Eigene Tabellen `episoden`, `claims`, `prozeduren` statt der
gemeinsamen `knowledge_nodes`/`lessons_learned`.**
- Abruf: JEDE Abfrage, die heute `knowledge_nodes` oder `lessons_learned`
  scannt (FTS-Trigger, `knowledge_search`, `lesson_query`, Ähnlichkeitskanten,
  Kurator, `melder/*`, `haken/*` — 258 Dateien laut `grep -rl "knowledge_nodes
  \|lessons_learned" --include='*.py' . | grep -v -e node_modules -e
  '.claude/worktrees' | wc -l`, ohne die parallelen Arbeitsbäume unter
  `.claude/worktrees/` mitzuzählen) müsste um die dritte/vierte Tabelle erweitert oder per
  `UNION` zusammengeführt werden. `knowledge_relations` referenziert heute
  vermutlich `knowledge_nodes.id`/`lessons_learned.id` als Fremdschlüssel-
  ähnliche Strings — eine dritte ID-Quelle bricht diese Annahme an jeder
  Stelle, die „ist das eine Node-ID oder eine Lesson-ID" unterscheidet.
- Migration: Daten physisch verschieben, IDs erhalten, alle bestehenden
  Referenzen (`node_path` in `lessons_learned`, `abgeleitet_von`,
  `zurueckgezogen_von`, `bedient_von`) nachziehen. Höchster Aufwand der drei
  Alternativen.
- **ABGELEHNT.** Die Messung in 104.1 zeigt keine reinen Cluster (keine
  Tabelle ist auch nur zu 90 % einer Art) — eine physische Dreiteilung würde
  ständig denselben Datensatz (ein Lessons-Eintrag mit Ereignis UND Rezept)
  künstlich auf zwei Tabellen aufspalten oder eine Art erzwingen, die nicht
  zutrifft. Der Migrationsaufwand ist ferner der einzige, der bestehende
  Fremdschlüssel-ähnliche Verweise bricht.

**(c) Die vorhandene Trennung Knoten/Lehre um eine dritte Art erweitern,
z. B. eigene Tabelle nur für `prozeduren`, episodisch/semantisch bleiben als
Teilmengen von `knowledge_nodes` per Spalte (Hybrid aus a und b, nur für die
eine Art, die laut 104.1 heute komplett fehlt).**
- Abruf: eine zusätzliche Tabelle nur für die Art, die strukturell am
  wenigsten mit den bestehenden zwei überlappt (Prozeduren haben einen
  eigenen Lebenszyklus — Freigabe/Widerruf laut `BDW-F03-AC1` — den weder
  `knowledge_nodes` noch `lessons_learned` heute abbildet). Episodisch/
  semantisch bleiben im bewährten Zwei-Tabellen-Schema, nur um eine
  Unterscheidungsspalte ergänzt.
- Migration: nur die 16 % (prozedural) müssen physisch wandern, nicht alle
  5172/1096 Zeilen; der Rest bekommt nur die neue Spalte per (a).
- Das ist die einzige Alternative, die 104.1.3 (kein Feld ist über 90 % eine
  Art, aber Prozedurales ist heute nirgends VOM RECHT her getrennt — kein
  eigener Freigabe-/Widerruftest existiert, siehe 104.3) tatsächlich trifft.

## 104.3 Was die Akzeptanzkriterien zusätzlich verlangen

Kein Teil von BDW-F01–F03 ist mit der Ablagefrage allein erledigt. Bestehende
Mechanismen laut Schema (`sqlite3 "file:brainlehr.db?mode=ro" -readonly
".schema knowledge_nodes"` / `".schema lessons_learned"`) gegen die AC-Teile
gehalten:

| AC-Teil | heute vorhanden an `knowledge_nodes` | heute vorhanden an `lessons_learned` | prüfbare Aussage für den späteren Test |
|---|---|---|---|
| Quelle (F02) | `source`, `quell_hash` (32 von 32 Stichprobenzeilen aus 104.1.2 haben `source` gesetzt, Befehl: `SELECT count(*) FROM knowledge_nodes WHERE path NOT LIKE '/germanquad/%' AND path NOT LIKE '/nasa-llis/%' AND rowid % 27 = 1 AND source IS NOT NULL AND source != '';`) | kein Quellfeld | „Jeder neu geschriebene Claim hat `source` NOT NULL." |
| Ableitung (F02) | `abgeleitet_von` (Spalte existiert, 257 `abgeleitet_von`-Kanten in `knowledge_relations`) | kein Feld | „Ein abgeleiteter Claim referenziert seinen Ursprung, auflösbar in `knowledge_relations` oder Spalte." |
| Status (F02) | `norm_entscheidung` (`offen`\|`norm_befristet`\|`norm_unbefristet`\|`keine_norm`), `zurueckgezogen` (0/1) | `status` (`active`\|`resolved`\|`escalated_to_rule`\|`open`\|`in_claude_md`) | „Jeder Claim/jede Lehre hat einen Status ungleich NULL aus einer geschlossenen Werteliste." |
| Korrekturpfad (F01+F02) | `zurueckgezogen_grund`, `zurueckgezogen_von`, `zurueckgezogen_am` | **fehlt vollständig** — keine `zurueckgezogen_*`-Spalten in `lessons_learned` | „Eine Korrektur an einer Lehre erzeugt denselben Vier-Felder-Nachweis wie an einem Knoten." Heute NICHT erfüllbar für Lehren — **Lücke, nicht Ablagefrage.** |
| Zeit (F01) | `created_at`, `updated_at`, `gilt_ab`/`gilt_bis` | `first_seen`, `last_seen` (kein `gilt_ab`/`gilt_bis`) | „Jede Episode trägt einen Zeitpunkt, der beim Schreiben gesetzt und beim Lesen unverändert bleibt." |
| Löschung (F01) | `zurueckgezogen`-Flag + `zurueckgezogen_grund` (weiches Zurückziehen) UND ein separates hartes Löschwerkzeug `kern/endgueltig_entfernen.py` (gefunden über `grep -rl "DELETE FROM knowledge_nodes" --include='*.py' .`) | kein `zurueckgezogen`-Pendant, dieselbe `kern/endgueltig_entfernen.py`-Route vermutlich mitgemeint (nicht in dieser Prüfung gelesen) | Zwei Löschbegriffe existieren bereits nebeneinander (weich/hart) — offen ist nur, WELCHEN „Löschtest" laut `BDW-F01-AC1` meint, nicht OB ein Mechanismus fehlt. **Klärung vor Bau nötig, keine Codeentscheidung hier.** |
| Freigabe (F03) | `freigabe` (`offen`\|`intern`\|`gesperrt`) | `freigabe` (dieselbe Wertemenge) | „Freigabe ist bereits generisch vorhanden — F03 verlangt keine neue Spalte, sondern einen Prozedur-spezifischen Test, der eine Freigabeänderung UND ihren Widerruf prüft." |
| Widerruf, prozedurspezifisch (F03) | — | — | Weder Tabelle bildet „Widerruf einer Prozedur, unabhängig von Widerruf eines Fakts" ab. **Das ist der einzige AC-Teil ohne jede heutige Spalte.** |

Befund: Quelle/Status/Korrektur/Zeit sind für `knowledge_nodes` strukturell
schon da (98 % der F02-Anforderung ist Prüfung bestehender Spalten, keine
neue Spalte). Der reale Fehlbestand liegt an zwei Stellen: `lessons_learned`
hat keinen Korrekturpfad, und Prozeduren haben nirgends einen eigenen
Freigabe-/Widerruf-Mechanismus, der von Fakten getrennt ist.

## 104.4 Reihenfolge, bindend wo markiert

1. **104.4.1 — Schemafrage entscheiden** (Alternative a/b/c, Betreiber oder
   Folgeauftrag). **Bindend vor allem anderen**, weil 104.4.2 sonst gegen ein
   Ziel migriert, das sich unter der Hand ändert.
2. **104.4.2 — Migrationsheuristik bauen und gegen die Stichprobe aus 104.1.2
   kalibrieren** (Genauigkeit gegen die 62 von Hand klassifizierten Zeilen
   messen, bevor sie auf 6268 losgelassen wird). **Bindend nach 104.4.1**,
   parallel zu nichts anderem — eine zweite Person, die gleichzeitig auf
   `knowledge_nodes` schreibt, entwertet die Kalibrierung.
3. **104.4.3 — Korrekturpfad an `lessons_learned` nachziehen** (die in 104.3
   gefundene Lücke) — unabhängig von 104.4.1/.2 planbar, weil sie eine reine
   Spaltenergänzung ist, keine Umsortierung.
4. **104.4.4 — Prozedur-Freigabe/Widerruf entwerfen** — hängt an 104.4.1,
   weil er wissen muss, ob Prozeduren in einer eigenen Tabelle (Alternative c)
   oder als Teilmenge (a) landen, bevor er den Freigabe-Mechanismus dafür
   entwirft.
5. **104.4.5 — Rot-Proben schreiben** je AC-Teil aus der Tabelle in 104.3,
   NACH 104.4.1–.4.4, weil ein Test gegen ein Schema, das noch verworfen
   werden kann, wertlos ist.

## 104.5 Was bewusst nicht getan wird

- **Keine Klassifikation der 4350 `germanquad`/`nasa-llis`-Knoten nach
  episodisch/semantisch/prozedural.** Preis: Falls diese Korpora je aus dem
  reinen Heuhaufen-Status in echte Abrufziele wandern, fehlt ihre Einordnung
  nachträglich. Begründung: Knoten `096669de` legt sie ausdrücklich als
  Prüfmaterial fest, nicht als Aussagequelle — eine Klassifikation für BDW-F01
  bis F03 wäre für sie zweckfremd.
- **Keine Festlegung, ob „Löschtest" (F01) harte SQL-Löschung oder Zurückziehen
  meint.** Preis: 104.4.5 kann diesen einen Test nicht vor einer Klärung
  schreiben. Begründung: Das ist eine Produktentscheidung mit Datenschutz-
  Implikation (Retention/Hold, RQ-013 „teilweise"), keine, die aus dem
  gemessenen Bestand ableitbar ist.
- **Keine automatisierte Neuklassifikation der 6268 Zeilen in diesem
  Auftrag.** Preis: Die Zahlen aus 104.1 bleiben Stichprobe, keine
  Vollerhebung. Begründung: Aufgabe 104 ist als Entwurfsauftrag begrenzt;
  eine Vollklassifikation ist Teil von 104.4.2 und braucht die
  Schemaentscheidung aus 104.4.1 zuerst.

## 104.6 Woran sich Erfolg misst

- Stichprobenkonkordanz: Bei einer zweiten unabhängigen Klassifikation
  derselben 62 Zeilen aus 104.1.2 stimmen mindestens 90 % der Einzel-
  zuordnungen überein (Cohen's Kappa ≥ 0,8) — sonst ist die Drei-Kategorien-
  Grenze selbst zu unscharf für einen automatisierten Migrationsschritt.
- Nach 104.4.2: Bei einer Zufallsstichprobe von 100 automatisch klassifizierten
  Zeilen (nicht identisch mit den 62 Kalibrierungszeilen) stimmen mindestens
  90 mit einer Handprüfung überein.
- Je AC-Teil aus 104.3 genau ein Rot-Probe-Test, der VOR der zugehörigen
  Implementierung nachweislich fehlschlägt (`pytest --collect-only` zeigt ihn,
  Lauf vor dem Fix ist rot) und danach grün — Nachweis über Commit-Historie,
  nicht über Behauptung.
- `lessons_learned`-Korrekturpfad: Anteil der Lehren mit vollständigem
  Vier-Felder-Nachweis (`zurueckgezogen_grund/-von/-am` + Status) nach
  104.4.3 muss für JEDE künftig zurückgezogene Lehre 100 % betragen (heute:
  0 %, weil die Spalten fehlen — `sqlite3 ".schema lessons_learned"` zeigt
  keine `zurueckgezogen_*`-Spalte).
