# ADR-009: Dokumentbasis — LuaLaTeX, mit Schranke statt Vertrauen

**Stand** 2026-08-14T09:21:18+0200
**Status** Angenommen
**Betrifft** jede Dokumentausgabe des Verbunds — Schreiben, Rechnungen, Dossiers, Auswertungen
**Entscheider** Betreiber, 2026-08-14

## Die Frage

Der Betreiber hatte die Richtung früh gesetzt: *„wichtig ist nicht wysiwyg, wichtig ist dass
zum schluss ein schönes dokument heraus kommt, deswegen latex, aber für word dummies
benutzbar."* Offen blieb, mit **welchem** Satzwerkzeug — und ob Satzqualität und
Barrierefreiheit einen Zielkonflikt bilden. Der Europäische Rechtsakt zur Barrierefreiheit
ist seit 2025-06-28 durchsetzbar; ein Schreiben an eine Behörde muss zugänglich sein.

Anlass war zusätzlich die Betreiberregel vom selben Tag: *„gibt es werkzeuge die unbekannter
sind oder auf den ersten blick nicht so bedienungsfreundlich aber bessere ergebnisse
bringen, sind diese zu nutzen"* — mit der Abbruchbedingung, dass nur ein Unterschied zählt,
den ein **Mensch am fertigen Erzeugnis** sieht.

## Entscheidung

1. **Satzwerkzeug: LuaLaTeX mit aktuellem TeX Live.** Nicht `tectonic` (Bündel eingefroren
   auf den LaTeX2e-Kern vom 2021-11-15, kennt `\DocumentMetadata` nicht), nicht pdfLaTeX
   (`tagpdf` bleibt dort in einem stillen Leerlauf).
2. **`verapdf -f ua1` ist eine SCHRANKE im Bau, kein Bericht daneben.** Fällt die
   Validierung, entsteht kein Dokument.
3. **`\DocumentMetadata` wird bedingt gesetzt** — beim PDF-Bau ja, beim HTML-Bau nein.
   tex4ht definiert `\HCode`; daran hängt die Verzweigung.
4. **Der Quelltext wird semantisch ausgezeichnet.** `\section` statt `\textbf`, Tabellen mit
   ausgewiesener Kopfzeile, Listen als Listen. Nicht als Stilfrage — siehe unten.
5. **Typst wird nicht verworfen, sondern zurückgestellt.** Sollte sich die Lage bei HTML
   oder MathML drehen, ist die Rechnung neu zu machen.

## Was gemessen wurde, und in welcher Reihenfolge es kippte

Vier Runden, drei davon haben eine vorherige Aussage widerlegt.

**Runde 1 — die Fremdbehauptung bestätigt, aber am falschen Gegner.** Typst erzeugt getaggte
Struktur im Standardbau, PDF/UA-1 mit einem Flag. `tectonic` kann es nicht. Daraus wurde
zunächst „Typst gewinnt bei der Zugänglichkeit" — richtig gemessen, falsch benannt: der
Gegner war nicht LaTeX, sondern ein Bündel von 2021.

**Runde 1b — der Mensch widerspricht der Maschine.** Der Betreiber sah beide PDFs an und
urteilte: das LaTeX-Erzeugnis ist schöner gesetzt, **hat aber einen Einrückungsfehler.** Der
Fehler war ein **Dokumentfehler** (fehlendes `\noindent`, keine Briefklasse), behoben mit
`parskip` und am Bild belegt. Befund über den Aufbau: Runde 1 hatte **zwei nachlässig
geschriebene Dokumente** verglichen, nicht zwei Werkzeuge.

**Runde 2 — der Zielkonflikt löst sich auf.** LuaLaTeX mit Kern 2026-06-01 erzeugt echt
getaggtes PDF/UA: `/MarkInfo {/Marked true}`, `/Lang de-DE`, `/StructTreeRoot` mit 5 Kindern,
75 Strukturobjekte, mit `pikepdf` geprüft. Drei stille Vorbedingungen dabei (Knoten
`66a4e633`): LuaLaTeX ist Pflicht · `latex-lab` und `pdfmanagement` müssen liegen ·
**`pdfstandard=UA-1` schaltet das Tagging NICHT ein**, es braucht `tagging=on`.

**Runde 3 — Diagramme, Formeln, und der eigentliche Befund.** Beide Werkzeuge tagen ein
Balken- und ein Ablaufdiagramm als `/S /Figure` mit echtem `/Alt`-Text im PDF (belegt per
`qpdf --qdf`). Dann aber:

> **LuaLaTeX kompilierte klaglos ein PDF, das die Kennung `pdfuaid:part=1` trug und die
> echte Validierung nicht bestand** (veraPDF, Klausel 7.1: fehlender `dc:title`).
> **Typst verweigert denselben Fehler** — der Bau bricht ab, es entsteht kein Dokument.

Das ist kein Fähigkeitsunterschied, sondern der Unterschied zwischen einem Werkzeug, das
sein Misslingen meldet, und einem, das schweigt — genau die Prüffrage des Grundgedankens:
*Kann ein Programm dieses Werkzeug fragen, ob es funktioniert hat?* **Und genau deshalb ist
Punkt 2 dieser Entscheidung keine Formalie: Die Schranke ersetzt die fehlende Selbstmeldung.**

**Runde 4 — HTML, und eine harte Grenze.** Von drei Wegen liefert nur einer Inhalt:
`tex4ht` erzeugt HTML mit CSS und `lang='de'` · LaTeXML bricht am aktuellen Kern fatal ab ·
Typsts HTML-Ausgabe **verliert den Inhalt jedes `#align(...)`-Blocks stillschweigend**
(Datumszeile und komplette Tabelle fehlten, ohne Fehlermeldung). Aber: **tex4ht bricht mit
`\DocumentMetadata` im Vorspann fatal ab** — und das ist die Zeile, die getaggtes PDF/UA
erst möglich macht. Daraus Punkt 3. Belege im Knoten `dbad8fb1`.

## Warum LaTeX, wenn die Satzqualität unentschieden ist

Der Betreiber sah die Grafikfassungen an und urteilte **gemischt** — „beides hat Vor- und
Nachteile im PDF-Design". Damit fällt Satzqualität als Kriterium weg, und sein Zusatz
*„gefühlt hört sich latex für mich aber immer noch besser an"* trägt allein nicht: Genau
diese Form war im ursprünglichen LaTeX-Fall dreimal falsch, damals als „umständlich".

Es trägt, weil **vier prüfbare Gründe** darunterliegen und keine Messung mehr dagegen steht:

- **Haltbarkeit.** LaTeX ist Jahrzehnte alt, Typst wenige Jahre. Für eine Dokumentbasis, aus
  der in zehn Jahren noch etwas fallen soll, ist das der Maßstab „was später teuer zu
  erkaufen ist".
- **Bestand an Vorlagen** — einschließlich `KOMA-Script` mit DIN 5008 für deutsche
  Geschäftsbriefe.
- **Formelaufwand, gemessen.** Typst verlangt Alternativtext für **jede** Formel, auch ein
  `$i$` im Fließtext, sonst bricht der Bau ab. Eine Steuerauswertung kostet dort spürbar
  mehr Schreibarbeit.
- **Beitragende.** Weit mehr Menschen können LaTeX lesen und schreiben — dieselbe
  Beitragenden-Decke wie eine deutschsprachige Schnittstelle.

Typsts einziger echter Vorsprung war die Selbstprüfung, und die holt Punkt 2 ein.

## Der Befund, der schwerer wiegt als die Werkzeugwahl

Das von tex4ht erzeugte HTML trug `<table>` mit allen Zahlen — aber **kein `<th>`, keine
Überschriften, keine Liste.** Ein Teil davon ist kein Werkzeugmangel: Der Probebrief benutzt
`\textbf` für Betreff und Zwischenüberschrift statt `\section`. **Aus visueller Auszeichnung
kann kein Werkzeug eine Überschrift ableiten.**

> Eine Vorlage, die visuell auszeichnet, erzeugt auf **beiden** Wegen ein unzugängliches
> Ergebnis. Die Auszeichnung entscheidet die Zugänglichkeit mehr als die Wahl des Werkzeugs.

Welcher Anteil am Werkzeug und welcher am Quelltext liegt, ist **nicht** gemessen.

## Alternativen, samt Ablehnungsgrund

| Weg | Abgelehnt weil |
|---|---|
| **tectonic** (Status quo) | Bündel eingefroren auf Kern 2021-11-15, kein `\DocumentMetadata`, kein getaggtes PDF. Vorteil war nur die kleinere Datei (20 KB gegen 145 KB) — bei einem Dokument, das barrierefrei sein muss, kein Argument. |
| **Typst** | Zurückgestellt, nicht verworfen. Verliert an Haltbarkeit, Vorlagenbestand, Formelaufwand und Beitragendenkreis. Sein Vorsprung bei der Selbstprüfung ist durch die Schranke aufgehoben. |
| **Eine Abstraktion über beide Werkzeuge** | Bei unentschiedener Satzqualität liegt es nahe, die Wahl offenzuhalten und über eine Zwischendarstellung zu rendern. Abgelehnt: Das ist die Vorratshaltung, an der laut Archäologie-Befund fünf von acht vergleichbaren Vorhaben starben — Tribut vor Gegenleistung. Zwei Renderer für eine Darstellung sind echte Arbeit ohne heutigen Nutzen. |
| **Nur HTML, kein PDF** | Ein Schreiben an eine Verwaltung wird unterschrieben und abgeschickt. Der Betreiber hat den Wert eines gut gesetzten Briefs ausdrücklich benannt. |

## Was das kostet

- **Zwei Bauläufe statt einem**, mit unterschiedlichem Vorspann. Die Verzweigung muss von
  Anfang an stehen — nachträglich ist es eine Änderung an jeder Vorlage.
- **Ein aktuelles TeX Live ist Voraussetzung.** Installiert wurde TinyTeX (nutzerseitig, ohne
  Administratorrechte) plus `parskip`, `babel-german`, `tagpdf`, `latex-lab`,
  `pdfmanagement`, `pgf`, `pgfplots`, `grfext`. Das minimale Grundsystem hatte TikZ und
  pgfplots **gar nicht**.
- **Die Schranke macht den Bau langsamer und gelegentlich rot.** Das ist ihr Zweck.
- **Kein automatischer Vorleser-Test.** Belegt ist Struktur und veraPDF-Gültigkeit, nicht das
  Verhalten eines konkreten Hilfsmittels. Und **MathML fehlt in beiden Werkzeugen** — Formeln
  haben einen Alternativtext, aber keine semantische Ebene. Für eine Steuerauswertung kann
  das später zählen.

## Woran sich Erfolg misst

- Ein Dokument, dem `dc:title` fehlt, **entsteht nicht** — die Schranke fällt, bevor eine
  Datei geschrieben wird. Vorher entstand es klaglos.
- Aus demselben Quelltext fallen PDF **und** HTML, beide mit Inhalt. Am Erzeugnis belegt,
  nicht am Bauprotokoll.
- Das HTML trägt `<th>` in Tabellenköpfen und echte Überschriften — das ist der Nachweis,
  dass die Auszeichnung semantisch ist und nicht nur der Bau läuft.
