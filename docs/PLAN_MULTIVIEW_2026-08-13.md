# Multiview: die App als Vorschaumonitor

Stand 2026-08-13T14:10:00+0200. Betreiberauftrag, Vorbild ausdrücklich genannt:
der **Vorschaumonitor eines Videomischers**, Konfiguration nach dem Muster der
Blackmagic-ATEM-Software. Frei belegbare Felder in einem Raster, jedes Feld
konfigurierbar, nichts fest verdrahtet.

**Übergabedokument.** Dieser Plan ist für eine **eigene Sitzung** geschrieben,
nicht für die laufende. Warum, steht unten.

## Der Termin, und was er bedeutet

Der Betreiber arbeitet **heute oder morgen Abend** mit zwei bis drei weiteren
Menschen am buckeberg-Projekt. Das ist kein Entwicklungstermin, sondern ein
Arbeitstreffen mit echten Leuten und echten Rechtsfragen.

**Daraus die einzige harte Priorisierung dieses Plans:** Von allem hier ist für
diesen Termin **eine** Sache entscheidend — *„zeig mir, wo das steht"*. Drei
Menschen an einem Tisch brauchen die Quelle im Original, aufgeschlagen an der
richtigen Stelle. Das Raster, die Fensteraufteilung, das Denken-Fenster, die
Live-Bearbeitung sind Infrastruktur **darum herum**.

Wer die Reihenfolge umdreht, hat am Abend ein schönes Raster und keine Quelle.

## Was heute steht

| | |
|---|---|
| `app/Ausgabe/brainlehr.app` | vorhanden, echtes Bündel |
| `DienstAufsicht.swift` | startet und überwacht den Dienst auf Port 8799 |
| Ansichten im Dienst | `/raum`, `/vergleich`, dazu neun Datenendpunkte |
| Bauform | SwiftUI-Schale, Grafiken als Web-Inhalt wiederverwendet |
| Seitenleiste | sechs Platzhalter |

## Die Gliederung, die der Betreiber vorgibt

**Ein Raster aus Feldern. Was in welchem Feld liegt, ist Konfiguration, nicht
Bauzeit.** Der Satz *„wenn mir etwas einfällt, ist noch nicht definiert, wo das
Feld ist"* ist die Anforderung — Felder sind Behälter, Inhalte sind Zuweisungen.

**Inhalte, die zur Wahl stehen** (Stand des Auftrags):

- die vorhandenen Ansichten — 3D-Raum, Netz, Abrufweg, Vergleich, jeweils auch
  in einem **eigenen Fenster**
- **Denken** — woran arbeitet das Modell gerade
- **Chat**
- **was brainlehr von sich aus einspielt**, mit wählbarer Ausführlichkeit
- **Quellen und Zitate im Original** — der Kern, siehe unten
- **Live-Bearbeitung** eines Dokuments

## Die zwei Kernfunktionen

### 1 · Quellen im Original, markiert wie mit dem Textmarker

**Was schon da ist** (zu prüfen, nicht anzunehmen): Für buckeberg sind die
meisten Dokumente maschinenlesbar gemacht, und die Homepage hat bereits
**Anker in die Dokumente hinein**. Was fehlt, ist die **Markierung** — die
Stelle sichtbar machen, nicht nur hinspringen.

**Ablauf:** Sobald der Chat ein Dokument benutzt, erscheint es an der richtigen
Stelle, markiert. Live.

**Drei Fensterrollen**, vom Betreiber vorgeschlagen und plausibel:
*aktuelles Dokument* · *letztes Dokument* · *eingefrorenes Dokument* (Pause,
Dauer). Bei vielen Quellen zugleich zusätzlich ein **Zeitstrahl**.

**Die technische Frage, die den Zuschnitt entscheidet: der Universal-Viewer.**
Der Betreiber schlägt als Notlösung vor, Bildschirmabzüge in ein PDF zu betten
und Texterkennung darüberlaufen zu lassen. **Das ist vermutlich nicht nötig**,
und das ist vor dem Bau zu klären:

> **MODELLWISSEN, ungeprüft, gehört gemessen:** Apple bringt zwei Bausteine
> mit, die den größten Teil abdecken könnten — **Quick Look** zeigt PDF, Office,
> Bilder, Text und Markdown nativ an, und **PDFKit** kann Anmerkungen und
> Hervorhebungen **setzen**, nicht nur anzeigen. Damit wäre die Markierung im
> PDF echt statt aufgemalt. Für alles, was Quick Look nicht kann, bliebe der
> Umweg über eine Umwandlung.
> **Diese Angabe stammt aus meinem Wissen, nicht aus einer Messung.** Erster
> Schritt jeder Umsetzung: an einem echten buckeberg-Dokument ausprobieren.

**Die Frage dahinter, die wichtiger ist als das Werkzeug:** Woher weiß die App,
**welche Stelle** zu markieren ist? Das ist keine Anzeigefrage, sondern eine
Frage an den Speicher — und dort gibt es seit heute die Voraussetzung dafür:
229 Herkunftskanten und die Unterscheidung *unbelegt* gegen *erfunden*. Ohne
eine belastbare Fundstelle markiert der Viewer die falsche Zeile, und das ist
schlimmer als gar keine Markierung.

### 2 · Live-Bearbeitung, und ihr Henne-Ei-Problem

Der Betreiber hat es selbst benannt: **Ich sehe live, wie das Modell das
Dokument ändert — und das Modell sieht live, wie ich es ändere.** Beide
reagieren aufeinander.

**Das ist kein Anzeigeproblem, sondern ein Nebenläufigkeitsproblem**, und es hat
einen Namen: zwei Schreiber auf einem Dokument ohne Konfliktauflösung. Wer das
als Anzeigefrage baut, bekommt verlorene Änderungen — leise, ohne Fehlermeldung.

**Drei Wege, keiner vorentschieden:**
- **Sperre je Absatz.** Wer schreibt, hält den Absatz. Einfach, sichtbar,
  fühlt sich hakelig an.
- **Vorschlag statt Änderung.** Das Modell schreibt nie direkt, sondern schlägt
  vor; der Mensch übernimmt. Das ist die Bauform, die openlehr bereits benutzt
  (*review-first*), und sie löst das Problem, indem sie es vermeidet.
- **Echte Verschmelzung.** Teuer, richtig, und für einen Termin morgen Abend
  die falsche Wahl.

**Empfehlung, begründet:** Der zweite Weg. Er ist im Verbund erprobt, und das
Henne-Ei-Problem entsteht gar nicht erst.

## Die Schranke, die vor dem Termin steht (Aufgabe 101)

Der Betreiber hat mitgeteilt, dass **alle Anwesenden WEG-Mitglieder** sind. Für
die buckeberg-Dokumente ist die Datenschutzfrage damit entschärft — Mitglieder
untereinander sind keine Dritten.

**Das Risiko liegt woanders: im Bestand daneben.** Dort liegen `/openlehr`
(Steuerdaten, 25 Knoten), `/apps` (75), `/shared` (50), `/ops` (41). Der Abruf
entscheidet nach **Bedeutungsnähe, nicht nach Zuständigkeit** — ein Fenster
„was brainlehr von sich aus einspielt" kann bei beliebiger Frage einen Knoten
aus einer völlig anderen Domäne zeigen, vor drei Menschen.

**Und die vorhandene Achse filtert nicht.** Gemessen: `offen` 1888, `intern`
281, **`gesperrt` 0**. Es filtert nur `gesperrt` — die einzige Stufe, die
niemand benutzt. **`intern` ist heute eine Absichtserklärung, keine Schranke.**

**Für den Termin: Die App zeigt nur, was `offen` ist.** Eine Bedingung im
Datenendpunkt, kein Eingriff in den Speicher, keine Wirkung auf laufende Arbeit,
umkehrbar. Bei Menschen im Raum ist die engere Voreinstellung die richtige.

`intern` zum echten Filter zu machen ist die eigentliche Entscheidung und gehört
dem Betreiber — sie stand ihm heute offen und ist unbeantwortet geblieben.

**Abnahme:** Ein Knoten mit `intern` erscheint vorher in der Ansicht und nachher
nicht. Negativfall, der wichtigere: Ein Knoten mit `offen` erscheint weiterhin —
sonst ist die App leer und der Termin hat nichts. Grenzwert: **auch der
Einspiel-Kanal filtert**, nicht nur die Suche; das sind zwei Wege in dieselbe
Anzeige.

## Was bewusst nicht getan wird, samt Preis

- **Kein Multiview vor der Quellenanzeige.** Preis: Die Fensteraufteilung
  kommt später. Gewinn: Der Termin hat, was er braucht.
- **Kein eigener Viewer, bevor Quick Look und PDFKit an einem echten Dokument
  gemessen sind.** Ein Bildschirmabzug mit Texterkennung ist die teuerste
  Lösung und wäre die erste, die man baut, wenn man nicht nachsieht.
- **Keine Live-Verschmelzung.** Vorschlag statt Änderung.
- **Keine Aufteilung auf mehrere Fenster oder Ströme, solange nicht gemessen
  ist, dass eines nicht reicht.** Der Betreiber stellt die Frage selbst — sie
  ist offen und wird nicht durch Bauen beantwortet.

## Woran sich Erfolg misst

- **Der Termin:** Eine Frage aus dem Kreis führt dazu, dass das Dokument an der
  richtigen Stelle markiert auf dem Schirm steht — ohne dass jemand sucht.
- **Rot vor grün am Viewer:** Ein buckeberg-Dokument jedes vorkommenden Formats
  wird angezeigt. Vorher: Liste der Formate mit Nenner. Ein Format, das nicht
  geht, ist ein Befund, kein Nebensatz.
- **Die Markierung trifft.** Gemessen an Fällen mit bekannter Fundstelle, nicht
  am Eindruck.
- **Jede Aktion ist im Raster zuordenbar und verschiebbar** — die Anforderung
  des Betreibers, und zugleich die Probe, ob die Felder wirklich Behälter sind.

## Warum eine eigene Sitzung — und was heute dazu gemessen wurde

Der Betreiber fragt, ob das ein eigener Chat sein sollte, „damit könnten wir
auch gleich testen, wie gut es funktioniert, wenn zwei Entwickler am gleichen
Projekt arbeiten".

**Der Test ist heute schon gelaufen, unbeabsichtigt, und hat drei Befunde
geliefert:**

1. Eine Fork-Sitzung wurde von einem Trigger blockiert, den **diese** Sitzung
   gebaut hatte — und musste per Sitzungsnachricht herüberrufen, weil ein
   Speichereintrag die andere Sitzung erst beim nächsten Start erreicht hätte.
2. Ein Agent hätte beinahe **fremdes Gestagtes mitcommittet** — `git commit`
   ohne Pfadliste schreibt den ganzen Index fest, und zwei Sitzungen teilen ihn.
3. Testläufe nebeneinander messen Halbstände, rot wie grün.

**Daraus die Bedingung, unter der es funktioniert:** getrennte **Dateimengen**,
nicht getrennte Themen. Und hier ist die Trennlinie ungewöhnlich sauber —
`app/` ist Swift, brainlehr ist Python. Sie berühren sich an genau einer Stelle:
dem Dienst auf Port 8799 und seinen Datenendpunkten.

**Auflagen für die neue Sitzung:**
- `app/` gehört ihr allein. `kern/`, `haken/`, `melder/`, `knowledge_mcp_server.py`
  gehören der laufenden.
- Braucht die App einen neuen Datenendpunkt, wird er **hier** bestellt, nicht
  dort gebaut.
- Commits ausschließlich mit expliziter Pfadliste.
- Die volle Suite fährt **eine** Sitzung. Wer sie nebenher fährt, misst
  Halbstände.

## Aufträge, fertig zum Übergeben

**Für alle Aufträge gleichermaßen gilt:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`. Zuerst
`CLAUDE.md` lesen, dann diesen Plan. „Sieht der Code anders aus als hier
beschrieben, halte dich an den Code und melde die Abweichung." Kein `git add
-A`, kein Push, kein `git stash`. Committen mit expliziter Pfadliste — eine
zweite Sitzung arbeitet parallel am Python-Teil und teilt den Index. Nicht
`swift build` tippen, sondern `app/bauen.sh`; es wählt die taugliche Kette nach
Fähigkeit und zählt die Testfälle selbst nach. Sichtprüfung **Text vor Bild**
über die Bedienungshilfen; wenn doch ein Bild nötig ist, ausschließlich über die
**Fenster-Kennung** der Zielanwendung, nie nach Bildschirmbereich — am
2026-08-12 wurden dabei zweimal private Inhalte des Betreibers miterfasst.

### Schritt 1 · Der Viewer, an einem echten Dokument gemessen

| | |
|---|---|
| **Darf ändern** | `app/` (gesamt) |
| **Tabu zusätzlich** | `kern/`, `haken/`, `melder/`, `knowledge_mcp_server.py`, `schema.sql`, `tests/` — die gehören der parallelen Sitzung |
| **Fakten** | Für buckeberg sind die meisten Dokumente maschinenlesbar gemacht, und die Homepage hat bereits Anker in die Dokumente hinein — **beides vor dem Bau prüfen, nicht annehmen**. Als Bausteine kommen Quick Look und PDFKit in Frage; das ist **Modellwissen, ungeprüft**. |
| **Abnahme** | **Zuerst zählen**: welche Dateiformate liegen in buckeberg tatsächlich vor, mit Nenner. Dann je Format eine Probe an einem **echten** Dokument. Ein Format, das nicht geht, ist ein Befund mit Namen, kein Nebensatz. Negativfall: ein beschädigtes Dokument führt nicht zum Absturz der App, sondern zu einer Meldung. |

### Schritt 2 · Die Markierung trifft die richtige Stelle

| | |
|---|---|
| **Darf ändern** | `app/` (gesamt) |
| **Tabu zusätzlich** | wie Schritt 1; zusätzlich der Viewer aus Schritt 1, sobald er steht |
| **Fakten** | Seit 2026-08-13 trägt der Speicher 229 Kanten vom Typ `abgeleitet_von` auf 126 Quellknoten, und `kern/normbezug.py` unterscheidet **unbelegt** von **erfunden**. Eine Fundstelle ohne Beleg ist damit erkennbar, statt geraten zu werden. |
| **Abnahme** | Rot vor grün an Fällen mit **bekannter** Fundstelle: vorher markiert nichts, nachher die richtige Stelle. Negativfall, der wichtigere: Wo die Fundstelle **unbelegt** ist, wird **nicht** markiert, sondern gesagt, dass sie fehlt. Eine falsch gesetzte Markierung ist schlimmer als keine — sie sieht aus wie ein Beleg. |

### Schritt 3 · Das Raster, erst danach

| | |
|---|---|
| **Darf ändern** | `app/` (gesamt), dazu eine Konfigurationsdatei für die Feldbelegung |
| **Tabu zusätzlich** | wie oben; die Datenendpunkte des Dienstes werden **bestellt**, nicht selbst gebaut |
| **Fakten** | Der Dienst liefert auf Port 8799 die Ansichten `/raum` und `/vergleich` samt neun Datenendpunkten. `DienstAufsicht.swift` startet und überwacht ihn. Die Seitenleiste hat sechs Platzhalter. |
| **Abnahme** | Jede Aktion ist im Raster **zuordenbar und verschiebbar** — das ist zugleich die Probe, ob die Felder wirklich Behälter sind und nicht fest verdrahtete Plätze. Negativfall: Eine Feldbelegung, die es nicht gibt, führt zu einem leeren Feld mit Hinweis, nicht zu einem Absturz. |
