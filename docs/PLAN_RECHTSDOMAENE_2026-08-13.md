# Rechtsdomäne: WEG, Miete, Verwaltung — und was daran anschließt

Angelegt 2026-08-13T19:25:00+0200. Anlass ist die Betreiberfrage nach den
Themen *WEG-Recht, Mietrecht, WEG-Verwaltungsrecht* und den anschließenden
*erneuerbaren Energien, Förderungen, Elektro- und Wasserinstallation*.

## Der gemessene Ist-Stand — und die Überraschung darin

**Der Bestand existiert bereits, er steht nur am falschen Ort.**
`/Volumes/daten/Begod2026/buckeberg/recht/` trägt 13 Dateien mit 691 Zeilen,
handkuratiert, genau in dieser Domäne:

| | |
|---|---|
| Verwaltung | Verwalterbestellung, Verwaltervertrag, Verwalterwechsel, zertifizierter Verwalter, Übergabe der Unterlagen |
| Abrechnung | Jahresabrechnung beim Wechsel, Betriebskosten vermieteter Wohnungen, Verursacherprinzip |
| Versammlung | Eigentümerversammlung Formalia, Selbstverwaltung und Notlösungen |
| Versicherung | Gebäudeversicherung und Sondereigentum |
| Energie | Gebäudemodernisierungsgesetz 2026 |

In brainlehr dagegen: `WoEigG` **0** Treffer, `Mietrecht` **0**, `Förderung`
**0**, `Photovoltaik` **0**, `Wärmepumpe` **0**. `WEG` 38 und `GEG` 85 — das
sind Verwaltungs- und Projektknoten, nicht der Rechtsstoff.

**Die Dateien sind bereits in der richtigen Form geschrieben.** Der
GModG-Knoten trägt Rang, Verkündungsblatt, Datum des Inkrafttretens und den
Wortlaut der Inkrafttretensregel. Das ist genau, was die Normachsen von
brainlehr aufnehmen — es müsste nichts erfunden, nur überführt werden.

## Die eigentliche Lücke ist nicht der Stoff, sondern die Geltung

| Spalte | gefüllt von 2178 |
|---|---|
| `gilt_ab` | 83 |
| `gilt_bis` | **2** |
| `norm_rang` | 83 |

Bei Recht ist das der Unterschied zwischen brauchbar und gefährlich. Ein
Gesetzestext altert **still**: Der Speicher liefert weiterhin den alten Satz,
und nichts an der Antwort verrät, dass er nicht mehr gilt.

Wir haben den Fehler bereits gemacht, am 2026-08-12 (`L-2fa1e2`): Aus der
Streichliste des Gebäudemodernisierungsgesetzes wurde geschlossen, auch § 47
GEG sei entfallen. Die Nummer stimmte, der Inhalt nicht — die Nachrüstpflicht
für die oberste Geschossdecke steht unverändert in § 35 GModG. Für das
betroffene Objekt war das der Unterschied zwischen *„Dämmung ist freiwillig"*
und *„Dämmung ist Pflicht"*.

**Daraus die bindende Reihenfolge:** Die Geltungsachse muss tragen, **bevor**
der erste Paragraf eingelesen wird. Nachträglich lässt sich nicht
rekonstruieren, welche Fassung beim Einlesen galt. Das gilt bei dreizehn
Dateien wie bei dreizehntausend — es ist die Reihenfolge, nicht die Menge.
Aufgabe 88 ist damit keine Aufräumarbeit mehr, sondern die Sperre davor.

## Die Alternativen, samt Ablehnungsgrund

1. **Gesetzestexte im Volltext holen und ablegen.** Abgelehnt als erster
   Schritt: Ohne Geltungsachse entsteht ein Bestand, der still veraltet, und
   die Menge macht den Fehler unauffindbar. Außerdem ein Netzabruf — braucht
   das Wort des Betreibers.
2. **Nur die buckeberg-Dateien überführen, Geltung später.** Abgelehnt aus
   demselben Grund, nur kleiner. Dreizehn falsch datierte Knoten sind
   schwerer zu finden als keine.
3. **Gewählt: erst die Geltungsachse tragfähig machen, dann die dreizehn
   vorhandenen Dateien überführen, dann erst fremde Volltexte.** Der
   vorhandene Bestand ist zugleich der beste Prüfstein für die Achse — er
   enthält mit dem GModG einen Fall, in dem ein Gesetz umbenannt wurde und
   Paragrafen umgezogen sind.

## Was bewusst nicht getan wird, samt Preis

- **Kein Netzabruf in diesem Plan.** Preis: Der Bestand bleibt auf das
  beschränkt, was schon im Haus ist. Grund: Ein Download von außen ist keine
  autonome Handlung.
- **Keine Förderdatenbank.** Preis: Die Anschlussthemen des Betreibers
  (Förderungen, Elektro, Wasser) bleiben vorerst unbelegt. Grund:
  Förderprogramme ändern sich häufiger als Gesetze — ohne Geltungsachse wäre
  das der Bestand, der am schnellsten falsch wird.

## Woran sich Erfolg misst

Eine Abfrage nach einem Paragrafen, der seit dem 29.07.2026 umgezogen ist,
liefert die **geltende** Fundstelle oder schweigt — sie liefert nicht
stillschweigend die alte. Vorher rot, nachher grün.

## Aufträge, fertig zum Übergeben

| | |
|---|---|
| **Tabu für alle Schritte** | `/Volumes/daten/Begod2026/buckeberg/` wird nur **gelesen** — fremdes Repo. Ebenso tabu: `app/`, `berichte/`, `pflege/`, `~/.claude/`. Kein Netzabruf. |

### Schritt A · Die Geltungsachse tragfähig machen

| | |
|---|---|
| **Darf ändern** | `kern/` (neue Datei), `tests/` (neue Datei) |
| **Fakten** | `gilt_bis` ist bei 2 von 2178 Knoten gefüllt, `gilt_ab` bei 83, `norm_rang` bei 83. Der Prüfer meldet diese Spalten seit Tagen als „gebaute Regel ohne Wirkung — Spalte unterscheidet nichts". Aufgabe 88 hält fest, dass Zeit und Geltung Spalten sind, keine Achse. |
| **Abnahme** | Eine Abfrage mit Stichtag liefert nur, was an diesem Tag galt. Rot-Probe: ein Knoten mit `gilt_bis` in der Vergangenheit darf bei einer Abfrage von heute nicht erscheinen, bei einer Abfrage zum damaligen Stichtag schon. Negativfall: ein Knoten ohne `gilt_bis` erscheint immer. Grenzwert: der Tag des `gilt_bis` selbst — gilt er noch oder nicht? Die Antwort wird festgelegt und geprüft, nicht offengelassen. |
| **Einsatz** | Ein Rechtssatz, der still veraltet, ist schlimmer als keiner: Er wird geglaubt. Am 2026-08-12 hing daran der Unterschied zwischen freiwilliger und pflichtiger Dämmung. |

### Schritt B · Die dreizehn vorhandenen Dateien überführen

| | |
|---|---|
| **Darf ändern** | `pflege/` (neue Datei), `tests/` (neue Datei). `buckeberg/recht/` nur lesen. |
| **Fakten** | 13 Dateien, 691 Zeilen, in `/Volumes/daten/Begod2026/buckeberg/recht/`. Der GModG-Knoten trägt bereits Rang, Verkündungsblatt (BGBl. I 2026 Nr. 226), Datum der Ausgabe (28.07.2026) und den Wortlaut der Inkrafttretensregel. `kern/fremdimport.py` arbeitet nach Projektion statt Filterung und ist die vorhandene Bauform. |
| **Abnahme** | Jeder überführte Knoten trägt `gilt_ab`, `norm_rang` und eine Fundstelle. Rot-Probe: ein Knoten ohne Fundstelle wird abgewiesen und namentlich genannt. Negativfall: der GModG-Knoten mit vollständiger Fundstelle geht durch. Grenzwert: eine Datei ohne jedes Datum — sie darf nicht mit einem geratenen Datum durchrutschen, sondern muss gemeldet werden. |
| **Einsatz** | Der Stoff ist bereits geschrieben und liegt ungenutzt. Er ist zugleich der ehrlichste Prüfstein für Schritt A, weil er mit dem GModG einen echten Umzugsfall enthält. |

### Schritt C · Die Suche nach dem Gegenstand, nicht nach der Nummer

| | |
|---|---|
| **Darf ändern** | `tests/` (neue Datei) |
| **Fakten** | `L-2fa1e2`, gemessen 2026-08-12: Aus einer Streichliste wurde auf den Wegfall einer Pflicht geschlossen; weggefallen war nur die Paragrafennummer. Der Inhalt steht in § 35 GModG. `L-48d8c8`: Das Wohnungseigentumsgesetz liegt auf gesetze-im-internet.de unter `/woeigg/`, nicht unter `/weg/` — geratene Abkürzungen laufen ins Leere. |
| **Abnahme** | Eine Suche nach dem Sachbegriff („Nachrüstung oberste Geschossdecke") findet den geltenden Knoten, auch wenn sich die Paragrafennummer geändert hat. Rot-Probe: Suche nach der alten Nummer allein darf nicht die alte Fassung als geltend ausgeben. |
| **Einsatz** | Eine Novelle verschiebt Inhalte, ohne sie zu streichen. Wer nach Nummern sucht, meldet Pflichten als entfallen, die weiter gelten. |

**Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.**
