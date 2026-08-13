# ADR-004: Kein Multiview für den Termin — die Anzeige ist nicht das Problem

**Stand** 2026-08-13T16:08:18+0200
**Status** Vorgeschlagen — die Entscheidung liegt beim Betreiber, siehe „Was zu entscheiden ist"
**Betrifft** brainlehr `app/`, buckeberg `homepage/`
**Grundlage** Opus-Konsil aus fünf Rollen, 2026-08-13, alle Zahlen nachgerechnet

## Anlass

Der Betreiber hat eine Multiview-Oberfläche nach dem Muster des Vorschaumonitors
eines Videomischers beauftragt (`docs/PLAN_MULTIVIEW_2026-08-13.md`), mit einer
harten Priorität für ein Arbeitstreffen: *„zeig mir, wo das steht"*.

Auf die Rückfrage, ob die vorhandene App als Blaupause dient, kam die Direktive:
*„keine dogmen bedienen! also nicht vorhandenes als gegeben nehmen. wenn wir
bessere wege der umsetzung finden dann vorhandenes verwerfen. deswegen opus
konsil"*.

Fünf Rollen haben unabhängig geprüft, keine kannte die Hypothese der anderen.

## Der Befund

**Das Anzeigeproblem, für das die App gebaut werden sollte, ist nicht das
Problem des Abends.** Drei Messungen tragen das:

### 1 · Der vorhandene Betrachter ist nicht schlecht, er ist tot

`buckeberg/homepage/vendor/pdfjs-viewer/` enthält `LICENSE` und `web` — **kein
`build/`**. Die `viewer.html` lädt `../build/pdf.mjs`; diese Datei existiert im
gesamten Repo nicht. Ursache ist `.gitignore` Zeile 21: `**/build/`.

Er zeigt eine graue Fläche **ohne Fehlermeldung**. `scripts/quellen_check.py`
meldet „Keine Fehler" — er prüft die Daten und ist damit zu Recht grün. Alle 14
gepflegten Fundstellen sind exakt, und keine einzige ist sichtbar.

Damit ist die Ausgangslage eine andere als angenommen: Es fehlte nie ein
Betrachter. Es fehlt ein Verzeichnis.

### 2 · Ein Raster kann auf diesem Bildschirm keinen Fließtext zeigen

Gemessen an allen 29 Quellen-PDFs: Fließtext im Median 10,9 pt, x-Höhe
gemessen (nicht angenommen) im Median 0,547 der Punktgröße. Bildschirm
345,6 × 223,4 mm, ein einziger, eingebaut.

| Schwelle | nötige A4-Breite (Median) | Bildschirm |
|---|---|---|
| flüssiges Lesen | 772 mm | 346 mm |
| bloßes Entziffern | 386 mm | 346 mm |

**Die Zahl der Felder, die aus 2 m eine A4-Seite im Fließtext tragen, ist
null** — auch bei einem einzigen Feld. Die Aussage hält, wenn man die Schwelle
halbiert.

Der billigste Hebel ist kein Software-Hebel: von 2,0 m auf 1,2 m rücken
verdreifacht das Zeichenbudget.

### 3 · Die Lücke liegt in den Daten, nicht in der Anzeige

| | |
|---|---|
| Quellen | 48 |
| markierbar (`suchtext`) | **14** |
| nur aufschlagbar (`seite`) | 1 |
| ohne jede Stelle | 33 |

Und die Kreuztabelle, die den Zuschnitt entscheidet: **alle 14 markierbaren
sind PDF. Keine der 20 HTML-Quellen trägt eine Stelle** — 42 % des Bestands,
geschlossen. Bei einem WEG-Abend sind das die meistgefragten Belege überhaupt
(§ 16 WEG, § 26a WEG, § 24 WEG, § 559 BGB).

Bei **19 von 20** steht die Stelle bereits im Klartext im Feld `kurz`. Sie ist
nicht unbekannt, sie steht im falschen Feld.

## Entscheidung

**Für den Termin wird keine Multiview-Oberfläche gebaut.** Stattdessen, in
dieser Reihenfolge (Aufträge in `docs/PLAN_MULTIVIEW_GESAMT_2026-08-13.md` §7):

| | Schritt | Aufwand | Wirkung |
|---|---|---|---|
| A | Betrachter reparieren bzw. den Umweg über pdf.js streichen | ~10 min | 14 Fundstellen werden überhaupt erst sichtbar; 22 Nicht-PDF-Quellen werden bedienbar |
| B | HTML-Quellen: Paragraph aus `kurz` als Fundstelle nachtragen | ~1 h | bis zu 19 Quellen von „keine Stelle" auf „Stelle bekannt" |
| C | Anzeige in der App, mit den gemessenen Werkzeugen | offen | erst nach dem Termin sinnvoll |

**Und als Rückfalllinie, die gegen jede denkbare Panne wirkt:** `dossier/`
enthält vier gesetzte, aktuelle PDFs (Gesamtband 25 S., Prüfliste 2 S.,
Empfehlung 3 S., Quellenverzeichnis 5 S.). Vier Ausdrucke kosten fünf Minuten
und sind aus jeder Entfernung lesbar.

## Alternativen, samt Ablehnungsgrund

| Weg | Abgelehnt weil |
|---|---|
| **Multiview aus Dokumenten** (Auftrag) | Auf diesem Bildschirm arithmetisch ausgeschlossen, nicht bloß unschön — siehe §2. Zusätzlich: aus 2 m ist „unmarkiert" nicht von „markiert, aber außerhalb des Ausschnitts" zu unterscheiden; das Raster verwischt genau die Unterscheidung, die `kern/fundstelle.py` herstellt. Und es nimmt den einzigen Handgriff weg, der heute funktioniert (⌘+ auf den Absatz). |
| **Eigener Viewer in der App zuerst** | Baut die Anzeige für 14 von 48 Quellen, während der vorhandene Weg für 48 kaputt daliegt. Löst das leichter zu bauende Nachbarproblem. |
| **Belegkarte statt Dokument** (Vorschlag einer Rolle) | Trägt lesbar und passt dreifach auf den Schirm — aber kauft Lesbarkeit mit **Auswahlmacht**: ein Satz ohne seinen „es sei denn"-Nachsatz ist überzeugender als jede Vorschau und kann falsch sein. In einer Streitsache ist das die teuerste Eigenschaft. Als Ergänzung zum vollen Dokument vorgemerkt, nicht als Ersatz. |
| **Texterkennung über Bildschirmabzüge** | 29 von 29 PDFs tragen eine Textschicht; auf Seitenebene 2 von 414 leer. Es gibt nichts zu erkennen. |

## Was das kostet

- **Der Betreiber sieht sein Vorschaumonitor-Bild zum Termin nicht.** Das ist
  eine Ablehnung seines ausdrücklichen Auftrags, und sie erfolgt **einmal**,
  mit dieser Begründung. Bekräftigt er ihn, wird gebaut.
- **Der Zusammenhang bleibt an die volle Seite gebunden.** Wer die umgebende
  Klausel lesen will, muss näher heran oder das Gerät in die Hand nehmen.
- **33 Quellen bleiben zunächst ohne gepflegte Stelle.** Schritt B senkt das
  auf bis zu 14; daran ändert keine Fensterform etwas.

## Was zu entscheiden ist

1. **Wie weit sitzen die Leute wirklich?** Bei 1,2 m statt 2 m trägt der
   Bildschirm eine ganze Seite, und Schritt C sieht anders aus. Das ist die
   einzige Frage, die wirklich blockiert — und keine Bauaufgabe.
2. **Darf in buckeberg geschrieben werden?** Schritt A und B ändern dort
   Dateien. Bisher galt: nur lesen.
3. **Schritt A mit oder ohne Hervorhebung?** Der Umweg über pdf.js zu streichen
   ist 10 Minuten und macht alle Formate bedienbar, verliert aber `#search=`.
   pdf.js 6.1.200 nachzuziehen erhält die Hervorhebung, ist aber ein Download
   aus dem Netz — der geht nicht ohne ausdrückliche Freigabe.

## Was daraus ohnehin bleibt

`kern/fundstelle.py` und die beiden Datenendpunkte sind unabhängig von der
Fensterform und bleiben. Sie beantworten „wo steht das" — oder sagen, dass sie
es nicht wissen, und das ist bei 33 von 48 Quellen der Regelfall.

## Was das Konsil über die eigene Arbeitsweise gezeigt hat

Von fünf Rollen haben **vier** mindestens eine meiner eigenen Messungen
widerlegt, und drei davon waren bereits im Plandokument veröffentlicht:

- 49 Quellen statt 48 — `_rang` ist eine Verwaltungszeile, aber als **Objekt**
  notiert und rutschte durch `isinstance(v, dict)`.
- „29 von 29 mit Textschicht, gemessen mit `textutil`" — `textutil` kann kein
  PDF lesen und reicht Rohbytes durch. **Ein reines Scan-PDF hätte den Test
  bestanden.** Ergebnis zufällig richtig, Beleg keiner.
- Eine laufende Kopfzeile wurde als Fundstelle mit Seite 1 gemeldet.
- „PDFKit + Quick Look" — Quick Look kann weder aufschlagen noch hervorheben
  noch einen Fehlschlag melden.
- Innerer Widerspruch: §3 begründete PDFKit mit „setzt Markierungen", §6
  verbietet Schreiben in buckeberg.

Eine Beanstandung war ihrerseits falsch und wurde **nicht** übernommen: Zwei
Rollen meldeten Quelle 1 als falsch hinterlegt, weil „Stimmrecht" auf Seite 14
steht. Seite 4 trägt „Garage" — genau was das `kurz`-Feld behauptet. Die Quelle
stimmt; die Stimmrechtsfrage ist eine andere Frage ohne eigene Nummer.

**Die Lehre daraus ist nicht „Konsile sind gut", sondern schärfer:** Jede der
widerlegten Zahlen hatte einen grünen Test. Was fehlte, war nicht Sorgfalt beim
Prüfen, sondern eine **zweite Rechnung von jemandem, der meine Absicht nicht
kannte**.
