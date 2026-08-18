# Plan: drei Richtungen gegen den Abstraktionssprung — vergleichbar gemessen

**Erstellt** 2026-08-16T12:30:12+0200
**Verhältnis zum geltenden Plan:** untergeordnet zu `docs/PLAN_KANALGUETE_2026-08-15.md`
(K1). Löst nichts ab; K1 Punkt 1 und 2 sind erledigt, dies ist die Folgefrage.
**Anlass** Betreiber: *„wir sollten alles 3 testen und vergleichbar machen/halten"*

## §0 Gemessener Ist-Stand (2026-08-16, Knoten `291c2e3f`)

Eigener Prüfkorpus `runs/pruefkorpus.jsonl`, 35 Fälle:

| | |
|---|---|
| gefunden in den ersten 5 | **5 (14 %)** |
| Rang 6–50 | 7 (20 %) |
| außerhalb Top-50 | **23 (66 %)** |
| davon ohne Einbettung | **0** |
| Rang der 23 im **reinen Bedeutungskanal** | bester 42 · **Median 134** · schlechtester 2487 von 5963 |

**Damit ist ausgeschlossen:** Fusionsformel, Sockel, Stichwortkanal, Relevanzschwelle.
Keine Umordnung erreicht Rang 134. Die Ursache ist der Abstand zwischen Frageform
(Situationsbeschreibung in Alltagssprache) und Zielform (technische Fehlerbeschreibung
mit Eigennamen).

## §1 Die drei Richtungen

| | Was geändert wird | Kosten |
|---|---|---|
| **V1 Zweiteinbettung** | je Lehre/Knoten eine zusätzliche Einbettung, die die **Lage** beschreibt statt der Technik | einmalig je Eintrag |
| **V2 Anfrage umschreiben** | die Anfrage wird vor der Suche in ein hypothetisches Zieldokument übersetzt | **je Anfrage, dauerhaft** |
| **V3 anderes Modell** | `bge-m3` gegen ein Alternativmodell | einmalig, aber Neuberechnung des ganzen Bestands |

## §2 Was Vergleichbarkeit hier konkret heißt

`L-3bf6c7` ist der Grund für diesen Abschnitt: Dort liefen Vorher- und Nachher-Messung
über **verschiedene Korpora**, und beide Zahlen sahen plausibel aus. Deshalb bindend:

1. **Ein Korpus, alle Varianten:** `runs/pruefkorpus.jsonl`, dieselben 35 Fälle, dieselbe
   Reihenfolge. Kein Vorgabewert für den Korpus — er wird verlangt.
2. **Eine Kennzahl, dieselbe für alle:** Rang des Ziels im **reinen Bedeutungskanal**.
   Nicht die Trefferquote@5 des vollen Suchwegs — die mischt Stichwortkanal und Fusion
   hinein und macht die Varianten ununterscheidbar.
3. **Jede Zahl trägt ihren Weg mit** (Korpus, Modell, Codestand, Kandidatenzahl).
4. **Der Produktivbestand wird nicht angefasst.** V1 und V3 rechnen mit zusätzlichen
   Vektoren im Arbeitsspeicher gegen dieselbe Kandidatenmenge — keine Schreiboperation
   auf `knowledge_embeddings`, bevor eine Richtung gewählt ist.
5. **Ausgangslage ist eine eigene Stufe**, nicht eine Erinnerung an die Messung von
   heute früh. Sie läuft im selben Lauf mit.

## §3 Die Grenze dieser Messung — was sie NICHT beantwortet

*Pflichtteil nach `L-0a05b2`: jede Messung benennt, welche Frage sie nicht beantwortet.*

- Sie misst den **Bedeutungskanal**, nicht den vollen Suchweg. Eine Variante, die dort
  gewinnt, muss danach noch am echten Weg gemessen werden.
- Sie misst **35 Fälle**. Das ist klein — heute früh hat eine Stichprobe von 12 gegen 12
  eine saubere Trennung gezeigt, die bei 40 gegen 40 verschwand. Ein knapper Unterschied
  zwischen zwei Varianten ist damit **kein** Ergebnis.
- Sie misst **nicht die Kosten im Betrieb.** V2 kostet je Anfrage; ob das tragbar ist,
  ist eine andere Frage als ob es wirkt.

## §4 Modellwahl — nicht frei

Für V1 und V2 wird ein Modell zum Umformulieren gebraucht. Die Betreiberentscheidung
dazu liegt vor (`L-a69129`, dreimal verletzt): **für Prüfläufe Haiku, nicht das lokale
Modell** — der Unterschied ist die Geschwindigkeit, und Wartezeit war ausdrücklich
unerwünscht. Für V3 wird ein zweites **Einbettungs**modell gebraucht; welche lokal
verfügbar sind, wird gemessen, nicht angenommen.

## §5 Reihenfolge, und wo sie bindend ist

1. Messwerkzeug mit **Stufe 0 (Ausgangslage)** — erst wenn es die heutigen Zahlen
   reproduziert, ist es vertrauenswürdig.
2. V1 an **fünf Lehren** als Vorprobe. Zeigt sich dort nichts, wird der ganze Bestand
   nicht angefasst.
3. V3 (nur wenn ein zweites Modell verfügbar ist), V2 zuletzt — sie ist die einzige mit
   dauerhaften Kosten.

**Bindend:** Stufe 0 zuerst. Ein Messwerkzeug, das die bekannte Ausgangslage nicht
trifft, misst etwas anderes als gedacht.

## §6 Woran sich Erfolg messen lässt

Nicht „eine Variante ist besser". Sondern: **der Median-Rang der heute 23 verlorenen
Fälle**, je Variante, mit Angabe der Kandidatenzahl. Und ausdrücklich auch das
Nullergebnis — eine Richtung, die nichts bringt, wird als solche festgehalten statt
stillschweigend fallengelassen.

## Fortschreibung 2026-08-16T14:15:00+0200 — V2 gemessen, und sie wirkt

Der Plan hielt die Messung für blockiert („kein Modellzugang"). Das war eine Aussage
über den eigenen Aufbau, nicht über die Lage: Ollama lief die ganze Zeit, und Haiku
ist über einen Subagenten erreichbar. Gebaut wurde deshalb `--umschriften` — ein
Haiku-Subagent schreibt die 35 Texte, das Modul rechnet sie. L-a69129 bleibt gewahrt,
sie verlangt das Modell, nicht den Abrechnungsweg.

| Lauf | top5 | top50 | Median-Rang |
|---|---|---|---|
| Stufe 0 (Ausgangslage) | 4/35 | 13 | 79 |
| **V2 Anfrageumschrift** | **11/35** | **19** | **35** |
| Gegenprobe (Identität) | 4/35 | 13 | 79 |

Von 5973 Kandidaten. Die Gegenprobe reproduziert Stufe 0 **exakt** — der Unterschied
kommt aus der Umschrift, nicht aus dem Messweg. Das ist der Beleg, den der Plan als
Bedingung genannt hat.

**Was die Zahl NICHT sagt:** Sie misst den reinen Bedeutungskanal, nicht den vollen
Suchweg; 35 Fälle sind klein; und die Betriebskosten je Anfrage sind hier nicht
gemessen, weil das Umschreiben vorher im Subagenten geschah. Ein Verfahren, das jede
Anfrage durch ein zweites Modell schickt, kostet Zeit und Geld — das gehört gemessen,
bevor es in den Produktivweg geht.

### Der Befund am Prüfstand, der die Zahl fast wertlos gemacht hätte

Der erste Subagentenlauf lieferte alle 35 Umschriften auf **Englisch**, gegen einen
durchweg deutschen Bestand. Die Messung wäre gelaufen, hätte eine plausible Zahl
geliefert — und eine Sprachdifferenz gemessen statt der Variante. Aufgefallen ist es
beim Lesen der Ausgabe, nicht durch eine Prüfung; die Abnahme des Auftrags verlangte
Vollständigkeit und Format, aber nichts über die Sprache.

Nachgefordert wurde mit einer Abnahme, die eine **Null** verlangt: Zahl der
Umschriften ohne deutsches Funktionswort. Das ist die Form, die trägt — eine
Zusicherung, die einen Fehlschlag verlangt, statt einer, die Erfolg beschreibt.

## Fortschreibung 2026-08-16T14:30:00+0200 — V1 gemessen, und ihre Gegenprobe korrigiert die eigene Zahl

| Lauf | top5 | top50 | Median-Rang |
|---|---|---|---|
| Stufe 0 (Ausgangslage) | 4/35 | 13 | 79 |
| **V1-Gegenprobe** (Volltext neu eingebettet) | 4/35 | **16** | **56** |
| **V1 situative Zweiteinbettung** | 6/35 | 18 | 42 |
| **V2 Anfrageumschrift** | **11/35** | **19** | **35** |

**Die Gegenprobe von V1 reproduziert Stufe 0 nicht.** Sie trifft die 4/35 in den Top-5,
aber top50 steigt von 13 auf 16 und der Median fällt von 79 auf 56 — **ohne dass eine
Variante wirkt**. Die Gegenprobe bettet nur den Originaltext des Ziels ein zweites Mal
ein; dass das allein schon Ränge verbessert, heißt: die gespeicherte Einbettung eines
Knotens ist schlechter als eine frisch aus seinem Volltext gerechnete.

**Das ändert, woran V1 zu messen ist.** Gegen Stufe 0 sieht V1 nach +2 Top-5 und +5
Top-50 aus. Gegen ihre **eigene Gegenprobe** — den ehrlichen Maßstab — bleiben +2 Top-5
und +2 Top-50. Der Rest war kein Variantenerfolg, sondern ein Nebeneffekt des
Neu-Einbettens.

**Der Nebenbefund ist wertvoller als die Variante:** Ein Teil des Rückstands liegt in
veralteten oder gekappten Einbettungen des Bestands, nicht im Verfahren. Der
Prüfer-Melder meldet unabhängig davon 94 Knoten mit veralteter Prüfsumme und 13 beim
Einbetten gekappte. Das ist billiger zu beheben als jede Variante und gehört zuerst
gemessen.

### Entscheid

**V2 (Anfrageumschrift) gewinnt** — 11/35 gegen 6/35, und ihre Gegenprobe reproduziert
Stufe 0 exakt, ihre Zahl ist also unverfälscht. V1 wirkt, aber schwächer als es zunächst
aussah. V3 (Zweitmodell) war bereits ausgeschieden.

**Nicht empfohlen wird der sofortige Produktiveinsatz von V2.** Sie schickt jede Anfrage
durch ein zweites Modell; die Betriebskosten sind in keinem der Läufe gemessen, weil das
Umschreiben vorher im Subagenten geschah. Bei 35 Fällen und einem Unterschied, der bei
7 Treffern liegt, wäre eine Umstellung des Produktivwegs eine Wette. Nächster Schritt ist
deshalb nicht der Einbau, sondern die Kostenmessung — und davor die Einbettungshygiene,
weil sie beide Varianten gleichermaßen hebt.

**Verzerrung, die zu benennen ist:** Die Kandidatenzahl wuchs während der Läufe von 5972
auf 5976, weil parallele Sitzungen Knoten anlegten. Vier Kandidaten auf sechstausend
ändern keine dieser Aussagen, aber die Läufe sind dadurch nicht bit-identisch vergleichbar.

## Fortschreibung 2026-08-16T14:45:00+0200 — meine eigene Empfehlung gemessen und widerlegt

Der Entscheid oben empfahl „zuerst Einbettungshygiene, sie hebt beide Varianten". **Gemessen,
und die Empfehlung trägt nicht.**

`kern/build_embeddings.py` gefahren: 128 Einträge neu gerechnet, danach meldet
`melder/vektorstand.py` **0** veraltete Prüfsummen (vorher 101 Knoten und 27 Lehren).
Stufe 0 danach neu gemessen: **top5 4/35, top50 13, Median 79** — Zeichen für Zeichen
dieselbe Zahl wie vorher. Die veralteten Prüfsummen betrafen die Korpusziele nicht.

### Drei Ursachen geprüft, drei ausgeschieden

| Vermutung | Messung | Ergebnis |
|---|---|---|
| Pfad im eingebetteten Text stört | 35 Ziele mit/ohne Pfad | 9 besser, 10 schlechter — kein Hebel |
| Veraltete Prüfsummen | 128 neu gerechnet, Stufe 0 wiederholt | unverändert 4/35, 13, 79 |
| `resolution` fehlt in `lesson_text` | 15 Lehren mit/ohne dieses Feld | 6 besser, 7 schlechter, Median 62→59 |

Der dritte Punkt bleibt trotzdem ein **Bestandsbefund**: `lesson_text()` setzt sich aus
Zuordnung, `description`, `root_cause` und `prevention` zusammen — `resolution` fehlt,
bei 925 von 954 Lehren gefüllt, im Schnitt 362 Zeichen. Das Feld ist im Bedeutungskanal
nicht auffindbar. Messbar besser wird die Suche dadurch aber nicht.

Außerdem geprüft und ausgeschieden: gespeicherte gegen frisch gerechnete Vektoren bei
identischem Text (12 Knoten, Kosinus **1,0000** durchgehend — der Bestand ist nicht
verrechnet), und die Fanout-Zeilen mehrwertiger Lehren (585 Lehren mit mehreren Zeilen,
Vektoren identisch, die Auswahl macht keinen Unterschied).

### Was bleibt: ein reproduzierter Effekt ohne erklärte Ursache

Ein frisch aus dem Volltext gerechneter Zielvektor rankt im Median besser als der
gespeicherte — **57 gegen 79**, in zwei unabhängigen Läufen reproduziert, bei
unverändertem top5 (4/35). Der Unterschied liegt also **nicht** an einer der drei
geprüften Stellen und ist bislang unerklärt.

**Damit ist auch die V1-Zahl weiter zu relativieren, nicht zu verbessern:** Ihr Zuwachs
gegenüber der eigenen Gegenprobe bleibt +2/+2, und der Sockel darunter stammt aus diesem
unerklärten Effekt, nicht aus dem Verfahren.

**Nächster Schritt ist deshalb nicht Hygiene und nicht Einbau, sondern die Ursachensuche
an diesem einen Effekt** — solange sie offen ist, trägt jede Variantenzahl einen Anteil,
den niemand zuordnen kann. Die Empfehlung „erst Hygiene" aus der Fortschreibung von 14:30
ist hiermit zurückgezogen.

---

## NACHTRAG 2026-08-18T12:10:00+0200 — der unerklärte Effekt war ein Messartefakt

Dieser Plan trägt die Warnung, ein frisch gerechneter Zielvektor rankte im
Median 57 statt 79 und die Ursache sei offen. **Sie ist es nicht mehr, und der
Effekt existiert nicht.** Gemessen über dieselben 35 Fälle
(`runs/pruefkorpus.jsonl`, bge-m3@ctx2048, heute 6164 Kandidaten):

| Weg | Median | top5 | top50 |
|---|---|---|---|
| gespeicherter Vektor (Stufe 0) | 80 | 4/35 | 13 |
| frisch, **kanonischer** Text (`build_embeddings.node_text`/`lesson_text` importiert) | 80 | 4/35 | 13 |
| frisch, Ad-hoc-Text (`variante_zweiteinbettung.lade_zieltext`) | 59 | 4/35 | 16 |

Bei gleichem Text ist der Rang in **35 von 35** Zeilen identisch. Der Unterschied
kam aus der Feldzusammensetzung: der Gegenprobe fehlt bei Knoten die
**Pfadzeile**, bei Lehren die **Zuordnung**, dafür trägt sie zusätzlich
**`resolution`**. Verglichen wurden also zwei verschiedene Texte unter dem Namen
„gespeichert gegen frisch".

**Folge für diesen Plan:** V1s Vergleichsbasis („V1-Gegenprobe", Median 56/57)
ist kein sauberer Nullpunkt — sie war selbst schon durch den Textunterschied
begünstigt. Der ehrliche Nullpunkt ist der kanonische Frisch-Wert (Median 80).
**V2 (Anfrageumschrift) ist nicht betroffen**: sie ändert nur die Anfrageseite.

**Offener Hebel, hier nur notiert:** Die abweichende Zusammensetzung rankt
*besser* — Lehren Median 43 statt 65, Knoten 71 statt 82. Gemessen allein im
reinen Bedeutungskanal über 35 Fälle, nicht über den vollen Suchweg und nicht
über den ganzen Bestand. Wer das bauen will, misst es zuerst über den vollen Weg.

Belege: Knoten `99f00e91`, Lehre `L-0e0ab6` (neuntes Vorkommen).

## ZWEITER NACHTRAG — 2026-08-18T13:30:00+0200: der Hebel trägt über den vollen Weg NICHT

Der erste Nachtrag nannte die abweichende Feldzusammensetzung als offenen Hebel
(Lehren Median 43 statt 65). Gemessen über den **vollen** Suchweg
(`knowledge_search`-Fusion inkl. Stichwort-Sockel, n=35, `MAX_RESULTS=300`,
5122 Knoten + 1057 Lehren, alle Varianten im selben Prozess, keine Schreibung):

| Zusammensetzung | top5 | top50 | Median | jenseits Rang 300 |
|---|---|---|---|---|
| heute | 4/35 | 12/35 | 115 | 7 |
| (a) nur Lehren geändert | 4/35 | 13/35 | **90** | 8 |
| (b) nur Knoten ohne Pfadzeile | 4/35 | 11/35 | 136 | 8 |
| (c) beides | 4/35 | 12/35 | 136 | 9 |

**top5 ist in allen vier Varianten identisch.** Der Stichwort-Sockel bestimmt
genau die Plätze, auf die es ankommt; die Textzusammensetzung wirkt erst
dahinter. Die Zahlen aus dem reinen Bedeutungskanal waren ein Artefakt dieses
Kanals — dieselbe Klasse wie im ersten Nachtrag, nur eine Ebene höher.

**Der Umbau unterbleibt.** Preis wäre gewesen: 6179 Vektoren, gemessen 453,5 s.
Positivkontrolle bestanden (Leitfall auf Rang 2). Ungemessen: Falschmeldeseite,
anderes `max_results`, Wirkung eines veränderten Sockels.

**Was daraus folgt:** Der Engpass ist der Sockel, nicht der Text. Knoten `99f00e91`.
