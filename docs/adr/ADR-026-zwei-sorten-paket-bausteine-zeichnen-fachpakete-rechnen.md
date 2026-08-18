# ADR-026: Zwei Sorten Paket — Bausteine zeichnen, Fachpakete rechnen

    cd /Volumes/daten/Begod2026/brainlehr

Status: **Angenommen** (Betreiberentscheidung 2026-08-18T17:05:00+0200)
Bezug: ADR-013 (eine Domäne ist ein Repo mit drei Teilen), ADR-014 (was ins
Atelier gehört), ADR-016 (Tabellenkalkulation als Bestandteil), ADR-024 (V1 ist
nativ, die Beschreibung bleibt plattformblind)
Lastenkatalog: `docs/REQUIREMENTS_INTERFACE_KOMPAT.md`, `INT-BST-001` bis `-003`

## Anlass

Betreiberfrage vom 2026-08-18, wörtlich:

> „also sprich den dokumenten scanner mit ocr usw vom openlehr_einzelunternehmer
> dem es im legacy schon gibt, kann ich dann übers atellier für jede weitere
> domäne mitbenutzten? dann müsste openlehr_X sagen: ich bin openlehr_X ich
> brauche das paket: dokumentenscanner und das paket: tabelle einzeigen, bitte
> neuste stable version downloaden?"

Die Frage wirft zwei Dinge zusammen, die verschieden sind. Die Antwort ist
zweimal ja — aber über zwei verschiedene Wege, und ein gemeinsamer Weg wäre ein
Sicherheitsloch.

## Entscheidung

**Es gibt zwei Sorten anforderbarer Teile, und sie werden nie über denselben
Mechanismus geliefert.**

### Sorte 1 — Darstellungsbaustein (zeichnet)

Beispiele: Tabelle, Dokumentfenster, Tabellenkalkulation, künftig Eingabefeld,
Ablagefeld, Diagramm.

- Lebt **im Atelier**, in Swift, wird mit dem Atelier ausgeliefert.
- Die Domäne fordert ihn im eigenen Paket über das Feld `bestandteile` an.
- Der Katalog ist **geschlossen** (`BrainlehrCore/BestandteilRegistry.swift`,
  Gegenstück `kern/bestandteile.py`). Eine Domäne wählt daraus; sie kann ihn
  nicht erweitern.
- **Keine Version, kein Nachladen.** Der Baustein gehört zum Atelier, nicht zur
  Domäne.

### Sorte 2 — Fachpaket (rechnet, liest, erkennt)

Beispiele: Dokumentenerkennung mit OCR, Bankabgleich, E-Rechnungs-Erzeugung.

- Lebt **auf der Domänenseite**, in Python, als eigenständiges Paket.
- Wird eingebunden wie jede Bibliothek, **mit Version** (SemVer-Major, dieselbe
  Regel wie `contract_version` aus `INT-VER-001`).
- Zeichnet nichts. Es liefert Daten; wie sie aussehen, entscheidet Sorte 1.

## Warum nicht ein gemeinsamer Mechanismus

Der naheliegende Entwurf ist genau der aus der Betreiberfrage: eine Liste
angeforderter Pakete, alle mit Version, alle nachladbar. Verworfen, aus einem
Grund, der nichts mit Bequemlichkeit zu tun hat:

**Ein Darstellungsbaustein läuft IM Atelier.** Dürfte ein Domänenpaket ihn
benennen und nachladen lassen, könnte jedes importierte Paket beliebigen Code in
die Anwendung holen, die alle anderen Domänen mitbenutzen. Genau davor steht die
Auflage in `BestandteilRegistry.swift` bereits geschrieben: *„eine Domäne kann
sich damit KEINE Rechte selbst geben."* Und ADR-016 hatte den Fremddatei-Import
aus demselben Grund gesperrt, bis er gemessen war.

Ein Fachpaket dagegen läuft **im Dienst der Domäne**, im selben Vertrauensraum
wie deren eigener Code. Dort ist eine Version die richtige Antwort, kein Risiko.

Die Trennlinie ist also nicht ästhetisch, sondern eine Vertrauensgrenze: *Läuft
das Ding im Atelier oder im Dienst der Domäne?*

## Zweite verworfene Alternative

**Den Scanner als Atelier-Bestandteil bauen** (also Sorte 1). Verworfen: Er
zeichnet nichts, er erkennt Text. Als Swift-Baustein müsste die OCR-Fähigkeit in
die Anwendung wandern und stünde dort auch Domänen zur Verfügung, die sie nie
angefordert haben. Außerdem wäre sie in Swift neu zu schreiben — der vorhandene
Code ist Python.

## Was das für den vorhandenen Scanner heißt

Gemessen 2026-08-18 in `openlehr_einzelunternehmer`:
`apps/openlehr/daemon/steuer/ingest.py` hat 2420 Zeilen, davon nennen 273
ausdrücklich Steuer, Beleg, USt oder EUR; `gemma4_ocr_bridge.py` hat 386 Zeilen
und ruft ein lokales Modell. Abhängigkeiten fast ausschließlich Standardbibliothek.

Er ist damit **heute nicht wiederverwendbar** — er ist ans Steuer-Paket gebunden.
Für Sorte 2 muss er entlang seiner eigenen Naht geschnitten werden:

- **allgemein**: Datei rein → Text, Felder, Beträge, Herkunft raus
- **fachlich**: was davon ist eine Betriebsausgabe

Der Schnitt fällt **einmal** an und trägt danach jede weitere Domäne.

## Folgen

- `BestandteilRegistry` bleibt geschlossen und wächst nur durch Arbeit am Atelier.
- Ein Fachpaket bekommt eine eigene Version und einen eigenen Vertragstest.
- Eine Domäne, die zeichnen will, was der Katalog nicht kennt, ist ein
  **Befund über den Katalog**, keine Erlaubnisfrage — sie meldet einen fehlenden
  Baustein an, statt ihn mitzubringen.

## Was ausdrücklich NICHT entschieden ist

- Der Schnittpunkt des Scanners im Einzelnen (welche Funktionen allgemein sind).
- Wo geteilte Fachpakete liegen — eigenes Repo, Unterverzeichnis, Paketregister.
- Ob es je ein Nachladen für Sorte 2 zur Laufzeit gibt; heute reicht Einbinden
  zur Bauzeit.
