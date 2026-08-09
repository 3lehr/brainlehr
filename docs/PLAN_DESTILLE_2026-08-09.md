# Plan: Was brainlehr von der Destille lernt — und was es besser kann

Stand: 2026-08-09T06:05:00+0200 · Anlass: Betreiber, nach dem Video zu „Distill" (YouTube YU9GscXWK-E) · Grundlage: eigene Messungen vom 2026-08-08/09, alle unten mit Zahl

## Wo steht was — damit dieser Plan nicht zur zweiten Wahrheit wird

Dieses Dokument und der Wissensspeicher sagen teilweise dasselbe. Das ist die Fehlerklasse, die am 2026-08-09 an zwei Fassungen desselben Katalogpfades aufgeflogen ist: Zwei Fassungen laufen auseinander, die Frage ist nur wann. Darum die Arbeitsteilung, ab hier verbindlich:

| | gehoert hierhin (.md) | gehoert in den Speicher |
|---|---|---|
| **Was** | Reihenfolge, Begruendung, verworfene Wege, Messreihen | die ENTSCHEIDUNG selbst, als Knoten mit Herkunft und Geltung |
| **Warum** | ein Gedankengang hat eine Richtung, ein Bestand hat keine | nur der Speicher kann sich weigern, zaehlen und von selbst ausliefern |
| **Bei Widerspruch gilt** | — | **der Knoten** |

**Der Plan verweist, statt nachzuerzaehlen.** Wo hier eine Entscheidung ausformuliert steht, die als Knoten existiert, ist die Knotenkennung genannt und der Knoten die massgebliche Fassung. Entscheidungen dieses Plans, die noch KEINEN Knoten haben, sind daran erkennbar, dass keine Kennung dabeisteht -- das ist kein Versehen, sondern der Hinweis, dass sie noch nicht bindend abgelegt sind.

Bekannte Knoten zu diesem Plan: `b6305304` (drei Normachsen), `d6f0dd0f` (brainlehr bleibt privat), `745f7ac1` (Recall fragt den Prompt, nicht das gelesene Material), `e504b10c` (Tokenspalten ohne Zeilenschreiber), `4361e92d` / `ad4bb80e` (UN- und EU-Nachhaltigkeitsziele als Nachschlagewerk).

## Der gemessene Ist-Stand, nicht der vermutete

| Frage | gemessen | wo |
|---|---|---|
| Trifft der Abruf? | **0 von 35** Prüffällen, in jeder Schalterstellung | `abrufguete.py` |
| Was kostet er? | **2512 Zeichen je Prompt**, 40 % der Fälle leer | `liefermenge.py` |
| Warum trifft er nicht? | 12 von 15 Ziel-Lehren scheitern an `MIN_HITS=3`; im Bedeutungskanal liegt das Ziel auf Rang 7–597 von 668, `MAX_LESSONS=2` erreicht es nie | dito |
| Wer stuft Normen ein? | **62 von 71** Normen hat die Maschine selbst eingestuft (`claude-code/opus-5`) | `knowledge_nodes.norm_entschieden_von` |
| Wieviel Bestand ist Fremdimport? | 1638 NASA-Knoten gegen 376 eigene | `knowledge_nodes.path` |
| Kommt gesammelte Literatur an? | 56 Paper in zwei Zitationsnetzen, **10** als Knoten im Speicher, **1** Knoten mit PDF-Quelle | `citation-network.json` + `knowledge_nodes.source` |

**Der rote Faden durch alle sechs Zeilen:** Es fehlt nicht an Wissen und nicht an Werkzeugen. Es fehlt an **Stufen**. Alles liegt sofort gleich weit vorn, gleich gültig, gleich auffindbar — und deshalb findet der Abruf nichts.

## Was die Destille besser macht (drei Dinge, gemessen an unseren Zahlen)

**1. Entstehung nach Bereich, nicht nur Auslieferung nach Bereich.** Dort entsteht Wissen projektlokal und wandert erst nach Prüfung nach oben. Bei uns landet jeder Fund sofort im globalen Bestand. Das erklärt die 1638-zu-376-Zeile: Der NASA-Import verdünnt jede Suche, weil es keine Ebene gibt, auf der er nicht mitspielt.

**2. Promotion als eigener, bestätigter Vorgang.** Nicht „ist wichtig, kommt rein", sondern: das System schlägt vor, der Mensch bestätigt, dann wandert es. Wir haben nur den Sofort-Weg.

**3. Ein festes Muster je Typ.** Jedes Paper dort: Kernaussage, Methodik, Vergleich, Bewertung, Zitation — immer gleich. Unsere Knoten haben Freitext in `summary`/`content`, und genau deshalb sind sie so ungleich brauchbar.

## Was wir besser machen, und es ist nicht wenig

Zahlen. Sein System sieht funktionierend aus und er ist zufrieden; ob der Abruf das Richtige liefert, ist dort nicht gemessen. Unseres sah gestern auch funktionierend aus. Dazu: Herkunftspflicht mit Umschreibsperre, Geltungsdauer, Rücknahme mit Begründung, Zugriffsprotokoll, Eskalation wiederkehrender Lehren. Nichts davon aufgeben.

**Und eine Warnung aus seinem eigenen Mund, die er nicht misst:** „Je mehr man der KI gibt, desto mehr verwirrt man sie." Er hält das mit kurzen Texten klein. Wir haben die Zahl dafür — 2512 Zeichen je Prompt — und sollten sie zur Kennzahl machen, nicht zur Anekdote.

## Vier Schritte, in bindender Reihenfolge

### S1 · Reifegrad MESSEN statt zuweisen (zuerst, weil billig und weil es eine gemessene Fehlstelle schließt)

Der Deckel aus dem Video („Maschine darf höchstens *Entwurf*") ist die halbe Antwort. Die andere Hälfte, vom Betreiber eingewandt: *bei vielen Sachen kann ich den Reifegrad selbst nicht bestimmen.* Ein Deckel, der auf ein Urteil wartet, das niemand fällen kann, erzeugt eine Halde statt einer Prüfung.

**Darum abgeleitet statt vergeben.** Die Bauform existiert bereits in `konfidenz.py` mit drei Regimen: *beobachtbar* (Bezug ist eine Datei, Änderungen zählbar → Zahl), *deklariert* (Ausgangswert), *unbeobachtbar* (keine Zahl, dafür ein Fälligkeitsdatum). Reifegrad bekommt dieselbe Dreiteilung mit eigenen Belegquellen:

- **abgeleitet** — der Bezug ist beobachtbar (Datei existiert, Commits zählbar), die Aussage hat einen Prüfvermerk, oder sie ist mehrfach unabhängig aufgetreten (`occurrences`).
- **erklärt** — ein Mensch hat entschieden, mit Grund. Das bleibt möglich und schlägt jede Ableitung.
- **unbestimmt** — nichts davon. **Kein Makel, sondern eine Fälligkeit**: der Knoten kommt auf Wiedervorlage, nicht in den Papierkorb.

Der Deckel gilt dann nur noch für **Normrang 1 und 2**: Was für alle gelten soll, entscheidet ein Mensch. Alles andere leitet sich ab. Das trifft die gemessenen 62 Fälle, ohne den Betreiber zu Urteilen zu zwingen, die er nicht hat.

*Nicht getan:* Reifegrad rückwirkend auf 2020 Knoten rechnen. Erst der Mechanismus, dann ein Lauf.

### S1b · Nachschlagewerke sind eine eigene Gattung — und die Belegquelle für S1

**Gemessen 2026-08-09, nachdem der Betreiber die Einordnung korrigiert hat:** Der NASA-Bestand kam als `anlass=skript` aus einem Datensatz für Themenmodellierung (`github.com/NASADatanauts/llis_topicModel`, `data/llis.csv`). Alle 1638 Knoten stehen auf `norm_entscheidung=offen` — sie tragen keine einzige Norm. Und sie wurden in der gesamten Protokollhistorie **3 mal** gezogen.

Das ist kein Wissen des Hauses. Es ist ein **Nachschlagewerk**: wissenschaftlich gewonnene Lebensweisheiten, wie eine Normensammlung. Man schlägt darin nach, es drängt sich nicht auf.

**Erste Folge — eine eigene Tür statt eines Platzes am Tisch.** Nachschlagewerke werden als Gattung gekennzeichnet und nehmen am automatischen Abruf NICHT teil. Sie bekommen eine gezielte Abfrage („hat das jemand vor uns bezahlt?"). Damit misst der Prüfstand wieder unser Wissen statt eines Wörterbuchs — heute sind 81 % des Bestands ein solches Werk, und der Abruf trifft 0 von 35.

*Grenze, die nicht verschwiegen wird:* Die 3 Zugriffe beweisen für sich genommen nichts — sie könnten auch heißen, dass der Abruf es nie an die Oberfläche bringt. Beides ist gemessen (1 von 5799 Kanten verlässt die Wolke; 0 von 13 Entsprechungen waren neu). Zusammen tragen die Befunde den Schluss, einzeln keiner.

**Zweite Folge, und sie ist der eigentliche Gewinn: das Nachschlagewerk wird zur Belegquelle für den maschinellen Rang aus S1.**

Die offene Frage von S1 lautete: Wenn nicht der Mensch die Gültigkeit verbürgt — was dann? Antwort: `belegrang`, und dort steht die Stufe **`fremdbericht`** bisher ohne Quelle. Eine Regel von uns, die im Nachschlagewerk eine Entsprechung findet, ist unabhängig gestützt — aus einem anderen Fach, teuer bezahlt, von niemandem hier beeinflusst. Genau das kann keine unserer eigenen Quellen leisten.

Belegt ist der Mechanismus bereits: Von 13 gefundenen Entsprechungen waren **13 Bestätigungen** eigener Direktiven (Walkthrough-Doktrin, Rot-Probe, WCAG, Grenzwert-Regel) — zwei davon fast wortgleich, dreißig Jahre früher.

**Drei Regeln, ohne die daraus ein Gütesiegel-Automat wird:**

1. Bestätigung ergibt `fremdbericht`, **niemals** `gemessen`. Dass jemand anders dasselbe lernte, macht eine Regel unabhängig gestützt, nicht messbar. Der Unterschied ist der ganze Wert der Skala.
2. **Fehlende Bestätigung ist kein Gegenbeleg.** Das Werk deckt Ingenieursarbeit ab, nicht unsere ganze Welt — gemessen waren 6 von 39 Lehren an Hardware gebunden. Unbestätigt ist nicht widerlegt. Dieselbe Falle wie beim leeren Filter (L-36d092): Leere ist erst ein Befund, wenn sie einer sein kann.
3. Der Abgleich läuft über die **destillierte Behauptung**, nicht über den Wortlaut — auf beiden Seiten. Belegt: 1 von 5799 Wortähnlichkeits-Kanten überschreitet die Grenze. Dafür müssen auch unsere eigenen Regeln destilliert werden, nicht nur die fremden.

**Und der Widerspruchsfall fällt gratis ab:** Widerspricht eine Lehre dort einer unserer Regeln, ist das kein Gütesiegel, sondern ein Vorgang — dieselbe Bahn wie ein Normkonflikt.

**Der Quellenrang haengt am WERK, nicht an der Aussage.** Gemessen: 1876 verschiedene Quellenangaben, alle Freitext, keine Werk-Tabelle. Ohne sie muesste dieselbe NASA-Sammlung 1638 mal beurteilt werden. Einmal einstufen, 1638 mal erben -- und stellt sich ein Werk als schlechter heraus, sinkt alles daraus in einem Zug.

`fremdbericht` wirft heute eine Institution mit dreissig Jahren bezahlter Fehler und einen Mann mit einer Kamera in denselben Topf. Drei Merkmale trennen sie, in der Reihenfolge ihrer Haerte:

1. **Preis des Irrtums beim Urheber.** NASA-Lehren stammen aus Fehlern, die Geraete, Missionen und Menschen gekostet haben -- der Urheber hatte etwas zu verlieren. Ein Video kostet nichts, wenn es falsch ist. Das schaerfste Kriterium, weil es nicht vom Ansehen abhaengt, sondern vom Einsatz.
2. **Nachpruefbarkeit.** Nennt das Werk Einzelfall, Kennung, Datum -- kommt man an den Fall heran?
3. **Fremdes Verfahren.** Hat jemand ausser dem Urheber es geprueft, bevor es hinausging?

Daraus drei Stufen, grob genug zum Entscheiden:

| Stufe | Bedeutung | Beispiele |
|---|---|---|
| `belegt` | nachpruefbare Einzelfaelle **und** fremdes Verfahren | NASA LLIS, DIN, BSI |
| `berichtet` | nachvollziehbare Herkunft, keine fremde Pruefung | Fachartikel, Konferenzbeitrag, gute Doku |
| `bekundet` | eine Person sagt etwas | Video, Blog, Forenbeitrag |

**Gesamtordnung:** `gemessen` > `belegt` > `berichtet` > `bekundet`. Eine eigene Messung an unserem Code sticht die NASA -- sie hat unseren Fall nie gesehen.

**Die Warnung dazu, und sie betrifft genau das Video, das diesen Plan ausgeloest hat:** Der Quellenrang steuert, wieviel eine Bestaetigung NORMATIV wiegt. Er sagt nichts darueber, ob eine Idee brauchbar ist. Das Transkript war `bekundet` und hat zwei Dinge geliefert, die diesen Plan geaendert haben (Reifegrad, Promotion). Wer aus dem Quellenrang einen Ideenfilter macht, haette beides weggeworfen.

> **Ein `bekundet` darf jeden Gedanken anstossen und keine Regel tragen.**

### S1c · Rastersuche: was abgesucht wurde, wird vermerkt

Aus der Bundeswehr, vom Betreiber eingebracht: Wer ein Gelaende absucht, teilt es in Raster und vermerkt jedes durchsuchte. Fehlt der Vermerk auch nur fuer eines, ist nicht ein Raster offen -- die ganze Suche ist unbrauchbar und beginnt von vorn.

Das trifft uns an vier Stellen gleichzeitig, und an dreien hat es heute schon Geld gekostet:

1. **Der NASA-Durchgang.** 40 von 1638 beurteilt. Ohne Vermerk, WELCHE 40, faengt der naechste Durchgang bei null an. (Die Datei `runs/nasa_uebertragung_2026-08-09.md` nennt sie -- der Vermerk existiert also, aber nur als Fliesstext, nicht als Zustand am Knoten.)
2. **Verlorene Messungen.** Ein Gitterlauf lief heute vollstaendig durch und war weg, weil seine Ausgabe nur auf der Standardausgabe stand. Ein Raster ohne Vermerk.
3. **Der Abruf selbst.** Der Fahrtenbuch-Fall: fuenf von sechs Befunden waren bereits als Lehre erfasst, zwei davon behoben -- und wurden erneut untersucht. Niemand hatte vermerkt, dass dieses Raster schon abgesucht war, weil der Speicher nur Funde kennt und keine Suchen.
4. **Der Bestand als Suchprotokoll.** Der eigentliche Gedanke dahinter: Eine Wissensdatenbank, die nur festhaelt, was gefunden wurde, zwingt zur Wiederholung jeder erfolglosen Suche. `zero_hit_log.jsonl` ist genau dieser Vermerk und wird heute nur zum Zaehlen benutzt.

**Regel, ab sofort:** Jeder Durchgang durch eine Menge (Knoten, Laeufe, Dateien, Regelwerke) haelt fest, WAS abgesucht wurde -- nicht nur, was dabei herauskam. Ein Ergebnis ohne Raster ist nicht wiederholbar, sondern nur wiederhol**bar von vorn**.

**Und ein Raster ohne den Blick, der es absuchte, behauptet eine Vollstaendigkeit, die es nicht hat** (Einwand des Betreibers). Dieselbe Suche liefert in einer anderen Sitzung ein anderes Ergebnis -- weil der Bestand sich bewegt, weil der Abruf je nach Prompt anderes einspielt, und weil ein Sucher mit engem Kontextfenster weniger halten kann als einer mit weitem. Wer spaeter "durchsucht" liest, wiederholt es nicht -- und uebersieht, was der damalige Blick nicht sehen konnte.

Zum Vermerk gehoert deshalb, WER mit WELCHEM Blick gesucht hat:

- **Sitzung und Agent** (`session`, `actor`) -- die Spalten gibt es bereits an Knoten und Lehren.
- **Modell** (`model`) -- seit heute in einer Schreibweise, also gruppierbar.
- **Bestandsstand**: Knotenzahl, Lehrenzahl, Kantenzahl zum Zeitpunkt der Suche. Heute sind 5799 Kanten dazugekommen; jede Suche von gestern hat ein anderes Gelaende abgesucht als dieselbe heute. Der Auszug unter `auszug/` ist der natuerliche Anker dafuer.
- **Kontextfenster**: wieviel der Sucher ueberhaupt halten konnte. Gemessen, nicht geschaetzt -- L-502be0 haelt fest, wie leicht sich hier das Gefuehl wie Wissen anfuehlt.

Beleg, dass das kein Formalismus ist: `ab_vergleich_abruf_2026-08-07` wurde von der Gegenprobe beanstandet, weil der Bestand waehrend des Laufs von 1971 auf 1974 wuchs. Derselbe Fehler, nur innerhalb einer einzigen Messung.

*Reihenfolge:* zwischen S1 und S3. Der Rang braucht die Belegquelle, und die Brücke aus S3 darf nicht schon wieder ein Nachschlagewerk in den Arbeitsbestand kippen.

### S1d · Geltung als dritte Achse — und die Vorgabe haengt an der Art der Aussage

Gemessen 2026-08-09: Die Arbeitssprache ist **Deutsch** (286 eigene Knoten deutsch, 2 englisch; 688 Lehren deutsch), mit einem **englischen** Nachschlagewerk darin (1045 NASA-Knoten englisch). Das Einbettungsmodell bge-m3 ist mehrsprachig, der Stichwortkanal ist es nicht -- Trigramme mit deutscher Umlautfaltung treffen englischen Text nie.

**Daraus folgt eine Unmoeglichkeit, keine Unwahrscheinlichkeit:** Solange die Ensemble-Pflicht verlangt, dass BEIDE Kanaele einen Kandidaten tragen, ist sprachuebergreifender Abruf ausgeschlossen -- der Stichwortkanal kann fuer ein deutsch-englisches Paar nie beitragen. Das ist die zweite, unabhaengige Erklaerung dafuer, dass genau eine von 5799 Kanten die NASA-Wolke verlaesst, und sie stuetzt die Entscheidung von S1b: ein Werk, das der automatische Abruf gar nicht erreichen kann, gehoert hinter eine eigene Tuer.

**Uebersetzt wird der Bestand NICHT.** Eine Uebersetzung ist eine zweite Fassung derselben Aussage; ab da gibt es zwei Wahrheiten, von denen eine ungeprueft altert -- derselbe Grund, aus dem die Herkunft unveraenderlich ist. Die Bruecke liegt in der **destillierten Behauptung**, die fuer die Analogie-Arbeit ohnehin entsteht: formuliert in der Arbeitssprache, das Original unangetastet daneben.

**Kulturwissen ist kein Uebersetzungsproblem, sondern ein Geltungsproblem.** "In Deutschland siezt man Fremde" ins Englische zu uebersetzen macht den Satz in den USA nicht richtig, nur lesbar. Wir haben zwei Geltungsachsen -- *wann* (`gilt_ab`/`gilt_bis`) und *wo im Wissen* (Zweig). Kultur- und Rechtsraum sind die dritte.

Der gefaehrliche Teil ist die **Vorgabe**: Fehlende Angabe heisst heute `shared`, also *gilt ueberall*. Fuer Technisches meist richtig, fuer Aussagen ueber Menschen, Umgangsformen, Recht und Erwartungen **immer falsch** -- und der Fehler ist still. Die Regel sieht universell aus, wird universell angewandt und ist es nie.

> **Die Vorgabe fuer die Geltung haengt an der ART der Aussage.** Technisches gilt bis zum Beweis des Gegenteils ueberall. Soziales, Rechtliches und Kulturelles gilt **gebunden**, bis jemand die Reichweite ausdruecklich weitet.

Das ist dieselbe Bewegung, die die NASA-Stichprobe schon vollzogen hat: 6 von 39 Lehren wurden als *gebunden* aussortiert, weil sie an Physik hingen. Bei Kulturwissen ist der Anteil hoeher und der Schaden anders gelagert -- eine falsch uebertragene Vibrationslehre faellt auf, eine falsch uebertragene Hoeflichkeitsregel nicht. Sie fuehrt nur dazu, dass jemand als unhoeflich gilt und nie erfaehrt, warum.

Japanisches Wissen waere danach kein Sonderfall, sondern der Normalfall in Reinform: Aussage im Original, destillierte Behauptung in der Arbeitssprache, Geltung ausdruecklich auf den Kulturraum gesetzt -- und ohne diese dritte Angabe kommt es gar nicht erst herein.

### S2 · Sichtbarkeit: was der Speicher liest und schreibt, steht im Gespräch

Betreiberwunsch, und er trifft eine echte Blindstelle. Der Abruf ist heute sichtbar (`<knowledge-recall>`), **jeder Schreibvorgang ist unsichtbar**. Genau daraus entstand die gemessene Lehre L-706807: Ein Agent meldete „gespeichert", die Herkunftsschranke hatte abgewiesen, niemand sah es.

Eine Zeile je Vorgang, im Gespräch, mit Kennung: `abgelegt: A-d93330 (Annahme)` bzw. `abgewiesen: source_fehlt`. Die Kennung ist der Punkt — sie lässt sich schlechter erfinden als ein „erledigt".

*Grenze:* Der MCP-Server kann nicht in den Chat schreiben. Der Weg führt über den vorhandenen `PostToolUse`-Haken, der das Zugriffsprotokoll ohnehin liest.

### S3 · Die Brücke vom Papernetz in den Speicher

Gemessen: 56 Paper gesammelt, 10 im Speicher, 1 Knoten mit PDF-Quelle. Die Sammelhälfte steht seit Langem, die Destillationshälfte fehlt.

Zu bauen ist **kein zweites Papernetz**, sondern ein Übergang: aus `citation-network.json` werden Knoten mit festem Muster (Kernaussage, Methodik, Bewertung, Zitation — das Muster aus dem Video, es taugt). Herkunft ist die Netzdatei, Reifegrad kommt aus S1.

*Bindende Reihenfolge:* **nach S1.** Ohne abgeleiteten Reifegrad kippen 56 Paper unsortiert in einen Bestand, der schon an Verdünnung leidet — das verschlimmert die 0-von-35-Zeile, statt sie zu heilen.

### S4 · Promotion und Ebenen (der Umbau, zuletzt)

Projektlokale Entstehung, Beförderung nach Prüfung. Das ist der größte Hebel und der einzige echte Umbau. Er beantwortet zugleich das offene „Bereichsauslieferung gehört in den Server" — und zwar besser, als es dort formuliert war: nicht Auslieferung nach Bereich, sondern **Entstehung** nach Bereich.

*Warum zuletzt:* Er ändert die Ablage. Jede Messung davor bleibt vergleichbar, jede danach nicht. Und ohne S1 fehlt das Kriterium, wonach befördert wird.

### S5 · Eine Oberflaeche, zwei Erbschaften

Es gibt zwei Betrachter, und sie zeigen verschiedene Dinge:

| | BeGood Wissensnetz | brainlehr Wissensraum |
|---|---|---|
| Ort | `hub/tools/knowledge-viz` | `brainlehr/entscheidungen*` |
| Umfang | 531 Zeilen + app.js 21,7 KB | 623 + 334 Zeilen, HTML 45 KB |
| zeigt | 385 Knoten, 835 Beziehungen | **2713 von 2713 Eintraegen**, Knoten UND Lehren |
| Darstellung | 3D-Kraeftegraph, Raeume farbig, Live-Spur | Baum · Bedeutung · Spuren · Vergleich · Ablauf, Zeitachse |
| fremde Adressen | **`cdn.jsdelivr.net` (3d-force-graph)** | **keine** |

**Die Richtung ist damit gemessen, nicht gewaehlt.** brainlehr ist seit dem 2026-08-08 ein eigenstaendiges Repo, und nach Entscheidung `d6f0dd0f` entsteht eine Veroeffentlichung als eigenes Repo mit frischer Historie. Eine Oberflaeche, die ohne Netz schwarz bleibt und einem Dritten meldet, wann jemand seinen Wissensspeicher oeffnet, kann nicht die Basis sein. **Der Wissensraum ist die Basis, das Wissensnetz die Ideenquelle.**

**Was der Wissensraum vom Wissensnetz erbt:** Kraefte-Anordnung als zusaetzliche Ansicht, Raeume farbig, die Live-Spur der Abrufe. Die Bibliothek wird dafuer mitgeliefert statt geladen (Lizenz vorher pruefen, nicht annehmen) -- oder die Anordnung selbst gerechnet, wenn die Lizenz das nicht hergibt.

**Was NICHT geerbt wird, und das ist der Kern:** Ein Kraeftegraph ordnet nach Anziehung und **sieht dadurch nach Erkenntnis aus** -- Naehe wirkt wie Verwandtschaft. Der Wissensraum schreibt statt dessen hin, was man sieht:

> *Bedeutung* ist eine lineare Projektion aus 1024 Dimensionen auf drei. Die drei Achsen tragen **8,9 % · 2,9 % · 2,0 %** der Streuung.

> Eine Linie in *Spuren* bedeutet **kam zusammen vor**, nicht *haengt zusammen* und schon gar nicht *fuehrt zu*.

Drei Sorten Linie -- Adresse, Modellnaehe, gemeinsame Auslieferung -- sehen im Kraeftegraph alle gleich aus. Diese Beschriftungen sind keine Zierde, sie sind der Unterschied zwischen einem Werkzeug und einem Bild.

**Und der Wissensraum liefert das Argument fuer S1b als Bild:** Im Baum-Modus erschlaegt der Block `nasa-llis 1638` optisch alles andere. Man muss die Verduennung nicht erklaeren, man sieht sie.

*Zu pruefen beim Zusammenfuehren:* warum das Wissensnetz nur 385 der 2020 Knoten zeigt -- der Mechanismus ist nicht nachgesehen, nur beobachtet. Wenn er die NASA-Wolke ausblendet, tut er heute schon, was S1b beschliesst; wenn er etwas anderes tut, ist es ein Fehler.

*Reihenfolge:* nach S1b. Erst gehoert entschieden, was ueberhaupt zum Arbeitsbestand zaehlt -- sonst baut die Oberflaeche eine Trennung nach, die im Speicher nicht existiert.

### S6 · Rechtevergabe — wer darf einen Schalter umlegen

Einwand des Betreibers 2026-08-09: Manche Schalter darf nicht jeder umlegen; in einem Unternehmen entscheidet ueber manches nur die Geschaeftsfuehrung.

Der Einwand trifft eine echte Luecke. Heute haelt der Speicher fest, WER entschieden hat (`norm_entschieden_von`, `actor`) -- und erzwingt **nichts**. Die Spalte ist ein Protokoll, keine Schranke. Gemessen: 62 von 71 Normen hat die Maschine sich selbst zugeschrieben.

Und es ist eine VIERTE Groesse, unabhaengig von den drei aus Knoten b6305304: nicht was der Satz sagt (Art), nicht wie bindend (Rang), nicht wie widerrufbar (Unabaenderlichkeit) -- sondern **wer ihn anfassen darf**.

**Trotzdem wird jetzt kein Rollenmodell gebaut.** In dieser Installation gibt es genau einen Menschen. Ein Rechtemodell mit einem Nutzer ist ein Schema ohne Schreiber -- dieselbe Krankheit wie `norm_art` (72 von 72 leer) und die vier Tokenspalten (2167 Zeilen, alle NULL). Beide wurden am 2026-08-08/09 diagnostiziert; sie ein drittes Mal selbst zu bauen waere schwer zu verteidigen.

**Was ohne Rollen schon gilt und echte Traeger hat:** die Unterscheidung Mensch gegen Maschine. Sie ist bereits eine Rechtefrage und in S1 entschieden -- abgeleiteter Rang braucht Beleg, das Hausrecht des Betreibers sticht. Ein Rechtemodell mit zwei Rollen, und beide sind besetzt.

**Abbruchbedingung, und sie bekommt einen MELDER statt einer Notiz:** Das Rollenmodell wird gebaut, sobald eine Installation existiert, in der **mehr als eine Person schreibt** -- messbar an verschiedenen menschlichen Schreibern in `actor`/`norm_entschieden_von` oder an einer fremden Installation. Vorher unterscheidet sich "darf" von "darf nicht" nicht messbar.

Warum ein Melder und keine Notiz: Am selben Tag wurde Achse 3 mit derselben Begruendung vertagt -- und der Melder, der ihre Abbruchbedingung pruefen sollte, widerlegte die Vertagung in derselben Minute (zwei Normen fremder Herkunft lagen laengst im Bestand). Eine Vertagung ohne Melder ist ein Vielleicht.

**Zu klaeren beim Bau, nicht vorher entschieden:** ob Rechte an der Person haengen, an der Rolle oder am Gegenstand (etwa: "Normrang 1 nur mit Rolle X"), und wie sich das zu `gattung` und `gilt_bis` verhaelt -- ein Recht, einen Schalter umzulegen, ist etwas anderes als das Recht, eine Aussage zu schreiben.

### S7 · Darlegung — der Speicher lernt Reihenfolge

Ein Wissensspeicher ist eine MENGE, ein Plan ist eine FOLGE. Der Speicher kann heute sagen, dass zwei Knoten zusammenhaengen -- nicht, dass einer VOR dem anderen zu lesen ist, und schon gar nicht, welcher Satz sie verbindet. Genau deshalb liegt dieser Plan als Datei und nicht im Bestand.

**Zu bauen:** eine Darlegung ist ein Knoten, dessen Inhalt die verbindende Prosa ist und dessen Teile ueber GEORDNETE Kanten haengen (`knowledge_relations` hat `relation_type`, es fehlt eine Ordnungszahl). Aus Knoten plus geordneten Gliedern rendert ein Erzeuger die lesbare Datei.

**Der Gewinn ist nicht Schoenheit, sondern Pruefbarkeit.** "S3 nach S1" ist heute ein Satz in Prosa, den niemand gegen die Wirklichkeit halten kann. Als Kante ist es eine Aussage, die ein Melder pruefen kann: *ist S3 gebaut, waehrend S1 offen ist?*

**Damit fallen zwei .md-Vorteile ohne Zusatzarbeit an den Speicher:**
- *In zwanzig Jahren lesbar*: die Datei wird ERZEUGT statt gepflegt -- eine Ansicht kann nicht driften. Das Muster existiert bereits (`build_node_index.py` -> `NODE_INDEX.md`).
- *Vergleichbar in git*: die erzeugte Datei liefert einen lesbaren Diff, der Auszug den zeilenweisen.

**Und die zwei Nachteile des Speichers bekommen ihre Gegenmittel benannt:**
- *Zerbrechlicher Stack* (heute dreimal erlebt: der MCP-Prozess lief stundenlang mit altem Code). Regel: **jeder Lesepfad muss ohne den Server funktionieren**. Vorbild ist `nachschlagewerk_suche.py` -- reine Standardbibliothek, nur lesend. Dann ist der Server Bequemlichkeit statt Voraussetzung.
- *Kein Zusammenfuehren*: der Auszug ist zeilenweises JSONL und damit grundsaetzlich mischbar. UNGEPRUEFT ist, ob zwei Sitzungen ihn konfliktfrei zusammenfuehren -- gehoert gemessen, nicht angenommen.

*Traeger ist sofort da:* dieser Plan, acht Abschnitte, mit begruendeter Reihenfolge.

## Alternativen mit Ablehnungsgrund

**Obsidian oder ein fertiges Zweitgehirn übernehmen.** Abgelehnt: löst Wiederfinden, nicht Widerspruchsfreiheit und nicht Geltung. Beides haben wir bereits härter.

**Reifegrad rein menschlich, wie im Video.** Abgelehnt auf Einwand des Betreibers: erzeugt eine Halde unentschiedener Knoten. Der Deckel bleibt nur dort, wo das Urteil zwingend menschlich ist (Normrang 1–2).

**Erst den Trichter feinjustieren (MIN_HITS, MAX_LESSONS, MAX_NODES).** Abgelehnt, und zwar gemessen — die Messreihe lief am 2026-08-09 über 36 Gitterpunkte (`runs/trichter_gitter_2026-08-09.txt`):

| MIN_HITS | Lehren | Knoten | Zeichen/Fall |
|---|---|---|---|
| 1 | 1/15 | 1–2/20 | **6299 – 12838** |
| 2 | 1/15 | 0/20 | — |
| 3 (Vorgabe) | 0/15 | 0/20 | 2512 |
| 4 | 0/15 | 0/20 | — |

Die Lockerung von 3 auf 1 kauft **einen** Treffer bei den Lehren und ein bis zwei bei den Knoten — für die zweieinhalb- bis fünffache Zeichenmenge je Prompt. **`MAX_LESSONS` und `MAX_NODES` bewegen die Trefferzahl praktisch überhaupt nicht** (nur Knoten 1→2 bei `MIN_HITS=1` und `MAX_NODES=8`); sie erhöhen ausschließlich die Liefermenge. Zwei von drei Reglern sind also wirkungslos, und das gehört benannt statt im Gitter versenkt.

Gegenprobe, dass die Messung überhaupt greift: `MIN_HITS=50` drückt auf 0/35 — das Setzen der Werte wirkt. Zwei Läufe desselben Punktes identisch.

**Daraus folgt die eigentliche Erkenntnis dieses Plans:** Der Abruf scheitert nicht am Trichter, sondern früher — an der Zuordnung selbst. Kein Punkt im Gitter liefert brauchbaren Abruf. Damit sind S1 und S4 nicht eine von mehreren Möglichkeiten, sondern der einzige verbliebene Weg.

*Vorbehalt, der bestehen bleibt:* Der Prüfkorpus ist absichtlich so formuliert, dass er wörtliche Überschneidung mit dem Ziel vermeidet. Er misst damit den schwersten Fall, nicht den durchschnittlichen. Echte Prompts überschneiden sich vermutlich stärker — belegt ist das nicht.

## Woran sich Erfolg messen lässt

Ausschließlich an den zwei Zahlen, die heute schon stehen: **Treffer auf dem Prüfkorpus** (heute 0 von 35) und **Zeichen je Prompt** (heute 2512). Jeder Schritt wird gegen beide gemessen, vorher und nachher. Ein Schritt, der die Trefferzahl hebt und die Zeichenmenge verdoppelt, ist kein Fortschritt, sondern ein Tausch — und wird als solcher benannt.

Zusatzkennzahl ab S1: Anteil der Knoten mit **abgeleitetem** Reifegrad. Steigt er nicht, misst die Ableitung nichts.

## Was bewusst nicht getan wird

Kein eigener Betrachter (der vorhandene reicht, und im Video ist er selbst „schön zum Zeigen, zum Arbeiten kaum relevant"). Keine PDF-Verarbeitung im Speicher — das Papernetz kann das, die Arbeitsteilung bleibt. Keine Rückrechnung alter Bestände vor dem jeweiligen Mechanismus.
