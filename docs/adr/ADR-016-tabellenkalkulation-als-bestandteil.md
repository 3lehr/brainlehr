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
