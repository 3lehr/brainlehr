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

### S8 · Pruefer, die urteilen statt zaehlen — GEBAUT am 2026-08-09

Anlass: Der Betreiber vermisste, dass sich Pruefer von selbst melden. Die Recherche korrigierte die Erinnerung (Lehre `L-479171`): der alte Skeptiker hat NIE autonom gefeuert -- er war Schritt 3 einer von Hand gestarteten Pipeline, und die `ACTIVATION: proaktiv`-Zeilen waren Prosa fuer ein Modell, kein Mechanismus. Null Treffer unter 75 registrierten Agenten.

**An Autonomie fehlt es nicht** -- 23 Haken feuern heute von selbst. Es fehlte, dass einer ein URTEIL faellt: ein Melder vergleicht eine Schwelle, ein Pruefer sagt, dass etwas schief steht, obwohl keine Zahl ueberschritten ist.

`pruefer.py` ist gebaut und am Sitzungsstart verdrahtet. Drei Auflagen fuer jede Pruefung darin, und sie sind der eigentliche Inhalt:

1. **Messbar aus dem Bestand**, nicht aus Stimmung.
2. **Fehlklasse benannt** -- ein Befund ohne Fehlklasse ist eine Meinung.
3. **Preis eines Fehlalarms beziffert** -- wer ihn nicht nennen kann, hat die Pruefung nicht zu Ende gedacht.

Dazu: schweigt, solange nichts anschlaegt.

**Zwei Pruefungen, beide schlagen heute an:**
- *Selbstzuschreibung*: 62 von 72 Normentscheidungen (86 %) hat ein KI-Akteur sich selbst gegeben. Fehlklasse: stille Selbstermaechtigung, Geltung ohne Gegenueber.
- *Stumme Spalte*: `norm_art` bei allen 72 leer. Fehlklasse: gebaute Regel ohne Wirkung -- dieselbe Signatur wie vier Tokenspalten ueber 2167 Zeilen NULL und wie der Skeptiker, dessen Ausloeser Prosa war.

**Bewusst NICHT gebaut**, obwohl es als Beispiel diente: die Erkennung "Plan-Nummerierung behauptet Abhaengigkeit". Reine Textheuristik, zu fehlalarmanfaellig. Die Zurueckhaltung ist Teil der Bauform.

**Untergrenze `MINDESTZAHL = 20`:** Unter 20 Zeilen wird nicht geurteilt, auch nicht bei 100 Prozent -- 2 von 3 sind 67 Prozent und sagen nichts. Der Negativfall steht als erster im Selbsttest.

**Elf weitere pruefende Rollen liegen in der alten Bibliothek** (`sokrates-review`, `pivot-richter`, `verfassungsgericht`, `spaghetti-monster`, `archaeologe` und sieben weitere) -- als Vorlage fuer Fehlklassen, nicht als Agenten zum Starten.

### S9 · Der Abruf soll den Suchpfad benutzen, statt einen eigenen zu haben

**Gemessen 2026-08-09, gegen DIESELBEN 35 Faelle:**

| Weg | Treffer | Preis |
|---|---|---|
| Abruf, Vorgabe (heute im Betrieb) | 0/35 | 2540 Zeichen **je Prompt** |
| Abruf, beide Kanaele offen | 4/35 | 6924 Zeichen je Prompt |
| **`knowledge_search`, gezielt** | **7/35** (Lehren 4/15, Knoten 3/20) | **3480 Zeichen je Anfrage** |

**Die gezielte Suche ist fast doppelt so gut wie der beste Abruf, zum halben Preis.** Und sie findet Lehren -- 4 von 15, waehrend der Abruf in JEDER Einstellung 0 von 15 lieferte.

**Damit faellt eine Diagnose dieses Tages.** "Lehren werden nicht gefunden" galt als Eigenschaft des Bestands (zu enger Trichter, MIN_HITS=3, Rang 7 bis 597 im Bedeutungskanal). Es ist eine Eigenschaft des ABRUFPFADS. Derselbe Bestand, dieselben Aufgaben, andere Implementierung -- und es geht.

**Der Unterschied liegt in der Bauform**, nicht in einer Einstellung: `knowledge_search` verschmilzt Stichwort- und Bedeutungsrangliste per RRF und kennt weder eine `MIN_HITS`-Sperre noch eine Ensemble-Pflicht. Der Abruf hat beides -- und beides wirft Kandidaten weg, BEVOR eine Rangfolge greift.

**Zu bauen ist deshalb keine zweite Einstellung, sondern eine Zusammenfuehrung:** Der Abruf ruft den Suchpfad auf und begrenzt danach die Menge, statt vorher zu sieben. Die Strenge des Abrufs gehoert an den AUSGANG (wieviel wird eingespielt), nicht an den EINGANG (was darf ueberhaupt Kandidat werden).

Das ist zugleich die Antwort auf die Frage des Betreibers, warum wir nicht beide Wege zugleich gehen: **wir haben beide, und der schlechtere laeuft im Betrieb.**

*Vorbehalt, der bestehen bleibt:* 7 von 35 sind 20 Prozent -- gut gegen 0, schlecht in absoluten Zahlen. Und der Pruefkorpus vermeidet woertliche Ueberschneidung absichtlich, misst also den schweren Fall.

*Reihenfolge:* vor S4 (Promotion). Eine Umstellung des Abrufs auf den Suchpfad aendert jede Messung danach -- sie gehoert vor alles, was sich an Abrufzahlen bewerten laesst.

### S10 · Nuetzlichkeit messen, nicht nur Ziel-Identitaet

**Der Betreiber fragte, ob 7 von 35 heisst "28 nicht gefunden" oder "28 nicht wichtig genug". Nachgemessen:**

| | |
|---|---|
| Ziel getroffen | 7 |
| etwas anderes kam | **28** |
| gar nichts kam | **0** |

**In keinem einzigen Fall kam nichts.** Jeder Fall hat genau EINE hinterlegte Ziel-Kennung (keine Listen), und die Aufgabe wurde aus dieser Lehre geschrieben und dann so lange umformuliert, bis keine woertliche Ueberschneidung blieb (`attempts[].collision`). Gemessen wird also: kommt genau diese eine Lehre zurueck, obwohl die Frage kein Wort mit ihr teilt.

**Damit traegt jede Zahl dieses Tages eine Fussnote:** `0/35`, `4/35`, `7/35` messen ZIEL-IDENTITAET, nicht NUETZLICHKEIT. Der Vergleich zwischen Konfigurationen bleibt gueltig -- gleicher Massstab. Die absolute Zahl ist zu streng, und um wieviel, weiss niemand.

Ich habe heute mehrfach gesagt "der Abruf trifft nichts". Richtig waere gewesen: *er trifft nie das hinterlegte Ziel, und was er stattdessen liefert, hat niemand beurteilt.*

**Zu bauen: eine zweite Kennzahl.** Die 28 Antworten werden gelesen und in drei Toepfe sortiert -- *haette geholfen* · *thematisch nah, aber nutzlos* · *am Thema vorbei*. Erst beide Zahlen zusammen sagen, wo das System steht.

**Die Auflage, ohne die das Urteil wertlos ist -- eine NEGATIVKONTROLLE im Urteilssatz.** Ein Modell als Richter neigt dazu, alles Plausible fuer hilfreich zu halten. Darum werden dem Urteilenden zusaetzlich absichtlich FALSCHE Paare untergemischt (Aufgabe A mit der Antwort zu Aufgabe B). Haelt er die fuer hilfreich, ist sein Urteil ueber die echten 28 wertlos, und die Messung wird verworfen statt berichtet. Ohne diesen Anteil misst man die Gutmuetigkeit des Richters, nicht die Guete des Abrufs.

*Zweite Auflage:* Der Urteilende erfaehrt NICHT, welches System die Antwort erzeugt hat und ob ein Fall als Treffer galt -- sonst begruendet er das bekannte Ergebnis nach.

*Reihenfolge:* nach S9. Erst umstellen, dann beide Wege mit beiden Kennzahlen vergleichen -- sonst misst man zweimal.

### S11 · Ein Melder auf die ARBEIT, nicht auf den Bestand

**Anlass, und er ist ein Selbstbeleg.** Innerhalb einer Stunde am 2026-08-09 habe ich drei Fehler gemacht, zu denen jeweils eine Lehre im Bestand liegt:

1. Einen Melder gebaut, der die GESAMTZAHL der Protokollzeilen zaehlte statt der Zeilen seit der Umstellung -- 866 statt 0. Lehre dazu: `L-502be0`, woertlich *"pruefen ob die gesuchte Groesse ein ZUSTAND oder ein DURCHSATZ ist. Ein Zustand steht in genau einer Zeile; wer ihn summiert, bekommt ein Integral und merkt es nicht."* Gestern erfasst.
2. Die Nulllinie danach von HAND eingetragen -- aus dem Hauptverzeichnis (42 Zeilen), waehrend der Melder die Datei an seinem eigenen Ort liest (866). Eine Zahl im Quelltext gilt fuer den Ort, den der Autor im Kopf hatte.
3. Zuvor behauptet, alle Zahlen des Tages seien wegen der fehlenden Prompt-Eingabe zu hart -- und es erst danach gemessen. Sie waren es nicht.

**Warum der Speicher schwieg -- gemessen, nicht vermutet:**

- Der Abruf durchsucht den PROMPT des Menschen. Der lautete "mach das!". Es gab nichts zu treffen. (Der offene Kreis aus `745f7ac1`, bis heute halb geschlossen.)
- Auch mit gutem Prompt haette er nichts gefunden: 0 von 35 im alten Weg, der bis zu diesem Zeitpunkt lief.
- Und das Werkzeug, das genau dafuer gebaut wurde (`befund_gegen_speicher.py`), habe ich auf den Fehler angesetzt: Es fand fuenf Lehren ueber `recall_log.jsonl` -- und `L-502be0` NICHT. Weil es nach BEZEICHNERN sucht (Dateien, Symbole, Ereignisnamen). Mein Fehler ist ein Denkfehler und hat keinen Bezeichner.

**Die Luecke in einem Satz:** Die Melder pruefen den BESTAND. Keiner prueft, was gerade ENTSTEHT. Der Speicher haengt am Gespraech, nicht an der Arbeit -- vierzig Werkzeugaufrufe in dieser Stunde haben ihn kein einziges Mal befragt.

**Zu bauen:** ein Melder, der geaenderten Code gegen bekannte FEHLERKLASSEN haelt, nicht gegen Bezeichner. Erste Kandidaten, alle drei mit Lehre im Bestand und alle drei heute eingetreten:
- eine Summe ueber ein Protokoll, wo ein Zustand gemeint ist (`L-502be0`)
- ein leeres Ergebnis, das als Befund gelesen wird, ohne den Filter zu verdaechtigen (`L-36d092`)
- eine Zahl im Quelltext, die einen ORT voraussetzt (Pfad, Nulllinie, Schwelle aus einem anderen Verzeichnis)

**Die Auflage, ohne die es ein Aergernis wird:** Ein Melder auf die Arbeit sieht viel und trifft selten. Er braucht dieselben drei Auflagen wie `pruefer.py` (messbar, Fehlklasse benannt, Preis eines Fehlalarms beziffert) UND eine vierte: **er meldet nur zu Code, der in DIESER Sitzung geaendert wurde.** Wer den ganzen Bestand prueft, erzeugt eine Liste, die niemand liest.

*Vorbehalt:* Fehlerklassen ohne Bezeichner maschinell zu erkennen ist schwer und fehlalarmanfaellig. Faellt die Trefferquote zu schlecht aus, ist die ehrliche Antwort, ihn auf die drei obigen Muster zu beschraenken statt ihn zu verallgemeinern.

### S12 · Mehrstufiger Abruf — der gemessen groesste Rueckstand

**Recherchiert 2026-08-09 (`runs/wettbewerb_2026-08-09.md`), und das Ergebnis ist unbequem:**

| | Recall |
|---|---|
| Standard-Hybrid-RAG 2026 (BM25 + Dense + Reranking + Query-Rewriting) | ~91 % |
| einfache Dense-only-Vektorsuche | 25-33 % |
| **brainlehr** | **20 %** (7 von 35) |

Wir liegen unter dem SCHWACHEN Referenzwert. Die benannte Ursache ist keine Feinheit, sondern eine fehlende Stufe: **Query-Rewriting und Reranking**. Unser Abruf sucht mit dem rohen Prompt und nimmt, was die RRF-Verschmelzung liefert.

**Zwei Einschraenkungen, die dazugehoeren und keine Ausrede sind:** Die Branchenzahlen sind selbstveroeffentlicht und oeffentlich umstritten (Mem0 nannte 91,6 % auf LoCoMo, Zep korrigierte auf 58,44 % und stellte 94,7 % dagegen). Und unser Pruefkorpus vermeidet woertliche Ueberschneidung ABSICHTLICH -- ein haerterer Massstab. Der Abstand bleibt trotzdem zu gross, um ihn wegzuerklaeren.

**Reihenfolge innerhalb des Schrittes, billig vor teuer:**
1. **Deterministische Erweiterung zuerst**, ohne Modell: Komposita zerlegen (deutsche Zusammensetzungen sind hier ein echter Faktor -- "Kilometergeld" gegen "Kilometersatz"), Umlautfaltung auch in der Anfrage, Stammformen. Kostet nichts je Prompt und ist vollstaendig nachvollziehbar.
2. **Reranking** ueber die vereinigte Kandidatenliste, bevor gedeckelt wird. Heute deckelt der Abruf VOR jeder Bewertung.
3. **Erst dann** Query-Rewriting mit Modell -- und nur, wenn 1 und 2 gemessen nicht reichen. Ein Modellaufruf je Prompt ist Laufzeit und Kosten in jeder Sitzung; das ist ein Tausch und gehoert als solcher gemessen.

*Massstab:* dieselben zwei Kennzahlen wie bisher -- Zieltreffer (heute 7/35) UND Zeichen je Prompt (heute 4776). Eine Verbesserung, die die Liefermenge verdoppelt, ist ein Tausch.

*Warum das jetzt vor S4 und S7 kommt:* Es ist der einzige gemessene Rueckstand gegen den Stand der Technik. Alles andere im Plan macht den Speicher genauer; dies macht ihn erst brauchbar.

### S13 · Die ANTWORT als Anfrage — der zweite Ausloeser, den 745f7ac1 seit Tagen fordert

Vorschlag des Betreibers 2026-08-09: die bereits erzeugten Antworten des Assistenten gegen
den Speicher werfen. Sie existieren ohnehin, die Anfrage kostet also nichts mehr.

**Gemessen, bevor entschieden wurde** — die letzten sechs eigenen Antworten dieser Sitzung als
Anfrage gegen `knowledge_search`, verglichen mit allem, was der Prompt-Abruf in derselben
Sitzung geliefert hat (167 Eintraege):

| Anfrage | Zeichen | Eintraege, die der Prompt-Weg NIE lieferte |
|---|---|---|
| ganze Antwort (1200 Zeichen je Stueck) | 7200 | 7 |
| top-60 Begriffe nach IDF | 3214 | 9 |
| **top-30 Begriffe nach IDF** | **1719** | **17** |
| top-15 Begriffe nach IDF | 902 | 15 |

**Der Befund ist nicht, dass es funktioniert, sondern dass VERDICHTEN SCHAERFT.** Ein Viertel
der Zeichen findet das Zweieinhalbfache. Der Volltext verwaessert die Anfrage; die dreissig
Begriffe mit dem hoechsten IDF-Gewicht sind das Thema, alles andere ist Bindegewebe. Damit
beantwortet sich die Kostenfrage des Betreibers von selbst — die kleine Anfrage ist nicht der
Kompromiss, sie ist die bessere Messung.

*Verworfen, mit Grund:* `pruefkorpus.rare_terms()` als Verdichter (Begriffe mit
Dokumenthaeufigkeit <= 3). Gemessen 0 Treffer aus 6 Antworten — es filtert auf das, was im
BESTAND selten ist, und der Assistent schreibt naturgemaess ueber genau die Themen, die dort
haeufig sind. Richtig ist die Gewichtung (hoechstes IDF), nicht der Seltenheitsfilter.

**Warum dieser Ausloeser die Luecke schliesst, die kein anderer erreicht:** 28 von 94
Betreibernachrichten erreichen den `UserPromptSubmit`-Haltepunkt nie (waehrend laufender
Arbeit als `attachment` zugestellt), weitere 22 reissen `MIN_HITS` nicht. Fuer beide Klassen
gibt es auf der Eingabeseite nichts zu suchen. Die Antwort dagegen liegt IMMER vor, traegt das
vollstaendige Fachvokabular und ist ueber den `Stop`-Haken erreichbar.

Dazu der Selbstbeleg dieses Tages: Der Assistent schrieb ueber stdio, ohne dass ein Abgleich
stattfand — der Speicher haelt dazu einen geprueften Knoten (`436cb221`). Der Abruf feuerte
erst, als der BETREIBER das Wort schrieb. Der Speicher prueft Eingaben, nie Ausgaben.

**Zu bauen, in dieser Reihenfolge:**
1. `Stop`-Haken verdichtet die letzte Antwort auf die dreissig Begriffe mit hoechstem
   IDF-Gewicht, sucht damit und legt die Treffer ab (Datei, nicht Gespraech — der Haken kann
   nicht in den laufenden Zug schreiben).
2. Der naechste `UserPromptSubmit` spielt sie zusaetzlich ein, dedupliziert gegen alles, was
   die Sitzung bereits gesehen hat (`_dedup_session` existiert).
3. Erst danach messen, ob der Deckel dafuer eigene Werte braucht.

*Massstab, und er ist NICHT der Pruefkorpus:* Der misst Ziel-Identitaet auf Eingabefragen.
Hier gehoert gemessen, ob eine Antwort auf eine EINGEREIHTE Nachricht besser ausfaellt — die
Klasse, um die es geht. Zweitens die Zeichen je Prompt, wie bei jedem Schritt.

*Vorbehalt, der bestehen bleibt:* "neu" heisst nicht "nuetzlich" (derselbe Einwand wie S10),
und sechs Antworten sind eine kleine Stichprobe. Belegt ist bisher nur, dass dieser Weg
anderen Bestand erreicht — nicht, dass er den besseren erreicht.

### S14 · Die Fehlklasse dieses Tages hat einen Namen: gebaut und ohne Wirkung

Nicht geplant, sondern aus vier unabhaengigen Funden des 2026-08-09 abgeleitet. Alle vier
haben dieselbe Signatur, und keiner waere durch Benutzen aufgefallen:

| Fund | Signatur |
|---|---|
| `norm_art` | 72 von 72 Normen leer — Regel gebaut, nie geschrieben |
| vier Tokenspalten in `access_log` | 3638 Zeilen durchgehend NULL |
| Selbsttest von `knowledge_recall_hook.py` | an fuenf Stellen rot, weil nichts ihn startet (`L-9a45b7`) |
| zweiter Relevanzkanal | an zwei Stellen abgeklemmt, im Ergebnis unsichtbar (`L-99f100`) |
| `_append_jsonl` | Vorgabewert ueberstimmte die Wahl des Aufrufers bei JEDEM Lauf |

**Verworfen, mit Grund:** `hub/scripts/wiring_check.py` auf brainlehr anzuwenden. Es findet
genau diese Klasse — deklarierter, nie erreichter Code — ist aber fuer Flutter/Dart gebaut
(25 Dart-Stellen im Quelltext) und kennt kein Python. Der Fund stammte aus dem Abruf und
wurde ohne Blick in die Kopfzeile weitergetragen; die Absage ist selbst ein Beleg fuer die
Regel, vor jeder Existenzaussage nachzusehen.

**Zu bauen statt dessen, weil es dieselbe Klasse ohne neue Bauform trifft:** die vorhandene
Pruefung "stumme Spalte" in `pruefer.py` wird generisch — nicht mehr eine fest benannte
Spalte, sondern jede Spalte in `knowledge_nodes`, `lessons_learned` und `access_log`, die zu
95 Prozent leer ODER zu 95 Prozent einwertig ist. Beides sagt dasselbe: die Spalte traegt
keine Unterscheidung. Mit `MINDESTZAHL = 20` wie bisher und einer benannten Ausnahmeliste,
je Eintrag begruendet.

*Warum das genuegt und kein zweites Werkzeug noetig ist:* Die vier Funde sind keine toten
Codepfade, sondern leere Traeger. Ein Schema ohne Schreiber ist aus dem Bestand messbar; ein
toter Codepfad braucht eine Aufrufanalyse, die es fuer Python hier nicht gibt. Wer beides in
einem Werkzeug will, baut das schwerere von beiden fuer den selteneren Fall.

### S15 · Der Pruefkorpus wird zusammengefuehrt, bevor irgendetwas daran gemessen wird

*Reihenfolge: BINDEND vor jeder weiteren Abrufmessung.* 35 Faelle rauschen nachweislich — die
Deckelreihe lieferte bei GROESSEREM Deckel weniger Treffer (12 gegen 13), was sachlich
unmoeglich ist. Jede Zahl, die vor der Zusammenfuehrung erhoben wird, ist gegen die spaeteren
nicht vergleichbar.

Vorhanden: 35 Faelle mit Ziel im alten Korpus, 55 im neuen (Haiku, 2026-08-09, 0 von 55 mit
Wortueberschneidung gegen dieselbe Prueffunktion gemessen, keine NASA-Ziele, keine
Ueberschneidung mit den 69 alten Zielen). Zusammen 90.

*Nicht getan:* die alte Korpusdatei ueberschreiben. Sie bleibt als eigene Datei stehen, sonst
ist der Vergleich vorher/nachher verloren — `abrufguete.py` bekommt statt dessen einen
Schalter fuer mehrere Korpusdateien samt Dublettenmeldung.

**KORREKTUR am selben Tag, nach der ersten Messung — die Zusammenfuehrung ist ausgesetzt.**
Gemessen ueber die zusammengefuehrten Faelle: 66 von 89 gegen vorher 16 von 35, also
scheinbar 46 auf 74 Prozent. Die Aufschluesselung zeigt zwei verschiedene Massstaebe unter
einer Zahl:

| Korpus | Faelle | Wortueberlappung Aufgabe→Ziel | Treffer |
|---|---|---|---|
| alt (mit Kollisionsschleife erzeugt) | 35 | **10,7 %** | 16/35 = 46 % |
| neu (Haiku) | 55 | **34,1 %** | 51/55 = **93 %** |

Der neue Korpus ist dreimal woertlicher und misst damit den leichten Fall. Mein Beleg fuer
seine Sauberkeit war zu schwach: `is_circular` prueft nur Begriffe mit Dokumenthaeufigkeit
≤ 3 — alles Mittelhaeufige, und daraus besteht Fachsprache, laeuft durch (`L-352afa`, jetzt
4 Vorkommen, damit zur Regel eskaliert).

**Daraus folgt fuer diesen Schritt:** Vergroessern allein hilft nicht gegen Rauschen; ein
Korpus braucht ein AUFNAHMEKRITERIUM statt einer nachtraeglichen Sichtprobe. Vorschlag zur
Messung, nicht als Beschluss: Wortueberlappung als Aufnahmegrenze, geeicht am alten Korpus
(dessen 10,7 % sind der einzige belegte Bezugspunkt), und je Fall im Korpus mitgefuehrt —
dann laesst sich die Trefferquote nach Schwierigkeitsgrad aufschluesseln, statt sie zu
mitteln.

*Bis dahin gilt:* Zahlen werden je Korpus getrennt berichtet, nie zusammengefasst.

### S16 · Quellenpflege ohne Anstoss — zuerst als FRAGE, Umsetzung erst danach

Vorschlag des Betreibers 2026-08-09, und er trifft die letzte Stelle, an der noch ein Mensch
anstossen muss: Bei den Barrierefreiheits-Anforderungen hat ER die Recherche ausgeloest, und
erst dabei kam heraus, dass eine neue Fassung ansteht. Der Speicher wusste weder, dass ihm
Quellwissen fehlte, noch dass eine Quelle altert.

**Zwei Fragen, die vor jedem Bau zu beantworten sind — und die erste ist nicht die
naheliegende:**

**Frage 1 — Woran erkennt das System, dass es zu einer Aussage KEIN Quellwissen hat?**
Das ist die schwerere Haelfte. Eine fehlende Quelle erzeugt kein Ereignis; sie sieht aus wie
gar nichts. Kandidaten, die es zu messen gilt: der Belegrang aus S1b (eine Aussage ohne
`belegt`/`berichtet` waere ein Kandidat), die Gattung (Fachaussage gegen Hausregel), und der
Weg aus S13 — die eigene Antwort traegt die Fachbegriffe, zu denen ein Beleg fehlen koennte.
Gegen die Verwechslung mit dem leeren Filter (`L-36d092`): Erst wenn belegt ist, dass eine
Fachaussage ueberhaupt erkennbar ist, taugt "kein Quellwissen gefunden" als Befund.

**Frage 2 — Was hat der Kalender ueberhaupt zu tun?** Gemessen am 2026-08-09:

| | |
|---|---|
| Normen im Bestand | 73 |
| davon mit `gilt_bis` | **2** |
| davon bereits abgelaufen | 2 |
| Knoten mit URL-Quelle | 1642 (ueberwiegend NASA-Nachschlagewerk) |
| Knoten, die Gesetz/Verordnung/Richtlinie/WCAG/BSI im Titel oder in der Quelle fuehren | 16 |

**Ein Ablaufkalender haette heute genau zwei Eintraege, und beide sind schon abgelaufen.**
Nicht weil nichts altert, sondern weil `gilt_bis` bei 71 von 73 Normen leer ist (gemessen als
stumme Spalte, S14). Der Kalender ist damit nicht die erste Massnahme, sondern die zweite:
**ohne gepflegte Ablaufdaten meldet er nichts und sieht dabei gesund aus** — dieselbe
Signatur wie die vier Funde aus S14.

**Zu bauen ist deshalb in dieser Reihenfolge, und die ist bindend:**
1. **Erst die Frist erheben, dann den Kalender.** Fuer die 16 Knoten fremder Herkunft ein
   Ablauf- ODER Wiedervorlagedatum bestimmen. Bei Gesetzen gibt es oft kein Ablaufdatum,
   sondern nur eine Fassung — dann traegt der Knoten ein Pruefdatum statt eines Ablaufs. Das
   Vorbild dafuer ist gemessen: `claude-obsidian` fuehrt `refresh_due` an jeder aktiven
   Quelle und verlangt es fuer jede akzeptierte Behauptung (Knoten `0011e658`).
2. **Dann der Melder**: was laeuft in den naechsten N Tagen ab, was ist bereits abgelaufen,
   und WELCHE Knoten stuetzen sich darauf. Die Kante dafuer existiert noch nicht — das ist
   dieselbe Bauform wie `bindend_vor` aus S7.
3. **Dann erst die Recherche ohne Anstoss**, mit Vermerk je Lauf: wonach gesucht, in welchen
   Raeumen, erfolgreich oder nicht, und wann eine Wiederholung sinnvoll ist. Der Rastervermerk
   aus S1c ist dafuer bereits die Form; ein erfolgloser Lauf ist ein Ergebnis und gehoert
   festgehalten, sonst sucht der naechste Durchgang dasselbe noch einmal.

**Die Verbindung zum Zitationsnetz, die der Betreiber sieht, ist real und noch ungenutzt:**
Das Papernetz kennt Quellen samt Zitationskanten (9 Netze, 297 Paper, 1624 belegte Kanten,
Umfang noch nicht entschieden). Eine Quelle, die dort als ueberholt gilt, ist derselbe
Vorgang wie eine abgelaufene Norm hier. S3 (die Papernetz-Bruecke) und dieser Schritt teilen
sich damit die Kante "stuetzt sich auf" — sie sollten dieselbe bekommen, nicht zwei
aehnliche.

*Was ausdruecklich NICHT beschlossen ist:* ob eine Recherche wirklich ohne Rueckfrage laufen
darf. Sie kostet, sie geht nach draussen, und ihr Ergebnis landet im Bestand. Die vier
Stopp-Punkte des Hauses (Zugangsdaten, Aussenwirkung, Unumkehrbares, Geld) beruehren das
mindestens an einer Stelle. Diese Entscheidung gehoert dem Betreiber und ist hier offen
vermerkt, nicht vorweggenommen.

## Abnahme je Schritt — ENTWURF, fuenf Schwellen warten auf den Betreiber

Erhoben mit `abnahme.py` am 2026-08-09: 4 von 21 Abschnitten haben ueberhaupt ein Kriterium,
und alle vier zeigen auf `pruefer.py` — dessen Selbsttest prueft das Werkzeug, nicht den
Schritt. **Kein Abschnitt ist heute maschinell abnehmbar.** Ohne diese Spalte ist die
Zielvorgabe `82d678f2` (Plan autonom abarbeiten) nicht erreichbar: nicht der Anstoss fehlt,
sondern die Abnahme.

| Schritt | Fertig, wenn | Werkzeug |
|---|---|---|
| S1 | Anteil Knoten mit ABGELEITETEM Reifegrad steigt gegen die Vormessung (43 %) | `reifegrad.py --selftest` |
| S1b | kein Treffer aus `gattung=nachschlagewerk` im `recall_log` ueber N Einspielungen | Abfrage, Werkzeug fehlt |
| S1c | schweigt | `rasterblick.py --melder` |
| S1d | jede Aussage ueber Menschen/Recht/Umgangsformen traegt einen Geltungsraum; Melder meldet 0 ohne | `normachsen.py --melder`, Achse fehlt noch |
| S2 | jeder abgewiesene Schreibversuch erscheint im Gespraech — Quote gemeldet/abgewiesen = 1 | `sichtbarkeit.py --selftest` + Zaehlung |
| S3 | Zahl der Knoten mit Quelle aus dem Zitationsnetz ueber Schwelle | **Schwelle offen** |
| S4 | mindestens ein Knoten ist nachweislich befoerdert worden, mit Herkunft und Zeitpunkt | Werkzeug fehlt |
| S5 | 0 fremde Adressen im ausgelieferten Betrachter, und er zeigt alle Eintraege | `grep` + Zaehlung |
| S6 | bewusst NICHT gebaut. Fertig ist der MELDER auf die Abbruchbedingung, nicht das Rollenmodell | Melder pruefen |
| S7 | `--schreiben` gelaufen, erzeugte `.md` deckungsgleich mit dem Bestand, Kantenarten im Server erlaubt | `planordnung.py --selftest` |
| S8 | Selbsttest gruen UND mindestens eine Pruefung, die im Bestand anschlaegt | `pruefer.py` ✓ erfuellt |
| S9 | Suchpfad-Weg trifft mindestens so viel wie der alte, bei nicht hoeherer Zeichenzahl | `abrufguete.py` |
| S10 | Vorlaufmessung mit 50–100 eindeutig unaehnlichen Negativpaaren ist gefahren UND die Grenze ist AUS IHR abgeleitet (Fehlerquote samt Konfidenzintervall), nicht gesetzt | Recherche 2026-08-09: **es gibt keinen Standardwert** |
| S11 | Selbsttest gruen UND mindestens ein echter Fund im Bestand | `arbeitsmelder.py` ✓ erfuellt |
| S12 | Reranking gebaut UND Trefferzahl steigt gegen die Basislinie bei gleicher Zeichenmenge | **Schwelle offen** |
| S13 | Selbsttest gruen UND `recall_log` fuehrt Zeilen mit `ausloeser=antwort` | `haken/antwort_abruf.py` ✓ fast erfuellt (3 Zeilen) |
| S14 | jede vom Melder genannte Spalte hat einen Schreiber ODER einen begruendeten Ausnahmeeintrag — Rest 0 | `pruefer.py --melder` |
| S15 | jeder Korpusfall traegt seine Wortueberlappung, und keiner liegt ueber der Aufnahmegrenze | **Schwelle offen** (Bezug: 10,7 %) |
| S16 | Stufe 1: alle 16 Knoten fremder Herkunft tragen eine Frist oder ein Pruefdatum | Abfrage |

**Die fuenf Schwellen gehoeren dem Betreiber, nicht dem Assistenten** — wer sie nachtraeglich
setzt, setzt sie zum Ergebnis passend. Das ist die Fehlklasse, die heute viermal auftrat
(`L-352afa`, inzwischen zur Regel eskaliert).

*Was diese Spalte NICHT leistet, und das steht auch im Werkzeug:* Ein gruener Selbsttest
belegt das Werkzeug, ein schweigender Melder den heutigen Bestand. Beides ist notwendig und
nicht hinreichend fuer "der Schritt ist inhaltlich erledigt". Wo ein Kriterium nur das
Werkzeug prueft, ist es als solches gekennzeichnet.

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

## Fortschreibung 2026-08-09T17:40:00+0200 — was der Quelltextvergleich mit claude-obsidian aendert

Anlass: Der Betreiber brachte `github.com/AgriciDaniel/claude-obsidian` ein (10.609 Sterne,
seit 2026-04-07, MIT, letzter Push 2026-08-01). Die Wettbewerbsrecherche dieses Tages hatte
es uebersehen, weil sie nach EIGENSCHAFTEN suchte und nur WebSearch als Suchraum hatte —
Codeverzeichnisse standen nicht einmal in ihrem Rastervermerk (`L-402a51`). Befund der
Quelltextpruefung: Knoten `0011e658`.

**Drei Abschnitte dieses Plans aendern sich, einer faellt weg.**

### S1b wird konkreter: zwei Merkmale fehlen im eigenen Entwurf

Der dortige Belegapparat ist gebaut und im Code durchgesetzt, nicht nur beschrieben
(`claude_obsidian/ledgers.py`): eine akzeptierte Behauptung braucht ein Pruefdatum und
frische, aktive, **nicht-synthetische** Stuetze; eine hochriskante braucht **zwei
unabhaengige** Quellen, wobei `_independent_group_count()` nach einem `independence_key`
gruppiert — drei Meldungen derselben Agentur zaehlen als eine Quelle; und eine akzeptierte
Behauptung mit frischem Gegenbeleg muss auf `contested` oder auf Schlichtungsnotizen.

Der eigene Entwurf (`belegt`/`berichtet`/`bekundet`) hat davon keines. **Zu ergaenzen:**
1. **Unabhaengigkeitsschluessel** am Werk. Ohne ihn zaehlt derselbe Urheber mehrfach.
2. **Eine eigene Stufe fuer maschinell Erzeugtes.** Das trifft die gemessene Wunde direkt:
   62 von 72 Normentscheidungen hat ein KI-Akteur sich selbst gegeben. Unter dieser Regel
   traegt keine davon eine akzeptierte Aussage.

*Nicht uebernommen:* die dortige Trennung in Quellen- und Behauptungsverzeichnis als zwei
Dateien. Unsere Aussagen sind Zeilen einer Datenbank; die Trennung ist bei uns eine Spalte.

### S12 ist kein Forschungsschritt mehr, sondern ein Nachbau

Dort laeuft, was hier als groesster Rueckstand gefuehrt wird (`scripts/retrieve.py`):
BM25 ueber kontextualisierte Abschnitte, top-20, danach Cosinus-Rerank ueber lokale
Ollama-Einbettungen auf top-5, mit Rueckfall auf reine BM25-Reihenfolge, wenn kein Modell
erreichbar ist. Alle Bausteine liegen hier bereits vor (bge-m3 laeuft lokal, Einbettungen
sind im Bestand). Die Reihenfolge aus S12 bleibt — billig vor teuer —, aber Stufe 2
(Reranking nach der Vereinigung, VOR der Deckelung) ist ab jetzt eine Uebertragung mit
lesbarem Vorbild unter MIT-Lizenz, keine Erfindung.

### NEU: Auslieferung am Sitzungsstart, als Antwort auf eine Klasse, die der Haken nicht erreicht

Dort haengt Wissen NICHT am Prompt: `hooks/hooks.json` kennt nur `SessionStart` und `Stop`.
Am Sitzungsstart wird ein begrenzter Block (`wiki/hot.md`) eingespielt, sonst wird auf
Aufruf gesucht.

Das ist zuerst als Schwaeche gelesen worden und ist an einer Stelle eine Staerke: gemessen
am 2026-08-09 erreichen **28 von 94** Betreibernachrichten den `UserPromptSubmit`-Haltepunkt
nie, weil der Klient sie waehrend laufender Arbeit als `attachment` zustellt. Fuer diese
Klasse ist ein Prompt-Haken strukturell blind — was am Sitzungsstart geladen wurde, ist
dagegen da, egal wie eine spaetere Nachricht zugestellt wird.

*Zu pruefen, nicht beschlossen:* ob ein begrenzter Startblock (Umfang gedeckelt, Auswahl aus
dem Arbeitsgegenstand) mehr traegt als die 44 von 94 gefeuerten Einspielungen. Massstab
bleiben die zwei Zahlen — Zieltreffer und Zeichen je Prompt; ein Startblock verschiebt Kosten
von je-Prompt auf einmalig und ist damit nicht direkt vergleichbar. Das gehoert vor dem Bau
gemessen.

### Was NICHT uebernommen wird, samt Preis — KORRIGIERT am selben Tag

*Erste Fassung dieses Abschnitts, falsch:* "Der Transaktionsapparat wird nicht uebernommen.
Bei einer lokalen Datenbank mit EINEM Schreiber leistet die Datenbanktransaktion dasselbe.
Die Abbruchbedingung ist dieselbe wie bei S6 (mehr als eine Person schreibt)."

**Der Betreiber hat widersprochen, und die Messung gibt ihm recht.** Die Abbruchbedingung ist
nicht "mehr als eine PERSON", sondern "mehr als ein gleichzeitiger SCHREIBER" — und der
existiert seit Wochen. Gemessen im `access_log`: in acht verschiedenen Stunden am
2026-08-08/09 schrieben ZWEI bis DREI verschiedene Sitzungen in dieselbe Datenbank, in der
Spitzenstunde 634 Zeilen. Der Grund ist die Arbeitsweise dieses Hauses: mehrere Arbeitsbaeume,
mehrere Klienten, Agenten nebenher. Eine Person mit fuenf Sitzungen ist fuer die Datenbank
dasselbe wie fuenf Personen.

**Was heute an dieser Stelle steht** (`knowledge_mcp_server.py`): WAL plus
`BUSY_TIMEOUT_MS = 2000`. Der Quelltext benennt die Grenze selbst — bei echtem Gedraenge
reichen zwei Sekunden nicht, dann kommt "database is locked". Das ist Warten und Hoffen, kein
Konfliktbegriff: es gibt keine Zusammenfuehrung zweier gleichzeitiger Aenderungen, keine
Inspektion vor der Anwendung, keinen Rueckweg bei Kollision. Genau das leistet der dortige
Apparat.

**Neue Fassung der Entscheidung:** Der Apparat wird nicht als Ganzes uebernommen (4.680 Zeilen
fuer eine lokale Datei waeren unverhaeltnismaessig), aber die Frage ist ab jetzt OFFEN statt
vertagt, und sie hat einen Messpunkt: wie oft schlaegt ein Schreibvorgang heute wegen Sperre
fehl, und was passiert dann mit dem Inhalt? Solange das ungemessen ist, ist "wir brauchen es
nicht" eine Behauptung. **Zu bauen zuerst: der Zaehler, nicht der Apparat.**

*Was S6 (Rechtemodell) davon NICHT beruehrt:* Nebenlaeufigkeit und Rechte sind zwei Fragen.
Wer gleichzeitig schreibt, ist ein Sperrproblem; wer schreiben DARF, ein Rechteproblem. Die
Vertagung von S6 stand auf "es gibt genau einen Menschen" — das bleibt richtig. Die
Vertagung der Nebenlaeufigkeit stand auf derselben Begruendung, und dort war sie falsch.

### Einwand des Betreibers zur Unabhaengigkeitsregel — sie gilt nicht ueberall

Der Betreiber wandte ein: Bei einem Gesetzestext gibt es nur EINE Wahrheitsquelle, die
amtliche. Zwei unabhaengige Quellen zu verlangen waere dort nicht strenger, sondern falsch.

Das trifft, und es zeigt eine Schwaeche der dortigen Bauform: ihre Regel haengt am RISIKO
(`high-risk acceptance requires two independent sources`), nicht an der ART der Aussage.
Fuer eine empirische Behauptung ist Mehrfachbestaetigung der richtige Massstab; fuer eine
Norm ist es AUTHENTIZITAET — stammt der Text von der Stelle, die ihn erlassen darf. Eine
zweite Quelle macht ein Gesetz nicht gueltiger, sie macht es nur abgeschrieben.

**Daraus die eigene, schaerfere Fassung** (und hier ist die Normachse aus Knoten `b6305304`
der Vorteil, den die dortige Bauform nicht hat):

| Art der Aussage | Massstab | zweite Quelle |
|---|---|---|
| empirische Behauptung | Mehrfachbestaetigung | ja, bei hohem Risiko zwei unabhaengige |
| Norm fremder Herkunft (Gesetz, DIN, BSI) | Authentizitaet der erlassenden Stelle | nein — eine amtliche Quelle genuegt und ist die beste |
| Hausnorm | Hausrecht des Betreibers | nein |

Der Unabhaengigkeitsschluessel bleibt trotzdem noetig — aber fuer die empirische Zeile, und
dort loest er ein echtes Problem: drei Meldungen derselben Agentur sind eine Quelle.

### Einwand des Betreibers zum Startblock — dynamisch schlaegt statisch, ausser bei einer Klasse

Der Betreiber wandte ein: Der eigene Weg ist dynamisch und sparsamer; die gesamte Datenbank
laesst sich nicht am Anfang einspielen.

Richtig, und die Zahlen stehen dagegen: 2.032 Knoten und 706 Lehren passen in keinen
Startblock. Der eigene Abruf waehlt je Prompt aus und liefert 9.409 Zeichen bei Deckel 10/7 —
ein Startblock verschiebt diese Kosten auf einmalig, kann aber nicht wissen, was in der
dritten Stunde gebraucht wird.

**Deshalb NICHT entweder/oder.** Der Startblock ist keine Alternative zum Abruf, sondern eine
Grundversorgung fuer die eine Klasse, die der Abruf strukturell nicht erreicht: die 28 von 94
Nachrichten, die waehrend laufender Arbeit zugestellt werden und keinen Haltepunkt ausloesen.
Fuer sie ist "dynamisch" wertlos, weil gar nicht gefragt wird.

*Massstab, bevor gebaut wird:* Der Startblock waere klein und an den Arbeitsgegenstand
gebunden (Groessenordnung: die Handvoll Knoten des aktuellen Projekts), nicht der Bestand.
Und er wird gegen die richtige Klasse gemessen — nicht gegen den Pruefkorpus, sondern gegen
die Frage, ob eine Antwort auf eine eingereihte Nachricht danach besser ausfaellt.

### Was der Vergleich NICHT hergibt

Keine veroeffentlichte Abrufzahl. Ein Pruefkorpus (`wiki/meta/retrieval-benchmark-v1.7.md`)
und ein Laeufer (`scripts/benchmark-runner.py`) sind in den Tests vorgesehen — der Laeufer ist
im ausgelieferten Stand nicht enthalten, die Tests behandeln ihn ausdruecklich als optional,
und in der gesamten Dokumentation steht keine Zahl zu Recall oder Trefferquote. Der Vorsprung
dieses Hauses bei der Selbstmessung besteht also weiter; er ist nur kein Vorsprung mehr beim
Belegapparat und keiner beim Reranking.

*Grenze der Pruefung:* gelesen wurden README, WIKI.md, `hooks/hooks.json`, `scripts/retrieve.py`
und `claude_obsidian/ledgers.py` in Auszuegen — nicht `transaction.py`, `capture.py`,
`release.py`. Aussagen ueber deren Inneres waeren unbelegt.

## Was bewusst nicht getan wird

Kein eigener Betrachter (der vorhandene reicht, und im Video ist er selbst „schön zum Zeigen, zum Arbeiten kaum relevant"). Keine PDF-Verarbeitung im Speicher — das Papernetz kann das, die Arbeitsteilung bleibt. Keine Rückrechnung alter Bestände vor dem jeweiligen Mechanismus.
