# ADR-016: Die Tabellenkalkulation wird ein Bestandteil — Formeln ja, Makros nie

**Stand** 2026-08-14T21:36:26+0200
**Status** Angenommen, Bauform offen bis zum Spike
**Betrifft** `atelier`, jede Domäne, `kern/`
**Entscheider** Betreiber, 2026-08-14

## Die Entscheidung des Betreibers

> *„nein ich will genau das ein excel im atelier auf betriebsystem ebene!"*

**Das hebt eine eigene Notiz vom selben Tag auf** (Knoten
`/brainlehr/der-baustein-vertrag-entscheidet-ueber`: *„Tabellenkalkulation
gehört ausdrücklich NICHT dazu"*). Der Widerspruch wurde einmal vorgelegt, mit
der Unterscheidung Tabelle / Tabellendatei / rechnende Zellen; der Betreiber hat
den dritten Fall gewählt. Die Notiz ist damit überholt.

## Warum das mehr ist als ein Merkmal

**Eine Formel ist eine sichtbare Belegkette.** Der Vertrag dieses Systems
lautet: keine Zahl ohne Herkunft. Was der Torwächter erzwingen soll — *eine
Summe kommt nur durch, wenn sie ihre Summanden mitliefert* (ADR-011) — ist in
einer Tabelle die **Normalform**: Die Zelle zeigt, woraus sie entsteht, und der
Weg dahin ist ein Klick.

Daraus folgt der praktische Nutzen:

- **EÜR und UStVA** stecken heute in Funktionen (`aveuer.py`, `tax_estimate.py`).
  Als Tabelle wird die Rechnung **prüfbar statt versteckt** — auch für einen
  Berater oder eine Behörde. Eine Zahl, deren Herleitung man ansehen kann, muss
  man nicht glauben.
- **Die Fristenrechnung** (Linie H, H6) ist Tabellenlogik: Datum plus Zeitraum,
  Betrag mal Zeit, sortiert nach Dringlichkeit.
- **Der Betreiber rechnet selbst**, ohne dass jemand Code baut. Jede Auswertung,
  die sonst ein Skript wird, wird eine Tabelle. Das ist der größte Hebel: Das
  System wird dort erweiterbar, wo es sonst immer Entwicklung braucht.

**Rang: Bestandteil, nicht Kern und nicht Domäne** (ADR-014). Alle Domänen
rechnen — brächte jede ihre eigene mit, wäre sie beim zweiten Kind kopiert. Eine
Domäne ohne Zahlen lädt sie nicht.

## Der Baustein: Univer

| | |
|---|---|
| **Lizenz** | **Apache-2.0**, am 2026-08-14 in der `LICENSE` des Projekts selbst nachgelesen — keine Zusatzklausel, kein Verweis auf eine kommerzielle Fassung |
| **Warum** | Einziger Kandidat mit **Oberfläche und eigenem Rechenwerk im Klienten**. Kein zweites Paket für Formeln, kein Dienst dazwischen |
| **Bauform** | Weboberfläche, eingebettet — dasselbe Muster wie `WissensraumWebView.swift` (ADR-013, Klasse „Fachbildschirme") |

**Ausgeschlossen, mit Grund:**

- **HyperFormula** — GPLv3 **oder** kommerziell. Der GPL-Weg zöge die gesamte
  einbindende Anwendung mit; der andere kostet Geld. Beides scheidet aus.
- **Handsontable** — seit 2019-03-06 nicht mehr quelloffen, gratis nur für
  nichtkommerzielle Nutzung. Fällt an der Bedingung des Betreibers
  (*Quelloffenheit ist Bedingung, nicht Vorliebe*).
- **ag-Grid Community** — MIT, aber Formeln nur in der kostenpflichtigen
  Fassung. Als Tabellenkalkulation untauglich.
- **x-spreadsheet** — MIT, aber eingestellt.

**Offen, nicht jetzt zu entscheiden:** der `xlsx`-Rundlauf. `SheetJS CE`
(Apache-2.0) trägt Formeln durch, verliert aber Gestaltung und Diagramme beim
Schreiben; `openpyxl` (MIT) ist die Python-Seite. Fällig, wenn die erste echte
Tabellendatei ins Haus kommt.

## Die Sperre, ohne die „Daten, nie Code" aufweicht

**Eine Tabelle mit Formeln ist eine Ausführungsumgebung.** ADR-011 und ADR-012
legen fest, dass ein Domänenpaket Daten ist und niemals Code. Eine Formel ist
die Grauzone: sie **rechnet**, aber sie darf nicht **rufen**.

Deshalb, verbindlich ab dem ersten Bauschritt:

- **Kein Dateizugriff, kein Netzzugriff, keine Makros.** Makros in
  Tabellendateien sind der klassische Angriffsweg überhaupt.
- **Der Funktionsumfang ist eine Positivliste**, keine Verbotsliste. Jede
  Verbotsliste hat ein Loch, und bei eingelesenen fremden Dateien liegt in
  diesem Loch der Schaden.
- **Eine importierte Tabellendatei bringt ihre Formeln als Daten mit** — sie
  werden gelesen und neu gerechnet, nie ausgeführt, wie sie ankommen.

## Vor dem Bau zu messen

1. Läuft Univer eingebettet und **ohne Netz** (die Anwendung darf keinen
   Auswärtsgang brauchen, ADR-014)?
2. Welches Gewicht bringt es mit?
3. Trägt es die Positivliste, oder muss der Funktionsumfang beschnitten werden?
4. Restrisiko aus der Recherche, ausdrücklich offen: In einem Sammelrepo können
   **einzelne Pakete** eine andere Lizenz tragen als die Wurzel. Vor dem
   Einbinden die tatsächlich eingebundenen Pakete einzeln nachlesen.

## Gemessen 2026-08-15T10:31:55+0200 — trägt mit drei Auflagen

Ergebnisdatei `runs/spike_univer_i3_2026-08-15T103155+0200.json`, Spike
`spikes/univer_i3_min/`.

**Frage 1, ohne Netz: belegt.** macOS-Seatbelt mit `deny network-outbound`,
nur `localhost` erlaubt. Gegenprobe in beide Richtungen: `curl` nach draußen
scheitert (exit 7), auf `127.0.0.1` antwortet es (200). Das Blatt rendert
vollständig (Bildschirmfoto im Spike). **Grenze:** nur Start und Rendern
geprüft, kein Dauerbetrieb — Chrome beendet sich unter dieser Sandbox nicht
sauber.

**Frage 2, Gewicht:** 2,74 MB gzip mit React, 896 KB als reine UMD-Datei ohne.

**Frage 4 hat getroffen, und sie ist die teuerste.** Der dokumentierte Weg
(`npm install @univerjs/presets`, nötig für die `createUniver()`-API) zieht
**27 Pakete `@univerjs-pro/*` ohne Lizenzfeld und ohne Lizenzdatei** — nicht
eine abweichende Lizenz, sondern **keine**. Die übrigen 140–199 Pakete sind
durchweg MIT, Apache-2.0, BSD-3-Clause oder ISC. Im ausgelieferten Bündel
selbst: **0 Treffer** für `univerjs-pro`.

> **Auflage 1:** Importe strikt auf Wurzelexport und `preset-sheets-core`
> begrenzen. Sonst wandern die 27 unlizenzierten Pakete mit — und selbst bei
> sauberem Bündel liegen sie auf der Bauplatte und im Sperrverzeichnis.

**Und der Fund, der die Sicherheitsauflagen oben bestätigt:** Das Grundpaket
enthält bereits die Formel `WEBSERVICE` (netzfähig) und einen
`new Function()`-Pfad für benutzerdefinierte Formeln.

> **Auflage 2:** Beide werden gesperrt, **bevor** die erste fremde Datei
> eingelesen wird. Das ist keine Vorsichtsmaßnahme, sondern dieselbe Bauform,
> die am 2026-08-15 auf einer fremden Anlage als Schadcode gefunden wurde:
> Code aus einer Datenquelle per `new Function` ausführen.
>
> **Auflage 3, offen:** Ungeklärt ist, ob der `new Function`-Zeichenkette auch
> aus einer **importierten Datei** stammen kann. Solange das nicht gemessen
> ist, gilt der Import fremder Tabellendateien als gesperrt — nicht als
> riskant, als gesperrt.

## Gemessen 2026-08-15T14:10:23+0200 — Auflage 3, Sperre für den Importweg aufgehoben

Ergebnisdatei
`runs/spike_univer_i3_auflage3_2026-08-15T141023+0200.json`, Testskript
`spikes/univer_i3_min/probe3/entry_import.js`.

**Codelese:** Beide `new Function`-Fundstellen im Bundle (0 mehr, 0 weniger —
`sheets-formula/lib/es/index.js:16529` und `:16534`, Funktionen
`createFunction`/`createAsyncFunction`) liegen ausschließlich hinter der
öffentlichen API `registerFunction`/`registerFunctions` — die Eingabe ist
`func.toString()` eines JS-Funktionsobjekts, das nur **Host-Code** übergeben
kann. Kein Aufrufpfad liest die Zeichenkette aus `cellData` (Feld `f`/`v`)
oder aus dem generischen Snapshot-Erweiterungsfeld `resources` — für Letzteres
belegt durch 0 Treffer für `"resources"` im gesamten `sheets-formula`-Paket.

**Herstellungsversuch:** Ein Univer-JSON-Snapshot (nativer Ladeweg,
`univerAPI.createWorkbook()`) wurde mit vier Angriffsversuchen bestückt —
WEBSERVICE-Formel, `fetch(...)` als Formelausdruck, `fetch(...)` als reiner
Zellwert, eine vorgetäuschte Funktionsregistrierung im `resources`-Feld.
`window.Function` wurde vorher durch einen mitschneidenden Proxy ersetzt.
**Ergebnis: 0 Treffer aus der Nutzlast, 0 Netzzugriffe.** Die Instrumentierung
selbst wurde doppelt positiv kontrolliert: ein eigener `new Function(...)`-Aufruf
wurde zuverlässig mitgeschnitten (Instrumentierung funktioniert), ein
legitimer Host-Aufruf von `univerAPI.registerFunction(...)` löste dagegen
**ebenfalls keinen** `new Function`-Aufruf aus — weil der dafür nötige
Remote-/Worker-Dienst in der aktuellen Paketkombination (`preset-sheets-core`
ohne separate Worker-Konfiguration) gar nicht gebunden ist. Der Pfad ist in
diesem Bundle strukturell tot, nicht nur unerreicht.

**Gegenbefund zur vorherigen Messung:** `WEBSERVICE` ist im installierten
Paketbaum nur als Beschreibungseintrag (Menü/Autovervollständigung)
vorhanden, ohne Executor — eine Zelle mit `=WEBSERVICE(...)` ergibt `#NAME?`.
Die frühere Aussage „WEBSERVICE ist im Bundle" stützte sich nur auf einen
Text-Grep, nicht auf eine Ausführungsprobe. Auflage 2 bleibt davon
unberührt: WEBSERVICE und der `new Function`-Pfad werden weiterhin vor dem
ersten Import gesperrt, weil ein künftiges Paket (z. B. eine Worker- oder
Advanced-Erweiterung) den fehlenden Executor bzw. Dienst nachliefern kann.

**Positivliste vs. Verbotsliste, entschieden:** Univer erzwingt technisch eine
**Verbotsliste**. Der Formel-Engine-Start hängt die Konfiguration `function`
nur per `.concat()` an die feste Liste `ALL_IMPLEMENTED_FUNCTIONS` an
(`engine-formula/lib/es/index.js:40564`) — sie ersetzt sie nie. Einzelne
Funktionen lassen sich nur nachträglich per `unregisterExecutors`/
`unregisterDescriptions` entfernen. Eine Positivliste („nur diese N
Funktionen") ist mit der öffentlichen Konfiguration nicht baubar.

**Ergebnis:** Auflage 3 gilt als gemessen. **Der Import fremder
Tabellendateien wird entsperrt**, gebunden an eine Bauvorschrift für den
kommenden Importer: Importcode darf `registerFunction`/`registerFunctions`
nie mit Daten aus der importierten Datei aufrufen — dafür ist beim Bau des
Importers eine eigene Ratsche vorzusehen. Auflage 2 (Verbotsliste vor dem
ersten Import ausführen, bei jedem Univer-Versionswechsel erneut gegen
`ALL_IMPLEMENTED_FUNCTIONS` abgleichen) bleibt unverändert in Kraft. Der
xlsx-Weg über SheetJS wurde **nicht** mitgemessen (Paket nicht installiert,
ADR nennt den xlsx-Rundlauf als eigene offene Frage) — die hier belegte
Kette (Dokumentmodell → `new Function`) ist aber unabhängig davon, wer das
`IWorkbookData`-Objekt befüllt hat; ein SheetJS-Parser selbst müsste eine
eigene Ausführungsstelle enthalten, was bei dessen Auswahl gesondert zu
prüfen ist.

## Auflage 4 — benannte Bereiche sind Pflicht, nicht Komfort

Betreiberentscheidung 2026-08-15 (Knoten `00e74420`). Grund: Ein Zellbezug
(`B2:B47`) ist eine Adresse ohne Bedeutung — ein Mensch liest die Bedeutung
aus der Nachbarschaft, ein Modell muss sie raten, und Raten ist genau das,
was der Belegvertrag ausschließt (siehe oben: „keine Zahl ohne Herkunft").
Mit Namen (`=SUMME(erloese)*ust_satz`) ist dieselbe Tabelle für beide Seiten
lesbar. Jetzt, vor dem ersten Blatt, kostet die Regel nichts; nachträglich
ist sie dieselbe Migrationsarbeit wie ein fehlendes Feld am Baustein.

**Gemessen: Univer trägt benannte Bereiche.** Das Paket `@univerjs/sheets`
(transitive Abhängigkeit von `preset-sheets-core`, im Spike installiert)
liefert die Facade-Klassen `FWorkbook`/`FDefinedName`/`FDefinedNameBuilder`
(`node_modules/@univerjs/sheets/lib/types/facade/f-defined-name.d.ts`,
`f-workbook.d.ts`) mit `insertDefinedName(name, formulaOrRefString)`,
`getDefinedNames()`, `getDefinedName(name)`, `deleteDefinedName(name)` sowie
Gültigkeitsbereich je Blatt oder Arbeitsmappe (`setScopeToWorksheet`/
`setScopeToWorkbook`). Die Funktion ist kein totes Typskript: `grep -c
insertDefinedName` findet die Zeichenkette je zweimal im tatsächlich
gebauten Anwendungsbündel (`spikes/univer_i3_min/dist/bundle.js` und
`spikes/univer_i3_min/probe3/bundle.js`) — sie ist im ausgelieferten Code
vorhanden, nicht nur in der Bibliotheksquelle.

> **Auflage 4:** Jedes Tabellenblatt, das dieses System erzeugt oder dem
> Nutzer zur Eingabe vorlegt, legt für jeden Wertebereich, der in einer
> Formel wiederverwendet wird, einen benannten Bereich über
> `insertDefinedName` an, bevor die erste Formel ihn referenziert. Ein
> Zellbezug ohne Namen in einer erzeugten Formel gilt als Verstoß gegen
> diese Auflage, keine Ausnahme aus Bequemlichkeit.

**Nicht gemessen, weil hier nicht nötig:** ob benannte Bereiche den
xlsx-Rundlauf (SheetJS/`openpyxl`, ADR nennt ihn als eigene offene Frage)
verlustfrei überstehen. Das ist bei der Auswahl des xlsx-Wegs gesondert zu
prüfen, sobald die erste echte Tabellendatei ins Haus kommt.
