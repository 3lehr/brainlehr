# Startprompt: Grundarchitektur brainlehr

Erzeugt 2026-08-13T21:32:22+0200 am Ende einer langen Bausitzung, für ein
**frisches Kontextfenster**. Der Betreiber will die Grundarchitektur
besprechen, nicht die App weiterbauen.

Alles unter „Gemessen" ist an diesem Tag mit Werkzeugen erhoben worden. Alles
unter „Betreiber" ist wörtliches Zitat. Was hier fehlt, fehlt absichtlich —
insbesondere gibt dieser Prompt **keine Empfehlung** ab.

---

## Der Auftrag

> **Betreiber, 2026-08-13:** *„so war das nicht gedacht, denk gross! mir geht
> es um die grundarchitektur"*

Es geht **nicht** um die Mac-App, nicht um den Editor, nicht um die
Plattformfrage im Kleinen. Es geht darum, was brainlehr im Kern ist und
welche Bauform daraus folgt.

## Der Grundgedanke des Betreibers, wörtlich

> *„für mich ist brainlehr die basis auf die gleichzeitig die verschiedensten
> domänen arbeiten können, ähnlich wie beim openlehr gedanken. Dazu könnte
> brainlehr ein regelwerk festlegen, wie andere domänen brainlehr nutzen
> können.*
>
> ***Grundgedanke: wir bauen keine tools die ki befähigen andere schon
> vorhandene tools zu benutzen, wir bauen software tools komplett neu, dass
> sie zusammen von ki und menschen bedient werden können!***
>
> *ganz zum schluss könnte dann brainlehr auch als community gehirn
> funktionieren, um zusammen neue brainlehr domänen zu entwickeln und zu
> pflegen"*

Dazu, zum Dokumenteneditor:

> *„wichtig ist nicht wysiwyg, wichtig ist dass zum schluss ein schönes
> dokument heraus kommt, deswegen latex, aber für word dummies benutzbar,
> oder bei rechnungserstellung (openlehr) per formularfelder. einmal eine
> basis die für alles mögliche wieder verwendet werden kann"*

Und zur Frage, ob das Modell die Dokumentstruktur ändern darf:

> *„das soll Entscheidung des menschen sein, gerne auch auf vorschlag des
> modells, und sollte offen gehalten werden!"*

---

## Warum der Grundgedanke keine These ist, sondern belegt

An einem einzigen Tag sind sechs Werkzeuge daran gescheitert, dass sie **für
Augen gebaut sind, nicht für Programme**. Jedes Mal mit Kosten:

| Werkzeug | Befund |
|---|---|
| Quick Look (macOS) | Kann weder aufschlagen noch hervorheben — **und meldet keinen Fehlschlag.** Eine erfundene Dateiendung wird angenommen und liefert ein Symbol, das von Erfolg nicht unterscheidbar ist |
| pdf.js in der buckeberg-Homepage | War monatelang tot (`vendor/pdfjs-viewer/build/` fehlte durch eine `.gitignore`-Zeile). Graue Fläche, keine Meldung. Kein Programm konnte es bemerken |
| `scripts/quellen_check.py` | Meldete „keine Fehler", während die Anzeige nichts zeigte — er prüfte die Daten, nicht die Darstellung |
| `textutil` | Lieferte bei PDFs die Rohbytes zurück und sah aus wie ein Ergebnis. Eine darauf gestützte Messung („29 von 29 haben eine Textschicht") hätte ein reines Scan-PDF genauso bestanden |
| `PDFMarkupType.redact` | Heißt „Redaktion" und malt nur ein Rechteck; der Text bleibt darunter lesbar |
| **Die eigene Mac-App** | Ihr Bedienungshilfen-Baum ließ sich nicht auslesen. Um das selbst gebaute Programm zu prüfen, mussten **Bildschirmabzüge** gemacht werden |

Der letzte Punkt ist der beweiskräftigste: Es wurde an einem Tag eine App
gebaut, die ihr Erbauer nicht programmatisch bedienen kann.

**Eine verwandte Regel steht bereits in den Hausregeln** (Walkthrough-Doktrin):
für native Apps eine „debug-only lokale Control-API für Kernaktionen + State-
Abfrage vorsehen, statt sich bei Verifikation auf UI-Automatisierung zu
verlassen". Dort ist sie als *Testhilfe* gedacht. Der Gedanke des Betreibers
dreht sie um: **die Programmschnittstelle ist nicht die Testhilfe, sondern die
eigentliche Oberfläche.**

---

## Gemessener Ist-Stand (2026-08-13)

### Der Verbund
- **46 Verzeichnisse** unter `/Volumes/daten/Begod2026/` — Domänen und
  Arbeitsbäume gemischt. `openlehr` (Steuer), `buckeberg` (WEG-Recht),
  `fahrtenbuch`, `wohlair`, `hub`, `brainlehr`.
- Wissensbestand: **2181 Knoten, 865 Lehren**, gemeinsam genutzt.

### Die Mac-App (heute gebaut)
| Schicht | Zeilen | Bindung |
|---|---|---|
| `BrainlehrCore` | 1648 | **ausschließlich `Foundation`** — keine Apple-Oberfläche |
| Tests | 1470 | hängen nur an Core, 134 XCTest-Fälle |
| `BrainlehrApp` | 2517 | SwiftUI, AppKit, PDFKit, QuickLook, CoreGraphics, Vision |

Dazu Python: `kern/fundstelle.py`, `kern/normfundstelle.py`,
`app/werkzeuge/pdf_schwaerzen.py`, `app/werkzeuge/lesbarkeit.py`,
`app/werkzeuge/ocr_stellen.swift`. 41 pytest-Fälle.

### Was heute DOPPELT existiert — der offene Nerv
| Fachlogik | Swift | Python |
|---|---|---|
| Fundstellen-Modell | `Fundstelle.swift` | `kern/fundstelle.py` |
| Lesbarkeitsrechnung | `Anzeigeform.swift` | `app/werkzeuge/lesbarkeit.py` |

Bisher billig, weil die **Zahlen** in einer gemeinsamen Datei stehen
(`app/Resources/lesbarkeit.json`) und nur die Formel zweimal existiert.
Bei einem Dokumentmodell mit Baum, Kennungen und Verschmelzung wäre dieselbe
Doppelung teuer.

### Was an Domänen-Regelwerk schon existiert
Ausweis mit Rollen (`kern/ausweis.py`) · Freigabe-Achse (`offen`/`intern`/
`gesperrt`) · Normschicht mit `norm_rang`, `gilt_ab`, `gilt_bis` · Fundstellen
mit Herkunft · Sichtbarkeit und echte Schwärzung (Text und PDF).

### Was gebaut, aber ungenutzt ist — gemessen
- `knowledge_nodes.access_count`: 96 % derselbe Wert
- `confidence`: praktisch ungenutzt
- `zurueckgezogen_grund` / `_von` / `_am`: **100 % leer**
- `gilt_bis`: 98 % leer
- `freigabe` im buckeberg-Quellenverzeichnis: existiert **gar nicht** (49 von
  49 ohne Angabe)

Das ist relevant, weil ein „Community-Gehirn" genau diese Felder als
Voraussetzung hätte.

---

## Vier Entscheidungen, die der Betreiber bereits getroffen hat

1. **brainlehr ist die Basis, Domänen docken an.** Ein Regelwerk soll
   festlegen, wie — aber (Vorschlag aus der Vorsitzung, nicht entschieden)
   erst nach der zweiten echten Domäne, sonst wäre es geraten.
2. **Neu bauen statt befähigen.** Vorgeschlagene Grenze, ebenfalls nicht
   entschieden: Formate und Rechenkerne werden benutzt (LaTeX, PDFKit,
   SQLite), Bedienoberflächen werden neu gebaut. Prüffrage im Einzelfall:
   *Kann ein Programm dieses Werkzeug fragen, ob es funktioniert hat?*
3. **Dokumentbasis mit domänenspezifischer Eingabeform** — Gliederung für
   Schriftsätze, Formularfelder für Rechnungen, LaTeX als gemeinsame Ausgabe,
   `tectonic` ist installiert.
4. **Struktur bleibt offen.** Änderungen an der Dokumentstruktur sind
   Vorschläge, die Entscheidung liegt beim Menschen. Technische Folge
   (vorgeschlagen): ein Dokument ist ein **Baum von Bausteinen mit stabilen
   Kennungen**, kein Text mit Leerzeilen — dann sind Inhalts- und
   Strukturänderung derselbe Vorgang.

---

## Die Fragen, um die es geht

Sie sind bewusst **ohne Antwortvorschlag** notiert.

1. **Was ist brainlehr im Kern?** Ein Wissensspeicher mit Aufsicht (so
   `docs/adr/ADR-026`), oder eine Plattform, auf der Domänen laufen? Beide
   Lesarten sind heute im Code vertreten.
2. **Wo lebt die Fachlogik?** Swift-Bibliothek, Python hinter einem Dienst,
   oder ein Schema, aus dem beides erzeugt wird? Die heutige Doppelung ist
   eine unentschiedene Frage, keine Bauform.
3. **Was heißt „von KI und Menschen bedienbar" konkret?** Eine Schnittstelle
   mit zwei Ansichten? Zwei Schnittstellen auf einem Kern? Und woran misst
   man, ob es erfüllt ist — gibt es eine Abnahme dafür?
4. **Was muss eine Domäne mitbringen, um anzudocken?** Die vier Fragen aus
   `brainlehr/CLAUDE.md` sind der Ansatz; Frage 3 („Was ist ein Treffer
   wert?") steht dort ausdrücklich als **offen** — eine falsche Rechtsauskunft
   kostet anders als ein falscher Funktionsname, heute gilt für beides die
   Schwelle 0,65.
5. **Welche Plattformen sollen getragen werden, und wann wird das
   entschieden?** Heute ist die Oberfläche Mac-gebunden; der Kern vermutlich
   nicht (nur `Foundation`, keine Apple-Typen — **nicht auf Linux gebaut,
   also nicht belegt**).
6. **Was ist die kleinste zweite Domäne, an der sich das Regelwerk beweisen
   muss?** Vorgeschlagen wurde openlehr-Rechnung, weil Formularfelder maximal
   anders sind als ein Schriftsatz.
7. **Community-Gehirn: welche Voraussetzungen fehlen?** Vertrauensstufen,
   Widerruf, Konfliktauflösung zwischen Domänen — die zugehörigen Felder
   existieren und sind messbar unbenutzt (siehe oben).

---

## Wie in dieser Sitzung gearbeitet werden soll

- **Erst denken, dann bauen.** Der Betreiber hat ausdrücklich gesagt: *„erst
  einmal planen und diskutieren!"*
- **Widerspruch ist erwünscht.** Er korrigiert scharf und erwartet dasselbe.
  An diesem Tag hat er mindestens sechs echte Fehler gefunden, darunter zwei
  Denkfehler in der Architektur.
- **Nichts behaupten, was nicht gemessen ist.** Wer nicht nachgesehen hat,
  sagt „ich habe nicht nachgesehen" — nicht „es gibt das nicht". Genau diese
  Regel wurde an diesem Tag zweimal verletzt und beide Male teuer.
- Die Hausregeln in `~/.claude/CLAUDE.md` und `brainlehr/CLAUDE.md` gelten
  unverändert. Lies zuerst `STAND.md` und
  `docs/adr/ADR-004-anzeige-waechst-mit-der-flaeche.md` — Letztere zeigt an
  einem Beispiel, wie eine Entscheidung hier begründet und wieder revidiert
  wurde.

## Was in dieser Sitzung NICHT passieren soll

- Kein Weiterbau an der Mac-App.
- Kein Docker (ausdrückliche Betreiberweisung 2026-08-13).
- Keine Agenten ohne Anlass — die Modell-Kaskade (Knoten `07fb68aa`) gilt:
  ein Agent je Aufgabe, Delegation nach unten, nicht drei zur Absicherung.
- Kein Regelwerk „auf Vorrat", solange die zweite Domäne nicht steht.
