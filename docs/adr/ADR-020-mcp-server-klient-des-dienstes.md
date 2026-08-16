# ADR-020: Sollen die MCP-Server Klienten des Dienstes werden, statt selbst zu schreiben?

**Stand** 2026-08-15T00:00:00+0200
**Status** ANGENOMMEN — Betreiberfreigabe 2026-08-15T12:40:00+0200, wörtlich:
„ADR-020 - Mach das wie oben beschrieben, Freigabe erteilt" (Knoten `b6b5a483`).
**Nicht gebaut.** Bindende Reihenfolge: erst echte Ausweisprüfung auf jedem schreibenden
Endpunkt, dann die 12 schreibenden Werkzeuge, dann erst die 13 lesenden.

*Bis zum 2026-08-16T12:10 stand hier weiterhin „Vorschlag — Entscheidung offen". Die
Freigabe lag seit einem Tag im Speicher, die Datei war nicht nachgezogen — und eine
brainlehr-Sitzung baute daraus die Warnung „nicht bauen, Entscheidung offen". Laufen
Datei und Speicher auseinander, gilt der jüngere Stand.*
**Betrifft** `knowledge_mcp_server.py`, `berichte/entscheidungen_server.py`, `kern/ausweis.py`,
`docs/G5_SYSTEMBENUTZER.md`, Linie G (`PLAN_GESAMT_2026-08-13.md`)
**Entscheider** Betreiber — diese ADR entscheidet nichts, sie legt die Rechnung vor

Sieht der Code an einer Stelle anders aus als hier beschrieben: an den Code halten, Abweichung
melden.

## Anlass

`docs/G5_SYSTEMBENUTZER.md` (heute erstellt, Commit `259672ce`) hat gemessen: 8 Kategorien
greifen auf `brainlehr.db` zu, 6 davon schreibend, alle unter der Anmeldekennung `lehrmacbook`.
Ein zweiter Systembenutzer für den Bestand bricht sieben dieser acht Kategorien — außer
Kategorie 2, der App. Die App (`app/`) greift laut Grep in `app/Sources` mit 0 Treffern für
`sqlite3`/`.db` **nicht mehr direkt zu** (Commit `648432e`, „die App gebiert den Dienst nicht
mehr — sie ist sein Klient"). G5 selbst schlägt für die MCP-Server einen Ausweg vor, der die
Wirkung fast aufhebt: eine gemeinsame Gruppe (`660`/`770` statt `600`/`700`) statt eines echten
Trennschnitts — wer in der Gruppe ist, darf weiter direkt schreiben.

Die Frage dieser ADR: **Soll `knowledge_mcp_server.py` denselben Weg gehen wie die App — kein
eigener `sqlite3.connect`, sondern HTTP-Klient von `berichte/entscheidungen_server.py`?**

## 1. Was der MCP-Server heute wirklich schreibt (gemessen, `knowledge_mcp_server.py`)

Der Server exponiert 25 Werkzeuge über eine `TOOLS`-Dispatch-Tabelle
(`grep -n '^    "[a-z_]*": {'` im `TOOLS`-Block). Für jedes Werkzeug wurde die zugehörige
Handler-Funktion (Grenze: nächste `^def `) auf `INSERT INTO`/`UPDATE `/`DELETE FROM`/
`conn.commit()` durchsucht:

| schreibend (12) | Treffer | rein lesend (13) | Treffer |
|---|---|---|---|
| `knowledge_add` | 2 | `knowledge_anmelden` | — (kein `def`, reine Identitätsauflösung) |
| `knowledge_update` | 4 | `knowledge_browse` | 0 |
| `freigabe_setzen` | 4 | `knowledge_read` | 0 |
| `knowledge_zurueckziehen` | 5 | `knowledge_search` | 0 |
| `knowledge_freigeben` | 2 | `kettenerklaerung_erklaeren` | 0 |
| `knowledge_relation_add` | 1 | `knowledge_relation_list` | 0 |
| `knowledge_relation_update` | 2 | `annahme_liste` | 0 |
| `knowledge_relation_remove` | 1 | `lesson_query` | 0 |
| `annahme_erfassen` | 4 | `knowledge_sitzung` | 0 |
| `annahme_entscheiden` | 2 | `knowledge_modell` | 0 |
| `lesson_record` | 2 | `knowledge_stats` | 0 |
| `lesson_update` | 3 | `knowledge_trust_score` | 0 |
| | | `kurator_lauf` | 0 |

**Zahl: 12 von 25 Werkzeugen schreiben, 13 lesen nur.** Jedes schreibende Werkzeug ruft
`sqlite3.connect(DB_PATH)` (Zeile 608, `get_db()`) direkt auf — ohne Ausweis-, Rollen- oder
Widerrufsprüfung durch den Dienst, weil der Dienst dabei gar nicht beteiligt ist.

## 2. Was ein Umbau kosten würde — Endpunkte des Dienstes, gemessen

`berichte/entscheidungen_server.py` (1237 Zeilen) hat heute 7 `GET`- und 9 `POST`-Pfade
(`do_GET`/`do_POST`, gemessen per Lesen der Methode):

- **GET (lesend):** `/api/stand`, `/api/raum`, `/api/vergleich`, `/api/echtkorpus`,
  `/api/quellenbestand`, `/api/quellenliste`, `/api/ausweisliste`.
- **POST (schreibend/handelnd):** `/api/eskalation`, `/api/eilmeldung`, `/api/siegbedingung`,
  `/api/nachtschicht`, `/api/abrufweg`, `/api/fundstelle`, `/api/domaene-import`,
  `/api/ausweis-anlegen`, `/api/ausweis-einladen`.

**Keiner dieser 16 Endpunkte bildet die generischen Wissens-Operationen ab** (Knoten anlegen/
ändern, Lehren, Annahmen, Relationen, Suche, Browse). Ein Umbau bräuchte — grob, ein Endpunkt
pro Werkzeug oder eine generische `/api/mcp/<werkzeug>`-Weiche — **in der Größenordnung der 25
heutigen `TOOLS`-Einträge** neue Rumpfschnittstelle, nicht eine Handvoll.

**Die Herkunftsprüfung des Dienstes ist heute browser-spezifisch und trägt nicht ohne Weiteres.**
`Handler._herkunft_ok()` (Zeile 867) prüft ausschließlich den `Origin`-Header gegen
`http://127.0.0.1:<port>` — kommentiert im Code selbst als Fund O2. Das ist eine Schranke, weil
**Browser** bei Cross-Origin-POST immer einen Origin-Header setzen, den eine fremde Webseite
nicht fälschen kann. Ein MCP-Server ist kein Browser: ein Python-`requests`-Aufruf setzt jeden
Origin-Header, den der Code will. Für MCP-Klienten wäre diese Schranke **wirkungslos**, nicht nur
schwächer — sie müsste durch etwas ersetzt werden, das eine Kennung wirklich prüft. Der einzige
mit Ausweis versehene Pfad ist heute `/api/ausweis-anlegen`/`/api/ausweis-einladen`
(`_ausweis_aufrufen`, ruft `pflege/ausweis_start.sh`), alle anderen 14 Endpunkte kennen keinen
Ausweis.

## 3. Was man gewinnt — und die Rechnerfrage

Über G5 hinaus: **ja, das ist der Unterschied, den der Betreiber gefragt hat.** Ein Dienst, den
nur ein HTTP-Klient anspricht, ist grundsätzlich auf einen anderen Rechner verschiebbar — die App
(Kategorie 2) demonstriert das bereits strukturell, auch wenn sie heute ebenfalls an
`127.0.0.1` gebunden ist. Voraussetzung dafür, laut ADR-018 (Wirkungsvorrat/Wirkung Null) und dem
dortigen Fund, dass die App **nicht** signiert/sandboxed ist (`codesign -dv`: `adhoc`, kein
`TeamIdentifier`): **fällt die Bindung an `127.0.0.1`, ist die Origin-Prüfung aus Abschnitt 2 die
einzige Instanz zwischen Netz und Bestand, und sie ist genau die Prüfung, die für Nicht-Browser-
Klienten wirkungslos ist.** Ohne einen echten, ausweisgeprüften Zugang auf jedem schreibenden
Endpunkt macht „auf einen anderen Rechner verschiebbar" den Bestand für jeden im selben Netz
erreichbar, der die 9 POST-Pfade kennt. Der Ausweis müsste vom Merkmal (heute: Datei, die
derselbe Benutzer schreiben darf, den sie einschränken soll — ADR-018, Abschnitt „Fast alles ist
Merkmal") zu einer echten Sperre werden, **bevor** die Bindung fällt.

## 4. Was man verliert (gemessen bzw. am Code nachvollzogen, nicht nur vermutet)

- **Ohne laufenden Dienst kein Wissenszugriff mehr.** Heute: `sqlite3.connect` funktioniert,
  solange die Datei lesbar ist, unabhängig von jedem Prozess. Nach dem Umbau: jeder der 25
  `TOOLS`-Aufrufe hängt am `ThreadingHTTPServer` aus `berichte/entscheidungen_server.py`
  (`main()`, Port 8799). Fällt der Dienst — Absturz, Neustart, Update — sind alle MCP-Werkzeuge
  tot, nicht nur die schreibenden. Heute ist nur der Dienst selbst so verwundbar, das Wissensnetz
  nicht.
- **Ein Netzaufruf statt eines Dateizugriffs je Abruf.** `knowledge_search`/`knowledge_read`
  werden nach Caveman-Kompressionsregel (`MEMORY.md`, „Kontext frisst Werkzeugausgabe") gerade
  wegen ihrer Häufigkeit genutzt — jeder Treffer zahlt sich über die Sitzung neu. Ein lokaler
  HTTP-Umweg über Loopback ist typischerweise niedrig-einstellig in Millisekunden, aber es ist
  eine zusätzliche Fehlerquelle (Timeout, Verbindung abgelehnt) gegenüber einem reinen
  Funktionsaufruf, und **nicht gemessen** — diese ADR behauptet keine Zahl dafür.
- **Mehr laufende Prozesse.** Heute läuft kein eigener Dienstprozess für das Wissensnetz nötig;
  jede MCP-Sitzung genügt sich selbst. Nach dem Umbau ist der Dienst eine zusätzliche
  Betriebsvoraussetzung mit eigenem Lebenszyklus (`dienst/de.brainlehr.dienst.plist`,
  `RunAtLoad`+`KeepAlive`), die vorher für das Wissensnetz nicht existierte.
- **Der Dienst wird zum Generalschlüssel für zwei bisher getrennte Bestände.** Er bediente bisher
  Entscheidungsoberfläche + Domänen-Import + Ausweis-Brücke; käme das Wissensnetz dazu, hinge ein
  Ausfall oder eine Schwachstelle des einen Dienstes an beiden Beständen zugleich.

## 5. Reihenfolge, falls entschieden wird

Nicht als Liste, als Folge, weil jeder Schritt den nächsten entwertet, würde er vorgezogen: Erst
muss die Origin-Prüfung aus Abschnitt 2 durch eine echte Ausweisprüfung auf **jedem** schreibenden
Endpunkt ersetzt sein — sonst öffnet der Umbau selbst die Lücke, die G5 schließen sollte, nur an
anderer Stelle. Erst danach die 12 schreibenden Werkzeuge aus Abschnitt 1 auf neue Endpunkte
ziehen (schreibend zuerst, weil sie der eigentliche G5-Anlass sind), erst danach — wenn überhaupt,
siehe Abschnitt 4 — die 13 lesenden hinterher, weil deren Umzug den größten laufenden Nutzen
(Kontext sparen durch günstigen Abruf) am stärksten unter das Dienst-Ausfallrisiko stellt. Vorher
zu klären, unabhängig von der Reihenfolge: ob G5 (Systembenutzer + Gruppenrechte) parallel dazu
noch gebraucht wird, oder ob dieser Umbau G5 ersetzt, weil dann kein MCP-Prozess mehr direkt auf
die Datei zugreift.

## Die Frage, die der Betreiber entscheidet

**Werden die MCP-Server (12 schreibende, 13 lesende Werkzeuge) zu HTTP-Klienten von
`berichte/entscheidungen_server.py` umgebaut — mit den in Abschnitt 5 genannten Voraussetzungen,
insbesondere einer echten Ausweisprüfung statt der heutigen Origin-Prüfung auf jedem schreibenden
Endpunkt — oder bleibt es bei G5s Gruppenlösung (Bestand bekommt einen eigenen Systembenutzer,
MCP-Prozesse bleiben direkte, aber gruppenberechtigte Schreiber)?**
