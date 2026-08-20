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
| A2 | -- | Rueckzug bei Leerlauf, gegen die Nulllinie 37,8 % |
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
    einem anderen Arbeitsbaum (`baum-20260818T114527`, seit 10,5 h). Es wird
    ausschliesslich committet, was die Agenten dieses Laufs angefasst haben.
