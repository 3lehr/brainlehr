# Multiview — Gesamtplan, gemessen statt vermutet

Stand 2026-08-13T15:38:18+0200. Ersetzt nicht
[PLAN_MULTIVIEW_2026-08-13.md](PLAN_MULTIVIEW_2026-08-13.md), sondern setzt ihn
fort: dort steht der Auftrag und die Priorisierung, hier der **gemessene
Ist-Stand** und die daraus folgende Bauform.

**Betreiberanweisung 2026-08-13T15:36:** *„ja zuerst die höchste Prio, aber
alles andere mitdenken, Gesamtplan erstellen und vollständig umsetzen"*. Der
Übergabecharakter des Vorgängerplans entfällt damit — es arbeitet eine Sitzung.

---

## §0 · Der gemessene Ist-Stand

Alles hier ist gezählt, nicht geschätzt. Der Vorgängerplan trug an drei Stellen
„zu prüfen, nicht anzunehmen" — das ist jetzt geprüft, und **zwei von drei
Annahmen waren falsch oder unvollständig**.

### Der Quellenbestand von buckeberg

| Menge | Zahl | Anmerkung |
|---|---|---|
| `dossier/quellen.json` | **48** Quellen | Schlüssel 1–48, lückenlos; dazu 3 Verwaltungszeilen |
| **davon markierbar** (`suchtext`) | **14** | ← die einzigen mit echter Fundstelle |
| davon nur aufschlagbar (`seite` ohne `suchtext`) | 1 | Quelle 1 |
| davon ohne jede Stelle | 33 | |

**Format gegen Fundstellenqualität** — die Randsummen allein verstecken den
Befund, der den Zuschnitt entscheidet:

| Format | markierbar | nur Seite | keine Stelle | Σ |
|---|---|---|---|---|
| pdf | **14** | 1 | 6 | 21 |
| html | 0 | 0 | **20** | 20 |
| bild / text / ohne Datei | 0 | 0 | 7 | 7 |

**Jede markierbare Quelle ist ein PDF. Keine einzige der 20 HTML-Quellen trägt
eine Stelle** — das sind 42 % des Bestands, geschlossen im Regelfall. Für HTML
ist die Fundstelle damit kein Anzeigeproblem, sondern ein Datenproblem, und die
Volltextsuche ist dort der einzige Weg, der überhaupt existiert. Festgehalten
als Test (`test_jede_markierbare_quelle_ist_ein_pdf`), nicht als Satz.
| Dateiformate der Quellen | 21 pdf · 20 html · 1 jpg · 1 txt · 6 ohne | |
| PDFs unter `homepage/public/quellen/` | 29 | |
| **davon mit Textschicht** | **29 von 29** | `textutil`, > 200 Zeichen |
| Dokumentenbestand `dokumente/` | 1103 Dateien | 363 pdf · 366 txt · 364 json |

### Die drei geprüften Annahmen

1. **„Die meisten Dokumente sind maschinenlesbar gemacht" — bestätigt, besser
   als gedacht.** Jedes PDF unter `dokumente/` trägt zwei Beidateien: `.txt`
   (Volltext) und `.json` (Volltext + `meta.seiten` + Zusammenfassung). Der
   Volltext ist mit `--- Seite N ---` **seitenweise gegliedert**. Damit ist die
   Seitenzahl zu einem Textschnipsel *rechenbar*, nicht zu raten.

2. **„Die Homepage hat bereits Anker in die Dokumente hinein" — bestätigt, aber
   in anderer Bauform als angenommen.** Die Anker sind keine PDF-Ziele, sondern
   URLs auf einen mitgelieferten pdf.js-Viewer:
   `homepage/src/lib/pdf-viewer-link.mjs` baut
   `/pdfjs-viewer/web/viewer.html?file=…#page=N&search=…&phrase=true`.
   Die **Datenform** ist wiederverwendbar (Datei + Seite + Suchtext), der
   **Anzeigeweg** nicht — er hängt am Browser der Homepage.

3. **„Bildschirmabzug + Texterkennung als Notlösung" — nachweislich nicht
   nötig.** 29 von 29 Quellen-PDFs tragen eine Textschicht. Es gibt nichts zu
   erkennen. Diese Notlösung wird nicht gebaut, und der Grund ist eine Zahl,
   kein Eindruck.

### Der Stand der App

| | |
|---|---|
| `app/Sources/BrainlehrApp/` | 5 Swift-Dateien, SwiftUI-Schale |
| `app/Sources/BrainlehrCore/` | 4 Dateien, oberflächenfrei, testbar |
| `app/Tests/BrainlehrCoreTests/` | 2 Testdateien |
| Seitenleiste | 6 Einträge, davon **4 Platzhalter** |
| Dienst | `berichte/entscheidungen_server.py`, Port 8799, 944 Zeilen |
| Routen | GET `/`, `/api/stand`, `/api/raum`, `/api/vergleich`, `/api/echtkorpus`; POST 5 weitere |
| Fremdpakete | **keine** — und das bleibt so |

---

## §1 · Der Befund, der den ganzen Zuschnitt trägt

> **14 von 48.** Nur vierzehn Quellen tragen eine markierbare Fundstelle. Für
> 33 weiß heute niemand, *welche Zeile* gemeint ist.

Das ist die eigentliche Lücke, und sie ist **keine Anzeigefrage**. Ein Viewer,
der 48 Dokumente öffnen kann, aber nur 14 aufschlagen, löst das Problem des
Termins zu einem Viertel.

Der Vorgängerplan sagt es schon, ohne die Zahl zu kennen: *„Eine falsch
gesetzte Markierung ist schlimmer als keine — sie sieht aus wie ein Beleg."*
Mit 14 von 48 ist das keine theoretische Sorge, sondern der Regelfall.

**Nachtrag — dieselbe Zahl war zweimal falsch, und beide Male aus demselben
Grund.** Er ist wichtiger als die Zahl:

1. Zuerst hieß es **13 von 49**, weil ich nach „`seite` UND `suchtext`" gezählt
   hatte. Quelle 48 trägt einen Suchtext ohne Seite — die Seite findet PDFKit
   beim Anzeigen selbst, markierbar ist sie trotzdem. Der Gegenprobe-Test
   („alle übrigen müssen schweigen") wurde rot und nannte sie namentlich.
2. Dann hieß es **14 von 49**, und der Nenner war falsch. `_rang` ist eine
   Verwaltungszeile, aber als **Objekt** notiert — mein Filter
   `isinstance(v, dict)` ließ sie durch und machte sie zur 49. Quelle. Richtig
   sind 48, Schlüssel 1–48 lückenlos. Gefunden hat das der Bauform-Prüfer des
   Konsils, indem er nachzählte statt zu übernehmen.

**Beide Male habe ich nach der FORM gefiltert statt nach der BEDEUTUNG** — erst
nach gefüllten Feldern statt nach Verwendbarkeit, dann nach Werttyp statt nach
Schlüsselform. Dass dieselbe Fehlerklasse zweimal in einer Sitzung durchkam,
ist der eigentliche Befund; beide Fälle sind jetzt als Test festgenagelt.

**Aufschlagen und Markieren sind zwei Aussagen**, und sie fallen auseinander.
Quelle 1 ist der Gegenfall: Seite 4 ist gepflegt, ein Suchtext nicht. Das
Dokument lässt sich richtig aufschlagen, hervorgehoben werden darf nichts.
`Fundstelle.markierbar` trennt das; `belegt` allein würde beides vermischen.

**Aufschlagen und Markieren sind zwei Aussagen**, und sie fallen auseinander.
Quelle 1 ist der Gegenfall: Seite 4 ist gepflegt, ein Suchtext nicht. Das
Dokument lässt sich richtig aufschlagen, hervorgehoben werden darf nichts.
`Fundstelle.markierbar` trennt das; `belegt` allein würde beides vermischen.

**Daraus die Reihenfolge, und sie ist bindend:**

```
Fundstelle rechnen  →  Dokument anzeigen  →  Stelle markieren  →  Raster
   (Python)              (Swift/PDFKit)        (Swift/PDFKit)     (Swift)
```

Wer den Viewer zuerst baut, hat einen Viewer und nichts zum Aufschlagen.

---

## §2 · Die Alternativen, samt Ablehnungsgrund

### Wo wird die Fundstelle gerechnet?

| Weg | Abgelehnt weil |
|---|---|
| **A · In Swift, in der App** | Der Volltext liegt in `.txt`/`.json` neben den PDFs; die Suche darüber ist reine Textarbeit. In Swift bräuchte sie eine zweite Implementierung, in Python steht sie neben dem Speicher, der die Belegkette hält. Und sie wäre nur über die gebaute App prüfbar statt per `python3 kern/fundstelle.py`. |
| **B · Im Speicher, als Tabelle** | Vorbau. Der Bestand ist eine JSON-Datei mit 49 Zeilen und ein Verzeichnis mit 366 Textdateien — dafür braucht es kein Schema. Wenn die Zahl wächst, ist die Tabelle ein Nachmittag. |
| **C · In Python, hinter dem Dienst** ✔ | Gewählt. Prüfbar ohne App, teilt sich den Speicher, und die App bekommt sie als Datenendpunkt — genau die Naht, die der Vorgängerplan vorschreibt. |

### Womit wird angezeigt?

| Weg | Abgelehnt weil |
|---|---|
| **A · pdf.js im WebView** | Wäre wiederverwendet — aber der Viewer liegt in buckeberg, nicht hier, und die App hinge an einem fremden Repo-Pfad. Dazu kein natives Markieren, keine Bedienungshilfen-Namen. |
| **B · Bildschirmabzug + Texterkennung** | 29 von 29 PDFs haben eine Textschicht. Es gibt nichts zu erkennen. Teuerste Lösung für ein Problem, das nicht existiert. |
| **C · PDFKit + Quick Look** ✔ | Gewählt. Beides ist im System (macOS 14), kein Fremdpaket. PDFKit **setzt** Markierungen als echte Anmerkung, Quick Look deckt HTML/JPG/TXT ab. Messbar an einem echten Dokument. |

### Wie schreiben Mensch und Modell gleichzeitig?

Unverändert übernommen aus dem Vorgängerplan: **Vorschlag statt Änderung**
(*review-first*, wie openlehr). Das Henne-Ei-Problem entsteht nicht, statt
gelöst zu werden. Eine Sperre je Absatz ist hakelig, echte Verschmelzung teuer.

---

## §3 · Die Bauform

### Schicht 1 · `kern/fundstelle.py` (Python, neu)

Eine Funktion, drei Quellen, in dieser Rangfolge:

1. **Gepflegte Fundstelle** aus `dossier/quellen.json` — Nummer → Datei, Seite,
   Suchtext. Höchster Rang, weil von Hand geprüft (`scripts/quellen_check.py`).
2. **Gerechnete Fundstelle** aus dem Volltext-Beidokument — Suchtext im `.txt`
   finden, Seite aus dem nächstliegenden `--- Seite N ---` davor ableiten.
3. **Keine.** Rückgabe `belegt: false` mit Grund. **Nicht raten.**

Der dritte Fall ist der wichtigste und der einzige, der ohne Vorsatz falsch
gebaut wird: Wer bei Nichtfund Seite 1 zurückgibt, hat aus „ich weiß es nicht"
ein „hier steht es" gemacht.

### Schicht 2 · `POST /api/fundstelle` (Dienst, Erweiterung)

Nimmt `{quelle: "14"}` oder `{text: "…", datei: "…"}`, gibt die Fundstelle
zurück. Die App **bestellt**, sie rechnet nicht selbst — die Naht des
Vorgängerplans bleibt, weil eine zweite Sitzung sonst dieselbe Logik zweimal
baut.

### Schicht 3 · `BrainlehrCore/Fundstelle.swift` (Swift, neu, oberflächenfrei)

Modell + Entscheidung *welche Rolle bekommt dieses Dokument* (aktuell / letztes
/ eingefroren). Reine Logik, ohne SwiftUI — dadurch **ohne gebaute App
testbar**, wie `DienstZustand` und `RepoWurzel` es vormachen.

### Schicht 4 · `BrainlehrApp/QuellenAnsicht.swift` (Swift, neu)

PDFKit für PDF, Quick Look für alles andere, drei Fensterrollen, ein
Zeitstrahl bei vielen Quellen. Fehlende Fundstelle → Dokument öffnet
**unmarkiert mit Hinweis**, nicht markiert auf Verdacht.

### Schicht 5 · `BrainlehrApp/RasterAnsicht.swift` (Swift, neu)

Felder sind Behälter, Belegung ist Konfiguration
(`app/Resources/raster.json`). Unbekannte Belegung → leeres Feld mit Hinweis,
kein Absturz.

---

## §4 · Was bewusst nicht getan wird, samt Preis

- **Keine Texterkennung, kein eigener Umwandler.** Preis: Ein PDF ohne
  Textschicht wird angezeigt, aber nicht markiert — und sagt das. Gewinn:
  Gemessen null Fälle im heutigen Bestand.
- **Keine Fundstellen-Tabelle im Speicher.** Preis: Bei sehr vielen Dokumenten
  wird die Volltextsuche langsam. Gewinn: kein Schema für 49 Zeilen. Umschlag,
  wenn eine Anfrage über 300 ms braucht — dann ist es ein Index, kein Umbau.
- **Keine Live-Verschmelzung.** Vorschlag statt Änderung.
- **Kein Chat-Feld, kein Denken-Fenster in dieser Runde.** Preis: Das Raster
  hat weniger zu zeigen. Grund: Beide brauchen einen Ereignisstrom aus der
  laufenden Sitzung, den es noch nicht gibt — das ist ein eigenes Vorhaben,
  kein Feld.
- **Keine Aufteilung auf mehrere Fenster oder Ströme**, solange nicht gemessen
  ist, dass eines nicht reicht.

---

## §5 · Woran sich Erfolg misst

| Schritt | Rot vor grün |
|---|---|
| Fundstelle | Die 13 gepflegten Quellen werden auf die richtige Seite aufgelöst. Die 36 ohne Fundstelle liefern `belegt: false` — **nicht** Seite 1. Gegenprobe in beide Richtungen. |
| Viewer | Je vorkommendem Format (pdf, html, jpg, txt) eine Probe an einem **echten** buckeberg-Dokument. Ein beschädigtes Dokument meldet, statt abzustürzen. |
| Markierung | Gemessen an Fällen mit **bekannter** Fundstelle, nicht am Eindruck. Negativfall: unbelegte Stelle wird nicht markiert. |
| Raster | Jede Aktion zuordenbar und verschiebbar. Unbekannte Belegung → leeres Feld mit Hinweis. |
| Termin | Eine Frage aus dem Kreis führt dazu, dass das Dokument an der richtigen Stelle markiert auf dem Schirm steht, ohne dass jemand sucht. |

---

## §6 · Auflagen für die Umsetzung

Aus dem Vorgängerplan übernommen, weiterhin gültig:

- Kein `git add -A`, kein Push, kein `git stash`. Commit mit **expliziter
  Pfadliste** — mehrere Sitzungen teilen den Index.
- Nicht `swift build`, sondern `app/bauen.sh`.
- Sichtprüfung **Text vor Bild** über die Bedienungshilfen. Wenn doch Bild:
  ausschließlich über die **Fenster-Kennung** der Zielanwendung, nie nach
  Bildschirmbereich (am 2026-08-12 wurden dabei zweimal private Inhalte
  miterfasst).
- „Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
  melde die Abweichung."
- buckeberg wird **nur gelesen**, nie geschrieben. Der Pfad
  `/Volumes/daten/Begod2026/buckeberg` ist konfigurierbar, nicht verdrahtet.

---

## Aufträge, fertig zum Übergeben (§7)

**Für alle Aufträge gleichermaßen:** Arbeitsort `/Volumes/daten/Begod2026/brainlehr`,
Zweig `brainlehr/b4-ausweis`. Zuerst `CLAUDE.md` lesen, dann diesen Plan.
„Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung." Kein `git add -A`, kein Push, kein `git stash`. Commit
mit expliziter Pfadliste. Nicht `swift build`, sondern `app/bauen.sh`.
Sichtprüfung **Text vor Bild** über die Bedienungshilfen; wenn doch ein Bild
nötig ist, ausschließlich über die **Fenster-Kennung** der Zielanwendung, nie
nach Bildschirmbereich. buckeberg wird **nur gelesen**.

### Schritt A · Der PDF-Betrachter der Homepage ist tot — das zuerst

| | |
|---|---|
| **Darf ändern** | `buckeberg/.gitignore`, `buckeberg/homepage/src/lib/pdf-viewer-link.mjs`, `buckeberg/homepage/src/pages/quellen.astro` |
| **Tabu zusätzlich** | alles in brainlehr; `buckeberg/dossier/`, `buckeberg/dokumente/`, `buckeberg/recht/` — Inhalte gehören dem Betreiber |
| **Fakten** | `homepage/vendor/pdfjs-viewer/` enthält `LICENSE` und `web`, **kein `build/`**. `web/viewer.html` lädt `../build/pdf.mjs`; diese Datei existiert im ganzen Repo nicht. Ursache: `.gitignore` Zeile 21 `**/build/`. Der Betrachter zeigt eine graue Fläche **ohne Fehlermeldung**. `scripts/quellen_check.py` meldet „Keine Fehler" — er prüft die Daten, nicht die Anzeige. Zusätzlich: `quellen.astro` hat `ANZAHL_QUELLEN = 45` fest verdrahtet, das Dossier zitiert [47] und [48]. 22 der 43 hinterlegten Dateien sind gar keine PDFs und werden trotzdem durch pdf.js geleitet. |
| **Abnahme** | Rot vor grün am **laufenden** `dist/`, nicht am Quelltext: vorher graue Fläche, nachher das Dokument. Je Format eine Probe (pdf, html, jpg, txt). Negativfall, der wichtigere: eine Quelle, deren Datei fehlt, führt zu einer **Meldung**, nicht zu einer grauen Fläche — der stille Fehlschlag ist der eigentliche Befund. Gegenprobe: `ANZAHL_QUELLEN` aus der Datei ableiten, dann müssen 46–48 erreichbar sein. |

### Schritt B · HTML-Quellen bekommen eine Fundstelle

| | |
|---|---|
| **Darf ändern** | `buckeberg/dossier/quellen.json` (nur die Felder `seite`/`suchtext`/`anker`), `buckeberg/scripts/quellen_check.py` |
| **Tabu zusätzlich** | `kern/`, `haken/`, `melder/`, `tests/`, `runs/`, `schema.sql`, `knowledge_mcp_server.py` — die gehören der parallelen Python-Sitzung |
| **Fakten** | Alle 14 markierbaren Quellen sind PDF. **Keine der 20 HTML-Quellen trägt eine Stelle** — 42 % des Bestands. Bei **19 von 20** steht die Stelle bereits im Klartext im Feld `kurz` („§ 16 Abs. 2 Satz 2 WEG — abweichende Kostenverteilung"). Die HTML-Dateien tragen 16 `id=`-Anker, alle Layout (`fTop`, `imgmap…`), keiner auf einen Absatz. |
| **Abnahme** | **Zuerst zählen**, wie viele der 20 einen Paragraphen im `kurz`-Feld tragen (erwartet 19, mit Nenner belegen). Dann je Quelle prüfen, ob der Paragraph im HTML als Textstelle auffindbar ist. Rot vor grün: vorher 0 von 20 markierbar, nachher die gemessene Zahl. Negativfall: ein Paragraph, der im Dokument **nicht** vorkommt, wird als Befund gemeldet und **nicht** eingetragen — eine erfundene Stelle ist schlechter als keine. |

### Schritt C · Die Anzeige, mit den gemessenen Werkzeugen

| | |
|---|---|
| **Darf ändern** | `app/` (gesamt) |
| **Tabu zusätzlich** | wie Schritt B; zusätzlich `berichte/entscheidungen_server.py` — neue Datenendpunkte werden **bestellt**, nicht dort gebaut |
| **Fakten** | Gemessen am 2026-08-13 auf diesem Rechner (macOS 26.5.1, nicht 14 — `Package.swift` setzt `.macOS(.v14)`, das ist hier **nicht** prüfbar): PDFKit findet die Seite selbst über `doc.index(for: selection.pages.first)`, Suchdauer 12 ms. **Quick Look kann weder aufschlagen noch hervorheben noch einen Fehlschlag melden** — es nimmt sogar eine erfundene `.zzq` an und liefert ein Symbol, das von Erfolg nicht zu unterscheiden ist. Für txt/html kann NSTextView beides nativ, mit Tastatur und Bedienungshilfen. Ein **gesperrtes** PDF ist nicht `nil`: `pageCount` stimmt, eine Miniatur entsteht, die Suche liefert 0 Treffer — aus „Passwort nötig" wird stillschweigend „keine Fundstelle". 8 Dokumente gleichzeitig = 240 MB, Suche darüber +200 MB; Öffnen kostet 2–5 ms. `PDFView` liefert `isAccessibilityElement()=false` und `AXUnknown`. |
| **Abnahme** | Rot vor grün je Format an einem **echten** buckeberg-Dokument. Vier Negativfälle, alle mit gebauten Gegenbeispielen: gesperrtes PDF → „Passwort nötig", **nicht** „keine Fundstelle" (`isLocked` **vor** der Suche abfragen); beschädigtes PDF → Meldung statt Absturz; unbekanntes Format → Meldung statt stillem Symbol; Quelle ohne Fundstelle → Dokument öffnet unmarkiert **mit Hinweis**. Gegenprobe zur harten Grenze: `shasum -a256` auf die Quelldatei vor und nach dem Markieren muss gleich sein — nie `write()`, sondern Anmerkung im Speicher oder `pageOverlayViewProvider`. |

## §8 · Fortschreibung

Wird nach der Umsetzung ergänzt: was anders kam als geplant, und warum.
