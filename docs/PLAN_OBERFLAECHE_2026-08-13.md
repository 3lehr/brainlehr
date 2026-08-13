# Die Oberfläche — vom geprüften Kern zur sichtbaren App

Stand 2026-08-13T18:51:50+0200. Setzt
[ADR-004](adr/ADR-004-anzeige-waechst-mit-der-flaeche.md) um.
Betreiberanweisung: *„arbeite alles geplant, mit klarer Zielvorgabe und autonom ab!"*

## §0 · Zielvorgabe in einem Satz

> **Jede Fähigkeit, die heute nur als geprüfter Kern existiert, wird sichtbar
> und bedienbar — oder sie wird als nicht vorhanden ausgewiesen.**

Kein Platzhalter, der behauptet, es käme noch etwas. Ein Eintrag, der nirgends
hinführt, ist teurer als ein fehlender.

## §1 · Der gemessene Ist-Stand

**Der Kern steht, die Haut fehlt.** Zehn Module in `BrainlehrCore`,
oberflächenfrei und geprüft — **108 XCTest-Fälle, 41 pytest, 23 Mutationsproben
gefahren, 23 rot.** Angeschlossen ist davon **keines**.

| Kernmodul | Was es kann | sichtbar? |
|---|---|---|
| `Anzeigeform` | Fläche + Abstand → Ausschnitt / ganze Seite / nebeneinander | nein |
| `Quelldokument` | Format-Weg, vier Negativfälle mit Handlung | nein |
| `Fundstelle` | Antwort des Dienstes, `markierbar` / `mehrdeutig` | nein |
| `Sitzungsstrom` | Chat, Denken, Werkzeuge, drei Ausführlichkeiten | nein |
| `Verschmelzung` | Live-Bearbeitung, Vorschlag annehmen/ablehnen | nein |
| `Sichtbarkeit` | Rollen, Freigabe, Schwärzung je Betrachter | nein |

Dazu die Python-Seite: `kern/fundstelle.py`, `kern/normfundstelle.py`,
`app/werkzeuge/pdf_schwaerzen.py`, `app/werkzeuge/ocr_stellen.swift`,
`app/werkzeuge/lesbarkeit.py`.

**Die Seitenleiste hat sechs Einträge, zwei davon führen zu
`PlatzhalterAnsicht`** — „Diese Ansicht wird als Nächstes gebaut." Das ist
Entwicklerinformation im sichtbaren Text und verstößt gegen die Hausregel.

## §2 · Die Reihenfolge, und wo sie bindend ist

```
B1 Quellenansicht ──► B2 Dateibrowser ──► B4 Raster
                 └──► B3 Sitzungsfenster
                 └──► B5 Live-Bearbeitung
```

**Bindend ist nur B1 vor B2 und B1 vor B4:** Der Browser rankt Dokumente, das
Raster stellt sie nebeneinander — beide brauchen eine Ansicht, die ein Dokument
zeigen kann. B3 und B5 hängen an nichts und dürfen jederzeit.

**B1 zuerst, weil es der Auftrag ist:** *„zeig mir, wo das steht"*.

## §3 · Alternativen, samt Ablehnungsgrund

| Weg | Abgelehnt weil |
|---|---|
| **Alles im WebView, wie der Wissensraum** | Der Dienst liefert HTML, das wäre schnell. Aber PDFKit-Markierung, Tastaturbedienung und zugängliche Namen gäbe es dann nicht — und für ein Beleg-Werkzeug ist die Markierung der Zweck, nicht die Zugabe. |
| **Ein Fenster pro Fähigkeit** | Gemessen (Konsil): Mehrfenster kostet rund 4 ms je Fenster und gleich viel Speicher — technisch gleichwertig. Abgelehnt aus Bedienbarkeit: Wer sechs Fenster sucht, sucht. macOS führt Tabs von selbst zusammen, das reicht. |
| **Raster zuerst (Vorbild ATEM)** | Ein Raster aus Feldern, die nichts anzeigen können, ist ein Gitter. |
| **Platzhalter stehen lassen, bis alles fertig ist** | Zwei Drittel der Navigation führen ins Nichts, und der Text nennt den Zustand des Quelltexts statt der Lage des Nutzers. |

## §4 · Was bewusst nicht getan wird, samt Preis

- **Keine eigene Fensterverwaltung.** Preis: kein selbstgebautes Layout-Gedächtnis.
  Gewinn: macOS-Tabs, Vollbild und Zweitschirm kostenlos.
- **Kein Einstellungsdialog in dieser Runde.** Der Betrachtungsabstand bekommt
  einen Regler in der Quellenansicht, wo er wirkt — nicht in einem Dialog, den
  niemand findet.
- **Keine Schreibrechte auf buckeberg aus der App.** Die Schwärzung erzeugt
  Kopien; das Original bleibt unangetastet.

## §5 · Woran sich Erfolg misst

| | |
|---|---|
| Kein Platzhalter mehr | `grep -c PlatzhalterAnsicht` = 0 |
| Jede Ansicht hat zugängliche Namen | Text-vor-Bild-Prüfung je Bildschirm |
| Die Negativfälle sind sichtbar | gesperrtes PDF, beschädigtes, unbekanntes Format, Quelle ohne Fundstelle — je eine Probe an einem **echten** Dokument |
| Der Kern bleibt oberflächenfrei | `BrainlehrCore` importiert weiterhin kein SwiftUI/AppKit |
| Tests | keine Zahl sinkt; jede neue Entscheidungslogik mit Mutationsprobe |

## Aufträge, fertig zum Übergeben (§6)

**Für alle gleichermaßen:** Arbeitsort `/Volumes/daten/Begod2026/brainlehr`,
Zweig `brainlehr/b4-ausweis`. Nicht `swift build`, sondern `app/bauen.sh`.
Kein `git add -A`, kein Push, kein `git stash`; Commit mit expliziter
Pfadliste. Sichtprüfung **Text vor Bild** über die Bedienungshilfen; wenn doch
ein Bild nötig ist, ausschließlich über die **Fenster-Kennung**, nie nach
Bildschirmbereich. buckeberg wird nur gelesen. „Sieht der Code anders aus als
hier beschrieben, halte dich an den Code und melde die Abweichung."

### B1 · Quellenansicht — ein Dokument, aufgeschlagen und markiert

| | |
|---|---|
| **Darf ändern** | `app/Sources/BrainlehrApp/QuellenAnsicht.swift` (neu), `HauptFenster.swift` |
| **Tabu zusätzlich** | `kern/`, `haken/`, `melder/`, `tests/`, `runs/`, `schema.sql` — parallele Python-Sitzung; `BrainlehrCore/*` bleibt oberflächenfrei |
| **Fakten** | `Quelldokument.weg(fuer:)` liefert pdf/text/bild/unbekannt; `befund(…)` die vier Negativfälle mit Meldung **und** Handlung. Gemessen: PDFKit findet die Seite selbst (`doc.index(for: selection.pages.first)`, 12 ms), ein **gesperrtes** PDF ist nicht `nil` — `isLocked` **vor** der Suche abfragen. Quick Look kann weder aufschlagen noch hervorheben noch scheitern melden; für txt/html gehört NSTextView hin. `PDFView` liefert `isAccessibilityElement()=false`, der Name muss gesetzt werden. |
| **Abnahme** | Je Format eine Probe an einem **echten** buckeberg-Dokument. Vier Negativfälle mit gebauten Gegenbeispielen: gesperrt → „Kennwort nötig", beschädigt → Meldung statt Absturz, unbekanntes Format → Meldung statt stillem Symbol, Quelle ohne Fundstelle → öffnet unmarkiert **mit Hinweis**. Gegenprobe zur harten Grenze: `shasum -a256` der Quelldatei vor und nach dem Markieren gleich. |

### B2 · Dateibrowser — thematisch statt Verzeichnisbaum, mit Live-Ranking

| | |
|---|---|
| **Darf ändern** | `app/Sources/BrainlehrCore/Rangfolge.swift` (neu), `app/Sources/BrainlehrApp/BrowserAnsicht.swift` (neu) |
| **Tabu zusätzlich** | wie B1 |
| **Fakten** | Betreiberauftrag: *„nicht einfach so wie im dateisystem abgelegt, sondern einmal thematisch sortiert und zum umschalten live ranking durch die ki was gerade am wichtigsten ist"*. Verfügbar: `dossier/quellen.json` mit `art` und `kurz` (thematisch), `Sitzungsstrom` (woran gerade gearbeitet wird), `Sichtbarkeit` (was der Betrachter sehen darf). Bestand: 49 Quellen, 31 markierbar. |
| **Abnahme** | Beide Sortierungen an den echten 49 Quellen. Rot vor grün am Ranking: ohne Sitzungsbezug ist die Reihenfolge stabil, mit Bezug stehen die zum aktuellen Thema passenden oben — an einem nachgestellten Strom belegt, nicht am Eindruck. **Negativfall, der wichtigere:** Was der Betrachter nicht sehen darf, taucht in keiner Rangliste auf und wird auch nicht mitgezählt. Mutationsprobe auf die Rangregel. |

### B3 · Sitzungsfenster — Chat, Denken, Ausführlichkeit

| | |
|---|---|
| **Darf ändern** | `app/Sources/BrainlehrApp/SitzungsAnsicht.swift` (neu), `HauptFenster.swift` |
| **Tabu zusätzlich** | wie B1 |
| **Fakten** | `Sitzungsstrom.zerlege(_:)` liefert Ereignisse, `gefiltert(_:_:)` drei Stufen, `aktuellerSchritt(_:)` das Denken-Fenster. Gemessen am echten Strom: 1215 Zeilen → 15 Eingaben, 96 Antworten, 90 Denk-Blöcke, 269 Werkzeuge; Systemtext-Durchschlupf 0. Die Datei wächst während des Lesens — halbe letzte Zeile ist Normalfall. |
| **Abnahme** | Gegen den **echten** laufenden Strom, nicht gegen ein Fixture. Systemtext darf nicht erscheinen — Gegenprobe mit einer Zeile, die `<system-reminder>` enthält. Nach einer fertigen Antwort zeigt das Denken-Fenster **nichts**, nicht den letzten Werkzeugnamen. |

### B4 · Raster — erst ab zwei tragfähigen Feldern

| | |
|---|---|
| **Darf ändern** | `app/Sources/BrainlehrApp/RasterAnsicht.swift` (neu), `app/Resources/raster.json` (neu) |
| **Tabu zusätzlich** | wie B1; die Feldzahl steht **nicht** in der Konfiguration |
| **Fakten** | `Lesebarkeit.form(…)` entscheidet aus Fläche und Abstand. Gemessen an den angeschlossenen Geräten: CG2700X 27,1″ trägt bei 0,5 m drei Felder, bei 0,7 m keines; Built-in 16,1″ keines. Ein Punkt ist **nicht** 1/72 Zoll — physische Größe kommt aus `CGDisplayScreenSize`. `raster.json` beschreibt nur, **was** in ein Feld darf. |
| **Abnahme** | Am echten Zweitschirm: Bei einer Fläche, die weniger als eine Seite trägt, erscheint **kein** Raster, sondern der Ausschnitt. Eine unbekannte Feldbelegung führt zu einem leeren Feld mit Hinweis, nicht zum Absturz. Verschieben ist ohne Ziehen möglich (WCAG 2.5.7) und über dasselbe Menü auch mit Tastatur. |

### B5 · Live-Bearbeitung — Vorschläge annehmen oder ablehnen

| | |
|---|---|
| **Darf ändern** | `app/Sources/BrainlehrApp/BearbeitungsAnsicht.swift` (neu) |
| **Tabu zusätzlich** | wie B1 |
| **Fakten** | `Verschmelzung.verschmelze(vorfassung:mensch:modell:)` liefert Absätze mit Herkunft; `entscheide(_:absatz:wahl:)` löst einzeln auf. `Absatz.offen` sagt, wo es etwas zu entscheiden gibt. Betreiber: *„ki macht live vorschläge, mensch darf live korrigieren und schreiben"*. |
| **Abnahme** | Zwei gleichzeitige Änderungen an verschiedenen Absätzen → keine Rückfrage, beide bleiben. An demselben Absatz → beide Fassungen sichtbar nebeneinander, keine wird überschrieben. Ein abgelehnter Vorschlag stellt die Fassung des Menschen wieder her, nicht den Vorschlag. |

## §7 · Fortschreibung

Wird nach der Umsetzung ergänzt: was anders kam als geplant, und warum.
