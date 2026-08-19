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
> **Widerlegt, siehe Fortschreibung 2026-08-15T14:05 unten:** Diese Aussage prüfte nur die
> repo-eigene `.claude/settings.json`. In `~/.claude/settings.json` steht der Matcher `Agent`
> bereits seit 2026-08-14T09:30 — `97` gilt als **erledigt** (`d786be7a`), nicht als wirkungslos.

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

**Zahl mit Nenner, gegenüber 13:30 um einen Fall korrigiert (siehe Nachtrag unten):** 65
geführte Kennungen — **36** erledigt, **9** teilweise (davon 2 als „gebaut, aber wirkungslos"
gekennzeichnet, siehe unten), 13 offen, 7 nicht nachgemessen.

> **Nachtrag 2026-08-15T14:05:00+0200 — die Ausgangsmessung hatte einen belegten blinden
> Fleck, hier nicht stillschweigend korrigiert.** `97` galt unten ursprünglich als „gebaut,
> wirkungslos", weil `.claude/settings.json` (die **repo-eigene**) keinen `PreToolUse`-Matcher
> für das Agent-Werkzeug trägt. Das ist richtig gemessen — aber unvollständig: Es gibt **zwei**
> Einstellungsdateien, und der Eintrag steht in `~/.claude/settings.json` (Matcher `Agent`,
> Zeile 278), seit einer Sicherung vom 2026-08-14T09:30 (Diff gegen `bak-2026-08-14T0010`
> bestätigt: dort fehlt er noch). Jetzt am Verhalten belegt, nicht nur an der Datei: Commit
> `d786be7a`, ein neuer Test führt den **exakten Kommandostring** aus `settings.json` aus (nicht
> nur das Modul direkt), rot-vor-grün am historischen Artefakt (die alte Sicherung ohne Eintrag
> hätte den Haken nie ausgelöst), Laufzeit 23,3 ms je Aufruf, 0 Fehlalarme bei 83 echten
> Aufträgen der heutigen Sitzung. **`97` gilt damit als erledigt**, nicht als wirkungslos —
> Korrektur unten in der Tabelle und in Linie A/Wellen-Übersicht (dort war `97` noch als offen
> geführt) nachvollzogen.
>
> **Der eigentliche Befund ist die Messmethode, nicht der Einzelfall.** `runs/planabgleich_
> 2026-08-15T133000+0200.json` — die Grundlage des gesamten Ausgangsstands dieser Datei — hat nur
> die repo-eigene `.claude/settings.json` gelesen. Dieselbe Verwechslung hat am selben Tag schon
> einmal einen roten Test erzeugt, nur umgekehrt (`b854d9c5`: eine Ratsche las nur
> `~/.claude/settings.json`, während die stash-Wache bewusst nur in der repo-eigenen steht). Jede
> **weitere** Verdrahtungsaussage in dieser Datei, die sich nur auf eine der beiden Dateien
> stützt, ist damit **verdächtig, nicht widerlegt** — das ist eine Prüfaufgabe, keine Korrektur,
> und steht deshalb als eigene Zeile unten, nicht als stiller Fix an jeder Fundstelle.

### Die neue Kategorie: gebaut, aber wirkungslos

Das ist die Fehlerklasse, die schon den ganzen Plan vom 13.08. trägt (zwölf Fälle, siehe oben)
— und sie trat seit 13:30 Uhr in dieser Fortschreibung selbst noch zweimal auf (ein dritter,
vermuteter Fall — `97` — hat sich laut Nachtrag oben als Messfehler herausgestellt, nicht als
Befund). Die verbleibenden zwei bekommen einen eigenen Platz statt eine Fußnote unter
„teilweise" zu bleiben:

| Kennung | Gebaut | Wirkungslos, weil |
|---|---|---|
| `73` | Vorwärts- und Rückwärtsmechanismus (`46d96bc3`, `kern/kanten_herkunft_rueckwirkend.py`), isoliert grün | am echten Bestand (2214 Knoten) **0** Kanten `abgeleitet_von` statt der geforderten ≥125; Spalte steht weiter in `schema.sql:151` |
| `79` | `speicher.normiere_modell()`/`normiere_akteur()` (`88aaf738`) | im Schreibpfad `knowledge_mcp_server.py` **0 Aufrufe** — jeder neue Knoten trägt weiter beliebige Modellschreibweisen |
| ~~`97`~~ | ~~Peer-Review-Wächter + Tests~~ | **entfällt, siehe Nachtrag oben — erledigt, nicht wirkungslos** (`d786be7a`) |

Beide verbleibenden bleiben **teilweise**, nicht offen — der Code existiert und ist geprüft, nur
die Wirkung fehlt. Die Unterscheidung ist nicht kosmetisch: „offen" heißt „noch zu bauen", diese
zwei sind fertig gebaut und brauchen nur den fehlenden Anschluss (Rückwärtslauf am echten
Bestand fahren, Aufrufstelle ergänzen) — der billigere nächste Schritt als ein Neubau.

### Neue Messaufgabe aus dem Nachtrag, kein Bau

`97` galt gemessen fälschlich als wirkungslos, weil nur eine von zwei Einstellungsdateien
gelesen wurde. **Jede Aussage in diesem Plan, die Verdrahtung behauptet oder verneint, ist gegen
BEIDE Dateien (`~/.claude/settings.json` und die repo-eigene `.claude/settings.json`) erneut zu
prüfen** — namentlich `98`, `92`, `96` und die Wellen-Tabelle unten, die alle von derselben
Ausgangsmessung abhängen. Das ist eine Messaufgabe, kein Bau, und wird hier nicht miterledigt.

**Offene Frage, kein Beschluss:** Der Wächter aus `97` hat bei 83 echten Aufträgen **null** Mal
gemeldet — und traf laut eigenem Testbefund einen Auftrag mit „Verdacht auf X" ohne das Wort
„liegt" nicht. Ist eine Regel ohne einen einzigen Treffer über 83 Fälle gut kalibriert oder zu
eng gefasst? Ungeklärt, nicht Gegenstand dieser Fortschreibung.

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
`I2` **Designvorrat als Daten** (ADR-015), nach **Dokumentart** einstellbar, nicht
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

**Ergänzt 2026-08-15T20:30:00+0200 — der Befund, den der Betreiber als Fehler eingestuft hat.**
`K1` **Die Verschmelzung gewichtet Rang statt Güte** (Knoten `d84b6b64`,
Ausführung in `docs/PLAN_KANALGUETE_2026-08-15.md`). Gemessen: eine deutsche
Anfrage findet 0 von 5 im englischsprachigen Bestand, dieselbe auf Englisch 5 von
5 — nicht wegen des Einbettungsmodells (das trifft Rang 1 von 2151) und nicht
wegen der Textmenge, sondern weil ein Kanal mit acht Trigramm-Zufallstreffern
seinem besten dasselbe Ranggewicht verleiht wie einer mit 773 guten.
**Der Betreiber dazu:** *„dann haben wir aber ein Fehler in unserem System!"* —
die erste Reaktion, weniger Daten zu laden, war der Umweg um einen Defekt.
**Zwei Schritte, getrennt messbar:** der Stichwortkanal trägt nur ganze Treffer
bei (nicht Wortfragmente) · ein Kanal ohne eigene Trennschärfe trägt kein volles
Ranggewicht.
**Erstmals messbar seit 2026-08-15T20:08:** GermanQuAD liegt im Bestand, 13.722
Fälle mit vorher bekanntem Label, davon 1.375 mit der Antwort nachweislich NICHT
im Bestand. Damit zerfällt die Trefferquote in drei Zahlen — gefunden, falsch
gemeldet, einsprachiger Normalfall. Die **Falschmeldequote hat dieses Haus noch
nie erhoben.**
**Bestandsstand:** 2217 → 4930 Knoten. Alle Zahlen vom Nachmittag (18 von 205,
8,78 %) gelten für 2217 und sind nicht vergleichbar.

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

---

## Fortschreibung 2026-08-18T21:45:00+0200 — Linie K: was nach dem Katalogtag offen bleibt

**Warum eine Linie und keine eigene Datei.** Der Abschnitt „Warum F und G — und
nicht S1, S2, S3" weiter oben verbietet genau das, und der dort mitgelieferte
Prüfgriff wurde vor dieser Fortschreibung gefahren. Ergebnis: **12 Kennungen
sind heute in mehreren Dateien definiert** (`B1`–`B6`, `F1`, `H12`, `S1`, `S2`,
`S3`, `S12`). Die Lehre hat sich also nicht durchgesetzt — das ist Aufgabe `110`
und der Grund, warum diese Fortschreibung Linie **K** heißt und bei Aufgabe
**99** beginnt: Linien A–J und Nummern bis 98 sind vergeben.

**Ausgangslage, gemessen am 2026-08-18T21:40.** Katalog: 24/56 belegt,
10 offen, 22 vertagt (`melder/gatestand.py`). Bestand: 5170 Knoten,
1095 Lehren, 9976 Ähnlichkeitskanten, **3** Ablösungskanten, 450
Ergebnisdateien unter `runs/`.

### K1 — die Messungen zu Ende bringen (blockiert alles Weitere an der Güte)

| Nr. | Aufgabe | Warum jetzt |
|---|---|---|
| `99` | **Bewertungskriterium der Wirkungsmessung schärfen.** Die Negativkontrolle scheiterte: 2 von 4 ziellosen Fällen galten als „vom Speicher verbessert". Der Wortabgleich mit Schwelle 0,4 schlägt bei allgemeinem Vokabular an. | Solange das Kriterium nicht trägt, ist **jede** Wirkungszahl ungültig — auch eine gute. |
| `100` | **Wirkungsmessung neu fahren**, mit `MAX_TOKENS=3000` (gemessen, `6f8fea8d`) und geschärftem Kriterium. Schließt `BDW-F05` und die Gateart *Aktion* aus `BDW-P04`. | Beide Gates hängen an genau diesem Lauf, an nichts sonst. |
| `101` | **LongMemEval-V2 mit fremdem Reader.** Der bisherige Lauf (16,7 %, n=18) war Reader *und* Richter in einem — nicht vergleichbar mit dem Weltstand 48,3 %. | Ohne fremden Reader misst jede Wiederholung dieselbe Vermischung. |

**Bindend:** `99` vor `100`. Ein neuer Lauf mit altem Kriterium erzeugt eine Zahl,
die niemand verwenden darf, und kostet 14 Minuten Modelllaufzeit.

### K2 — die zwei halben Gates ganz machen

| Nr. | Aufgabe | Stand |
|---|---|---|
| `102` | `BDW-E07`: Verschlüsselung erreicht **Index und Backup**, nicht nur die Daten. | TEILWEISE. Der Preis steht in ADR-029: verschlüsselte Inhalte sind nicht durchsuchbar — entweder ist ein Eintrag unter Frist nur über Metadaten auffindbar, oder der Index führt Klartext und ist selbst löschpflichtig. **Diese Frage ist zu entscheiden, bevor gebaut wird.** |
| `103` | `BDW-E13`: Fristlauf erreicht **Indizes, Caches und Kopien** des echten Bestands, nicht nur den Schlüsselspeicher. | TEILWEISE. Hängt an `102`. |

### K3 — die zwei großen Bündel

| Nr. | Aufgabe | Aufwand (gemessen, `runs/bestandsaufnahme_vier_buendel.json`) |
|---|---|---|
| `104` | **Gedächtnisarten** episodisch/semantisch/prozedural (`BDW-F01`–`F03`). | **groß.** `gattung` kennt zwei Werte, prozedural existiert nicht. Das Repo hat die Lücke selbst diagnostiziert (`docs/RESEARCH_ZIELBILD_2026-08-17.md:147`). Wie die Mandantenachse eine **Ablagefrage** — später teurer. |
| `105` | **Connectoren** mit Allowlist (`BDW-F08`, `U04`). | **groß.** Weder Prüfsumme noch Provenienz noch Registry; `kern/fremdimport.py` löst ein engeres Problem. |
| `106` | `BDW-E18`, `U01`, `U06` — Risikomatrix, Org-Grenze, Benachrichtigungsrouting. | `U01` ist in einem Ein-Nutzer-System **konzeptionell nicht baubar**; `kern/vertrauen.py` benennt das selbst. Kandidat für DEFERRED statt Bau. |

### K4 — der Bestand selbst, und hier steht die unangenehmste Zahl

| Nr. | Aufgabe | Zahl |
|---|---|---|
| `107` | **Gerichtete Kanten.** 9976 Ähnlichkeitskanten gegen **3** Ablösungskanten. Ähnlichkeit ist symmetrisch und hilft beim Finden; Abhängigkeit ist gerichtet und entscheidet über Gültigkeit. | 3 von 9979 |
| `108` | **144 Knoten und 158 Lehren mit veralteter Prüfsumme** — ihr Vektor beschreibt einen Text, den es so nicht mehr gibt. Die Suche liefert falsch, ohne dass ein Fehler auftaucht. | 302 Einträge |
| `109` | ~~Sechs stumme Spalten.~~ **Auf 3 zurückgemessen 2026-08-19.** Die vier `tokens_*`-Spalten waren ein Artefakt des Melders (voller Nenner über eine Historie, die sie nicht tragen konnte) — behoben in `melder/pruefer.py`. Echt bleiben `knowledge_nodes.abgeleitet_von` (1 von 5172), `lessons_learned.bedient_von` und `access_log.bedient_von` (je 0, keine Schreibstelle im Repo). | **3** statt 6 |
| ~~`110`~~ | ~~**12 Kennungskollisionen** in `docs/`.~~ **GESTRICHEN 2026-08-19, die Zahl haelt nicht.** Nachgemessen mit `melder/kennungskollision.py`: **0** echte Kollisionen, 4 spaetere Wiederaufgreifen (`S12`, `S1b`, `§4`, `B5`) -- und die sind gewollte Fortschreibung, kein Fehler. Siehe Fortschreibung 2026-08-19. | 0 statt 12 |
| `111` | **450 Ergebnisdateien**, davon 73 ohne Gegenprobe- und 74 ohne Rastervermerk. Eine Messung ohne festgehaltenes *was abgesucht wurde* ist nicht wiederholbar, nur wiederholbar von vorn. | 73 / 74 |

### Was bewusst NICHT in diese Linie kommt, samt Preis

**Die 22 vertagten Katalogzeilen.** Sie sind an den ersten Mehrbenutzer-Piloten
gebunden (`9d77ad16`, Rang 1). Sie hier aufzunehmen würde die Vertagung
unterlaufen. **Preis:** Wird Mandantenfähigkeit später bejaht, ist die
Mandantenachse ein Schema-Umbau in einem dann größeren Bestand — der einzige
der neun Punkte, bei dem Warten wirklich teurer wird.

**Die 9976 Ähnlichkeitskanten neu berechnen.** Sie sind dicht in der falschen
Dimension, aber sie schaden nicht. **Preis:** Der Graph bleibt symmetrisch.

**Ein weiterer Melder.** Es gibt genug; was fehlt, ist Wirkung. Aufgabe `109`
misst genau das an sechs Spalten, die keine Unterscheidung tragen.

### Woran sich Erfolg misst — drei Zahlen, keine davon „gebaute Module"

1. **Verhinderte Korrekturen** beim nächsten Rundruf. Heute 0 in vier Sitzungen.
2. **Gerichtete Kanten im Bestand.** Heute 3 gegen 9976 symmetrische.
3. **Belegte Katalogzeilen mit nachfahrbarem Prüfbefehl.** Heute 24 von 56,
   davon 22 vertagt — der ehrliche Nenner ist also 24 von 34.

---

## Fortschreibung 2026-08-19T05:50:00+0200 — `112`, und warum er nicht aus dieser Linie stammt

### `112` — die Nachrangung liegt fertig auf einem anderen Zweig

Eine parallele Sitzung hat am 2026-08-18 gemessen und gebaut, was hier als
Engpass geführt wurde. Geprüft, nicht übernommen (`git ls-tree` über alle
Zweige, Knoten `/brainlehr/nachrangung-bewegt-top5-von-17-auf-51`):

| | top5 |
|---|---|
| ohne Nachrangung (**dieser Zweig, heute**) | 6/35 = 17,1 % |
| Regel ohne Modell (Wortdeckung) | 6/35 — **bewegt nichts** |
| `gemma4:e4b`, ein Aufruf über 50 Kandidaten | 18/35 = 51,4 % |

Drei Commits (`798ef2ff`, `48fb98ca`, `04bd7f00`) auf **`brainlehr/atelier`**,
nicht auf `brainlehr/b4-ausweis`. Damit ist `112` keine Bau- und keine
Messaufgabe, sondern eine **Zusammenführung mit einer Vorgabeentscheidung**.

**Der Preis steht neben der Zahl, und er ist der eigentliche Inhalt der
Entscheidung:** Median **48,6 s je Anfrage**. Eine Suche im Abrufpfad einer
Sitzung wächst damit von unter einer Sekunde auf fast eine Minute. Deshalb ist
der Parameter dort **`nachrangung=False` in der Vorgabe** — die bessere Zahl
darf sich nicht als Voreinstellung hinter dem Rücken der Latenz einschalten.

**Was diese Linie daraus lernt, unabhängig vom Zusammenführen:** Die Nulllinie
ist der schärfere Befund, nicht die 51 %. Wortdeckung bewegt **nichts**. Hätte
die Regel dieselbe Verbesserung gebracht, wäre das Modell eine Abhängigkeit für
nichts gewesen — und danach nicht mehr zu entfernen, ohne dass jemand sie
verteidigt. Eine Nulllinie gehört in jede solche Messung als **erste** Frage.

### Was das für `100` bedeutet, und das ist eine Grenze, keine Nebensache

Aufgabe `100` misst, ob der Speicher einem Modell hilft. Ihre Zufuhr sind die
**Top-5** aus `knowledge_search` — auf diesem Zweig also eine Liste, die das
Ziel in **17 %** der Fälle enthält. Jede Aussage aus `100` gilt damit für die
**un-nachgerangte** Zufuhr. Ein Ergebnis „Speicher wirkt kaum" wäre unter
dieser Bedingung nicht widerlegt, aber auch nicht zugeschrieben: es könnte die
Zufuhr sein, nicht der Speicher. Dieselbe Fehlerklasse wie `L-08b79a` (dort
war es das Token-Budget) — eine **Grenze des Aufbaus**, die sich als Ergebnis
liest.

`100` wird trotzdem zuerst gefahren: sie ist die Nulllinie, gegen die ein
späterer Lauf mit Nachrangung überhaupt erst etwas zeigen kann.

**Bindend:** `112` (Zusammenführen) vor jedem *zweiten* Wirkungslauf. Ein
zweiter Lauf ohne Nachrangung misst dieselbe Zufuhr noch einmal.

### `110` gestrichen — die Zahl hielt nicht, und wie sie entstanden sein dürfte

Aufgabe `110` führte **12 Kennungskollisionen** in `docs/`. Für diese Zahl gibt
es im Repo **keine Ergebnisdatei und kein Skript** (`grep` über `docs/`: die
Zahl steht genau einmal, in der Aufgabenzeile selbst). Sie war nicht
nachrechenbar.

Nachgemessen am 2026-08-19 mit `melder/kennungskollision.py` (Selbsttest grün,
Gegenprobe in beide Richtungen):

```bash
python3 melder/kennungskollision.py
```

**0 echte Kollisionen. 4 spätere Wiederaufgreifen** — `S12` und `S1b`
(`PLAN_DESTILLE`), `§4` (`PLAN_WURZELORDNUNG`), `B5`
(`FORTSCHRITT_OPENLEHR_EINZELUNTERNEHMER`). Alle vier sind *derselbe*
Abschnitt, später fortgeschrieben („§4 gegengerechnet", „S12 ist kein
Forschungsschritt mehr"). Sie als Kollision zu zählen würde genau die
Arbeitsweise bestrafen, die dieses Haus verlangt: einen Abschnitt nach der
Messung fortzuschreiben statt ihn zu ersetzen.

**Der Fehler, den das Messskript selbst zuerst machte, ist der übertragbare
Teil.** Der erste Lauf meldete 6 Kollisionen — 5 davon erfunden. Ursache: in
`(S|P|G|K|B)\d+|B4\.\d+` nimmt Python die **erste** passende Alternative, nicht
die längste. `B4` schluckte das `B4.1`, und die sechs verschiedenen Abschnitte
`B4.1`–`B4.6` erschienen als sechs Vorkommen *einer* Kennung `B4`; ebenso
`104.1.1`–`104.1.3` als drei Vorkommen von `104.1`. **Wer eine hierarchische
Kennung mit `|` zerlegt, ordnet die längste Form zuerst — sonst misst er seine
Regex, nicht den Bestand.** Der Selbsttest hält genau diesen Fall fest.

Ob die ursprünglichen 12 aus demselben Fehler stammen, lässt sich **nicht**
sagen: es gibt kein Skript, das sie erzeugt hat. Genau das ist der Grund, warum
sie gestrichen und nicht bearbeitet wird.

**Was daraus für die übrigen Zahlen dieser Linie folgt:** `107` bis `111`
stammen aus laufenden Meldern und sind mit einem Befehl nachrechenbar. `110`
war die einzige Zeile ohne Prüfbefehl — und die einzige, die der Nachprüfung
nicht standhielt. Das ist kein Zufall, sondern dieselbe Regel wie beim
Phantom-Gate: eine Zahl ohne nachfahrbaren Befehl liest sich wie ein Befund
und ist keiner.

### `109` zurückgemessen — von sechs stummen Spalten bleiben drei

```bash
python3 melder/pruefer.py | grep stumme_spalte
```

**Vier der sechs waren ein Fehler des Melders, nicht des Bestands.**
`access_log.tokens_input` las sich als „19545 von 20069 (97 %) leer" und damit
als gebaute Regel ohne Wirkung. Die Spalte existiert erst seit
2026-08-18T12:21; **seit ihrer ersten Belegung sind es 1133 von 1669 (68 %)**.
Fünf Monate Historie gegen einen Tag Spalte. Behoben: der Nenner beginnt bei
der ersten Belegung (`MIN(rowid)`), nie befüllte Spalten behalten den vollen
Nenner. Rot-vor-grün und die Gegenprobe in beide Richtungen stehen im
Selbsttest (`_selftest_junge_spalte`).

**Die drei echten, und sie sind drei verschiedene Sachen — nicht eine Aufgabe:**

| Spalte | Lage | Was zu entscheiden ist |
|---|---|---|
| `knowledge_nodes.abgeleitet_von` | 1 von 5172. Hat Schreibstelle, **fünf** Lesestellen und einen Unveränderlichkeits-Trigger. | Die einzige echte *gebaute Regel ohne Wirkung*: der Weg ist vollständig da, die Aufrufer übergeben nichts. Verdrahten. |
| `lessons_learned.bedient_von` | 0 von 1096, **keine Schreibstelle** im ganzen Repo. | `schema.sql:636` benennt die Leere selbst, `knowledge_mcp_server.py:3094` sagt „was leer bleiben darf, bleibt leer". Verdrahten **oder** streichen — eine Entscheidung, kein Defekt. |
| `access_log.bedient_von` | 0 von 20089, **weder Schreib- noch Lesestelle**. | Dasselbe, eine Stufe schärfer: niemand fragt sie ab. |

**Die Gegenprobe, die den Unterschied trägt:** `knowledge_nodes.bedient_von`
ist **335 von 5172** belegt und war nie unter den Befunden. Der Einladungsweg
funktioniert also — die Spalte ist dort kein totes Feld, sondern eines, das nur
gefüllt wird, wenn wirklich eine Maschine geführt wird. Ohne diese Zahl daneben
läse sich „`bedient_von` ist leer" wie ein Bauversagen; mit ihr ist es eine
Aussage über den Weg, nicht über die Spalte.

**Die übertragbare Hälfte** steht als `L-412e20` im Speicher: Vor jeder
Anteilszahl über einen Bestand die Frage stellen — *seit wann kann dieser Wert
überhaupt vorkommen?* Ist die Antwort jünger als der Bestand, ist der volle
Nenner falsch. Ein Nenner ist die stillste Stelle einer Messung: er erzeugt
keinen Fehler, nur eine falsche Zahl, und die liest sich wie ein Befund.

---

## `100` gefahren 2026-08-19 — der Lauf hält, das **Kriterium** hält nicht

Messstand `20260819T053907-139e3687`, 28 Modellaufrufe, **904,6 s**, kein
Abbruch, `kein_ergebnis` 0/0 (das Token-Budget aus `99` trägt).
Ergebnisdatei: `runs/wirkung_llm_probe_2026-08-19T075426.json`.

Roh: `mit_speicher=2`, `ohne_speicher=0`, `n=10`.

**Diese Zahl darf niemand verwenden.** Zwei Kontrollen haben angeschlagen, und
beide zeigen auf die *Bewertung*, nicht auf den Speicher.

### 1. Die Positivkontrolle scheitert am Kriterium, nicht am System

Der Fall, dessen Ziel nachweislich auf Rang 1 der Zufuhr liegt
(`/ops/buckeberg-konsil-2026-07-22-governance`), wird mit `trifft_ziel=False`
gewertet — obwohl die Antwort **mit** Speicher den Kern des Zielknotens
wiedergibt: „Der ETV-Beschluss (Ziel Nov. 2026) steht vor dem Ranking", genau
die Aussage „Governance vor dem Ranking". Ohne Speicher kommt stattdessen eine
allgemeine Moderationsberatung („Parking-Lot-Methode").

Der Grund steht in `zielausschnitt()`: für einen Knoten ist der Zielausschnitt
**der Titel**. Das Kriterium fragt also, ob die Antwort ≥ 40 % der Wörter des
*Titels* wörtlich wiederholt — ein **Titelwiederholungstest, kein
Richtigkeitstest**. Eine sinngemäß richtige Antwort mit anderen Worten fällt
durch. Genau das steht seit dem ersten Lauf unter `grenze`; neu ist, dass die
**eigene Positivkontrolle** daran scheitert. Ein Kriterium, das seinen
bestmöglichen Fall nicht besteht, misst nicht streng, sondern falsch.

### 2. Die Negativkontrolle zählt das **Zurückweisen** des Speichers als Kontamination

2 von 4, und die beiden Fälle sind das exakte Gegenteil voneinander:

| Frage | ohne Speicher | mit Speicher | was das ist |
|---|---|---|---|
| „Welcher Knoten zum Verzurren einer Plane?" | **Mastwurf** (richtig) | „Der Knoten **Kalibrierbremse**" | **echter Schaden.** Der Speicher zerstört eine richtige Antwort — ein *Wissensknoten* wird als Seemannsknoten ausgegeben. |
| „Welches Papier fürs Ordnungsamt?" | korrekte Liste | „Das Hintergrundwissen enthält **keine** Informationen dazu … bezieht sich auf technische Software-Dienste" | **vorbildlich.** Das Modell weist den Speicher ausdrücklich zurück. |

Der Wortabgleich sieht beide Male Speicherwörter in der Speicher-Antwort und
zählt beide als Kontamination. **Er kann „falsch benutzt" nicht von
„ausdrücklich zurückgewiesen" unterscheiden** — und die Zurückweisung ist das
Verhalten, das wir wollen. Ein Kriterium, das gutes Verhalten bestraft, treibt
die Entwicklung in die falsche Richtung, sobald jemand die Zahl optimiert.

Der `Kalibrierbremse`-Fall bleibt davon unberührt und ist der ernsteste Befund
des Laufs: **ein Wortkanal, der bei fachfremden Fragen zuschlägt, macht
Antworten schlechter, nicht besser.**

### Was daraus folgt, und was ausdrücklich NICHT

**Nicht** getan: das Kriterium nachbessern und neu fahren. Ein Kriterium nach
Sicht des Ergebnisses zu ändern ist genau die Anpassung, die der Modulkopf
selbst ausschließt („vor der Messung festgelegt, nicht nachträglich an ein
Ergebnis angepasst"). Der Preis: es gibt aus `100` **keine** Wirkungszahl.

`113` (neu): Ein Kriterium, das **vor** dem nächsten Lauf zwei Abnahmen
besteht, beide an gespeicherten Antworten dieses Laufs prüfbar, ohne neuen
Modelllauf —
1. **Positiv:** Die Buckeberg-Antwort *mit* Speicher gilt als Treffer, die
   *ohne* Speicher nicht. Beide Texte liegen in der Ergebnisdatei.
2. **Negativ:** Die Ordnungsamt-Antwort gilt **nicht** als kontaminiert, die
   Plane-Antwort schon.

Besteht ein Vorschlag beide nicht, wird er nicht gefahren. Erst danach ist
`100` wiederholbar und erst dann trägt seine Zahl.

**Bindend:** `113` vor jedem weiteren Wirkungslauf — und `112` (Nachrangung)
vor dem *zweiten*, sonst misst er dieselbe un-nachgerangte Zufuhr.

---

## `113` gebaut, `100` damit gefahren — die erste verwendbare Zahl

`messungen/kriterium_113.py`, Abnahme **vor** dem Bau festgelegt (Commit
`5c66f2d8`) und bestanden:

```bash
python3 messungen/kriterium_113.py --abnahme
```

Lauf: Messstand `20260819T063335-6270801b`, 910,2 s, Ergebnisdatei
`runs/wirkung_llm_probe_2026-08-19T084859.json`. **Die Positivkontrolle besteht
jetzt** (`urteil = besser`) — das war der Grund, warum `100` beim ersten Mal
keine Zahl hergab.

| | n=10 |
|---|---|
| **besser** | **3** |
| unentschieden | 7 |
| **schlechter** | **0** |
| nicht messbar | 0 |

### Der eigentliche Befund steht nicht in dieser Tabelle

`schlechter = 0` bei den **Zielfällen** — bei den **Negativfällen** dagegen
2 von 4 kontaminiert, und beide sind echt (keine leere Vergleichsseite mehr):

| Frage | ohne Speicher | mit Speicher |
|---|---|---|
| Knoten zum Verzurren einer Plane | **Mastwurf** (richtig) | „**Kaliblerbremse**" — 8 Wörter aus einem Plan-Knoten |
| macOS-Auflösung per Terminal | **displayplacer** (richtig) | „displaychanger", dazu **AppleScript** aus der Zufuhr |

**Der Speicher hilft, wo er etwas hat, und schadet, wo er nichts hat.** Bei den
Zielfällen liegt das Ziel im Bestand — dort nie eine Verschlechterung. Bei
fachfremden Fragen liefert der Wortkanal trotzdem Material, und das Modell
baut es ein. Das ist **kein Trefferquotenproblem**: bessere Suche macht es
schlimmer, nicht besser. Die Stellschraube heißt **Enthaltung** — der Kanal
muss schweigen können, statt den besten verfügbaren Treffer zu liefern. Das
System konnte das am 18.08. schon einmal („schweigt zehnmal von zehn"), und
diese Fähigkeit ist unterwegs verlorengegangen.

### Zwei Schwächen des neuen Kriteriums, benannt statt behoben

1. **`statt` ist kein Stoppwort.** Im macOS-Fall trugen nur zwei Wörter die
   Kontamination, und eines davon war das Funktionswort `statt`. Der Befund
   steht damit auf einem Bein. `statt` gehört offensichtlich auf die
   Stoppwortliste — **jetzt nachzutragen wäre aber genau die Anpassung nach
   Sicht des Ergebnisses**, die `100` beim ersten Anlauf entwertet hat. Gehört
   vor den nächsten Lauf, mit eigener Abnahme.
2. **7 von 10 „unentschieden"** ist viel. Ob dort der Speicher wirklich nichts
   bewirkt oder `ABSTAND = 2` zu grob greift, ist offen und **an den
   gespeicherten Antworten nachprüfbar** — ohne neuen Modelllauf, weil `zufuhr`
   und beide Antworten jetzt in der Ergebnisdatei stehen.

**`114`** (neu): Enthaltungsschwelle im Wortkanal — der Fall
„Plane"/„displayplacer" als roter Testfall, bevor an der Trefferquote gedreht
wird. **Bindend vor `112`:** Nachrangung hebt top5 von 17 auf 51 % und macht
damit die Zufuhr bei fachfremden Fragen *dichter*, nicht leiser.

---

## `114` vermessen — und meine eigene Zahl von heute früh ist damit widerlegt

`messungen/enthaltungsschwelle_kosinus.py`, Ergebnis
`runs/enthaltungsschwelle_kosinus_2026-08-19.json`, Schnappschuss
`20260819T082700-f6234218`. n = **35 einschlägig** (alle Zielfälle des
Prüfkorpus, keine Auswahl) gegen **41 fachfremd**.

**Die Verteilungen überlappen um 0,0297** — einschlägig 0,5113–0,6477,
fachfremd 0,3619–0,5410. **Es gibt keine Schwelle, die beide Seiten sauber
trennt.**

Damit ist `runs/enthaltung_114_2026-08-19.json` mit seinem `trennbar: true`
**widerrufen** (Vermerk in der Datei, Feld auf `false` gesetzt). Der Fehler war
die Stichprobe: 10 von 35 Zielfällen sind nicht der Korpus, sondern ein
Ausschnitt — und ausgerechnet die drei Zielfälle unter 0,5410 lagen nicht
darin. Dieselbe Klasse wie `L-412e20` von heute Vormittag: nicht die Messung
war falsch, sondern woran sie gemessen wurde.

### Was der Handel kostet, in beiden Richtungen

| Schwelle | fälschlich enthalten (von 35) | fälschlich geliefert (von 41) |
|---|---|---|
| 0,50 | **0** | 6 |
| 0,54 | 3 | 1 |
| **0,55** | **3** | **0** |
| 0,58 | 11 | 0 |

Die beiden belegten Schadensfälle liegen bei **0,4747** (Plane/Mastwurf) und
**0,5410** (macOS/displayplacer). Der zweite ist zugleich der höchste
fachfremde Wert überhaupt — er ist es, den jede Schwelle überbieten muss, und
er kostet dabei die drei einschlägigen Fälle darunter.

### Die Entscheidung, die daraus folgt — und sie ist nicht die Zahl

**Die Enthaltung gehört nicht in `knowledge_search`, sondern in die Zufuhr.**
Der gemessene Schaden entstand nicht beim Suchen, sondern beim automatischen
**Einspielen** in einen Modellprompt. Wer selbst sucht, will die schwachen
Treffer sehen und kann sie einordnen; ein Modell, dem sie ungefragt vorgelegt
werden, kann das nicht — es baut sie ein.

Daraus folgt eine Trennung, die keine Schwelle braucht, um richtig zu sein:

- `knowledge_search` bleibt **vollständig** und liefert weiterhin alles, jetzt
  mit `bedeutungs_kosinus` je Zeile (`4c88915b`). Wer sucht, entscheidet selbst.
- Die **automatische Zufuhr** (`haken/knowledge_recall_hook.py` und jeder
  Messweg, der sie nachbildet) schweigt unterhalb der Schwelle.

Damit trifft der Preis von 3 aus 35 nur den Weg, auf dem der Schaden belegt
ist — nicht jede Suche im Haus. Das ist derselbe Schnitt wie bei der
Nachrangung: die Fähigkeit steht bereit, aber sie wirkt dort, wo sie hingehört.

**Gewählt: 0,55.** Nicht weil 3 zu 0 „besser aussieht" als 0 zu 6, sondern weil
diese Richtung im Haus bereits entschieden ist und hier nur angewandt wird:
`_embedding_ranking` sagt wörtlich **„Lieber kein Vektor als ein falscher"**,
die Freigabe steht auf `intern` als Vorgabe, und `BDW-P05` verlangt eine
belegbare Aussage. Ein fehlender Treffer ist eine Lücke, die der Nutzer sieht;
ein falsch eingespielter ist eine, die er nicht sieht.

**Der Preis, ausdrücklich:** In 3 von 35 echten Fällen schweigt die Zufuhr,
obwohl der Speicher etwas hätte. Umkehrbar — es ist eine Zahl an einer Stelle,
und die Messung, die sie begründet, liegt daneben.

**`115`** (neu): Die drei fälschlich enthaltenen Fälle einzeln ansehen. Liegen
sie niedrig, weil der Bestand zu ihnen wirklich wenig hat, oder weil ihre
Einbettung schlecht ist? Der zweite Fall wäre kein Schwellenproblem.

---

## `112` geholt, `114` gebaut, `115` beantwortet — und `115` benennt eine Grenze der Enthaltung

### `112` — Nachrangung liegt jetzt auf diesem Zweig

Per `cherry-pick`, nicht `merge` (`07623126`, `196d82c7`, `474b6097`). Selbst
nachgeprüft: Parameter `nachrangung` vorhanden, **Vorgabe `False`**, und ohne
Parameter dieselbe Reihenfolge wie mit `nachrangung=False`. 8 Tests grün.

Der Auftrag war unvollständig, und das hat der Agent gemeldet statt umgangen:
`48fb98ca` importiert `kern/nachrangung.py`, das erst in einem vierten Commit
entsteht. Beim Zusammenführen kollidierten außerdem zwei Zweige an derselben
Stelle im Lehre-Treffer; die erste Fassung übernahm beide Feldgruppen additiv
und warf `IndexError: No item with that key`, weil die SQL-Abfrage drei der
Felder gar nicht selektiert. Korrigiert.

### `115` — die drei enthaltenen Fälle sind **Kanalfälle**, kein Bestandsproblem

`runs/enthaltung_115_faelle.json`, Schnappschuss `20260819T102108-cf9c2d51`.
Alle drei stehen auf **Rang 1 der vollen Fusion** — der Abruf findet sie und
ordnet sie korrekt zuoberst:

| Fall | bester Kosinus | Kosinus des Ziels | Stichwort-Rang | Bedeutungs-Rang | Fusion |
|---|---|---|---|---|---|
| `/ops/buckeberg-konsil-…-governance` | 0,5294 | 0,5154 | 1 | 6 | **1** |
| `/apps/metahuman-podcast-…` | 0,5101 | 0,4883 | 10 | 9 | **1** |
| `/stadtwerke` | 0,5399 | 0,5270 | 39 | 2 | **1** |

**Die Schwelle zu senken wäre die falsche Antwort.** Die Rangfolge stimmt; was
zu niedrig liegt, ist der Kosinus selbst. Das ist ein Einbettungsproblem, und
eine niedrigere Schwelle würde zugleich den Schaden zurückholen, gegen den die
Enthaltung gebaut wurde — der höchste fachfremde Wert liegt bei 0,5410, also
**über** zwei dieser drei Zielwerte.

### Die Grenze, die dabei sichtbar wurde, und sie gehört ausdrücklich benannt

Die Positivkontrolle (`/testing/pytest`, bester Kosinus **0,6334**) zeigt, dass
dieser hohe Wert **nicht vom Ziel stammt**: das Ziel selbst liegt bei 0,5412 auf
Fusionsrang **70**.

Daraus folgt, was die Enthaltung leistet und was nicht:

- Sie fragt **„ist hier überhaupt etwas Starkes?"** — und das ist zur Laufzeit
  die einzig verfügbare Frage, denn welches Dokument das *richtige* wäre, weiß
  niemand im Moment des Abrufs.
- Sie fragt **nicht** „ist das Richtige dabei?". Ein hoher Wert eines fremden
  Dokuments lässt den Block passieren, auch wenn das Ziel weit hinten liegt.

**Sie verhindert also Schaden, sie garantiert keinen Nutzen.** Das ist kein
Mangel der Umsetzung, sondern die Grenze des Signals — und sie steht hier, damit
niemand die Enthaltung später für eine Trefferzusage hält.

**`116`** (neu): Einbettungsgüte der drei Fälle. Sie sind inhaltlich einschlägig
und stehen auf Rang 1, tragen aber Kosinuswerte unter dem höchsten fachfremden
Wert des Korpus. Solange das so ist, kostet jede Schwelle in diesem Bereich
echte Fälle.

---

## `108` erledigt — und meine Begründung dafür ist widerlegt

```
vorher:  8 Knoten + 1 Lehre ohne Einbettung · 157 + 172 = 329 mit veralteter Prüfsumme
nachher: 0 · 0 · 0                            478 Einbettungszeilen in 30,1 s
```

`kern/build_embeddings.py`, Prüfsumme der Bestandsdaten vor und nach dem Lauf
identisch (das Skript prüft das selbst): **keine Bestandsdaten angefasst**.

### Die Begründung war falsch, und das gehört hierher

Ich habe `108` vor `116` gezogen mit der Überlegung, die niedrigen
Kosinuswerte der drei enthaltenen Fälle könnten von veralteten Vektoren
kommen — dieselbe Sache von zwei Seiten. **Gemessen: unverändert.**

| Fall | vorher | nach dem Neurechnen |
|---|---|---|
| `/ops/buckeberg-konsil-…-governance` | 0,5294 | **0,5294** |
| `/apps/metahuman-podcast-…` | 0,5101 | **0,5101** |
| `/stadtwerke` | 0,5399 | **0,5399** |

Auf die vierte Stelle identisch — die drei waren nie unter den 329 veralteten.
Und auch die zweite naheliegende Erklärung fällt: **keiner der drei** gehört zu
den 14 beim Einbetten gekappten Knoten (nachgesehen mit
`embeddings.wird_gekappt()` über den echten Bestand).

`108` war trotzdem richtig — 329 Einträge, deren Vektor einen Text beschreibt,
den es so nicht mehr gibt, sind ein echter Defekt, und die Suche lieferte
dadurch falsch, ohne dass irgendwo ein Fehler auftauchte. Aber die beiden
Aufgaben hängen **nicht** zusammen, und `116` steht damit unverändert offen,
nur ohne seine bequemste Vermutung.

**Was für `116` übrig bleibt, nachdem zwei Erklärungen ausgeschieden sind:**
Die drei Texte sind inhaltlich einschlägig, stehen auf Fusionsrang 1, sind
frisch eingebettet und nicht gekappt — und tragen trotzdem einen Kosinus unter
dem höchsten fachfremden Wert des Korpus (0,5410). Damit ist die nächste Frage
nicht mehr „ist der Vektor kaputt", sondern was der Bedeutungskanal an *diesen*
Texten misst, das er an fachfremden Texten höher bewertet.

---

## Schwelle nach dem Neurechnen nachgeprüft — sie trägt, und der Nullbefund belegt weniger, als er scheint

`runs/schwelle_nachlauf_abrufweg_2026-08-19.json` (`26a02785`), Schnappschuss
`20260819T105004-e7853b33` gegen den alten `20260819T094703-31bcb647`,
dieselben 76 Fragen, derselbe Weg:

| | alt | neu |
|---|---|---|
| Überlappung | 0,0309 | **0,0309** |
| bei 0,55 | 3 / 0 | **3 / 0** |
| Fragen mit Bewegung > 0,01 | — | **0 von 76** |

Alle 30 Schwellenzeilen alt = neu. **Die Schwelle 0,55 steht also weiterhin auf
einer gültigen Messung**, und das war der Anlass — ich hatte den Bestand unter
einer produktiven Schwelle verändert, ohne sie nachzuprüfen.

### Die Gegenprobe, die den Befund kleiner macht

Ein Nullbefund über *alle* 76 Fragen ist zu sauber, um ihn ungeprüft zu
übernehmen. Nachgesehen:

- Die Neuberechnung hat wirklich geschrieben: **480 Einbettungszeilen, 339
  Kennungen**, `updated_at` von heute.
- Von den **35 Zielkennungen des Prüfkorpus** war dabei aber **genau eine**
  (`483acb56`).

Dass sich nichts bewegt, ist damit **erwartbar** — die Neuberechnung hat fast
nichts angefasst, was dieser Korpus abruft. Der Lauf belegt: *die Schwelle
trägt gegen diese 76 Fragen*. Er belegt **nicht**: *Neurechnen ist folgenlos*.
Wer den zweiten Satz daraus zitiert, zitiert etwas, das hier nicht gemessen
wurde.

**Was daraus für den Prüfkorpus folgt:** Er deckt 35 von 5189 Knoten ab. Eine
Änderung, die 339 andere Kennungen betrifft, ist über ihn grundsätzlich nicht
sichtbar. Das ist keine Kritik am Korpus — er ist für Abrufgüte gebaut, nicht
für Bestandsänderungen —, aber es begrenzt, welche Fragen er beantworten kann.

---

## `116` beantwortet — nicht durch eine Messung, sondern durch den eigenen Speicher

Der Agent hat die Textzusammensetzung vermessen und meine Annahme **widerlegt**:
weder Länge noch Variantenwahl trennen die drei Fälle von den Gegenproben, und
die beste Variante gewönne 0,003 bis 0,02 — es fehlen aber 0,08 bis 0,15 zur
Schwelle. Er hat ehrlich „unerklärt" gemeldet statt eine Erklärung zu bauen.

**Erklärt ist es trotzdem, seit dem 2026-08-16, im eigenen Bestand:** Knoten
`291c2e3f` „Warum der echte Prüfkorpus bei 14 Prozent liegt".

| | |
|---|---|
| Ziel in Top-5 | 5 von 35 (14 %) |
| Rang 6–50 | 7 |
| **außerhalb Top-50** | **23** |
| die 23 im **reinen** Bedeutungskanal | Median-Rang **134** von 5963 |

Und die Ursache steht dort im Klartext: **Die Aufgaben sind
Situationsbeschreibungen in Alltagssprache, die Ziele sind technische
Beschreibungen mit Eigennamen.** Dazwischen liegt ein Abstraktionssprung, den
das Einbettungsmodell nicht überbrückt. Derselbe Abruf erreicht auf GermanQuAD
**37 von 40** — dort ist die Frage aus der Zielpassage gebildet. *Der
Unterschied zwischen 93 % und 14 % ist nicht die Güte des Abrufs, sondern der
Abstand zwischen Frageform und Zielform.*

### Was das für die Enthaltung bedeutet, und es ist unangenehm

Die drei enthaltenen Fälle sind **keine Ausreißer, sondern der Normalfall
dieses Korpus**. Ihr niedriger Kosinus ist kein Defekt an diesen drei Knoten —
er ist die gemessene Eigenschaft der Aufgabenform. Und er erklärt zugleich,
warum fachfremde Fragen **höher** liegen können: die sind schlicht formuliert
und treffen schlicht formulierte Inhalte.

Die Schwelle 0,55 kodiert damit den Abstraktionssprung mit. Sie bleibt richtig
— sie verhindert belegten Schaden —, aber sie ist keine Aussage über
Wissensqualität, sondern über Frageform.

### Der eigentliche Befund des Tages steckt im Weg dorthin

Diese Diagnose lag **drei Tage** im Speicher und wurde heute in vier Aufträgen
nicht gefunden — ich habe stattdessen zwei Agenten (rund 250.000 Token) auf
Erklärungen angesetzt, die dort bereits ausgeschlossen waren. Eingespielt hat
sie am Ende der **automatische Abruf**, ungefragt, im richtigen Moment.

Das ist an einem Tag, an dem ich den Abruf vermessen, beschnitten und mit einer
Enthaltung versehen habe, der beste Beleg für ihn — und zugleich `L-f2858b`
(4 Vorkommen) zum sechsten Mal: **Bei einer Frage der Form „woran liegt X"
gehört der Speicher vor die Messung.**

**`117`** (neu): Von den drei im Knoten genannten Richtungen ist keine
beschlossen, und vor jeder fehlt eine Wirkungszahl. Richtung 1 (situative
Zweiteinbettung je Lehre) lässt sich an einer Handvoll billig prüfen, bevor der
Bestand angefasst wird. `116` ist damit erledigt und geht in `117` über.

---

## `118` — der Widerspruch ist aufgelöst: beide Messungen stimmen, eine Formulierung nicht

`runs/widerspruch_118_kandidatenquelle.json` (`1dd882a7`), Schnappschuss
`20260819T110946-72b64534`. Kein einziger Modellaufruf nötig — die Frage war
über den Code beantwortbar, nicht über einen Nachlauf (der hätte 1.719 s
gekostet).

**Die beiden Messungen sprechen über zwei verschiedene Kandidatenmengen:**

| | Ziel in Top-50 |
|---|---|
| gemeinsame Kosinusliste über Knoten+Lehren (was `A` maß) | 13 von 35 |
| **tatsächliche Kandidatenquelle der Nachrangung** | **21 von 35** |

Fundstelle statt Vermutung: `knowledge_search()` reicht `final_ids` aus
`_fuse_with_keyword_floor()` weiter. Dort werden Knoten und Lehren **getrennt**
per Kosinus gerankt und erst über die **Rangposition** verschmolzen — eine
gemeinsame Kosinusliste, wie `A` sie bildet, entsteht nie.

**Der Einzelfall entscheidet es schneller als jede Statistik:**
`/ops/buckeberg-konsil-2026-07-22-governance` steht in der gepoolten Liste auf
**Rang 150** und in der echten Kandidatenquelle auf **Rang 1**.

**Ein Satz:** Messung `A` gilt weiter für ihre eigene Frage, beschreibt aber
nicht die Kandidatenmenge der Nachrangung; die 18 von 35 aus `B` sind mit den
21 erreichbaren Zielen vereinbar und bleiben die maßgebliche Zahl.

Falsch war nie eine Zahl, sondern **ein Satz**: *„Keine Umordnung erreicht ein
Ziel auf Rang 134."* Er gilt für die gepoolte Liste und wurde als Aussage über
jede Umordnung gelesen. `L-352afa` (4 Vorkommen) zum fünften Mal — das
Werkzeug beantwortet eine engere Frage als der Satz, in dem seine Zahl steht.

### Zwei Nebenbefunde, die jede frühere Zahl dieses Korpus betreffen

**Der Prüfkorpus hat 45 Zeilen, nicht 35.** Selbst nachgezählt: 35 mit
`target_id`, **10 Enthaltungsfälle mit `target_id: null`**. Keine der beiden
Messungen sagt das; beide rechnen „von 35" und meinen die Teilmenge. Für die
Enthaltung sind ausgerechnet diese 10 der interessante Teil — sie sind der
Fall, in dem Schweigen richtig ist.

**Knoten-Ziele stehen als Pfad, nicht als Kennung** (`/methodik/einstieg` statt
Hex). Ohne Auflösung wären alle 20 Knotenfälle künstlich verfehlt worden,
unabhängig von der eigentlichen Frage.

### Entscheidung zur Nachrangung: Vorgabe bleibt AUS

Sie ist eingebaut, geprüft und abschaltbar. **Preis: Median 48,6 s je Anfrage.**
Der Abruf läuft in **jedem Prompt jeder Sitzung**; aus unter einer Sekunde
würde fast eine Minute. Das ist keine Verbesserung, die man stillschweigend
einschaltet — sie steht bereit, wer sie einschaltet, bezahlt bewusst.

**Was ich stattdessen für nötig halte:** eine Nachrangung, die nicht 48 s
kostet. Die Nulllinie aus derselben Messung sagt, wo sie nicht zu holen ist —
die regelbasierte Variante bewegt **nichts** (6/35 wie ohne). Das ist eine
Aufgabe mit einer klaren Abnahme, kein Schalter.

---

## `F03` vermessen — Prozeduren gibt es, und ihr Widerruf ist ein anderer als der eines Fakts

`BDW-F03-AC1`: *„Prozeduren sind von Fakten/Episoden getrennt und besitzen
eigenen Freigabe- und Widerrufstest."*

**Gemessen 2026-08-19, bevor irgendetwas gebaut wird** — die Frage war, ob es
überhaupt Einträge gibt, die eine Prozedur *sind*:

| | |
|---|---|
| Lehren mit erkennbarer Schrittfolge | **248** von 1116 |
| davon Art `pattern` („Verfahren, das …") | 85 von 172 |
| Knoten mit Schrittfolge | **244** von 5108 |

Prozeduren existieren also — rund 490 Kandidaten. `F03` ist damit eine
**Zuordnung**, keine Erfindung. Das unterscheidet die Zeile von `BDW-U01`, die
heute vertagt wurde, weil es die Org-Ebene *nicht gibt*.

### Der Unterschied, an dem die Zeile wirklich hängt

`F03` verlangt einen **eigenen Freigabe- und Widerrufstest**. Der Grund dafür
wird erst sichtbar, wenn man fragt, was ein Widerruf jeweils bedeutet:

- Ein **Fakt** wird widerrufen, weil er **nicht stimmte**. Der Widerruf ist eine
  Aussage über Wahrheit, und er gilt rückwirkend — die Aussage war schon immer
  falsch.
- Eine **Prozedur** wird widerrufen, weil sie **nicht mehr funktioniert**. Sie war
  richtig, als sie geschrieben wurde. Der Widerruf gilt **ab einem Zeitpunkt oder
  einer Version**, nicht rückwirkend.

Das ist exakt die Achse aus `ADR-030` von heute: `gilt_bis_version` plus
`bezug`. Eine Prozedur, die an Flutter hängt, verliert ihre Gültigkeit mit
einer Flutter-Version — ein Fakt über Flutter wird dadurch nicht falsch,
sondern historisch.

**Damit ist `F03` nicht mehr die schwerste der drei offenen Zeilen, sondern die
am besten vorbereitete:** Die Felder liegen seit heute (`bezug`,
`gilt_bis_version`, `gedaechtnisart` mit zulässigem Wert `prozedural`), und
der Unterschied im Widerruf ist benannt statt geraten.

**Was noch fehlt und nicht geraten werden darf:** die Zuordnung selbst. 248
Lehren tragen eine Schrittfolge — das heißt nicht, dass 248 Lehren Prozeduren
*sind*. Eine `antipattern`-Lehre mit Schritten in ihrer Vorbeugung bleibt eine
Lehre über einen Fehler; die Prozedur steckt *in* ihr. Die 85 `pattern`-Lehren
mit Schrittfolge sind der belastbare Kern, und mit ihnen ist zu beginnen.

---

## `P05` bleibt bei 3/35 — und meine Vorhersage war falsch, was die Frage schärft

Lehren liefern seit `2a2afe45` ihre Herkunfts- und Geltungsfelder: `session`,
`actor`, `model`, `pruefstelle`, `status`, `first_seen`, `last_seen`,
`occurrences`, `bezug`, `gilt_ab`, `gilt_bis`, `gilt_bis_version`,
`node_path`. Am echten Weg geprüft, sie kommen an.

**Die Zahl bewegt sich trotzdem nicht: 3/35, unverändert.** Ich hatte
vorhergesagt, Status springe auf 15/15. Falsch — und der Grund steht in drei
Zeilen von `messungen/zielbild_a_vollstaendigkeit.py`:

```python
"quelle":  bool(ziel.get("source") or ziel.get("quelle")),
"status":  ziel.get("norm_rang") is not None or bool(ziel.get("norm_entscheidung")),
"geltung": bool(ziel.get("gilt_ab") or ziel.get("gilt_bis")),
```

**Alle drei nennen Knoten-Vokabeln.** Eine Lehre hat weder `source` noch
`norm_rang` noch `norm_entscheidung` — für 15 der 35 Ziele ist das Ergebnis
strukturell null, unabhängig davon, was ausgeliefert wird. Dieselbe Klasse wie
`L-352afa`: das Werkzeug beantwortet eine engere Frage als der Satz darüber.

Die Auslieferung war trotzdem richtig: die Felder sind jetzt für **jeden**
Verbraucher da. Nur dieses eine Kriterium schaut nicht hin.

### Die Entscheidung, unverkürzt

| | |
|---|---|
| **Anerkennen** | Das AC sagt selbst „geprüft wird, was beim Fragenden ankommt". Eine Lehre mit *Sitzung, Zeitpunkt, Status, Vorkommen* lässt sich beurteilen. Ohne Anerkennung ist `P05` bei **57 % gedeckelt** und damit unerfüllbar formuliert. |
| **Ablehnen** | `session=9efc6a71` ist für einen Menschen **keine Quelle**. Bei einem Knoten steht dort „erzeugt aus Datei X, Stand Y". `P05` ist die Zeile, die diesen Anspruch überhaupt misst — wer die Vokabel erweitert, senkt ihn. |

**Entschieden, bis der Betreiber widerspricht: ablehnen.** Eine Lehre bekommt
eine echte Quelle statt einer nachgelassenen Definition. Das Feld dafür
existiert — `pruefstelle` sagt, *woran* eine Lehre gemessen wurde — und ist bei
**92 von 1117** gefüllt.

**Der Preis, ausdrücklich:** Für die 1025 Altlehren ist `pruefstelle` nicht
rekonstruierbar. `P05` bleibt damit auf absehbare Zeit unter der Schwelle, und
das ist die ehrlichere Zahl als eine, die durch eine erweiterte Vokabel
entsteht.

**Was ausdrücklich NICHT getan wird:** das Kriterium so umschreiben, dass die
vorhandenen Felder passen. Das wäre die Messlatte ans Ergebnis angepasst — der
Fehler, der heute früh schon einmal `100` entwertet hat.

## `BDW-E15`: Sicherungen liegen neben der Datenbank — was daran wirklich fehlt

**Gemessener Ist-Stand** (2026-08-19, `grep` über alle `*.py` ohne Arbeitsbäume):
zwölf identische Zeilen in `knowledge_mcp_server.py` bilden den Sicherungspfad
als `DB_PATH.parent / f"{DB_PATH.name}.bak-{stamp}"`. Es gibt **keine** Stelle,
die einen anderen Ort kennt. Die Katalogzeile sagt dazu „getrennt: NEIN", und
das ist richtig gemessen.

**Was „getrennt" heißt, und hier wird unterschieden statt zusammengeworfen:**

| Trennung | heute | mit dieser Änderung |
|---|---|---|
| anderes Verzeichnis | nein | ja (`sicherungen/` neben der DB) |
| anderer Datenträger | nein | nur, wenn der Betreiber `BRAINLEHR_SICHERUNGSORT` setzt |
| offline | nein | nein |

Die erste Zeile ist die, die im Alltag trägt: ein `rm knowledge.db*`, ein
falsch gezielter Aufräumlauf, ein Verzeichnis, das jemand leert — all das
nimmt heute Bestand **und** Sicherung mit. Die zweite und dritte Zeile sind
Betreibersache (welcher Datenträger, welches Medium) und werden **nicht**
erraten; die Umgebungsvariable ist der Griff dafür.

**Alternativen, verworfen:**
- *Eine Helferfunktion an jeder der zwölf Stellen einbauen und dort den Ort
  entscheiden.* Verworfen: dieselbe Falle wie beim Aufräumen (`kern/sicherungen.py`
  ist genau deshalb verzeichnisweit gebaut). Die dreizehnte Schreibstelle wird
  es wieder falsch machen.
- *Auf ADR-029 verweisen und nichts tun* („der Schlüssel ist weg, also ist die
  Sicherung mitgelöscht"). Verworfen: ADR-029 löst die **Löschfrist** in
  Kopien, nicht den **Verlust** von Bestand und Kopie in einem Griff. Das sind
  zwei verschiedene Fragen, und E15 stellt die zweite.

**Reihenfolge, bindend:** `kandidaten()` muss BEIDE Orte lesen, **bevor** die
erste Sicherung an den neuen Ort geht. Sonst sieht das Aufräumen die alten 
Sicherungen nicht mehr — genau der Befund vom 2026-08-19, bei dem 96 % des 
Gegenstands unerreichbar waren, nur mit dem Verzeichnis statt dem Namen als 
Ursache.

**Was bewusst nicht getan wird:** kein Zeitplan (E15 verlangt „automatisch";
heute ist es ereignisgetrieben beim Serverstart). Preis: eine Woche ohne
Serverstart ist eine Woche ohne Sicherung. Bleibt offen und wird in der
Katalogzeile benannt, statt sie auf PASS zu heben.

**Erfolgsmaß:** `kern/sicherungen.py --selftest` grün mit einem Fall, der eine
Sicherung am ALTEN und eine am NEUEN Ort anlegt und beide gefunden sieht; rot
gegen einen festen Commit.

## `BDW-E07` / `BDW-E13`: das Crypto-Shredding ist gebaut und an nichts angeschlossen

Stand 2026-08-19T22:14:52+0200. Beide Zeilen stehen seit heute auf **FAIL**, nicht mehr auf
TEILWEISE — und zwar nicht, weil Tests fehlen, sondern weil die Messung am
echten Weg etwas anderes zeigt als die Messung am Modul.

**Gemessener Ist-Stand** (`tests/test_e07_bestand_im_klartext.py`, 6 grün):

| Teil des AC | Modul allein | echter Bestand |
|---|---|---|
| Daten unlesbar | ja (7 Fälle grün) | **nein** — Klartext in den Rohbytes |
| Index unlesbar | — | **nein** — `knowledge_fts` gibt ihn heraus |
| Backup unlesbar | — | **nein** — Bytekopie erbt alles |
| Fristlauf erreicht ihn | — | **nein** — `fristlauf()` hat keinen Parameter dafür |

Einziger Aufrufer von `kern/kundenschluessel.py` außerhalb der Tests ist
`kern/aufbewahrung.py`; per Test festgenagelt, damit ein echter Schreibpfad
den Test rot macht, sobald er entsteht.

**Reihenfolge, bindend** (ADR-031). Der Grund für genau diese Folge ist der
Index, nicht die Bequemlichkeit:

1. ~~Spalten `sensibel` und `chiffre`, FTS-Trigger schließen sensible Knoten
   aus~~ — **erledigt** (`aa8d954d`), Migration für die gewachsene Datenbank
   gefahren, 5200 Knoten, Index heil.
2. ~~Schreibweg: `knowledge_add` nimmt `sensibel` entgegen~~ — **erledigt**
   (`6760901e`), `BDW-E07` auf PASS. Die Ersetzung sitzt ganz am Anfang der
   Funktion, weil fünf Wege darunter denselben Text weiterreichen.
3. ~~`fristlauf()` an den Bestand hängen~~ — **erledigt** (`16ac76c1`),
   `BDW-E13` auf PASS. Die Reihenfolge ist jetzt ein Test statt einer
   Absicht: `fristlauf_bestand()` verweigert sich, solange ein sensibler
   Knoten im Volltextindex steht — sonst bescheinigte der Nachweis eine
   Löschung, die nicht stattfindet.

**Was als Nächstes ansteht** (nicht getan, bewusst): Kein Bestandsknoten ist
heute als sensibel markiert, und `knowledge_update` kennt `sensibel` nicht —
ein bestehender Knoten lässt sich also nur über SQL hochstufen, nicht über
den produktiven Weg. Solange niemand echte Fremddaten einpflegt, kostet das
nichts; sobald buckeberg oder openlehr liefern, ist es der erste Schritt.

**Was bewusst nicht getan wird:** kein durchsuchbarer Index über sensible
Knoten. Preis: ein sensibler Knoten ist über die Volltextsuche nicht
auffindbar. Für Daten Dritter ist das richtig; für den Arbeitsbestand wäre es
Selbstverstümmelung, deshalb ist die Vorgabe `sensibel = 0`.

**Erfolgsmaß:** `tests/test_e07_bestand_im_klartext.py` schlägt um — die heute
grünen Zusicherungen („Klartext lesbar") müssen für einen sensiblen Knoten rot
werden und für einen normalen grün bleiben.
