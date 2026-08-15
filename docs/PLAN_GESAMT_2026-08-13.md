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

## Fortschreibung 2026-08-15T13:30:00+0200 — Abgleich Melder gegen Bestand, mit Gegenrichtung

Vollstaendiges Ergebnis: `runs/planabgleich_2026-08-15T133000+0200.json`. Verfahren:
jeder Melder-Kandidat (`python3 melder/plan_bestandsabgleich.py`, 27 Treffer) am
genannten Commit gegen sein eigenes im Plan formulierte Erfolgskriterium
geprueft (Test, DB-Abfrage) — dazu die Gegenrichtung: jede Plan-Zeile OHNE
Melder-Treffer geprueft, ob sie trotzdem erledigt ist. **35 von 58 geprueften
Zeilen erledigt, 10 teilweise, 13 offen.**

**Gegenprobe (zwei von 27 Melder-Kandidaten bestehen NICHT):**
- **`73` bleibt teilweise, nicht erledigt.** Vorwaerts- und Rueckwaertsmechanismus
  (`46d96bc3`, `kern/kanten_herkunft_rueckwirkend.py`) sind gebaut und isoliert
  getestet — am ECHTEN Bestand (2214 Knoten) aber **0 Kanten** vom Typ
  `abgeleitet_von`, Soll war laut `PLAN_HERKUNFTSKETTE_2026-08-13.md` mindestens
  125. Die Spalte `abgeleitet_von` sollte danach **weg** sein — steht weiterhin
  in `schema.sql:151` und wird in `kern/herkunft_belegung.py` aktiv gelesen.
- **`79` bleibt teilweise, nicht erledigt.** `speicher.normiere_modell()`/
  `normiere_akteur()` existieren (`88aaf738`) — werden aber **nirgends im
  Schreibpfad** aufgerufen (`knowledge_mcp_server.py`: 0 Treffer). Einziger
  Aufrufer ist `herkunft_belegung.py`, dort nur zur Leer-Erkennung. Jeder neue
  Knoten traegt weiter beliebige Modellschreibweisen.

**Ein dritter Fall, den der Melder gar nicht fand:** `97` (PreToolUse-Wache
gegen die eigene Hypothese im Agentenauftrag) — `haken/auftragshypothese_waechter.py`
und Tests existieren, `.claude/settings.json` traegt im `PreToolUse`-Block aber
nur einen Matcher fuer `Bash`, keinen fuer das Agent-Werkzeug. Der Waechter
feuert in keiner echten Sitzung. Bleibt **teilweise**.

**Schritt-2-Funde (erledigt, ohne dass Melder oder Plantext das bisher
auswiesen):** `42`, `68`, `71` (Linie D — im Plantext bislang nur als offene
Liste gefuehrt, tatsaechlich alle drei mit rot-vor-gruen belegt) · `76`, `89`
(Linie B — keine erledigt-Markierung im Text, kein Melder-Treffer, beide mit
Tests am echten Bestand belegt) · `86` Schritt 2 (Melder fand nur die Vorarbeit
`386bbf2b`, nicht die eigentliche Abnahme-Messung `c2752801` mit getrennter
Reichweite/Fehlanwendung und Negativkontrolle).

**Damit fuer Linie C, D, B der aktualisierte Stand:** Linie C `73`/`79`
**bleiben offen** wie in `STAND.md` behauptet — die Melder-Vermutung war hier
falsch. Linie D ist **vollstaendig erledigt** (`42`, `67`, `68`, `70`, `71`).
Linie B ist bis auf die weiter oben beschriebenen offenen Punkte (`77`/`78`
nicht Teil dieser Linie) ebenfalls durch — `75`, `76`, `86`, `88`, `89` alle
erledigt.

**Nicht nachgemessen** (Zeitgrenze dieses Laufs, nicht als offen zu lesen):
`82`, `83`, `87`, `23` (nur als Sammelnennung im Plan, keine eigene Definition
gefunden) · `G3`, `G6`, `F8` (Plan selbst erklaert sie als unzureichend
gemessen bzw. ungemessen, hier nicht erneut angefasst). **Echt offen, kein
Commit-Beleg gefunden:** `H2`–`H7`, `H12`, `I2`–`I4`, sowie `20`/`29`/`31`
(Linie E, wartet auf den Betreiber).

## Fortschreibung 2026-08-15T13:50:00+0200 — neun Wissenszeilen eingearbeitet, eine neue Kategorie

Auftrag des Betreibers: den Plan „wegen unserem neuen Wissen aktualisieren", VOR der
Abarbeitung. Diese Fortschreibung baut nichts, sie ordnet neun seit 13:30 Uhr entstandene
Befunde ein. Beleg je Zeile am Repo nachgesehen, nicht aus dem Auftrag übernommen — Ergebnis
in `runs/planfortschreibung_2026-08-15T1350+0200.json`.

**Zahl mit Nenner, unverändert gegenüber 13:30 (keine neue Zeile, nur Umsortierung):** 65
geführte Kennungen — 35 erledigt, 10 teilweise (davon 3 jetzt als „gebaut, aber wirkungslos"
gekennzeichnet, siehe unten), 13 offen, 7 nicht nachgemessen.

### Die neue Kategorie: gebaut, aber wirkungslos

Das ist die Fehlerklasse, die schon den ganzen Plan vom 13.08. trägt (zwölf Fälle, siehe oben)
— und sie trat seit 13:30 Uhr ein drittes Mal in dieser Fortschreibung selbst auf. Sie bekommt
deshalb einen eigenen Platz statt eine Fußnote unter „teilweise" zu bleiben:

| Kennung | Gebaut | Wirkungslos, weil |
|---|---|---|
| `73` | Vorwärts- und Rückwärtsmechanismus (`46d96bc3`, `kern/kanten_herkunft_rueckwirkend.py`), isoliert grün | am echten Bestand (2214 Knoten) **0** Kanten `abgeleitet_von` statt der geforderten ≥125; Spalte steht weiter in `schema.sql:151` |
| `79` | `speicher.normiere_modell()`/`normiere_akteur()` (`88aaf738`) | im Schreibpfad `knowledge_mcp_server.py` **0 Aufrufe** — jeder neue Knoten trägt weiter beliebige Modellschreibweisen |
| `97` | Peer-Review-Wächter + Tests (`028bd979`, 0/72 Fehlalarme) | `.claude/settings.json` `PreToolUse` hat nur einen Matcher für `Bash`, keinen für das Agent-Werkzeug — feuert in keiner echten Sitzung |

Alle drei bleiben **teilweise**, nicht offen — der Code existiert und ist geprüft, nur die
Wirkung fehlt. Die Unterscheidung ist nicht kosmetisch: „offen" heißt „noch zu bauen", diese
drei sind fertig gebaut und brauchen nur den fehlenden Anschluss (Rückwärtslauf am echten
Bestand fahren, Aufrufstelle ergänzen, `PreToolUse`-Matcher erweitern) — der billigere
nächste Schritt als ein Neubau.

### Die neun Wissenszeilen, einzeln geprüft

1. **„Gebaut, wirkungslos" als eigene Kategorie** — eingearbeitet, siehe Tabelle oben.
2. **Sechs unbemerkt erledigte Zeilen (`42`,`68`,`71`,`76`,`89`,`86` Schritt 2)** — **nicht
   zutreffend als neue Arbeit**: Die Fortschreibung von 13:30 Uhr (Zeilen 166–214 dieser Datei)
   führt alle sechs bereits im Wortlaut als erledigt, mit Commit-Beleg. Nachgesehen statt
   übernommen: stimmt. Einzige Ergänzung hier — Linie D (`42`,`67`,`68`,`70`,`71`) unten in der
   Linienübersicht als **vollständig** markiert, was der Fließtext dort noch nicht tat.
3. **ADR-019 entschieden, ADR-020 Schritt 1 gebaut, ADR-021 vorbereitet** — geprüft, mit einer
   Abweichung vom Auftragstext: `docs/adr/ADR-019-drei-entscheidungen-vor-dem-ersten-dokument.md`
   trägt laut eigenem Korrekturvermerk **fünf**, nicht drei Entscheidungen (Dateiname bewusst
   unverändert als Adresse). `docs/adr/ADR-020-mcp-server-klient-des-dienstes.md` steht im Kopf
   weiter als „Status: Vorschlag — Entscheidung offen, nicht getroffen"; Schritt 1 (`03cce992`,
   echte Ausweisprüfung statt Origin-Header auf 7 von 9 POST-Pfaden) ist ein vorgezogener
   Härtungsschritt, **unabhängig davon**, ob die Grundsatzfrage je entschieden wird — Abschnitt 5
   der ADR selbst nennt ihn Voraussetzung, bevor überhaupt ein Werkzeug umzieht. Schritt 2 (12
   schreibende MCP-Werkzeuge auf Endpunkte) offen, Schritt 3 (13 lesende) hängt an einer nicht
   vorliegenden Zeitmessung des HTTP-Umwegs (ADR-020 Abschnitt 4). `docs/adr/ADR-021-eingabeweg-dokumentfenster.md`
   existiert. **Neue Kennungen `I5`/`I6` für ADR-020-Schritt-2/3 und `I7` für ADR-021 unten in
   Linie I ergänzt**, da sie bisher in keiner Linie geführt waren.
4. **Urheberschaft entschieden (`62ed1a2a`)** — geprüft, zutreffend. Der Knoten trägt genau den
   Titel „Urheberschaft ist das Herkunftsfeld am Baustein — und dasselbe Feld entscheidet die
   Trainingsfrage". Das Feld selbst ist noch nicht gebaut (`schema.sql` kennt keine Tabelle
   `bausteine` — konsistent mit ADR-019: „Tabellen `dokumente`/`bausteine` existieren nicht"),
   die **Sperre** ist trotzdem weg, weil die Entscheidung vor dem ersten Schreibvorgang fiel statt
   danach nachgezogen zu werden müssen. `I2` (Designvorrat, bisher „Sperre davor: kanonische
   Guide-Quelle ungeprüft") bleibt unverändert offen — das ist eine andere Sperre (Tokendatei), von
   dieser Entscheidung nicht berührt.
5. **Homepage nach hinten verschoben (`9a27a332`)** — geprüft, zutreffend, Knotentitel bestätigt.
   Die rund 51 Zeilen `register_post_meta` stehen nicht in dieser Plandatei (keine Fundstelle
   hier), sie fallen also nirgends aus **dieser** Reihenfolge heraus — nur zur Kenntnis, falls ein
   anderer Plan sie führt.
6. **Textregeln als Domänenpaket 0, Bilderzeugung existiert längst (`cbd79aaa`)** — geprüft,
   zutreffend, Knoteninhalt vollständig gelesen: 0 Treffer bei 13563 Dateien für
   Domänenpaket-Textregeln, `voice_und_tone`/`zielgruppen` tot in `aka-design-guide.json`,
   `ai_image_forge.py` (1322 Zeilen, `openlehr/begod/scripts/`) ruft Gemini/Imagen mit befülltem
   Profil. Trennlinie Diagramm (Tokens als `fundstelle` belegbar, Belegvertrag passt unverändert)
   gegen Foto (Bildsprache, `image_style_anchor`-Muster passt, hat mit Tokens nichts zu tun) steht
   **im selben Knoten**, nicht gesondert entschieden. **Neue Zeile `I8`** unten ergänzt: Diagramm-
   Erzeugung über den Belegvertrag, getrennt vom Foto-Pfad.
7. **Abruf wirkt in 11,1 % (`f4ebc128`), zwei neue Melder nicht verdrahtet** — geprüft,
   zutreffend. `melder/abrufwirkung.py` und `melder/agentendauer.py` existieren, kein Treffer in
   `.claude/settings.json` für beide Namen. Reiht sich in dieselbe Kategorie wie Punkt 1 ein —
   hier nicht als eigene Zeile geführt, weil noch nicht einmal am eigenen Bestand geprüft, nur als
   „gebaut, ungeprüft ob wirksam".
8. **Sechs Selbstlauf-Blindgänger entschieden (`d6ab2505`)** — Knoten-ID selbst nicht per
   Präfixsuche in der DB gefunden (könnte eine andere Kennung tragen), die **Wirkung** aber am
   Code bestätigt: `melder/wirkkette.py` führt wörtlich eine „STUFE 2, RUBRIK ‚bewusst nur für
   Menschen'" mit Verweis auf „Aufgabe wirkkette-6-widerspruch, 2026-08-15". Als eingearbeitet
   gewertet, mit dieser Einschränkung offen benannt statt verschwiegen.
9. **Prüfer gegen nackte Zahlen (Bauform wie `normbezug.py`/`existenzpruefung.py`)** —
   **als offene Frage aufgenommen, NICHT als Zeile**, siehe unten. Weder Datei noch Knoten dazu
   gefunden — passt zum Auftragstext „Entscheidung steht aus".

### Neue offene Frage, keine Zeile, keine Entscheidung

**Soll ein Prüfer am Haltepunkt nackte Zahlen über zählbare Dinge in der eigenen Antwort
beanstanden** (Bauform wie `normbezug.py`/`existenzpruefung.py` — Regel gegen unbelegte
Existenzaussagen, hier gegen unbelegte Zahlen)? Der Betreiber hat das angeregt, nicht
entschieden. Bewusst **nicht** als Zeile `Kxx` eingetragen, weil eine Zeile „geplant, zu bauen"
bedeutet — diese Frage ist noch nicht einmal das.

### Wo die Reihenfolge bindend ist — ein konkreter Fall aus dem neuen Wissen

**ADR-020 Schritt 1 vor Schritt 2, wörtlich in Abschnitt 5 der ADR selbst begründet:** Die
Ausweisprüfung (`03cce992`) musste vor jedem Umzug eines MCP-Werkzeugs auf einen Dienst-Endpunkt
stehen, weil die bisherige Origin-Prüfung ausschließlich Browser bindet — ein MCP-Klient (reiner
Python-Aufruf) kann jeden Origin-Header selbst setzen. Würde `I5` (Schritt 2, Werkzeuge
umziehen) vor dieser Härtung gebaut, öffnete der Umbau selbst die Lücke, die G5 schließen sollte,
nur an einer neuen Stelle — derselbe Fehler wie bei `78` vor `73` (beide ändern
`knowledge_add`) oder `98` vor `92`/`96`/`97`. Schritt 1 ist bereits erledigt; **`I5` darf jetzt
erst beauftragt werden, `I6` (13 lesende Werkzeuge) erst nach einer Zeitmessung des
HTTP-Umwegs (ADR-020 Abschnitt 4) — diese Messung ist die Vorbedingung von `I6`, nicht von
`I5`.**

### Was bewusst nicht in diese Fortschreibung aufgenommen wird, samt Preis

- **Punkt 8 (Selbstlauf-Blindgänger) nicht mit eigener Knoten-ID zitiert**, obwohl der Auftrag
  sie nennt — die Suche in der Datenbank fand `d6ab2505` nicht. Preis: eine Zeile bleibt am
  Code statt am Wissenseintrag belegt. Vorzug vor der Alternative (Zahl ungeprüft übernehmen):
  eine falsche Kennung wäre eine neue unbelegte Existenzaussage, genau die Fehlerklasse, die
  dieser Plan selbst mehrfach kritisiert.
- **`I5`/`I6`/`I7`/`I8` als reine Kennungen ergänzt, nicht als vollständig ausformulierte
  Aufträge.** Die „Aufträge, fertig zum Übergeben" weiter unten bleiben unverändert — ein
  Auftrag zu `I5` bräuchte eine eigene Dateiliste (welche der 12 Werkzeuge zuerst) und ist damit
  mehr als eine Fortschreibung leisten soll. Preis: Wer `I5` als nächstes bauen will, formuliert
  den Auftrag noch selbst.
- **Keine neue Schätzung für `H2`–`H7`.** Das neue Wissen berührt Linie H nicht; sie bleibt mit
  dem Stand aus der 13:30-Fortschreibung offen.

## Die fünf Linien, in bindender Reihenfolge

**Linie A — Wirksamkeit vor allem anderen.** Solange Mechanismen nicht feuern,
ist jede weitere Messung eine Aussage über etwas, das niemand benutzt.
`81` (Kanten wieder rechnen — entsperrt, `83` und `87` sind erledigt) ·
`85` (Melder gegen auslöserlose Mechanismen) · `84` (Vorschlagsbericht
verdrahten, mit Neuheitsfilter).

**Linie B — die fehlenden Achsen.** `88` (Zeit als Filter; Geltung erst nach der
Vorfrage, wer `gilt_bis` setzt) · `89` (Kanalwahl an die Anfragelänge binden) ·
`76` (jede Kante trägt ihre Hinsicht) · `75` (W-Fragen — **Achtung, das Kürzel
war zweideutig und hat am 2026-08-15 einen Agentenlauf gekostet:** gemeint ist
ADR-005 *„vier W-Fragen, nur eine bekommt ein Feld"*, also die
**Qualitätsfragen am Knoten** (woran erkennt man falsch, wie sicher, …) samt
Spalte `herkunftsart` — **nicht** Fragewörter in Nutzernachrichten. Diese
zweite Lesart wurde gemessen und ist ein Nullbefund: von 35 lösbaren
Korpusfällen steht **keiner** in Frageform, alle 5 Fragefälle liegen in der
negativen Klasse. Struktur über 1730 echte Nutzertexte: 609 Fragen, 1121
Aufträge; Fragen nennen seltener einen Pfad (8,7 % gegen 14,2 %) und seltener
eine Kennung (0,2 % gegen 2,1 %) — die Kandidatenbildung hängt an der
fehlenden **Adresse**, nicht an der Frageform) · **`86` (trägt eine
metaphorisch benannte Regel weiter als eine wörtliche?).**

`86` steht hier und nicht in einer eigenen Ecke, weil es dieselbe Frage ist wie
die übrigen vier: **woran hängt eine Aussage außer an ihrem Wortlaut?** Bei `88`
ist es die Zeit, bei `89` die Sprache, bei `76` die Hinsicht — bei `86` das
Bild. Die Sperre gilt auch dort: Vor der Messung wird keine Regel umbenannt,
sonst wäre die Umbenennung ihre eigene Begründung.

**Linie C — der Speicher schreibt mit.** `78` (Dublettenerkennung beim Anlegen)
→ `73` (Herkunftskette; **dieselbe Funktion**, deshalb streng danach) ·
`79` (Herkunftsfelder normalisieren, kein neues Feld). **Stand 2026-08-15T13:50:
beide gebaut, beide wirkungslos** (siehe Fortschreibung oben) — `73` schreibt 0
Kanten am echten Bestand statt ≥125, `79` wird im Schreibpfad nie aufgerufen.
Bleiben **teilweise**, nächster Schritt ist der fehlende Anschluss, kein Neubau.

**Linie D — Messbarkeit wiederherstellen — vollständig erledigt (Stand
2026-08-15T13:30).** `71` (die nicht zuordenbare Differenz 45 gegen 33, gelöst
als Kategorienfehler, `06169cee`) · `68` (Prüfkorpus deterministisch, `c37e8161`)
→ `67` (`51f1912e`) → `42` (Okkultation mit Vollerhebung, `f318479f`). Alle vier
mit rot-vor-grün belegt, siehe Fortschreibung 13:30 oben.

**Linie E — nur der Betreiber.** `20`, `23`, `29`, `31`. Nicht autonom, in
keiner Reihenfolge erzwingbar.

**Linie F — das Dokumentfenster.** Nachgetragen 2026-08-14. Ausführung in
`docs/PLAN_DOKUMENTDIENST_2026-08-14.md`, Rahmen in `docs/adr/ADR-010`.
`F1` Teilnehmerkennung (Auflage unter 2³²) · `F2` Dienst mit einem Raum ·
`F3` Ablage, der Stand überlebt den Neustart · `F4` Anmerkungen im **selben**
Dokument wie die Bausteine · `F5` Fenster im atelier.
**F1–F4 sind erledigt** (`5266ca7`, `f00fff3`, `eb71e92`, `662748e`, `cf4cc28`).

**Nachgetragen 2026-08-14T21:36:26+0200 — was F5 NICHT ist.** Gemessen statt aus
dem Plan zitiert: Der Text lebt wirklich im CRDT (`yswift` fest auf 0.2.1,
kleinste Änderung statt Vollersatz), belegt durch
`test_zwei_teilnehmer_tippen_gleichzeitig`. **Zwei Lücken, beide im Code
sichtbar:** die Anmerkungsspalte fehlt (ausdrücklich, Begründung im Dateikopf),
und **das Modell hat noch nie danebengesessen** — „modell" kommt in
`kern/dokument.py` nur als Wert in einem Selbsttest vor. Der grüne Test belegt
„mehrere gleichzeitig", nicht „Mensch und Modell am selben Dokument".

**Und die größere Lücke, vom Betreiber benannt:** Das Fenster zeigt **Text**,
nicht das Erzeugnis. Das Ziel war von Anfang an *„links das fertige Dokument,
live bearbeitet"*.

`F6` **Zwei Geschwindigkeiten statt einer Wahl.** Gemessen: ein voller Satzlauf
dauert **1,1 s** (kalt 1,20 s, warm 1,12 s, mit PDF/A-3 und UA). Zum Tippen ist
das zu langsam, zum Nachziehen genau richtig. Also **beides**: eine schnelle
eigene Darstellung, in der wirklich getippt wird, und rund eine Sekunde später
das gesetzte Blatt als Wahrheit. Rechts der Baustein-Baum als zweite Ansicht —
Rechnungspositionen, Gliederung, Sprungziele.
**Der Einwand gegen eine eigene Darstellung (sie driftet vom Erzeugnis ab) ist
zurückgezogen und in eine Auflage verwandelt:** Wir besitzen beide Seiten, beide
entstehen aus demselben Baum — also prüft ein Wächter sie gegeneinander und
fällt, sobald die Darstellung etwas zeigt, was im Blatt nicht steht. Drift wird
damit messbar statt schleichend.
`F6a` **Satzweg Baustein-Baum → LaTeX** (`kern/satz.py`). **Gebaut; seine Probe
lief bis 2026-08-15T06:20:00+0200 nie und war rot** — das Modul stand nicht in
der Selbsttestliste, und die Maskierungsprobe fragte je Sonderzeichen
„kommt roh nicht vor", was nach dem Maskieren nicht halten kann (`\#` enthält
`#`). Beides behoben (`a864845`), Zählprobe 90 → 91. Der Satzweg selbst war
korrekt; ungeprüft war er trotzdem. Ursprünglich: **Fehlte vollständig** —
der Spike `spikes/pdf_a3_erechnung/` setzt eine handgeschriebene Datei. Ohne
diesen Weg gibt es weder Darstellung noch Blatt noch Vergleich. Enthält die
Maskierung fremden Texts: ein eingelesener Beleg trifft hier auf einen Satzlauf.
`F7` Anmerkungen im Bild, verankert am **Baustein**, nicht an einer
Bildschirmposition — deshalb überleben sie den Neusatz.
`F8` Rückweg vom Blatt in den Text (SyncTeX). **Nicht gemessen:** ob SyncTeX mit
`\DocumentMetadata` zusammenarbeitet — dieselbe Zutat hat heute schon tex4ht
gebrochen.

**Linie G — Sicherheit und Überwachung.** Nachgetragen 2026-08-14 auf
Betreiberwunsch, Ausführung in `docs/PLAN_SICHERHEIT_2026-08-14.md`.
`G1` Kennzahlen verlassen den Prozess · `G2` Melder, nur die schwellenfreie
Klasse · `G3` Nullmessung mit dem Mini, **danach erst** Schwellen.
Die Schranken selbst stehen bereits (`14b34f3`): Ausweispflicht außerhalb von
`127.0.0.1`, Nachrichtengröße, Rate, geschlossenes Protokoll.

**Stand 2026-08-15 — erledigt und geprüft:** `G1` (`72f2b2b`, Kennzahlen
überleben den Neustart, `kern/dokumentdienst.Kennzahlen`) · `G2`
(`50518c5`, `melder/dienstwache.py`, in `~/.claude/settings.json` als
SessionStart-Hook verdrahtet, in `MODULE`/`tests/test_alle_selftests.py`).
**Offen:** `G3`. Eine Vormessung liegt vor (`5b86ee4`,
`runs/nullmessung_dokumentdienst_2026-08-14.json`), erklärt darin aber
selbst als unzureichend — 180 s statt einer Stunde, ohne den Mini, nur
loopback. Ohne diesen Aufbau bleibt eine Schwelle geraten; die eigentliche
Messung braucht den Mini im LAN und eine Stunde echten Tippbetriebs und
konnte in dieser Sitzung nicht nachgeholt werden.

**Linie H — openlehr als erste Instanz.** Nachgetragen 2026-08-14 auf
Betreiberauftrag (*„zuerst openlehr integrieren"*), Ausführung in
`docs/PLAN_OPENLEHR_2026-08-14.md`.
`H1` Belegvertrag wird brainlehr-Kern · `H2` `classifier.py` an den Vertrag ·
`H3` Naht `ingest.py`/`api.py` schließen · `H4` Prüfkorpus mit bekanntem
Sollergebnis (Kriterium für „100 % richtig", F24 angenommen) · `H5`
Bestandsaufnahme als E2E-Journey vor den Bildschirmen.
Bindend: `H1` vor `H2` und `H3`. Gemessene Grundlage: 128 Dateien / 43 237
Zeilen unter `apps/openlehr/daemon/steuer/`, **0 tote Module** — Altlast ist
hier nicht als toter Code zu haben, die Trennung läuft über Belegbarkeit.

**Stand 2026-08-15T00:20:00+0200 — erledigt:** `H1` (`kern/belegvertrag.py`) ·
`H8a`/`H8b`/`H8c` (Domänen-Import, Menüpunkt im atelier, erstes echtes Paket) ·
`H11` (PDF/A-3 und PDF/UA gehen zusammen, selbst nachgemessen). `H12` neu
gefasst: **Blaupause statt Herauslösung**, kein `git filter-repo`, kein
`_legacy`. **Offen:** `H2` bis `H7`, `H10`.

**Linie I — die Anwendung selbst.** Nachgetragen 2026-08-15, entstanden aus
Betreiberfragen an einem Abend. Ausführung in den ADRs, nicht in einer eigenen
Plandatei.
`I1` **Kern / Bestandteil / Domäne** (ADR-014): Ins atelier gehört, was alle
Domänen gemeinsam haben oder was keine über sich selbst entscheiden darf.
Dokumentfenster und Tabellenkalkulation sind **Bestandteile**, keine
Kernbauteile — eine Domäne ohne Dokumente lädt keines. **Der Mechanismus für
anforderbare Bestandteile fehlt und ist zu bauen.**
`I2` **Designvorrat als Daten** (ADR-015), nach **Gattung** einstellbar, nicht
nach Domäne — und der Editor bietet nur an, was der Satz kann. Anschlussstelle
gemessen: der AKA-Design-Konsil hat Tokens bereits als Daten mit Erzeugern für
CSS/SCSS/Dart; uns fehlt ein vierter für LaTeX. **Sperre davor:** über zehn
Kopien der Guide-Datei, kanonische Quelle ungeprüft.
`I3` **Tabellenkalkulation** (ADR-016), Univer, Apache-2.0 an der Lizenzdatei
selbst nachgelesen. Vor dem Bau zu messen: läuft es eingebettet **ohne Netz**,
welches Gewicht, tragen die einzelnen Pakete dieselbe Lizenz wie die Wurzel.
`I4` **Bedingte Ausweise statt Verbote** (ADR-017): Rechte an die Identität,
nicht Verbote in den Code. **Offen und vor dem ersten eingeräumten Recht zu
prüfen:** ob es für Ausweise überhaupt einen Widerruf gibt.

**Ergänzt 2026-08-15T13:50:00+0200, aus ADR-019/020/021 (siehe Fortschreibung
oben) — bisher in keiner Linie geführt:**
`I5` **ADR-020 Schritt 2:** die 12 schreibenden MCP-Werkzeuge auf Endpunkte von
`berichte/entscheidungen_server.py` ziehen. **Bindend nach Schritt 1** (Ausweisprüfung,
bereits erledigt, `03cce992`) — Begründung siehe Reihenfolge-Abschnitt oben.
Grundsatzfrage der ADR selbst weiterhin „Vorschlag, nicht entschieden".
`I6` **ADR-020 Schritt 3:** die 13 lesenden Werkzeuge, **erst nach** einer
Zeitmessung des HTTP-Umwegs (ADR-020 Abschnitt 4, heute unbeziffert) — nicht vor,
nicht gleichzeitig mit `I5`.
`I7` **ADR-021** (Eingabeweg Dokumentfenster) — Rahmen steht, Ausführung nicht
geprüft in dieser Fortschreibung, keine eigene Aussage.
`I8` **Diagramm-Bilderzeugung über den Belegvertrag** (Knoten `cbd79aaa`):
Tokens sind als `fundstelle` belegbar wie ein Gesetzeszitat — der Belegvertrag
passt unverändert. **Ausdrücklich getrennt vom Foto-Pfad** (`ai_image_forge.py`,
bereits vorhanden in `openlehr/begod/scripts/`, Bildsprache statt Zahlenvergleich)
— beide „konsistente Bilder" zu nennen wäre der Denkfehler, den der Knoten
benennt.

**Linie G, fortgeschrieben 2026-08-15 — die Anwendung ist kein Betriebssystem.**
`codesign -dv` auf das gebaute Bündel: `adhoc`, kein `TeamIdentifier`, **kein
Entitlement-Block — die Sandbox ist nicht aktiv**. Damit sind Ausweis, Mandat
und Widerruf heute **Merkmale, keine Sperren**: sie liegen in Dateien, die
derselbe Benutzer schreiben darf, den sie einschränken sollen. Einzige wirksame
Grenze ist die kernel-erzwungene Bindung auf `127.0.0.1`.
`G4` **Die App gebiert den Dienst nicht mehr** — erledigt (`648432e`),
Prozessstart entfernt, `launchd`-Beschreibung in `dienst/`.
`G5` **Eigener Systembenutzer** für Bestand und Ausweisdatei (`0600`). Größter
Hebel, weil nicht der Ausweis das größte Merkmal ist, sondern **der Bestand**:
solange die Datenbank dem angemeldeten Benutzer gehört, überschreibt ein
einziger `sqlite3`-Aufruf jede Rolle und jeden Widerruf. **Braucht das Passwort
des Betreibers — ein Befehl, den er selbst ausführt.**
`G6` Signatur, Hardened Runtime, Sandbox. **Prüfstein vorher, ungemessen:** lädt
das CRDT-Rahmenwerk in einer Sandbox?
Fünf offene Sicherheitsfunde mit Fundstelle: `docs/SICHERHEITSFUNDE_2026-08-14.md`.
Schwerster: fremder Text aus der Datenbank landet roh per `innerHTML` in einer
Ansicht, die **gleichursprünglich mit der schreibenden Schnittstelle** läuft —
und genau dorthin soll `I3`.

**Linie J — Abgleich zwischen Soll und Wirklichkeit.** Nachgetragen
2026-08-15T10:05:00+0200. Entstanden nicht aus einem Plan, sondern aus einem
Fund: Auf der laufenden Homepage des Betreibers lag untergeschobener Schadcode
(`site-helper-793a1a8ec754`, angezeigt als „Debug Log Viewer Lite"), der
JavaScript aus einem Smart Contract nachlädt und per `new Function` ausführt.
**Gefunden wurde er als Nebenprodukt der Frage „läuft online derselbe Stand wie
im Repo?"** — die Bundle-Hashes wichen ab. Lehren `L-600726`, `L-ed0b73`.

**Der Befund für uns ist nicht der Schadcode, sondern die Blickrichtung:** Alle
16 Melder prüfen den Bestand gegen sich selbst — Datenbank gegen Schema, Code
gegen Code, Dokument gegen Dokument. **Keiner prüft das wirksame Artefakt gegen
seine Quelle.** Und brainlehr kennt diese Form bereits an drei Stellen, ohne sie
je als eine benannt zu haben: die installierte Triggerfassung gegen `schema.sql`
(steht wörtlich in `CLAUDE.md`), der verschwundene Haken-Eintrag (`L-083b95`),
die Arbeitsbaum-Kopien mit eigenem Stand (`L-c9d2aa`).

`J1` **Triggerabgleich.** `select sql from sqlite_master` gegen `schema.sql`.
Gemessen: 51 Trigger auf 30 Tabellen. Die vorhandenen Ratschen prüfen, dass die
gewollten da sind — **keine prüft, dass keine zusätzlichen da sind.**
`J2` **Haken- und Prozessabgleich.** Was ist in `settings.json` wirklich
verdrahtet, welcher Code läuft in den Prozessen — gegen das, was Commit und Plan
behaupten. Vorarbeit steht: `melder/ausloeserlos.py` (14 echte Funde),
`haken/mcp_veraltet.py`.
`J3` **Vollständigkeit statt Anwesenheit.** Jede Prüfung, die heute fragt „ist X
da?", bekommt die Gegenrichtung „ist etwas da, das nicht auf der Liste steht?".
Am 2026-08-15 hat genau diese Umkehrung `kern/satz.py` gefunden — mit
`--selftest` angelegt, nirgends aufgerufen, Probe seit Anlage rot.
`J4` **Herkunft als Pflichtfeld.** `abgeleitet_von` ist bei 2199 von 2200 Zeilen
leer, `bedient_von` bei allen 909 Lehren. Ein Eintrag ohne Herkunft ist von einem
untergeschobenen nicht unterscheidbar — nicht wegen eines Angreifers, sondern
weil die Unterscheidung im Datenmodell nicht existiert. **Vor `J4` steht die
Vorfrage, wer Herkunft setzen darf** — sonst wiederholt sich `L-34e5f8` (eine
Identitätsprüfung entwertete eine bestehende Sperre).

**Die Prüffrage, die aus demselben Fund kommt und in jeden Melder gehört:**
*Verhält sich das anders, wenn niemand zusieht?* Der Schadcode sparte `wp-admin`
aus — er versteckte sich vor dem Betreiber. `L-b3eb79` Stufe 2 beschreibt den
Spiegelfall: ein Haken an `UserPromptSubmit` ist im Selbstlauf blind, also genau
dann, wenn niemand zusieht. Dieselbe Achse, entgegengesetzte Richtung.

### Warum F und G — und nicht S1, S2, S3

Am 2026-08-14 wurden beide Pläne zunächst **neben** diesen Gesamtplan gelegt,
mit eigener Zählung ab 1. Ergebnis: `S1`, `S2` und `S3` bezeichneten je drei
verschiedene Dinge (`PLAN_DESTILLE`, `PLAN_DREITEILUNG`, `PLAN_SICHERHEIT`), und
die Frage des Betreibers *„wieviele S haben wir insgesamt?"* war nicht mehr
beantwortbar — 18 verschiedene S-Nummern über alle Dateien, 21 Sprints in
`docs/SPRINTS.md`.

**Eine Kennung braucht einen Raum, in dem sie eindeutig ist.** Fehlt er, ist der
Raum stillschweigend „diese Datei" — und das fällt erst auf, wenn jemand über
Dateien hinweg fragt, also genau beim Formulieren eines Auftrags. Der Prüfgriff
kostet Sekunden und gehört vor jeden neuen Plan:

```bash
for k in $(grep -rhoE '^(#+ *|\*\*)[A-Z][0-9]{1,3}\b' docs/*.md | grep -oE '[A-Z][0-9]{1,3}' | sort -u); do
  d=$(grep -rlE "^(#+ *|\*\*)$k\b" docs/*.md | wc -l); [ "$d" -gt 1 ] && echo "$k in $d Dateien definiert"
done
```

**Nur DEFINIERENDE Stellen zählen** — Überschrift oder Zeilenanfang. Die erste
Fassung dieses Griffs zählte jedes Vorkommen und meldete damit auch jeden
Verweis als Kollision: `F1` stand danach „in 3 Dateien", obwohl es genau einmal
definiert und zweimal zitiert ist. Ein Prüfgriff mit dieser Fehlalarmquote wird
weggeklickt und meldet dann auch den echten Fall nicht (`L-528f0c`).

Er hat sich beim Nachtragen dieser beiden Linien sofort bezahlt gemacht: `D` und
`E` waren bereits vergeben, der naheliegende Griff hätte die nächste Kollision
erzeugt. Lehre `L-30be01`.

**Was danach noch steht, vorbestehend und nicht aus dieser Arbeit:** `S1`, `S2`
und `S3` sind in `PLAN_DESTILLE_2026-08-09.md` **und** in
`PLAN_DREITEILUNG_2026-08-11.md` definiert. Nicht angefasst, weil beide Pläne
Historie tragen — aber wer dort etwas beauftragt, nennt die Datei mit.

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
- **Wirkung Null steht, BEVOR `kern/domaene.py` das erste Mal speichert**
  (ADR-018, Konsil vom 2026-08-14). Ein Domänenpaket muss wirkungslos ankommen
  und erst durch einen Willensakt eines Menschen wirksam werden — so wie
  `kern/regelpaket.py` es beim Import bereits tut (`norm_rang = NULL`). Der
  Grund ist die **Reihenfolge, nicht die Menge**: danach existiert Bestand ohne
  Rangdisziplin, und das gilt bei null Zeilen wie bei einer Million. Heute
  speichert `domaene.py` nichts — das Fenster schließt sich mit dem ersten
  Schreibvorgang.
- **Kein Bau an den beiden Dokumentausgaben, solange `H11`s Ablösung nicht
  belegt ist.** Der Weg ist gemessen, die Ablösung nicht: geprüft wurde mit
  einer Minimal-XML, nicht mit der echten Ausgabe aus openlehr. Wer vorher
  baut, schreibt die Wahrheit fest, die zufällig zuerst dran war.

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

> **ACHTUNG, 2026-08-15T09:30:00+0200 — dieser Abschnitt ist NICHT der Stand.**
> Die Aufträge zu `81`, `85` und `84` stehen hier im vollen Wortlaut, obwohl die
> Fortschreibung weiter oben (2026-08-13T13:00, „Linie A vollständig") sie als
> erledigt führt und beide Male recht hat: gebaut waren sie, nachgezogen war der
> Auftragstext nicht. Heute haben **zwei** Agenten je einen halben Arbeitszug
> darauf verwendet, das nachzumessen — und ich selbst habe dem Betreiber „Linie A
> ist offen" gesagt, weil ich diese Liste gelesen habe und die Fortschreibung 170
> Zeilen weiter oben nicht (dieselbe Form wie `L-813c8f`).
>
> **Regel daraus, für jeden künftigen Auftragsabschnitt:** Ein Auftrag verliert
> seinen Wortlaut, sobald er erledigt ist — er wird gestrichen oder trägt in
> Zeile 1 seinen Status. Ein vollständig ausformulierter Auftrag ist die
> stärkste Behauptung „hier ist noch etwas zu tun", die ein Dokument abgeben
> kann; steht sie neben einer Erledigt-Meldung, gewinnt sie beim Lesen.
>
> **Status der drei:** `81` erledigt (`1d55a42`, Melder-Fund darin behoben) ·
> `85` erledigt (`b3dfc6f`) · `84` erledigt (`38bebd9`). Die Auftragstexte bleiben
> als Beleg dessen stehen, was verlangt war — nicht als Arbeitsvorrat.

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

**Fortschreibung 2026-08-15 — A1 war bereits gebaut, ein Fund darin behoben:**
Auslöser (`haken/auszug_nachziehen.py` → `kern/kanten_aus_bedeutung.automatischer_lauf()`),
Wiring (`~/.claude/settings.json`, `Stop`-Hook, Zeile 352) und Melder
(`melder/kantenstillstand.py`) lagen bereits aus `5a4d65b` u.a. vor — der
Plan hier war nicht nachgezogen. Rot-vor-grün am echten Bestand (2026-08-15,
2202 Knoten): der Melder schlug an (jüngste Kante 2026-08-14T21:04:29Z <
jüngster Knoten 2026-08-15T03:57:45Z), der Nachlauf lief manuell fehlerfrei,
schrieb aber 0 Kanten — und der Melder blieb **trotzdem** rot. Ursache: reiner
Zeitvergleich kann „nie gelaufen" nicht von „gelaufen, kein Kandidat über der
Schwelle" unterscheiden. Fix in `melder/kantenstillstand.py`
(`fehlende_kandidaten()`): Zeitvergleich bleibt billiger Vorfilter, bei
Verdacht folgt ein Trockenlauf von `finde_kandidaten` nur über die
unverbundenen Knoten — meldet nur, wenn dabei wirklich ein Kandidat fehlt.
Selftest erweitert um genau diesen Gegenfall (A2). Die drei Achsen-Knoten
(`dd367fd1`, `b6305304`, `6e0f0395`) aus der ursprünglichen Abnahme sind am
heutigen Bestand **nicht** vollständig paarweise verbunden — gemessen:
dd367fd1↔b6305304 0,739 (verbunden), dd367fd1↔6e0f0395 0,621, b6305304↔6e0f0395
0,602, beide unter der unantastbaren Schwelle 0,65. Das ist kein Fehler des
Mechanismus, sondern eine Abnahme-Vorgabe, die die feste Schwelle bei diesem
Tripel nicht erfüllen kann — hier offen vermerkt statt verschwiegen.

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
