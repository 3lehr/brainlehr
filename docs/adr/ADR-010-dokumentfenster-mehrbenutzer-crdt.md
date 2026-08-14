# ADR-010: Das Dokumentfenster — nativ, mehrbenutzerfähig, Yjs-Familie

**Stand** 2026-08-14T09:57:14+0200
**Status** Angenommen, mit zwei benannten Spikes
**Betrifft** `app/Sources/Atelier/`, `app/Sources/BrainlehrCore/Verschmelzung.swift`, einen künftigen Dokumentdienst unter `kern/`
**Entscheider** Betreiber (Ziel und drei Richtungsentscheide), Assistent (Werkzeugwahl, ausdrücklich delegiert)

## Die Frage

Knoten `de9aba1a` hält das Ziel: ein Fenster, in dem Mensch und Modell am selben
Dokument arbeiten — links das fertige Erzeugnis mit Undo/Redo, rechts die
Anmerkungen beider Seiten, und eine Anmerkung ist **kein Kommentar, sondern ein
Auftrag mit Anker**. Zwei Fragen standen dort ausdrücklich offen. Beide sind
heute beantwortet.

## Was der Betreiber entschieden hat (2026-08-14)

| Frage | Antwort, wörtlich | Folge |
|---|---|---|
| Darf die KI Anmerkungen selbst umsetzen? | *„Weil es die soll User Entscheidung sein"* | **Einstellbar, nicht festgelegt.** Vorgabe: alles bleibt Vorschlag. Die Klassentrennung (Tippfehler automatisch, Rechtssatz nie) ist ein Schalter, den der Nutzer stellt — sie ist nicht unsere Entscheidung. Deckt sich mit seiner Weisung vom 2026-08-13: *„sollte offen gehalten werden"* |
| Wer liest mit? | *„Mehrere Menschen und die ki"* | Das Dokument kann nicht mehr im atelier leben. Die Wahrheit liegt im **Dienst**; das atelier ist Klient. Die KI ist kein Sonderfall, sondern ein Teilnehmer mit demselben Protokoll |
| Wie fein ist gleichzeitig? | „Live Zeichen für Zeichen" | **CRDT.** Absatzsperre und Drei-Wege-Verschmelzung fallen als Grundmechanik aus |
| Reichweite | „Erst LAN, Konten später" | Dienst auf dem eigenen Rechner, Klienten im eigenen Netz. `kern/ausweis.py` und die Freigabe-Achse bleiben die Naht für später, werden heute nicht gebaut |
| Bauform | *„Ich will das zuerst schon nativ in der Mac App, entscheide du"* | Kein Web-Fenster. Native Oberfläche, und die Werkzeugwahl war delegiert — sie steht unten |

Der dritte Punkt ist der teure. Er wurde mit ausgewiesenem Preis gewählt
(„andere Klasse Arbeit, Monate") und ist damit entschieden, nicht zu
verhandeln.

## Entscheidung

**Yjs-Familie auf beiden Seiten: `pycrdt` im Dienst, `yswift` (yrs) im atelier.**

Das Dokument ist ein CRDT-Baum aus Bausteinen mit stabilen Kennungen. Ein
Baustein trägt einen Typ — Absatz, Überschrift, Tabelle, Grafik, **Feld**.
Schriftsatz und Rechnung benutzen damit dieselbe Struktur; die
Rechnungserstellung braucht keine zweite.

## Gemessen, nicht angenommen

Alles am 2026-08-14 auf diesem Rechner erhoben, reproduzierbar über
`spikes/crdt_pyswift/probe.py`.

| | Python | Swift |
|---|---|---|
| **Yjs / yrs** | `pycrdt` 0.14.2, frisches cp314-Wheel, lädt und rechnet | `yswift` 0.2.1 — laut Repository WIP, letzter zusammengeführter PR über ein Jahr alt; **baut und läuft hier trotzdem** |
| **Automerge** | `automerge` 0.1.2 — **unbrauchbar, gemessen**: `Doc` kennt nur `json`, `merge`, `obj`; kein `save`/`load`; eine Änderung über `obj()` wirkt nicht; `merge(Doc)` scheitert mit `TypeError: 'Doc' object cannot be converted to 'Sequence'` | `automerge-swift` 0.7.2, gepflegt |

Was der Spike belegt:

- Zwei gleichzeitige Änderungen an derselben Zeile laufen konvergent zusammen
  (`'Hallo schoene Welt, heute'` auf beiden Seiten).
- Der Baustein-Baum trägt Absatz und Feld nebeneinander.
- **Swift liest einen Stand, den Python geschrieben hat, zeichengenau.**
- Zweimaliges Anwenden desselben Updates ändert nichts — der Negativfall hält.
- Updates sind klein: 33 Byte für den Anfangsstand, 53 für die Rückgabe.
- `YDocument.undoManager` existiert — Undo/Redo ist nicht zu bauen.

## Spike 1 — erledigt am 2026-08-14T11:5x, und der Befund wird zur Auflage

Die Rückrichtung verdoppelte (`'[Swift] Hallo aus PythonHallo aus Python'`), und
der Zustandsvektor filterte nichts (53 Byte gegen den Python-Vektor, 53 gegen
einen leeren). **Beides war dieselbe Ursache, und es lag an keiner der beiden
Vermutungen** (Wurzelbenennung, durchgereichter Vektor) — die Wurzeln passen,
gemessen in beide Richtungen.

**`yswift` schneidet die Teilnehmerkennung (client id) auf 32 Bit ab.**
`pycrdt` vergibt sie standardmäßig zufällig bis etwa 2^53. Liegt sie darüber,
kommt der eigene Beitrag als **fremder** zurück und wird pflichtgemäß daneben
gestellt statt zusammengeführt. Die Schranke ist scharf gemessen, nicht
geschätzt:

| Kennung | Ergebnis |
|---|---|
| 42 · 2^31−1 · 2^32−2 · **2^32−1** | `'[Swift] Hallo aus Python'` — sauber |
| **2^32** · 2^32+1 · 2^32+7 | `'[Swift] Hallo aus PythonHallo aus Python'` — verdoppelt |

Mit tragbarer Kennung filtert auch der Zustandsvektor (25 gegen 53 Byte).

**Auflage, die daraus wird:** Jeder Teilnehmer — Dienst, atelier, jeder weitere
Klient — vergibt seine Kennung **unter 2^32** und niemals per Zufall aus dem
Standardbereich. Das ist keine Kosmetik: der Fehler zeigt sich nicht als
Absturz, sondern als still verdoppelter Absatz, und träfe genau die
Zusammenarbeit, für die das Fenster gebaut wird. Festgehalten als Negativfall
in `spikes/crdt_pyswift/probe.py` — eine Kennung über der Schranke **muss**
verdoppeln, sonst misst die Probe nichts mehr.

**Spike 2 — die Pflege von `yswift`.** Ein Jahr ohne zusammengeführten PR ist
ein Risiko, kein Ausschluss. Rückfallweg, falls es kippt: `yrs` trägt eine
C-Schnittstelle; die Swift-Seite hinge dann direkt daran statt an diesen
Bindungen. Zweiter Rückfallweg unten.

## Verworfen, mit Grund

**Automerge, nativ.** `automerge-swift` ist die gepflegtere Bibliothek — aber die
Python-Seite ist gemessen unbrauchbar (siehe Tabelle). Der Kern müsste nach Rust
wandern, gegen ADR-006. Eine Werkzeugwahl, die die Grundsprache umstößt, ist
keine Werkzeugwahl mehr.

**Web-Fenster im `WKWebView`.** Technisch der kürzeste Weg — `WissensraumWebView.swift`
existiert, ADR-009 hat den HTML-Zweig ohnehin als Vorschau, Yjs ist dort zu
Hause. Der Betreiber will nativ. Entschieden.

**Dünner Klient — Dienst rechnet allein.** Kein CRDT im atelier, das Fenster
schickt Tastendrücke und zeigt, was zurückkommt. Bleibt der **Rückfallweg**,
falls Spike 1 oder 2 kippen: die Oberfläche bleibt nativ, der Nutzer merkt am
selben Rechner nichts, und es fällt allein die Bearbeitung ohne Netz weg.

**Absatzweise Verschmelzung.** `app/Sources/BrainlehrCore/Verschmelzung.swift`
(Drei-Wege auf Absatzebene) ist als Grundmechanik hinfällig — Zeichen für
Zeichen ist eine andere Klasse. Sie wird **nicht gelöscht**: ihre
`Absatz.Herkunft` (mensch/modell/konflikt) beantwortet, WER einen Baustein
zuletzt angefasst hat, und genau daran dockt die Herkunftskette an. Sie liegt
zudem in Swift und damit auf der falschen Schicht — das ist die zweite der
beiden Doppelungen aus ADR-006 und wird mit dem Dienst aufgelöst, nicht vorher.

## Reihenfolge, und wo sie bindet

1. ~~Spike 1 klären.~~ **Erledigt** — Paarung trägt in beide Richtungen, unter
   der Auflage zur Teilnehmerkennung. Rückfallweg dünner Klient bleibt für
   Spike 2 (Pflege von `yswift`) reserviert.
2. **Baustein-Vertrag festlegen** (Typen, Kennungen, Anker) — *bevor* das erste
   Dokument existiert. Ein Anker, der eine Änderung nicht überlebt, wandert
   still an die falsche Stelle; nachträglich ist nicht rekonstruierbar, worauf
   eine Anmerkung einmal zeigte. Derselbe Grund gilt bei null Dokumenten wie bei
   tausend.
3. **Anmerkung mit Zustand** — offen, umgesetzt, abgenommen, abgelehnt.
   Zurückgegeben wird nie eine Bestätigung, sondern der erreichte Zustand
   (`L-db37c6`).
4. Dienst, Fenster, Formularfelder.

## Woran sich Erfolg misst

- Zwei Klienten am selben Dokument, gleichzeitig in denselben Satz getippt →
  beide Seiten zeigen dasselbe. Rot vorher: heute existiert kein Dienst.
- Eine Anmerkung mit Anker überlebt eine Umsortierung der Bausteine und zeigt
  danach auf dieselbe Stelle. Negativfall: ein gelöschter Baustein hinterlässt
  eine Anmerkung, die sichtbar verwaist ist statt still zu wandern.
- Eine selbständig umgesetzte Änderung ist markiert und rücknehmbar — und der
  Schalter, der das erlaubt, steht per Vorgabe auf „nur vorschlagen".
