# Tabellenkalkulation-Kandidaten — Recherche 2026-08-14T00:00:00+0200

Nur Recherche. Nichts installiert, nichts geladen. Primaerquelle = LICENSE-Datei im Repo, wo erreichbar.

## OHNE Einschraenkung offen (permissive: MIT/Apache/BSD)

### A) Oberflaeche

1. **Univer** — dream-num/univer. https://github.com/dream-num/univer
   Lizenz: Apache-2.0, woertlich Standardtext, LICENSE-Datei https://github.com/dream-num/univer/blob/dev/LICENSE. Keine AGPL-Anteile im Kern gefunden. Achtung: separates `univer-presets`-Repo eigene LICENSE-Datei, ebenfalls Apache-2.0 — aber `docs.univer.ai/guides/pro/license` nennt "Pro"-Features (Server/Enterprise) separat lizenziert, NICHT geprueft was darin steht (nicht Teil der Kern-UI).
   Pflege: aktiv, Release v0.25.1 am 2026-06-27, Doku-Update 2026-07-25. Ziel v1.0 offen.
   Formeln: eigenes Rechenwerk integriert (sheets-formula-Modul, Teil des Apache-Repos) — rechnet im Klienten, kein externes Rechenwerk noetig.
   xlsx Rundlauf: nicht belegt in dieser Recherche (nicht primaerquellig geprueft).

2. **Fortune-Sheet** (Luckysheet-Nachfolger, React/Vue). https://github.com/ruilisi/fortune-sheet
   Lizenz: MIT (laut Projektangabe, LICENSE-Datei selbst NICHT einzeln abgerufen — als "nicht per Primaerdatei verifiziert" kennzeichnen, nur Repo-Metadaten gesehen).
   Pflege: aktiv (npm-Paket "fortune-sheet" gepflegt).
   Formeln: eigener Formel-Parser im Klienten, Funktionsumfang nicht gezaehlt.
   xlsx Rundlauf: nicht belegt.

3. **x-spreadsheet** (myliang). https://github.com/myliang/x-spreadsheet
   Lizenz: MIT, LICENSE-Datei https://github.com/myliang/x-spreadsheet/blob/master/LICENSE, Copyright 2017 myliang.
   Pflege: EINGESTELLT. Projekt migriert zu @wolf-table/table, kein aktives Repo mehr unter diesem Namen. Letzter Aktivitaetsstand nicht exakt datiert, aber Repo-Beschreibung selbst sagt "migrated".
   Formeln: rudimentaeres eingebautes Set (SUM etc. vorhanden lt. Doku-Referenzen), exakte Funktionsliste NICHT belegt — als unbelegt kennzeichnen.
   xlsx Rundlauf: nicht belegt.

4. **Jspreadsheet CE** (Community Edition). https://github.com/jspreadsheet/ce
   Lizenz: MIT, LICENSE-Datei https://github.com/jspreadsheet/ce/blob/master/LICENSE, Copyright 2024 Jspreadsheet Ltd.
   Pflege: aktiv, Issues bis Januar 2026 belegt.
   Formeln: nutzt eigenes Modul jspreadsheet/formulajs (formula.js-Ableger), 403 Funktionen in Basic-Variante (kostenlos/CE), 455 in "Pro"-Erweiterung (KOSTENPFLICHTIG, separates Produkt "Formula Pro" — NICHT Teil von CE). Rechnet im Klienten.
   xlsx Rundlauf: nicht belegt in dieser Recherche.

5. **ag-Grid Community**. https://github.com/ag-grid/ag-grid
   Lizenz: MIT fuer Community-Paket (ag-grid-community). Enterprise-Features (u.a. "Formulas"!) NUR in ag-grid-enterprise, kommerzielle EULA-Lizenz — Formel-Feature selbst ist NICHT im offenen Teil enthalten. Damit fuer diesen Zweck (Formeln) die MIT-Kernversion allein NICHT ausreichend.
   Pflege: aktiv, kommerziell getrieben.
   Formeln: nur in Enterprise-Bezahlversion. Als Oberflaeche fuer reines Grid brauchbar, als Formel-Tabellenkalkulation ohne Kauf NICHT geeignet.

### B) Rechenwerk

6. **HyperFormula** — s.u. bei "doppelte Lizenzlage" (GPLv3/kommerziell), NICHT frei von Bedingungen.

7. **formulas** (Python, vinci1it2000). https://github.com/vinci1it2000/formulas
   Lizenz: EUPL 1.1+ (European Union Public Licence), Copyleft-Lizenz — Primaerquelle LICENSE-Datei selbst nicht einzeln abgerufen in dieser Runde, nur Projekt-/PyPI-Metadaten. Als "quelloffen, aber Copyleft mit EU-Sonderregeln" kennzeichnen — nicht permissiv wie MIT/Apache. EUPL erlaubt kommerzielle Nutzung, verlangt aber bei Weitergabe modifizierter Werke Offenlegung (aehnlich LGPL/CeCILL-Familie, EUPL hat Kompatibilitaetsliste zu GPL). Fuer Betreiber-Zweck vermutlich unproblematisch, da EUPL kommerzielle Nutzung nicht verbietet — aber Bedingung ist da, also NICHT in die Kategorie "ohne jede Einschraenkung".
   Pflege: sehr aktiv, v1.3.4 am 2026-03-11, v1.3.3 am 2025-11-04.
   Formeln: kompiliert Excel-Formeln zu Python, breiter Funktionsumfang (Doku nennt viele Excel-Funktionen), rechnet serverseitig/Python, nicht im Browser.
   xlsx Rundlauf: liest xlsx/ods/json, Schreiben von Formeln in dieser Recherche nicht primaerquellig verifiziert.

8. **pycel** (dgorissen, jetzt stephenrauch-Fork aktiv). https://github.com/dgorissen/pycel
   Lizenz laut Paket-/Repo-Metadaten: GPL-3.0. LICENSE-Datei selbst nicht einzeln abgerufen — Kennzeichnung "GPL-3.0, aus Paketmetadaten, nicht aus LICENSE-Datei selbst gelesen". GPL-3.0 bedeutet: Verlinkung/Weitergabe des Gesamtwerks zwingt bei Distribution zur GPL-Offenlegung — Folgen fuer eine Auslieferung, falls pycel eingebunden wird.
   Pflege: Issues bis November 2025 belegt, aktiv.
   Formeln: kompiliert Excel-Blatt zu Python-Graph, viele Mathefunktionen + INDEX/LOOKUP/MIN/MAX etc., rechnet in Python, kein Klient.

9. **koala2** (vallettea). https://github.com/vallettea/koala
   Lizenz laut PyPI/Repo-Metadaten: GNU GPL3 — LICENSE-Datei selbst nicht einzeln gelesen, Kennzeichnung wie bei pycel.
   Pflege: NICHT aktuell verifizierbar in dieser Recherche (kein Archiv-Badge gefunden, aber auch keine juengeren Releases belegt) — als "Pflegestand unbelegt" kennzeichnen, nicht als tot behaupten.
   Formeln: transponiert Excel-Berechnungen zu Python-Netzwerk mit Abhaengigkeiten, rechnet in Python.

### C) Dateiformat xlsx

10. **openpyxl**. https://openpyxl.readthedocs.io/ , PyPI https://pypi.org/project/openpyxl/
    Lizenz: MIT (lt. PyPI-Metadaten/Doku, LICENSE-Datei des Haupt-Repos selbst nicht einzeln in dieser Runde abgerufen — Kennzeichnung wie oben).
    Pflege: aktiv (3.1.x-Reihe).
    Formeln: liest/schreibt FORMELTEXT (String), wertet NICHT selbst aus — Trennung Datenformat vs. Rechenwerk. `data_only=True` liest nur den zuletzt von Excel gespeicherten Wert, nicht die Formel selbst.
    xlsx Rundlauf: JA fuer Formeln als Text (verlustfrei beim reinen Lesen/Schreiben von Formelstrings); Stil/Diagramme teils eingeschraenkt (aus Doku-Hinweisen, nicht tief verifiziert).

11. **XlsxWriter** (jmcnamara). https://github.com/jmcnamara/XlsxWriter
    Lizenz: BSD-2-Clause, LICENSE-Datei https://github.com/jmcnamara/XlsxWriter/blob/main/LICENSE.txt.
    Pflege: aktiv, Copyright-Zeile bis 2025.
    Formeln: kann Formeln SCHREIBEN (als Text, Excel berechnet beim Oeffnen neu), kein Lesen von xlsx — reine Schreib-Bibliothek, daher KEIN Rundlauf (kein Read).

12. **SheetJS Community Edition (xlsx)**. https://git.sheetjs.com/SheetJS/sheetjs (Spiegel: https://github.com/sheetjs/sheetjs)
    Lizenz: Apache-2.0 fuer CE, LICENSE-Datei https://github.com/SheetJS/SheetJS.github.io/blob/master/LICENSE als Beleg gesehen (Haupt-Repo-LICENSE selbst nicht separat abgerufen in dieser Runde — mit dieser Einschraenkung kennzeichnen). ACHTUNG doppelte Lage: CE ist offen, "SheetJS Pro" ist ein SEPARATES kommerzielles Produkt fuer Styles/Charts/Bilder/Pivot/Validierung beim Schreiben — CE laesst diese beim Schreiben bewusst weg.
    Pflege: aktiv, Repo umgezogen zu git.sheetjs.com, GitHub bleibt Spiegel.
    Formeln: CE erhaelt Formelausdruecke beim Lesen/Schreiben (Text), wertet selbst NICHT aus (kein Rechenwerk enthalten) — braucht externes Rechenwerk wie HyperFormula fuer echte Neuberechnung.
    xlsx Rundlauf: JA fuer Formeln/Werte, NEIN fuer Styles/Charts/Pivot (die verliert CE explizit beim Schreiben laut office-kit/xlsx-Vergleichsnotiz — als Fremdaussage, nicht aus SheetJS-Primaerquelle selbst geprueft, kennzeichnen).

## Doppelte Lizenzlage — GETRENNT ausgewiesen, Folgen fuer Auslieferung

13. **HyperFormula** (Handsoncode). https://github.com/handsontable/hyperformula
    Lizenz woertlich aus LICENSE.txt: zwei Pfade. Pfad 1 "Your use of this software is subject to the terms included in an applicable proprietary license agreement between you and HANDSONCODE" (= kommerzielle Lizenz, kostenpflichtig). Pfad 2: GNU GPLv3 — nur nutzbar, wenn NICHT-kommerziell bzw. das eigene Gesamtwerk GPLv3-kompatibel offengelegt wird. Primaerquelle: https://github.com/handsontable/hyperformula/blob/master/LICENSE.txt.
    FOLGE FUER AUSLIEFERUNG: Wird atelier NICHT selbst vollstaendig GPLv3 und oeffentlich mit Quellcode ausgeliefert, ist HyperFormula nur gegen Kauf einer proprietaeren Lizenz nutzbar. Bei geplantem produktivem/kommerziellem Einsatz ohne GPLv3-Offenlegung: HARTE BEDINGUNG DES BETREIBERS (Quelloffenheit) durch GPLv3-Pfad theoretisch erfuellbar, aber erzwingt dann GPLv3 fuers GESAMTE einbindende Werk — Tragweite pruefen, bevor eingebunden wird.
    Pflege: sehr aktiv, ~418 Funktionen (Release-Notes), Handsontable-Firmenprodukt.
    Formeln: ueber 400 Excel-Funktionen, rechnet im Klienten (Browser) ODER Node — kein Server-Zwang. Abhaengigkeitsgraph/Neuberechnung eingebaut (Kernzweck).
    xlsx Rundlauf: kein eigenes Dateiformat-Handling — reines Rechenwerk, braucht A/C-Baustein fuer Datei.

14. **Handsontable** (Grid-UI derselben Firma). https://handsontable.com/docs/javascript-data-grid/software-license/
    Lizenz: SEIT v7.0.0 (2019-03-06) NICHT mehr Open Source. "Source-available", kostenlos nur fuer nicht-kommerzielle Zwecke (Forschung, Studium, Evaluierung) — Produktiveinsatz mit kommerziellem Bezug AUSDRUECKLICH ausgeschlossen ohne Kaufvertrag. Primaerquelle: handsontable.com/docs/.../software-license/ und PDF-Lizenztext unter handsontable.com/static/licenses/non-commercial/.
    FOLGE: scheidet wegen HARTER BEDINGUNG (Quelloffenheit) aus — ist keine offene Lizenz, sondern proprietaer mit Gratis-Ausnahme nur fuer Nicht-Kommerz.

## Nicht abschliessend geprueft / offene Luecken dieser Recherche
- LibreOffice headless (`soffice --convert-to xlsx`) als C)-Alternative: Lizenz MPLv2 / LGPLv3+ dual (Quelle: documentfoundation.org, GNU-Lizenzliste) — beide unproblematisch offen, KEIN Copyleft-Zwang fuer aufrufende Programme (reiner Prozessaufruf, keine Verlinkung). Kann xlsx MIT Formeln lesen/schreiben/neu berechnen (Neuberechnung beim Convert nicht mit dediziertem Flag belegt, laeuft laut Nutzerberichten idR automatisch mit). Kein Kandidat A/B, sondern Alternative fuer C) auf Dienstseite (Python ruft soffice als Subprozess).
- Bei mehreren Punkten (Univer-Formelmodul-Details, Fortune-Sheet-LICENSE-Datei direkt, x-spreadsheet-Funktionsliste, openpyxl/pycel/koala2/formulas LICENSE-Dateien direkt, SheetJS Haupt-LICENSE direkt) wurde NICHT die Repo-LICENSE-Datei selbst abgerufen, sondern Metadaten/Sekundaerquellen — einzeln oben gekennzeichnet. Vor Einbindung: jeweilige LICENSE-Datei nochmal direkt oeffnen.
