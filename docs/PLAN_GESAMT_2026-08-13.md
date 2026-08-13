# Gesamtplan brainlehr, Fassung 2026-08-13

Ersetzt die **Reihenfolge** von `PLAN_GESAMT_2026-08-11.md`. Dessen Befunde
bleiben gültig; sie beantworten nur nicht mehr die wichtigste Frage.

## Was sich seit dem 11.08. geändert hat

Der Plan vom 11.08. fragte: *Warum findet der Abruf das Ziel nicht?* Die Nacht
zum 13.08. hat eine andere Frage beantwortet, und sie liegt darunter:

> **Was ist gebaut, läuft, meldet — und wirkt in null Fällen?**

**Zwölfmal belegt, jedes Mal einzeln gemessen:**

| Mechanismus | Befund |
|---|---|
| `ui_guard.py` | 0 Treffer in `settings.json` |
| `push_guard.py` | in 6 von 8 Repos nicht installiert |
| `existenzpruefung.py` | 0 von 949 Stop-Ereignissen |
| `kanten_aus_bedeutung.py` | kein Aufrufer, steht seit 2026-08-09 |
| `berichte/vorschlag.py` | 0 Einträge, 55 fertige Vorschläge liegen brach |
| 11 von 19 Hausregeln | kein Mechanismus |
| Caveman | angeordnet, nirgends verdrahtet |
| PostToolUse-Kanal | liefert nichts, 8 Skripte stumm |
| 8 von 15 Melder | kein Eintrag in einer Regelablage |
| 10 Spalten | 98–100 % leer |
| Kalibrierbremse | wirkte nie, ausgebaut |
| zweite Oberfläche | leer, stillgelegt |

**Und der Fund, der das Muster erklärt:** Die Regel dagegen existierte vor
Monaten. Die Stiftshütten-Rolle `spaghetti-monster` trug wörtlich *„Agent ohne
Trigger in 5+ Sessions → Sunset-Kandidat"*. Verloren ging sie nicht durch
Nachlässigkeit, sondern durch den **Plattformwechsel**: Bei einem Umzug wandern
die Artefakte, die man sieht. Eine Rolle, deren einziger Wert ihr **Auslöser**
war, hat keinen Gegenstand, den man mitnehmen könnte.

## Der dritte Befund, und er fasst Linie B zusammen: die fehlende Hinsicht

Auf Betreiberfrage *„wo taucht das noch auf?"* zusammengetragen (Knoten
`012500e5`). **Eine Aussage trägt einen Wahrheitswert nur zusammen mit der
Hinsicht, in der sie gilt.** Katze und Delfin sind beide Säugetiere, nur einer
mag Wasser. Der Speicher legt Aussagen ohne ihre Hinsicht ab — dann ist jede
Vergleichbarkeit geraten, und zwar **unsichtbar**, weil das Ergebnis plausibel
bleibt.

Dieselbe Form, heute an **sechs** Stellen gemessen und **sechsmal einzeln**
behandelt:

| Stelle | Die fehlende Hinsicht |
|---|---|
| 5814 Kanten `aehnlich_bedeutung` | ähnlich **worin**? Der Typ nennt die Art der Beziehung, nicht die Hinsicht |
| Schwelle `0,65` | gilt für Rechtsfrage und Funktionsnamen gleich — ein falscher Rechtssatz kostet anders |
| kein Rechtsraum | eine Norm gilt hier und nebenan nicht |
| Zeit nicht im Vektor | 2026 und 2020 sind im Bedeutungsraum ununterscheidbar nah |
| `trigram` | im Deutschen tauglich, im Japanischen blind |
| zwei Ausgangszustände | frisch gegen gewachsen — dieselbe Software, zwei Wahrheiten |

**Die Prüffrage, billig und vor dem Bau zu stellen:** *Gibt es einen Fall, in
dem dieselbe Aussage hier wahr und dort falsch ist?* Lautet die Antwort ja,
gehört die Hinsicht ins **Datenmodell** — nicht in den Fließtext, wo sie beim
Vergleichen nicht mitgelesen wird.

**Warum es sechsmal einzeln auftrat:** Jede Stelle hat ihre eigene Fachsprache
(Kante, Schwelle, Geltung, Zeitstempel, Tokenizer, Migration). Die gemeinsame
Form wurde erst sichtbar, als der **Betreiber** fragte, wo das noch auftaucht.
Der Speicher hat die Frage nicht gestellt — genau die Lücke, die `78` und `90`
schließen sollen.

## Der zweite große Befund: der Speicher hat nur eine Achse

Gemessen am 13.08.:

| | |
|---|---|
| Kanten | `aehnlich_bedeutung` 5814 · vier weitere Typen zusammen 61 |
| im Vektor | `path + title + summary + content` — **kein** Datum, keine Geltung, keine Tags |
| `created_at` | 2166 von 2166 |
| `gilt_bis` | **2** von 2166 |
| Knoten ohne jede Kante | 307 von 2166 (14 %) |

„Was wurde letzte Woche gemacht" ist mit vorhandenen Daten beantwortbar und hat
keinen Weg. „Das gilt bis X" hat einen Weg und keine Daten. Und der
Stichwortkanal ist **unter drei Zeichen strukturell blind** — im Deutschen ein
Randfall, im Japanischen der Normalfall (nachgestellt: `知識` findet 0).

## Linie 0 — „brainlehr sagt", und sie steht vor allem anderen

Betreiberanweisung 2026-08-13, wörtlich: *„wen aus brainlehr sollte es in
zukunft heißen: brainlehr sagt: …"* — und *„stell es voran, es hat gleich
nutzen"*.

**Anlass:** Ich hatte einen Befund samt Zahlen (0,531 gegen 0,527, Modellwahl
`bge-m3`) als eigene Aussage weitergegeben. Er stammte vollständig aus dem
eingespielten Knoten `/brainlehr/das-einbettungsmodell-trennt-auf`, war sechs
Tage alt und aus einem Codestand, den es nicht mehr gibt. Aus der Formulierung
war nichts davon erkennbar.

**Warum sie vorangeht, obwohl sie klein ist:** Sie beantwortet nebenbei die
Frage, an der die Okkultation seit Tagen hängt — *trägt der Abruf etwas bei?*
Ist jede eingespielte Aussage gekennzeichnet, **sieht der Betreiber die
Trefferquote im Gespräch mit**, ohne Messlauf, ohne Korpus, ohne Eingriff. Das
ist billiger als jedes geplante Verfahren und liefert ab der ersten Antwort.

**Die Gefahr, und sie ist dieselbe wie bei allen elf mechanismuslosen Regeln:**
Eine Kennzeichnungsregel, die nur im Text steht, ist Disziplin — und Disziplin
hat heute zwölfmal versagt. Deshalb hat Linie 0 einen **mechanischen** Teil:

1. Der Abruf-Haken **markiert seinen eigenen Block** so, dass maschinell
   feststellbar ist, welche Aussagen aus dem Speicher stammen.
2. Ein Melder auf der Antwortseite prüft, ob **kennzeichnende Begriffe** aus dem
   eingespielten Block in der Antwort auftauchen, **ohne** dass die Antwort den
   Speicher als Quelle nennt. `haken/antwort_abruf.py` liest die letzte eigene
   Antwort bereits — die Stelle existiert.

**Zwei Grenzen, ohne die die Regel schadet:**

- **Nicht jeder Satz bekommt ein Etikett.** Gekennzeichnet wird, was der Leser
  sonst für meine eigene Aussage hielte: Zahlen, Existenzaussagen, Befunde,
  Datumsangaben. Was in derselben Sitzung selbst gemessen wurde, bleibt eigen —
  dort ist die Herkunft die Messung, nicht der Abruf.
- **„brainlehr sagt" ist keine Bestätigung.** Ein eingespielter Treffer ist
  Hintergrund, kein Beleg. Die Kennzeichnung sagt, **woher** etwas kommt, nicht
  dass es stimmt. Wo es zählt, wird weiterhin gegen den echten Stand geprüft.

Und der Stand gehört dazu, wo er zählt: *„brainlehr sagt, Stand 07.08."* hätte
die Nachfrage nach der heutigen Architektur überflüssig gemacht — sie hätte in
der Aussage gestanden.

### Zwei Sorten von „brainlehr sagt", und sie tragen verschieden

Betreiberzusatz 2026-08-13: Es macht einen Unterschied, ob der Speicher eine
**eigene Regel oder Selbsterfahrung** wiedergibt oder ein **fremdes Zitat** —
Gesetz, DIN, ISO, BSI, WCAG. Beim fremden Zitat gehört gesagt, **von wem** es
stammt, und seine **Geltung** geprüft: **bis wann** und **wo**.

**Gemessen, wie weit der Bestand das heute kann:**

| | |
|---|---|
| `norm_entscheidung` = **`offen`** | **1919** von 2166 — bei 89 % ist die Frage gar nicht entschieden |
| `keine_norm` | 169 · `norm_unbefristet` 76 · `norm_befristet` **2** |
| `norm_rang` (wie bindend) | 83 |
| `gilt_ab` | 83 |
| **`gilt_bis`** (Ablauf) | **2** |
| **`norm_art`** (eigen oder fremd) | **0** |
| **örtliche Geltung** | **kein Feld** |

`kern/geltungsbereich.py` gibt es — es behandelt aber die **Projekt**-Zugehörigkeit,
nicht den **Rechtsraum**. Der Fall, den der Betreiber genannt hat (jedes
Bundesland, jeder Staat hat andere Gesetze), ist im Schema nicht abbildbar.

Die **Prüfseite existiert bereits**: `normbezug.py` meldet, wenn eine Antwort
ein Gesetz, eine Norm oder eine interne Kennung nennt, für die kein Beleg im
Bestand liegt — bei internen Kennungen heißt ein Fehltreffer nicht „unbelegt",
sondern „erfunden". **Es fehlt nicht der Prüfer, es fehlen die Daten.**

**Die Reihenfolge, und sie folgt aus der 2:** `gilt_bis` steht bei 2 von 2166.
Ein Feld, das niemand füllt, wird auch als örtliche Geltung niemand füllen.
Deshalb **erst `norm_art`** — eigen oder fremd ist beim Schreiben ohne Recherche
entscheidbar und trennt sofort die beiden Sorten. **Dann** Ablauf und Ort, und
zwar **nur für fremde Normen**: Eine eigene Hausregel braucht kein Bundesland.
Das reduziert die zu füllende Menge von 2166 auf die Handvoll fremder Zitate —
und macht den Unterschied zwischen einer Spalte, die gefüllt wird, und der
zwölften leeren.

## Die fünf Linien, in bindender Reihenfolge

**Linie A — Wirksamkeit vor allem anderen.** Solange Mechanismen nicht feuern,
ist jede weitere Messung eine Aussage über etwas, das niemand benutzt.
`81` (Kanten wieder rechnen — entsperrt, `83` und `87` sind erledigt) ·
`85` (Melder gegen auslöserlose Mechanismen) · `84` (Vorschlagsbericht
verdrahten, mit Neuheitsfilter).

**Linie B — die fehlenden Achsen.** `88` (Zeit als Filter; Geltung erst nach der
Vorfrage, wer `gilt_bis` setzt) · `89` (Kanalwahl an die Anfragelänge binden) ·
`76` (jede Kante trägt ihre Hinsicht) · `75` (W-Fragen) · **`86` (trägt eine
metaphorisch benannte Regel weiter als eine wörtliche?).**

`86` steht hier und nicht in einer eigenen Ecke, weil es dieselbe Frage ist wie
die übrigen vier: **woran hängt eine Aussage außer an ihrem Wortlaut?** Bei `88`
ist es die Zeit, bei `89` die Sprache, bei `76` die Hinsicht — bei `86` das
Bild. Die Sperre gilt auch dort: Vor der Messung wird keine Regel umbenannt,
sonst wäre die Umbenennung ihre eigene Begründung.

**Linie C — der Speicher schreibt mit.** `78` (Dublettenerkennung beim Anlegen)
→ `73` (Herkunftskette; **dieselbe Funktion**, deshalb streng danach) ·
`79` (Herkunftsfelder normalisieren, kein neues Feld).

**Linie D — Messbarkeit wiederherstellen.** `71` (die nicht zuordenbare Differenz
45 gegen 33; `70` ist erledigt, damit möglich) · `68` (Prüfkorpus deterministisch)
→ `67` → `42` (Okkultation mit größerer Fallmenge).

**Linie E — nur der Betreiber.** `20`, `23`, `29`, `31`. Nicht autonom, in
keiner Reihenfolge erzwingbar.

## Fortschreibung 2026-08-13T13:00 — Linie 0 und A stehen, die Reihenfolge kippt

**Erledigt:** Linie 0 vollständig (`94` Zuschreibung maschinell, `95` `norm_art`),
Linie A vollständig (`81` Kanten, `85` Melder gegen auslöserlose Mechanismen,
`84` Vorschlagsbericht), dazu `83`, `87`, `82`, `23`.

**Was die Reihenfolge kippt:** Gemessen gegen die Referenz sind **7 von 29**
Haken-Ereignissen verdrahtet (`98`). Drei ungenutzte sind der **fehlende
Mechanismus** dreier offener Aufgaben:

| Ereignis | entsperrt | warum |
|---|---|---|
| `WorktreeCreate` | `92` Identität | bekommt `base_directory`, **blockiert bei Exit ≠ 0** — setzt die Datei, statt ihr Fehlen zu melden |
| `PreToolUse` auf das Agent-Werkzeug | `97` Peer Review | sieht `tool_input`, kann per `updatedInput` den **Auftrag ändern** |
| `FileChanged` | `96` Schemaabgleich | Matcher auf literale Dateinamen — `schema.sql` |

Dazu `TaskCreated`/`TaskCompleted`, die **blockieren** können: dort wird „kein
`completed` ohne Beleg, der vorher rot war" mechanisch statt appellativ.

**`98` rückt damit vor `92`, `96` und `97`** — es ist deren Voraussetzung, nicht
ihr Nachbar.

### Der Engpass, der die Parallelität bestimmt

`knowledge_mcp_server.py` wird von **`89`, `88` und `78`** gebraucht. Drei
Agenten dort verlieren Arbeit. Also:

| Welle | parallel | Dateien |
|---|---|---|
| **1** | `98` Haken · `71` Messbarkeit · `89` Kanalwahl | `haken/`+Ablage · `messungen/` · `knowledge_mcp_server.py` |
| **2** | `78` Dubletten · `92` Identität · `68` Prüfkorpus | Server (nach 89) · Haken (nach 98) · `messungen/` |
| **3** | `73` Herkunft · `88` Zeit · `96`+`97` Wächter | Server (nach 78) · Server (nach 88 frei) · Haken |

**Auflage für alle Wellen:** Nur **einer** fährt die volle Suite — nämlich ich,
zwischen den Wellen. Ein Testlauf neben fremder halbfertiger Arbeit misst
Halbstände, rot wie grün (`L-243dde`).

## Die Sperren, die nicht verhandelbar sind

- **`80` vor `69`.** Die Identität eines Vektors ist allein der Modellname;
  `num_ctx` ändert ihn nicht. Ein Neulauf erzeugt sonst Vektoren gleicher
  Dimension und anderer Abschneidegrenze, an denen jeder Filter vorbeigeht.
- **`78` vor `73`.** Beide ändern `knowledge_add`.
- **`89` vor jeder weiteren Abrufmessung.** Ein blinder Kanal, der Ranggewicht
  beansprucht, verfälscht jede Zahl, die danach entsteht.
- **Keine Abrufzahl nach außen, solange `71` offen ist.**

## Was bewusst nicht getan wird, samt Preis

- **Kein Nachbau des Rollen-Pantheons in einem Zug** — 81 Rollen zu übernehmen,
  bevor eine einzige gemessen ist. Das alte System wusste um diese Gefahr und
  hielt sich einen Widersacher dagegen (*„Agentenkette länger als vier →
  Vereinfachung prüfen"*).

  **Das ist ausdrücklich keine Entscheidung gegen Metaphern.** Ob eine
  metaphorisch benannte Regel weiter trägt als eine wörtliche, ist eine offene
  Frage mit widersprüchlicher Fremdlage — und sie wird in **Linie B** gemessen
  (`86`), nicht hier entschieden. Was hier abgelehnt wird, ist allein die
  Reihenfolge: übernehmen, dann messen.

  Zwei **Bauformen** sind davon unabhängig und werden übernommen, weil sie keine
  Metaphern brauchen: die Bindung einer Regel an einen **Schritt** (dagegen sind
  unsere 19 Hausregeln alle immer aktiv, und genau deshalb haben elf keinen
  Aufhängepunkt) und die Trennung von **Grenzwert-Setzen und Durchsetzen**.
- **Keine Metadaten im Einbettungstext.** Preis: Der Bedeutungskanal bleibt
  zeitblind. Gewinn: Ein Datum bekommt keine falsche semantische Nähe zu einem
  anderen Datum — es hat einen Abstand, keine Ähnlichkeit.
- **Kein Umstellen der Regeln auf Metaphern vor der Messung** (`86`). Sonst wäre
  die Umstellung ihre eigene Begründung.
- **Keine Verdrahtung in `~/.claude/settings.json`.** Preis: andere Projekte
  bekommen nichts. Gewinn: keine Wirkung auf die parallel laufenden Sitzungen
  des Betreibers. Genau diese Vorsicht war am 13.08. die Ursache dafür, dass die
  Existenzprüfung nie lief — die Lösung ist, an einen bereits laufenden Haken zu
  hängen, nicht die globale Datei anzufassen.

## Woran sich Erfolg misst

- **Linie A:** Ein Melder findet die bekannten Fälle des heutigen Bestands und
  schweigt bei einem nachweislich verdrahteten Haken. Kein Veto, nur Hinweis.
- **Linie B:** Eine Anfrage mit Zeitraum liefert eine echte Teilmenge; eine
  Anfrage aus lauter Zwei-Zeichen-Begriffen erhält kein Stichwort-Ranggewicht
  mehr.
- **Linie C:** Der dritte Achsen-Knoten bekommt beim Anlegen die beiden älteren
  als Hinweis. Ein Verfahren, das diesen belegten Fall nicht findet, ist nicht
  gebaut.
- **Linie D:** Zwei Abrufzahlen desselben Standes sind wieder zuordenbar — je
  mit Codestand, Korpus, Pfad und gleichzeitiger Last.
- **Übergreifend:** Jede erledigte Aufgabe trägt einen Beleg, der vorher rot
  war. Ohne den bleibt sie offen, mit einem Vermerk was fehlt.

## Aufträge, fertig zum Übergeben

**Für alle Aufträge gleichermaßen gilt:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis` — ein
Startverzeichnis unter `.claude/worktrees/` ist ein alter Stand. Zuerst
`CLAUDE.md` lesen, dann diesen Plan. „Sieht der Code anders aus als hier
beschrieben, halte dich an den Code und melde die Abweichung." Kein `git add
-A`, kein Push, kein `git stash`. Committen mit expliziter Pfadliste
(`git commit -- pfad1 pfad2`), weil mehrere Agenten im selben Baum arbeiten.
Volle Suite im Vordergrund mit `timeout=600000` (rund 280 s). Schreibende Läufe
nie parallel zu einem Suitelauf. Datenbanknamen über `kern/speicher`.

### Schritt 0 · „brainlehr sagt" maschinell prüfbar machen (Aufgabe 94)

| | |
|---|---|
| **Darf ändern** | `haken/knowledge_recall_hook.py` (nur die Ausgabeform des Blocks), ein neuer Melder unter `melder/`, dazu Tests |
| **Tabu zusätzlich** | `haken/antwort_abruf.py` **inhaltlich** — der Melder wird von dort nur **aufgerufen**, wie es die Existenzprüfung heute früh vorgemacht hat; `knowledge_mcp_server.py`, `schema.sql` |
| **Fakten** | Der Abruf-Haken ist verdrahtet und liefert bei jedem Prompt (`knowledge_recall_hook`, 53 Nennungen, Eintrag vorhanden). `antwort_abruf.py --stop` läuft belegt 719-mal und liest die letzte eigene Antwort. Der Anlassfall: Knoten `/brainlehr/das-einbettungsmodell-trennt-auf`, Zahlen 0,531 gegen 0,527, ohne Zuschreibung weitergegeben. |
| **Abnahme** | Rot vor grün an genau diesem Fall: Eine Antwort, die eine kennzeichnende Zahl aus dem eingespielten Block trägt und den Speicher **nicht** nennt, wird gemeldet — vorher nicht. Negativfall, und er ist der wichtigere: Eine Antwort, die den Speicher **nennt**, wird nicht gemeldet; und eine Antwort ohne jeden Bezug zum Block ebenfalls nicht. Ein Melder, der bei jeder Antwort anschlägt, wird nach dem dritten Mal überlesen. Grenzwert: ein Begriff, der **zufällig** in beiden vorkommt (etwa „Speicher"), darf nicht auslösen — gekennzeichnet wird an seltenen Begriffen, nicht an häufigen. |

### Schritt A1 · Kantenberechnung wieder auslösen (Aufgabe 81)

| | |
|---|---|
| **Darf ändern** | `kern/kanten_aus_bedeutung.py` (nur der Auslöser-Teil), ein neuer Melder unter `melder/`, deren Tests |
| **Tabu zusätzlich** | `knowledge_mcp_server.py`, `schema.sql`, `kern/ausschreibekatalog.py`, `kern/anfrage_erweiterung.py` |
| **Fakten** | Jüngste Kante 2026-08-09T12:54:59. Am 12.08. 0 von 36 neuen Knoten mit Kante, am 13.08. 0 von 2. 307 von 2166 ohne jede Kante. Voller Trockenlauf mit numpy 0,234 s. Schwelle 0,65 stammt aus der Messung vom 2026-08-08 und bleibt unangetastet. |
| **Abnahme** | Der Melder schlägt **gegen den heutigen Bestand** an (jüngste Kante älter als jüngster Knoten) und schweigt nach dem Nachlauf. Negativfall: vollständig verbundener Bestand meldet nichts. Und die drei Achsen-Knoten (`dd367fd1`, `b6305304`, `6e0f0395`) sind danach untereinander verbunden — eine Berechnung, die diesen belegten Fall nicht findet, ist nicht gebaut. |

### Schritt A2 · Melder gegen auslöserlose Mechanismen (Aufgabe 85)

| | |
|---|---|
| **Darf ändern** | ein neuer Melder unter `melder/`, dazu sein Test |
| **Tabu zusätzlich** | beide `settings.json` — der Melder **liest** sie, er ändert nichts |
| **Fakten** | 8 von 15 Meldern und 3 von 12 Haken ohne Eintrag in einer Regelablage. `knowledge_recall_hook` ist nachweislich verdrahtet (53 Nennungen, Eintrag vorhanden) und dient als Negativfall. Vorbild ist die Stiftshütten-Regel „Agent ohne Trigger in 5+ Sessions → Sunset-Kandidat". |
| **Abnahme** | Findet die bekannten Fälle. Meldet `knowledge_recall_hook` **nicht**. Grenzwert: ein Mechanismus, der nur über ein anderes verdrahtetes Skript läuft, gilt **nicht** als unverdrahtet — genau diese Unterscheidung fehlt meiner Vormessung, und ohne sie wird der Melder nach dem dritten Fehlalarm ignoriert. Kein Veto, nur Hinweis. „Abschaltkandidat" ist eine gleichwertige Antwort zu „verdrahten". |

### Schritt B0 · Metaphernwirkung messen (Aufgabe 86)

| | |
|---|---|
| **Darf ändern** | eine neue Datei unter `messungen/` für die Regelpaare und Fallmengen, das Messskript, die Ergebnisdatei unter `runs/`, dazu Tests |
| **Tabu zusätzlich** | jede bestehende Regel, jeder Agentenauftrag, `~/.claude/` — **es wird nichts umbenannt**, es wird gemessen |
| **Fakten** | Personas verbessern die Genauigkeit nicht (162 Rollen, 2410 Fragen, 4 Modellfamilien, EMNLP Findings 2024). Metaphern wirken kausal als Brücke zwischen Domänen (13,5 % → 45,0 % bei Lyrik im Vortraining; 47,1 % → 28,8 % beim Maskieren; Zufallsmaskierung als Kontrolle fast wirkungslos — Hu et al. 2026). **Die zweite Arbeit misst Trainingsdaten, nicht Prompts** — diese Lücke ist der Messgegenstand. Eigene Vorerfahrung `L-5c7f86`: Eine Persona-Runde lieferte Verdachtsmomente, keine Befunde — von den lautesten Meldungen hielt **keine einzige** in der gemeldeten Form; die vier echten Fehler kamen aus der Nachprüfung. |
| **Abnahme** | Reichweite (Menge 2) **und** Fehlanwendung (Menge 3) stehen getrennt als Zahl mit Nenner. Die Negativkontrolle mit **unpassender** Metapher trennt messbar — sonst ist der Aufbau untauglich, unabhängig vom Ergebnis. Bewertung blind gegen die Fassung, nachweisbar. Zwischen Befund und Folgerung liegt eine **Prüfstufe**, die je Meldung zwei Ursachen zur Wahl stellt (echte Wirkung / Artefakt des Aufbaus) — ohne diese Alternative sucht der Prüfer nur Bestätigung. Ein Nullergebnis ist ein Ergebnis. |

### Schritt B1 · Zeit als Filter (Aufgabe 88)

| | |
|---|---|
| **Darf ändern** | den Abrufpfad an der Stelle der Kandidatenauswahl, dessen Tests |
| **Tabu zusätzlich** | `kern/build_embeddings.py`, `kern/embeddings.py` — der Einbettungstext wird **nicht** angefasst |
| **Fakten** | `created_at`/`updated_at` bei 2166 von 2166. `gilt_ab` 83, `gilt_bis` 2. Der Vektor enthält keine Metadaten (`node_text` = path+title+summary+content). |
| **Abnahme** | Anfrage mit Zeitraum liefert vorher dieselbe Menge wie ohne, nachher eine echte Teilmenge — an einem Fall, bei dem die Zeit den Ausschlag gibt. Negativfall: ein alles umfassender Zeitraum ändert nichts. Grenzwert: je ein Knoten genau am Rand, davor, danach. |
