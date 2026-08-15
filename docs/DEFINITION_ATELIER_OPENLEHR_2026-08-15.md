# Was soll wo können — atelier, openlehr, brainlehr

**Stand** 2026-08-15T21:00:00+0200
**Zweck** Übergabe an ein frisches Kontextfenster. Diese Sitzung läuft seit 05:44
und ist zu lang, um die Frage sauber zu Ende zu bringen.
**Anlass** Betreiber: *„im atelier finde ich es noch nicht"* — und danach:
*„aber das original openlehr könnte ja noch viel mehr!"* sowie *„wir wollten das
excel like machen!"*

## Die Frage, die zu entscheiden ist

Nicht *was soll gebaut werden* — sondern **was von dem, was es gibt, gehört
wohin.** Der Fehler dieser Sitzung war, eine Anwendung zu entwerfen, die
existiert.

## Der gemessene Stand, nicht der vermutete

| | |
|---|---|
| Bestand brainlehr | 4930 Knoten (2217 + 2713 GermanQuAD), 6626 Vektoren |
| Steuerpaket | `pakete/steuer.domaene.json` — 3 Quellen, 4 Regeln |
| Import in den Bestand | **meldet Erfolg, schreibt nichts** — Endpunkt ruft `pruefe()` statt `speichere()`; wird gerade behoben |
| Weg in der Oberfläche | **keiner** — nur ein Menübefehl „Domäne importieren…", ⌘⇧I, kein Bildschirm |
| `setze_in_kraft()` | existiert, **kein Aufrufer im ganzen Repo** |
| openlehr Fachlogik | umfangreich, Umfang **nicht erhoben** — die Messung wurde von der Wiederverwendungs-Wache abgewiesen und ist offen |

## Was bereits entschieden ist und nicht neu verhandelt wird

**ADR-016 — die Tabellenkalkulation.** Betreiber wörtlich: *„nein ich will genau
das ein excel im atelier auf betriebsystem ebene!"* Begründung, die trägt: **Eine
Formel ist eine sichtbare Belegkette.** Was der Torwächter erzwingen soll — eine
Summe kommt nur durch, wenn sie ihre Summanden mitliefert — ist in einer Tabelle
die Normalform. EÜR und UStVA stecken heute in Funktionen; als Tabelle wird die
Rechnung **prüfbar statt versteckt**, auch für einen Berater oder eine Behörde.
Und: *Der Betreiber rechnet selbst, ohne dass jemand Code baut.*
**Stand:** Positivliste scharf (37 von 511 Funktionen, als Mengengleichheit gegen
die laufende Rechenmaschine belegt), Import fremder Dateien entsperrt, Anmeldung
als Bestandteil auf beiden Seiten. **Es fehlt der Bildschirm.**

**ADR-016 Auflage 4 — benannte Bereiche sind Pflicht.** `=SUMME(erloese)*ust_satz`
statt `=SUMME(B2:B47)*C1`. Ein Zellbezug ist eine Adresse ohne Bedeutung; ein
Mensch liest sie aus der Nachbarschaft, ein Modell muss sie raten. Jetzt kostenlos,
nach dem ersten Blatt eine Migration.

**ADR-014 — die Trennlinie.** Ins atelier gehört, was **alle** Domänen gemeinsam
haben oder was **keine über sich selbst entscheiden darf**. Eine Rechnungsnummer
ist Steuersache. Ein Dokumentfenster ist es nicht. Diese Linie ist wichtiger als
jede Vollständigkeit.

**ADR-018 — Wirkung Null.** Eingelesene Regeln treten **nicht von selbst** in
Kraft. Ein Gesetzestext ist eine Norm der Welt, keine Norm dieses Hauses, solange
niemand sie in Kraft setzt. **Folge, die heute sichtbar wurde:** Ein Paket kann
vollständig importiert und trotzdem wirkungslos sein — und der Betreiber erkennt
den Unterschied nicht, weil ihn nichts anzeigt.

**H12 — Blaupause statt Herauslösung.** openlehr wird **gelesen**, nicht kopiert
und nicht weggeworfen. Begründung des Betreibers: *„der vorhandene Code ist ja auch
Wissen"* — `router.py` ist wertvoll, weil es die feldgeprüfte Liste der Anforderung
ist, genauer als jedes Pflichtenheft, weil unter Druck entstanden.

## Was das frische Fenster zuerst tun sollte

**1. Erheben, was openlehr kann — in drei Stufen, streng getrennt.**
Fachlogik vorhanden · über einen Endpunkt erreichbar · von einem Bildschirm aus
bedienbar. **Von den Routen ausgehen, nicht von einer Liste aus dem Gedächtnis.**
Eine Fähigkeit auf Stufe 1 ohne Stufe 2 ist keine Fähigkeit, sondern eine
Bibliothek — das hat hier schon zweimal Geld gekostet (`L-b38d85`).

**2. Je Fähigkeit die Trennlinie ziehen (ADR-014), nicht den Aufwand schätzen.**
Gehört sie ins atelier, bleibt sie in openlehr, oder ist sie ein Bestandteil, den
mehrere Domänen anfordern? Die Art der Lücke ist belastbar, eine Aufwandsschätzung
wäre es nicht.

**3. Erst danach bauen — und der erste Bildschirm ist vermutlich die Tabelle**,
weil sie beschlossen, gemessen und entsperrt ist und weil sie den Belegvertrag
sichtbar macht.

## Die offene Frage, die niemand entschieden hat

**Wer setzt eine Regel in Kraft, und woran erkennt man es später?**
`setze_in_kraft()` existiert seit Tagen und wird nirgends gerufen. Ein Knopf allein
genügt nicht: Inkraftsetzen ist eine **Entscheidung**, und ADR-018 hat den Vorrat
bewusst von der Wirkung getrennt. Erkennbar muss bleiben, **wer** entschieden hat —
sonst ist die Trennung eine Formalie.

## Was in dieser Sitzung noch läuft und nicht angefasst werden darf

- `kern/embeddings.py` und der Suchpfad — Kanalgüte, `docs/PLAN_KANALGUETE_2026-08-15.md`
- `berichte/entscheidungen_server.py` und `app/Sources/Atelier/` — Domänenimport

## Warnung an das nächste Fenster

Fünfmal wurde heute ein Agent auf etwas angesetzt, das bereits gebaut war
(`L-229bb2`). Die Ursache war jedes Mal dieselbe: dem Plan geglaubt statt dem
Repo. **Vor jedem Bauauftrag eine Existenzprobe am Code, gesucht nach der Sache und
nicht nach der Kennung.** Der Satz, der in allen fünf Fällen gerettet hat, gehört
in jeden Auftrag: *„Sieht der Code anders aus als hier beschrieben, halte dich an
den Code und melde die Abweichung."*
