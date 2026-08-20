# Plan: Gesamtbau der acht Straenge A-G

Angelegt 2026-08-21T00:33:03+0200. Umsetzungsplan zu
`docs/PLAN_BETRIEBSPROFILE_2026-08-20.md` (710 Zeilen, Straenge A-G).
Betreiberauftrag vom 2026-08-21: "Bau den Gesamtplan ... ohne Rueckfragen, bis
morgen frueh. Du entscheidest Reihenfolge und Zuschnitt innerhalb der
genannten Sperren."

Der Betriebsprofil-Plan sagt WAS und WARUM. Dieser hier sagt WER, in WELCHER
REIHENFOLGE und WORAN der Erfolg gemessen wird. Er wird waehrend der Arbeit
fortgeschrieben, nicht danach.

## §0 Gemessener Ist-Stand (2026-08-21T00:33)

| | |
|---|---|
| Zweig / Stand | `brainlehr/b4-ausweis`, `1d0e7470` |
| Bestand | 5 240 Knoten, 1 173 Lehren, 22 634 Zugriffszeilen |
| Schema | 35 Tabellen, 63 Trigger |
| Katalog | 66 BDW-Zeilen, 10 auf NOT RUN (P09-P14, E22-E25) |
| Testdateien | 294 unter `tests/` |
| Achsen im Schema | `mandant` **fehlt**, `kreis` **fehlt**, `sprache` **fehlt**, Geltung nur als Spalte (`gilt_ab`/`gilt_bis`), keine Tabelle je Kreis |

**Gemessen, nicht uebernommen:** `PRAGMA table_info(knowledge_nodes)` nennt 40
Spalten, keine davon traegt Mandant, Kreis oder Sprache.
`PRAGMA table_info(lessons_learned)` nennt 29, dasselbe Bild.

**Der Nachzugsweg steht bereits und wird nicht neu gebaut** -- das ist der
Grund, warum B1 klein ist: `kern/schema_nachzug.py` zieht fehlende
Spaltendefinitionen generisch aus `schema.sql` in eine gewachsene Datenbank
nach (mit WAL-Checkpoint und Sicherung davor), `_ensure_core_schema()` spielt
`schema.sql` fuer die Erstanlage ein. Eine neue Spalte mit `DEFAULT` und eine
neue Tabelle brauchen deshalb **nur einen Eintrag in `schema.sql`**, kein
eigenes Migrationsskript. Was `schema_nachzug` bewusst NICHT annimmt: `NOT
NULL` ohne `DEFAULT`, gerechnete `DEFAULT`s, mehrzeilige `CHECK`s -- daran
richtet sich die Bauform der Achsen aus.

## §1 Die Sperren, uebernommen und nicht neu verhandelt

```
                B1  Achsen ins Schema  (mandant · kreis · sprache · geltung)
                 |   BINDEND ZUERST
        +--------+--------+
        |                 |
       B2 Wechsel        B3 Enterprise-Achsen (E03 E06 E22 E23)
        +--------+--------+
                 |
                C  Einrichtungsassistent
                 |
                F  Forderungen als Vorgang (braucht die Spalte aus B1)

  AB SOFORT UND NEBENEINANDER:
    A2 Rueckzug bei Leerlauf · A3 Sicherung gegen tote Dienste
    D  Zugriffsmuster · E1 Verfallsrate · P14-Tuer
```

**Eine Sperre kommt hinzu, sie ist neu und dieser Plan hat sie eingezogen:**
`schema.sql` gehoert im ersten Zug **ausschliesslich B1**. F braucht ein
eigenes Feld an `knowledge_nodes` (Plan §F1), D und E1 brauchen keines. Zwei
Agenten, die gleichzeitig dieselbe Datei umbauen, erzeugen einen
Zwischenstand, den keiner von beiden geprueft hat. Deshalb traegt B1 die
Forderungsspalte gleich mit ein, und F baut nur noch die Logik darauf.
Derselbe Grund wie beim Zusammenfallen von P14-Schemaumbau mit B1 im
Betriebsprofil-Plan.

## §2 Zuschnitt: was in diesem Lauf gebaut wird

| Strang | Katalogzeile | Zuschnitt |
|---|---|---|
| B1 | P09, P10, E22, E23 (Schemateil) | vier Achsen ins Schema, beide Ausgangszustaende, je Achse ein Negativtest |
| B2 | P09-AC2 | Wechsel `einzelplatz` -> `unternehmen` und Rueckweg, mit Bestandszaehlung |
| B3 | E03, E06, E22, E23 | Mandanten- und Kreistrennung erzwungen, Negativmatrix |
| C | P11, P12 | `einrichtung_starten` im Chat, Kataloge als `nachschlagewerk`, Fremdimport ohne erfundene Herkunft |
| A2 | -- | **verworfen nach Messung**, siehe §6 |
| A3 | -- | Aussetzer-Sicherung gegen tote Dienste |
| D | E25 | Zugriffsmuster: Zugriffe je Knoten und Abdeckung, nicht Menge |
| E1 | P13 | Verfallsrate je Ast: Schaetzung + Widerrufsquote |
| F | -- | Forderung als Vorgang mit Abschluss und Ausloeser |
| P14 | P14-AC1 | README und CONTRIBUTING englisch |

## §3 Was bewusst NICHT gebaut wird, und der Preis

* **E24 zweiter Faktor** -- sechs Wege liegen vor, keiner ist entschieden.
  Betreiber. Preis: der Bestand bleibt bei Beschlagnahme lesbar.
* **E01, E04, E05** -- an einen echten Mehrbenutzer-Piloten gebunden
  (`BDW-C03`). Ein gegen einen erfundenen IdP gebauter Anschluss prueft den
  Pruefstand, nicht die Sache. Preis: drei Zeilen bleiben offen.
* **E19 Datenregionen** -- ohne zweiten Standort gibt es nichts zu begrenzen.
* **E2/E3 Gremienbeobachtung** -- erst nach E1; sie liest eine Menschenseite
  (gemessen: kein RSS, keine API) und ist die bruechigste Bauform des Plans.
* **Push des oeffentlichen Exports** -- das GitHub-Konto ist gesperrt.
* **P14 Schnittstelle und Docstrings** -- nur die Tuer in diesem Lauf. Der
  Rest faellt mit einem Schemaumbau zusammen, den B1 gerade erst gemacht hat;
  ihn zweimal anzufassen erzeugt einen Zwischenstand mit `mandant` neben
  `tenant`.

## §4 Abnahme

Fuer jeden Schritt gilt: **rot vor gruen an einem festen Bezugspunkt**,
Gegenprobe in beide Richtungen, Negativfall. Zusaetzlich:

| Schritt | Nachweis |
|---|---|
| B1 | Frischer UND gewachsener Bestand tragen dieselbe Achse; je Achse ein Negativtest |
| B2 | Wechsel und Rueckweg je einmal, Bestandszaehlung davor/danach |
| B3 | Je Achse ein Negativtest: der fremde Mandant/Kreis sieht nichts, auch nicht in der ZAEHLUNG |
| C | Einrichtung gefahren auf leerem UND gewachsenem Bestand |
| A2 | Leer-Anteil vor/nach gegen dieselbe Nulllinie (37,8 %) |
| A3 | Nachstellprobe mit abgeschaltetem Dienst |
| D | Hergestellter Lauf ueber 500 Knoten schlaegt an; die 4-%-Sitzungen des echten Bestands nicht |
| E1 | Rate je Ast gegen den echten Bestand gerechnet, nicht gegen Fixtures |
| F | Eine Forderung laesst sich abschliessen und verschwindet aus der Startliste |

**Jeder neue Melder wird einmal gegen den ECHTEN Bestand gefahren und seine
Treffer werden gelesen, bevor ihm geglaubt wird.** Gemessen am 2026-08-20:
zwei von drei Entwuerfen waren beim ersten Lauf falsch.

## §5 Betreiberentscheidungen dieses Laufs

| Entscheidung | Wortlaut / Grund |
|---|---|
| `mandant` Vorgabe `lokal` | Betreiberauftrag 2026-08-21 woertlich: "mandant Vorgabe lokal" -- sticht den Planvorschlag `einzelplatz` fuer die SPALTE |
| Profilnamen `einzelplatz` / `unternehmen` | offene Entscheidung des Betriebsprofil-Plans, hier vom Assistenten getroffen: deutsch wie der uebrige Bestand (`freigabe`, `geltung`, `herkunft`) |
| `schema.sql` gehoert B1 allein | dieser Plan, §1 |

## §7 Verworfen nach der Messung: A2 Rueckzug bei Leerlauf

Zwei Fassungen gebaut und gegen dieselben 259 Protokollzeilen gerechnet:

| | Zustand je Sitzung | Zustand je Sitzung UND Thema |
|---|---|---|
| gesparte Suchen | 40,5 % (105/259) | **0,4 %** (1/259) |
| verpasste echte Treffer | 38,6 % (66/171) | **0,0 %** (0/171) |

Die erste Fassung frisst 38,6 % der echten Treffer -- fuer einen Speicher,
dessen einziger Zweck das Wiederfinden ist, der falsche Tausch. Rechenzeit
und ein verpasster Treffer sind nicht dieselbe Waehrung.

Die zweite Fassung haelt die Schranke (0 % verpasst), spart aber nichts:
Zwei aufeinanderfolgende Prompts zum selben Gespraechsthema benutzen fast nie
dieselben acht Stichwoerter, also gilt fast jeder Aufruf als neues Thema und
wird sofort gesucht. **Sicher und wirkungslos.**

**Entscheidung: nicht gebaut.** Ein Mechanismus, der 0,4 % spart, kostet
dauerhaft Zustand und ein Protokollfeld auf dem heissesten Pfad des Systems
-- er laeuft bei JEDEM Prompt. Das ist teurer als das Problem. Der Code ist
verworfen, die MESSUNG bleibt
(`runs/leerlauf_nulllinie_2026-08-21.json`), und mit ihr der Nebenbefund,
der unabhaengig davon gilt: die 37,8 % Leer-Anteil aus dem Plan waren ein
Codekommentar ueber den alten Suchweg vor dem 2026-08-09; gemessen sind es
**34,1 %** am wirklich haengenden Hook.

**Was ein Folgeauftrag versuchen muesste**, falls jemand es doch will:
unscharfe Themenzugehoerigkeit (Stichwort-UEBERLAPPUNG statt Gleichheit),
gegen dieselbe 5-%-Schranke gemessen. Ausdruecklich nicht angefangen.

## §6 Verlauf

* 2026-08-21T00:33 -- Plan angelegt, Ist-Stand gemessen, Welle 1 vorbereitet.
* 2026-08-21T00:46 -- Welle 1 laeuft (B1, A2, A3, D, E1, P14-Tuer).
  Zwei Vorbefunde fuer Welle 2, gemessen statt vermutet:
  * **Der Profilbegriff existiert nirgends.** `grep -rln "standalone|multiuser|
    betriebsprofil"` ueber `kern/`, `melder/`, `haken/` und
    `knowledge_mcp_server.py`: **null Treffer**. B2 und C bauen ihn von Grund
    auf; es gibt nichts zu uebernehmen und nichts, was dabei brechen koennte.
  * **Und er braucht keine Schemaaenderung.** `knowledge_config` ist eine
    Schluessel-Wert-Tabelle und traegt heute bereits vier Betriebswerte
    (`embed_model`, `herkunftsmodus`, `instanz_kennung`, ein Laufvermerk). Der
    Profilschalter gehoert dorthin -- eine Zeile, kein Feld, keine Migration.
    Damit faellt der Schalter aus der B1-Sperre heraus: B2 haengt nur noch an
    der Mandanten-ACHSE, nicht am Profilbegriff.
  * Fremde Arbeit im Baum: acht weitere Claude-Fenster laut Startmeldung,
    aber im Agentenregister nur EIN fremder Agent ohne `stop` -- und der in

* 2026-08-21T01:15 -- Welle 1 abgeschlossen bis auf A2, Welle 2 laeuft.

  | Strang | Commit | Ergebnis |
  |---|---|---|
  | B1 | `f64e7a12` | vier Achsen im Schema, beide Ausgangszustaende, je Achse Negativtest |
  | A3 | `7bc2dcb6` | Aussetzer nach 5 Fehlern, 120 s, protokolliert und an `SessionStart` verdrahtet |
  | D | `7a41e528` | Zugriffsmuster, Positivkontrolle schlaegt an, echter Bestand 0 Treffer |
  | E1 | `abde354f`, `f6933dbd` | Verfallsrate je Ast, dritte Quelle gesetzt statt geraten |
  | P14 | `df9299cf` | englische Tuer, deutsche Fassungen erhalten |
  | A2 | -- | **NICHT committet**, siehe unten |

  **Vier Befunde, die den Plan geaendert haben:**
  * **Die Spracherkennung aus dem Plan existiert nicht.** "36 Stoppwoerter,
    758/770" stand als Messung da, im Code gab es sie nur in fremden
    Arbeitsbaeumen. Neu gebaut, gemessen: 0,05 % Falschzuweisung.
  * **Die 37,8 % Leer-Anteil sind widerlegt.** Es war ein Codekommentar ueber
    den ALTEN Suchweg vor 2026-08-09. Am wirklich haengenden Hook gemessen:
    **34,1 %**. Und der zweite Kandidat aus dem Auftrag
    (`hub/scripts/knowledge_recall_hook.py`) existiert gar nicht.
  * **A2 wird nicht gebaut, solange die Messung Nein sagt.** Der Rueckzug
    spart 40,7 % Suchen und verpasst dabei 38,8 % der echten Treffer. Fuer
    einen Speicher, dessen Zweck das Wiederfinden ist, ist das der falsche
    Tausch -- Rechenzeit und ein verpasster Treffer sind nicht dieselbe
    Waehrung. Ursache ist klein: der Zustand haengt an der SITZUNG statt am
    THEMA, also bestraft er das naechste Thema fuer das Schweigen des
    vorigen. Nacharbeit laeuft, Schranke: hoechstens 5 % verpasste Treffer,
    sonst wird der Rueckzug verworfen.
  * **Der naive Zugriffsmelder haette eine Massenmigration gemeldet** (754
    Schreibzeilen, 380 Knoten, NULL Lesevorgaenge, Faktor 2,04). Er zaehlt
    jetzt nur lesende Aktionen; die Rot-Probe dazu ist festgehalten.

  **Eine Sperre wurde verkleinert, ohne ihre Begruendung anzutasten:** Der
  Profilschalter gehoert in `knowledge_config` (Schluessel-Wert) und nicht ins
  Schema -- eine Zeile, kein Feld. Damit haengt B2 nur noch an der Achse.
    einem anderen Arbeitsbaum (`baum-20260818T114527`, seit 10,5 h). Es wird
    ausschliesslich committet, was die Agenten dieses Laufs angefasst haben.
* 2026-08-21T01:30 -- B2 fertig (`56602630`). A2 nach Messung verworfen, siehe §7. Vorrichtungsfehler aus B1 behoben (`8d2f99ae`); die sechs uebrigen Fehler derselben Datei sind vorbestehend, in einem Arbeitsbaum auf 1611398b nachgewiesen.
