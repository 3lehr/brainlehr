# Plan: Betriebsprofile, Enterprise-Achsen und drei Abruf-Lücken

Angelegt 2026-08-20T20:46:38+0200. Auftrag des Betreibers vom 2026-08-20, drei Punkte:
(1) die Lücken schließen, die der Wettbewerbsvergleich zeigte, (2) die am
2026-08-18 auf DEFERRED gestellten Enterprise-Achsen jetzt bauen, (3) vor der
Installation die Wahl Einzelplatz/Unternehmen lassen — **mit späterem Wechsel**.

## Die zentrale Einsicht: 3 ist der Schalter für 2, nicht ein Zusatz

Ohne Profilwahl müsste Mandantenfähigkeit immer vorhanden sein und würde den
Einzelplatz belasten. Mit ihr ist `local-first` der Auslieferungszustand und
`corporate` ein Profil, das etwas **zuschaltet**. Genau das steht bereits im
Katalog: `BDW-P05` nennt das Ziel „governierter Local-first-Memory-Kern",
`BDW-E17` hält fest, dass Betriebsprofile „später entschieden" werden.
Punkt 3 ist diese Entscheidung.

**Und daraus folgt die bindende Reihenfolge.** Der geforderte Wechsel
Einzelplatz → Unternehmen ist nur möglich, wenn die Mandanten-Achse von
Anfang an im Schema liegt — unbenutzt, aber da. Sie nachträglich einzuziehen
hieße, 5.239 Bestandseinträgen rückwirkend einen Mandanten zuzuschreiben, den
sie nie hatten. Das ist keine Frage des Füllstands: Es gilt bei null
Einträgen genauso wie bei einer Million, weil sich nicht rekonstruieren
lässt, wem ein Altbestand gehörte.

## Gemessener Ist-Stand (2026-08-20)

| | |
|---|---|
| Bestand | 5.239 Knoten, 1.171 Lehren, 35 Tabellen, 63 Trigger |
| Katalog | 56 BDW-Zeilen, davon 16 Sprints offen |
| Enterprise-Achsen | E01, E03, E04, E05, E06, E11, E17, E19 auf DEFERRED |
| Produktgates | 24 von 24 sind **Baulücken, nicht Testlücken** (Stichprobe 2026-08-18) |

**Korrektur an der Lückenliste**, gemessen statt übernommen: Von den sechs
Punkten aus dem Wettbewerbsvergleich sind nur **drei** echte Lücken
(0 Treffer im Quelltext). Zwei existieren bereits, einer ist gegenstandslos:

| Punkt | Befund |
|---|---|
| Widerspruchserkennung | **fehlt** — 0 Treffer auf `widerspruch\|contradict\|konflikt` |
| Rückzug bei Leerlauf | **fehlt** — 0 Treffer auf `backoff\|leerlauf` |
| Sicherung gegen tote Dienste | **fehlt** — 0 Treffer auf `circuit\|breaker\|aussetzer` |
| Vertrauen, das sich bewegt | **existiert** als `knowledge_trust_score`, fünf Nutzungsgrößen. Beim Bau wurde ausdrücklich Hermes' `store.py` verglichen (2026-08-07). Bewusst anders: berechnet statt selbst gemeldet |
| Kein Datenverlust bei Sitzungswechsel | `session_checkpoint_*` vorhanden — **zu prüfen**, ob es beim Wechsel flusht |
| Absturzfeste Schreibschlange | **gegenstandslos** — brainlehr schreibt synchron in SQLite, es gibt keine Warteschlange, die ein Absturz verlieren könnte |

## Reihenfolge, und wo sie bindend ist

**B1 — Profilbegriff und Mandanten-Achse im Schema** (bindend zuerst)
Eine Spalte `mandant` auf allen Bestandstabellen, Vorgabewert `einzelplatz`.
Ein Profilschalter, der heute nur zwei Werte kennt. Kein Rollenmodell, keine
Rechte — nur die Achse. Danach ist der spätere Wechsel eine Datenänderung
statt eines Umbaus.

**B1b — Sprachachse, im selben Zug** (nicht bindend, aber hier billig)
Eine Spalte `sprache` neben `mandant`. Anlass ist die Betreiberfrage vom
2026-08-20: „wenn wir Apps fürs Handy bauen, haben wir aber Mehrsprachigkeit?"

**Der Abruf braucht sie NICHT** — gemessen am 2026-08-20: eine deutsche Frage
trifft den gleichbedeutenden englischen Text mit Kosinus 0,819, weit über der
Schwelle 0,65. Genau deshalb antworten die 1.637 englischen NASA-Einträge
heute auf deutsche Fragen, ohne dass jemand sie übersetzt hat.

**Die ANZEIGE braucht sie**, und zwar als WCAG-Auflage, nicht als Komfort:
`3.1.1 Language of Page` / `3.1.2 Language of Parts`. Ein Vorleseprogramm
liest englischen Text mit deutscher Aussprache vor, wenn die Sprache nicht
ausgezeichnet ist — das macht den Inhalt unverständlich. Heute liefert
`knowledge_search` einen NASA-Eintrag aus, ohne dass eine App wüsste, dass er
englisch ist; sie könnte ihn also gar nicht regelkonform darstellen.

**Es braucht genau EIN Feld, kein Übersetzungssystem.** Kein `titel_en`, keine
parallelen Fassungen, keine Pflege: Ein Eintrag hat die Sprache, in der er
geschrieben wurde. Übersetzung ist ein Problem der Ausgabe, nicht des
Speichers — die App entscheidet zur Laufzeit.

**Der Unterschied zur Mandanten-Achse, und er ist der Grund, warum B1b nicht
bindend ist:** Einen Mandanten kann man einem Altbestand nicht rückwirkend
zuschreiben. Eine Sprache steht im Text. Gemessen mit einer Heuristik aus
36 Stoppwörtern, ohne neue Abhängigkeit: 758 von 770 richtig, 9 unklar
(/nasa-llis 200/200, /germanquad 198/200, /brainlehr 197/200, /methodik
163/170). Sie ließe sich also jederzeit nachziehen.

Sie fährt trotzdem hier mit, weil sie in diesem Zug fast nichts kostet: Wer
ohnehin eine Spalte hinzufügt und alle Zeilen einmal anfasst, nimmt die
zweite gratis mit. Ein eigener Durchlauf über 5.239 Zeilen später kostet
mehr als die Spalte jetzt.

**Offen und ausdrücklich nicht entschieden:** Französisch liegt bei 0,630 und
fällt damit unter die Schwelle 0,65 — dieselbe Sache, andere Sprache, Treffer
verworfen. Die Schwelle ist an deutschem Material kalibriert und
sprachübergreifend nicht gleich streng. Heute folgenlos (es gibt kein
französisches Material), vor einer Öffnung nach außen zu messen.

**B2 — Der Wechsel selbst**, als Werkzeug mit Rot-Probe: Bestand wandert
geschlossen auf einen benannten Mandanten. Ein Rückweg gehört dazu.

**B3 — Enterprise-Achsen** (E01, E03, E04, E05, E06, E11, E19), erst danach.
Sie setzen die Achse aus B1 voraus; jede vorher gebaute Rechteprüfung hätte
nichts, worauf sie prüfen könnte.

**A1–A3 — die drei Abruf-Lücken.** Hängen an keinem der beiden und können
sofort und parallel laufen:
* **Widerspruchserkennung.** holographic vergleicht Jaccard-Überlappung gegen
  Inhaltsähnlichkeit (`retrieval.py:355-430`, Schwelle 0,3, O(n²) mit Deckel
  bei 500). brainlehr hat echte Einbettungen und kann es feiner — hohe
  Entity-Nähe bei niedriger Bedeutungsnähe. Direkt einschlägig für
  Normkonflikte, die heute nur auffallen, wenn ein Mensch stolpert.
* **Rückzug bei Leerlauf.** Der Recall lieferte 37,8 % leer und fragte
  unbeirrt weiter. honcho verbreitert das Intervall je leerem Treffer, Deckel
  bei 8 (`__init__.py:1015-1021`).
* **Sicherung gegen tote Dienste.** mem0 pausiert nach 5 Fehlern für 120 s
  (`__init__.py:294-335`). Bei uns heute zweimal gebraucht: Ollama war weg,
  und niemand merkte es.

## C — Erststart: der Einrichtungsassistent

Betreiberzusatz vom 2026-08-20: „wir brauchen beim erstart eines neuen User
einen Chat Einrichtungs Assistenten, ein startenden, die Möglichkeit wissen
aus anderen nicht brainlehr Systemen zu installieren, und wir sollten Dinge
wie bsi usw. zum Import vorschlagen!"

**Das löst zugleich die Einstiegshürde**, die am selben Tag benannt wurde: Eine
Anmeldung kostete einmal über eine Stunde und vier Fehlversuche („das rafft so
keine Sau"), und von vier eingetragenen Ausweisen ließ sich am 2026-08-19 nur
einer auflösen. Ein Assistent, der durch die Einrichtung führt, ersetzt die
Handarbeit — unabhängig davon, ob im Profil `standalone` überhaupt ein Ausweis
Pflicht ist.

**Die Bauform ergibt sich aus der Bauart des Systems:** brainlehr ist ein
MCP-Server, also läuft die Einrichtung IM Chat, nicht in einem zweiten
Programm. Ein Werkzeug `einrichtung_starten`, das beim ersten Aufruf gegen
einen leeren Bestand von selbst anspringt. Kein Installer, kein Fenster,
keine zweite Oberfläche, die gepflegt werden müsste.

**C1 — Was der Assistent fragt.** Vier Dinge, mehr nicht:
* Profil: `standalone` oder `multiuser` (siehe B1)
* Sprache des eigenen Materials (siehe B1b)
* Einbettungsdienst: erreichbar? Welches Modell? — sonst entstehen Einträge
  ohne Vektor und sind über die Bedeutungssuche unauffindbar, ohne dass ein
  Fehler erschiene. Genau das ist am 2026-08-20 dreizehnmal passiert.
* Welche Kataloge sollen mit?

**C2 — Kataloge zum Mitnehmen, vorgeschlagen statt versteckt.** Was heute
schon vorliegt und nur niemand anbietet:

| Katalog | Umfang | liegt |
|---|---|---|
| BSI Stand der Technik | 951 Controls | als JSON im Verbund |
| NASA LLIS | 1 637 Einträge | bereits im Bestand, englisch |
| WCAG 2.2 AA | Regeltext | `~/.claude/regeln/wcag.md` |

Wichtig ist die Gattung: Solche Kataloge werden als `nachschlagewerk`
eingelesen, nicht als `arbeitsbestand` — sonst verdünnen 951 fremde Controls
die eigene Trefferquote. Das Feld gibt es bereits (`gattung`).

**C3 — Wissen aus fremden Systemen.** Nach Aufwand geordnet, gemessen am
2026-08-20:

* **`holographic`** speichert in einer einzigen SQLite-Datei
  (`$HERMES_HOME/memory_store.db`, Tabelle `facts` mit `category`, `tags`,
  `trust_score`). Der einzige lokale Anbieter der acht ist damit **ohne API
  direkt auslesbar** — der billigste Fremdimport, den es gibt.
* **Markdown-Ordner** (Obsidian, Logseq, ein Verzeichnis voll Notizen). Kein
  Anbieter nötig, und vermutlich der häufigste reale Fall.
* **Cloud-Anbieter** (mem0, honcho, supermemory, hindsight): nur über deren
  API, also mit Schlüssel des Nutzers. Zuletzt, weil aufwendig und weil der
  Nutzer dann ohnehin schon woanders ist.

**Die Grenze, die für jeden Import gilt:** Ein fremder Eintrag hat keine
Herkunft im Sinne von brainlehr — keiner der acht erzwingt ein solches Feld
(gemessen am Quelltext, vier Agenten, vier Fehlanzeigen). Der Import darf
deshalb **keine Herkunft erfinden**. Er trägt ein, woher er stammt
(„importiert aus holographic memory_store.db am <Zeitpunkt>"), und das ist
ehrlich: Die Aussage selbst bleibt unbelegt, nur ihr Weg ist bekannt.

## D — Zugriffsmuster: was Krypto nicht kann

Betreiberidee vom 2026-08-20: „zieht ein user/mitarbeiter knoten die er sonst
nicht zieht, zieht er besonders viele usw."

**Warum es diese Schicht braucht:** Gegen den, der eine rohe Kopie der Datei
zieht, hilft keine Verschlüsselung — er umgeht jede Schnittstelle. Was bleibt,
ist, es zu BEMERKEN. Monitoring macht Zugriff nachweisbar, nicht unmöglich;
es ist die dritte Schicht, nicht die erste.

**Die Grundlage liegt vor:** `access_log`, 22 478 Zeilen, mit `actor`,
`session`, `node_path`, `action`, `timestamp`. Es muss nichts Neues gesammelt
werden.

**GEMESSEN, bevor gebaut wird — und das Ergebnis widerlegt das naheliegende
Signal.** Menge taugt nicht:

| Sitzung | Lesen | versch. Knoten | je Knoten |
|---|---|---|---|
| `d695fd29` | 4 859 | 201 | **24,2** |
| `be48feea` | 1 684 | 214 | 7,9 |
| `6bb5aa2e` | 613 | 121 | 5,1 |

Die auffälligste Sitzung ist die harmloseste — sie hat dieselben 201 Einträge
24-mal gelesen. Ein Melder auf „viele Zugriffe" hätte den Falschen erwischt.

**Zwei Merkmale trennen, beide aus denselben Daten:**
* **Zugriffe je Knoten.** Arbeit wiederholt sich (5–24). Ein Abzug liest jeden
  Eintrag einmal — Faktor nahe 1. Umkehrung des naiven Signals.
* **Abdeckung.** Die breiteste Sitzung überhaupt berührte 214 von 5 240
  Knoten = 4 %. Wer auf 50 % zugeht, tut etwas, das in 20 Tagen Betrieb nie
  vorkam.

**Verworfen, weil gemessen unbrauchbar:** „Lesevorgänge je Suche" liegt bei
fast allen Sitzungen bei 0,0 — `search` wird ohne `node_path` protokolliert,
das Verhältnis ist nicht rechenbar. Klingt plausibel, liefe im Melder still
daneben.

**Die Lücke, ohne die der Melder Zierrat wäre:** Im Bestand gibt es KEINEN
Positivfall. Kein Lauf sieht nach Abzug aus — gut für den Betrieb, schlecht
für die Kalibrierung. Ein Melder, der nie ausgeschlagen hat, ist von einem
kaputten nicht zu unterscheiden. Abnahme deshalb: ein hergestellter Lauf, der
500 verschiedene Knoten je einmal liest, MUSS anschlagen; die 4-%-Sitzungen
des echten Bestands dürfen es NICHT.

## E — Wissen, das altert: der Speicher als Aufsicht über das Modell

Betreiberfrage vom 2026-08-20, in drei Schritten entwickelt: „was ist wenn ich
die richtige quelle schon bei der ersten suche brauche?" → „brainlehr sollte
erkennen: in welchem thema arbeitet der user, wie alt ist das modell, wie
wichtig ist aktuelles wissen" → „wir müssen ja nicht die quellen hinterlegen,
sondern einen prompt der auffordert danach zu suchen".

**Die Umkehrung der Rolle, und darin liegt die Tragweite.** Bisher ist
brainlehr ein Gedächtnis: Man fragt, es antwortet. Hier wird es zur Aufsicht
über das Modell — es müsste wissen, was das Modell NICHT wissen kann, bevor
dieses es behauptet.

Der Grund ist eine Eigenschaft von Modellen, die sie selbst nicht bemerken:
**Ein Modell hat keine Uhr.** Der Stichtag des am 2026-08-20 arbeitenden
Modells war Mai 2026 — rund drei Monate blind, und es antwortet auf eine
Frage von heute mit derselben Zuversicht wie auf eine von damals. An diesem
einen Tag ist es dreimal passiert: ein fremder Klient beschrieb brainlehr mit
Zahlen von früher, eine Lizenzangabe kam aus dem Gedächtnis, und ein
„unmöglich" wurde ungeprüft aus einer ADR übernommen.

**Warum das das Henne-Ei-Problem löst.** Die drei nötigen Größen sind alle VOR
der ersten Frage bekannt — es braucht keine zwölf erfolglosen Suchen:

| | woher | Stand heute |
|---|---|---|
| Thema | aus der Frage ableitbar | der Recall tut es bereits |
| Modellstichtag | steht im Kontext | ungenutzt |
| Verfallsrate des Gebiets | Eigenschaft des THEMAS, nicht der Frage | fehlt ganz |

Der dritte Punkt ist der Schlüssel: Man muss nicht wissen, was gefragt wird —
nur, dass Steuerrecht sich jährlich ändert und Zahlentheorie nicht.

**Der Zwecksatz sagt es bereits, nur für die falsche Hälfte:** „…und sagt
dazu, wie belastbar es noch ist." Gebaut ist das für den BESTAND (`gilt_bis`,
Geltung, Normrang). Was fehlt, ist derselbe Satz für das MODELL.

**Gemessener Ist-Stand (2026-08-20):**

| | |
|---|---|
| Knoten mit Verfallsdatum | **2 von 5 232** |
| Knoten, die das schreibende Modell festhalten | 610 von 5 232 |
| Verfallsrate je Themengebiet | existiert nicht |

`gilt_bis` ist praktisch ungenutzt, weil es je Eintrag gepflegt werden müsste.
Als Eigenschaft des ASTES wäre es billig: ein Wert je Gebiet statt 5 232
Einzelentscheidungen.

**E1 — Die Verfallsrate, aus drei Quellen (Betreiberentscheidung: alle drei):**

| Quelle | Blickrichtung | Kosten | was sie kann |
|---|---|---|---|
| Schätzung je Ast | keine | minimal | sofort da, ungenau |
| Widerrufsquote | rückwärts | braucht Historie | ehrlich, lernt erst nach dem Schaden |
| Gremienberatungen | **vorwärts** | Quellenanbindung | warnt, BEVOR etwas veraltet |

**E2 — Quellen werden nicht hinterlegt, sondern gesucht.** Betreiberentscheidung
vom 2026-08-20, und sie wendet ein bereits geltendes Hausprinzip an: Der
Startauftrag für neue Fachdomänen entsteht seit dem 2026-07-31 durch ein
Skript, das seine Quellen zum Erzeugungszeitpunkt LIVE liest — „kein
abgeschriebener Prompt, weil ein eingebackener Wissensstand ab dem nächsten
Tag falsch ist" (`/shared/arch/startauftrag-fuer-neue-fachdomaenen`,
`hub/scripts/domaenen_startauftrag.py`).

Eine gepflegte Quellenliste hat zwei Fehler, und der zweite wiegt schwerer:
Sie ist bei tausend Themen nie vollständig — und sie altert unsichtbar. Ein
AUFTRAG altert nicht, weil er nichts behauptet.

**Der Punkt, an dem es kippen würde:** Ein Modell, das nach Quellen sucht,
erfindet welche. Deshalb gilt die Belegpflicht aus dem vorhandenen
BGH-Prüfverfahren: zwei unabhängige Quellen, und ein Ergebnis ohne abrufbare
Fundstelle zählt als „nicht gefunden", nicht als Treffer. Sonst baut sich
brainlehr eine Liste plausibler Erfindungen auf — schlimmer als keine, weil
sie Vertrauen erzeugt.

**E3 — Die Liste wächst, statt gepflegt zu werden.** Jede erfolgreiche Suche
wird ein Eintrag mit Herkunft und Geltung. Beim ersten Mal in einem Gebiet
kostet es eine Suche; danach steht die Quelle im Bestand und meldet sich
selbst, wenn sie zu alt wird.

**E0 — DIE MESSUNG, DIE ÜBER DEN GANZEN STRANG ENTSCHEIDET (läuft):**
Wie viele Monate VOR Inkrafttreten war eine Rechtsänderung öffentlich
absehbar? Gemessen am eigenen Fall aus `L-049e01` (GEG → Nachfolgegesetz,
§§ 71–73 weggefallen; am 2026-08-17 wäre beinahe die alte Fassung als
geltendes Recht berichtet worden).

**Bei sechs Monaten Vorlauf ist E ein Frühwarnsystem. Bei zwei Wochen ist es
Aufwand ohne Ertrag — dann wird E1 auf die Schätzung je Ast reduziert und der
Rest fällt weg.** Kein anderer Schritt beginnt vor diesem Ergebnis.

## Verworfene Wege

* **Mandanten-Achse erst beim ersten Piloten** — der vom Betreiber geforderte
  Wechselweg wäre dann ein Umbau mit rückwirkender Zuschreibung. Verworfen
  aus Reihenfolge, nicht aus Menge.
* **Zwei getrennte Auslieferungen** (Einzelplatz-Zweig, Unternehmens-Zweig) —
  zwei Stände, die auseinanderlaufen, und der Wechsel wäre ein Umzug statt
  eines Schalters. `BDW-E17` sieht Profile ausdrücklich als Zuschaltung.
* **Vertrauens-Rückmeldung nach holographic-Vorbild nachbauen** — wir haben
  das Objektivere (Aufgriffsquote misst tatsächliche Nutzung, nicht die
  Selbstauskunft eines Modells). Verworfen als Rückschritt.

## Was bewusst NICHT getan wird

* **Kein IdP-Anschluss ohne echten Piloten.** `BDW-E04` bindet SSO an den
  ersten Mehrbenutzer-Piloten. Ein gegen einen erfundenen IdP gebauter
  Anschluss prüft den Prüfstand, nicht die Sache.
* **Keine Datenregionen (E19)** ohne zweiten Standort — es gäbe nichts zu
  begrenzen. Preis: Die Zeile bleibt offen.
* **Kein neues Bewertungssignal.** `docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md`
  hält fest, warum zuerst die Wirkung des Abrufs gemessen wird.

## Woran sich Erfolg misst

| Schritt | Nachweis |
|---|---|
| B1 | Frischer Bestand und gewachsener Bestand tragen dieselbe Achse. Beide Ausgangszustände fahren, nicht nur der leere |
| B2 | Wechsel und Rückweg je einmal, mit Bestandszählung davor/danach |
| B3 | Je Achse ein **Negativtest**: der fremde Mandant sieht nichts. Ein Positivtest allein belegt keine Trennung |
| A1 | Mindestens ein Widerspruch, den heute niemand kennt — und eine gezählte Fehlalarmquote gegen den ECHTEN Bestand, nicht gegen gestellte Fälle |
| A2 | Leer-Anteil vor/nach, gegen dieselbe Nulllinie (37,8 %) |
| A3 | Nachstellprobe mit abgeschaltetem Dienst, wie bei `melder/modellwege.py` |
| C1 | Ein frisch angelegter Bestand führt durch die Einrichtung und ist danach benutzbar — gefahren auf einem leeren Bestand UND einem gewachsenen, nicht nur dem leeren |
| C2 | Ein eingelesener Katalog steht als `nachschlagewerk` da und senkt die eigene Trefferquote nicht — gemessen gegen dieselbe Nulllinie wie vorher |
| C3 | Ein Fremdimport trägt seinen Weg als Herkunft und erfindet keine |

## Offene Entscheidung für den Betreiber

Die Profilnamen. Vorschlag: `einzelplatz` und `unternehmen` — deutsch wie
der übrige Bestand, und `corporate` wäre das einzige englische Wort in einem
Schema, dessen Felder `freigabe`, `geltung` und `herkunft` heißen.
