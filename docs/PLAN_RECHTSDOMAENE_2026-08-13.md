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

## Block 1 · Gerichtsstand — belegt, und wozu er im Speicher taugt

**Amtsgericht Ettlingen, Landgericht Karlsruhe, Oberlandesgericht Karlsruhe.**
Belegt über zwei amtliche Quellen, nicht aus dem Gedächtnis:

- Der Bezirk des Amtsgerichts Ettlingen listet wörtlich „Gemeinde Karlsbad
  mit den Ortsteilen Auerbach, Ittersbach, Langensteinbach, Mutschelbach,
  Spielberg" —
  <https://amtsgericht-ettlingen.justiz-bw.de/pb/,Lde/1161739>, abgerufen
  2026-08-13.
- Der Bezirk des Landgerichts Karlsruhe listet das Amtsgericht Ettlingen
  unter seinen Amtsgerichten —
  <https://landgericht-karlsruhe.justiz-bw.de/pb/,Lde/Startseite/Landgericht/Bezirk%20-%20Amtsgerichte>,
  abgerufen 2026-08-13. Das Oberlandesgericht Karlsruhe folgt daraus nach
  dem allgemeinen Instanzenzug (§ 119 GVG), **nicht gesondert nachgeprüft** —
  Vermerk „ungeprüft".

**Zuständigkeit in WEG-Sachen — eigene Zuweisung, mit Paragraf.**
§ 43 WEG (gleichbedeutend: WoEigG, siehe `L-48d8c8`) weist Streitigkeiten aus
der Gemeinschaft der Wohnungseigentümer **ausschließlich** dem Amtsgericht
zu, in dessen Bezirk das Grundstück liegt — ohne Streitwertgrenze, nicht
abdingbar. Für ein Objekt in Auerbach-Karlsbad bleibt es damit bei Amtsgericht
Ettlingen, auch wenn ein allgemeiner Streitwert das sonst zum Landgericht
gehoben hätte. Quelle: § 43 WEG (Normtext, z. B.
<https://www.gesetze-im-internet.de/woeigg/__43.html>), **nicht** die
Sekundärzusammenfassungen aus der Suche — die sind hier nur als Fundhinweis
verwendet, der Normtext selbst trägt die Aussage.

**Ob Ettlingen WEG-Sachen konzentriert bearbeitet oder an ein anderes
Amtsgericht in Baden-Württemberg abgibt: ungeklärt.** Die Bezirksseite selbst
äußert sich dazu nicht; die eigene Navigation des Amtsgerichts Ettlingen führt
„Wohnungseigentum" als eigene Aufgabe unter „Sonstige" — das spricht gegen
eine Konzentration anderswo, ist aber kein Konzentrations- oder
Zuständigkeitstext. Eine Zuständigkeitskonzentrationsverordnung des
Justizministeriums Baden-Württemberg (ZuVOJu) wurde in der Suche nur als
Fundstelle genannt, ihr Text zu WEG-Sachen nicht gelesen. **Wer das braucht,
liest die ZuVOJu selbst** unter
<https://www.landesrecht-bw.de> (Suchbegriff „ZuVOJu") — hier nicht
nachgeholt, weil dieser Auftrag plant, nicht prüft.

**Wozu das im Speicher gut ist — und wozu nicht.** Materielles WEG-, Miet-
und Energierecht ist Bundesrecht und ändert sich durch den Gerichtsstand
**nicht um ein Wort**. Der Gerichtsstand ändert drei andere Dinge:

1. Er beantwortet die Verfahrensfrage „wo klage ich", die ein Nutzer mit
   einem konkreten Fall stellen kann — reiner Verfahrensinhalt, kein
   materielles Recht.
2. Er markiert den **Landesrecht-Filter**: Landesbauordnung BW,
   Landes-Klimaschutzgesetz BW, kommunale Satzungen Karlsbad/Landkreis
   Karlsruhe gelten nur, weil der Fall dort liegt — nicht wegen des Gerichts,
   sondern wegen desselben Orts, den auch das Gericht anhand des
   Belegenheitsprinzips (§ 43 WEG, § 29a ZPO) abbildet. Der Gerichtsstand ist
   hier ein **Indikator**, keine Rechtsquelle.
3. Er grenzt das lokale Förderprogramm-Universum ein (Block 2): Land
   Baden-Württemberg, Landkreis Karlsruhe, Gemeinde Karlsbad statt
   bundesweiter Auswahl.

**Ohne diese drei Verwendungen wäre der Gerichtsstand ein Ordnungsmerkmal
ohne Rechtsinhalt.** Er ist keins — er ist der Schlüssel, mit dem
Landesrecht und Förderprogramme später gefiltert werden, sobald diese Achse
existiert (vergleiche Block 3).

## Block 2 · Quellen je Thema — Bezugsweg und Lizenz

| Thema | Quelle | Bezugsweg | Lizenz |
|---|---|---|---|
| WEG-Recht | Wohnungseigentumsgesetz (WoEigG) | `gesetze-im-internet.de/woeigg/` | Amtliches Werk, § 5 Abs. 1 UrhG — frei, Volltext darf in den Speicher. |
| Mietrecht | BGB §§ 535–580a (Mietrecht) | `gesetze-im-internet.de/bgb/` | Amtliches Werk, § 5 Abs. 1 UrhG — frei. |
| WEG-Verwaltungsrecht | WoEigG §§ 18–29 (Verwaltung, Verwalter, WEMoG-Fassung) | `gesetze-im-internet.de/woeigg/` | Wie oben — frei. |
| Gebäudeenergie | GModG (vormals GEG) | `gesetze-im-internet.de/geg/` sowie Verkündungstext `recht.bund.de/bgbl/1/2026/226/VO.html` (BGBl. I 2026 Nr. 226, ausgegeben 28.07.2026) | Amtliches Werk — frei. Bereits als Knoten in `buckeberg/recht/` vorhanden, nicht neu zu holen. |
| Erneuerbare Energien | EEG (aktuelle Fassung) | `gesetze-im-internet.de/eeg_2014/` | Amtliches Werk — frei. |
| Förderung Bund | BAFA-Förderrichtlinien (BEG, Heizungsförderung) | `bafa.de`, Richtlinientext im Bundesanzeiger | **Richtlinientext** (im Bundesanzeiger veröffentlichte Verwaltungsvorschrift) vermutlich amtliches Werk, **nicht geprüft**. Die Erklär- und FAQ-Seiten von `bafa.de` sind Redaktionstext des Amts und **nicht** automatisch frei — Vermerk „ungeprüft". |
| Förderung Bund | KfW-Förderprogramme (energetische Sanierung, Neubau) | `kfw.de` | Merkblätter/Konditionen sind KfW-Redaktionstext, urheberrechtlich der KfW zuzuordnen — **nicht** ohne Prüfung übernehmen. |
| Förderung Land BW | L-Bank Wohnraumförderung, „Klimaschutz-Plus" | `l-bank.de` | Wie bei KfW — Redaktionstext, ungeprüft. |
| Förderung Landkreis Karlsruhe | **kein eigenes Förderprogramm des Landkreises gefunden** — nur die Klimaschutzstrategie „zeozweifrei 2035" ohne direkte Fördertöpfe, sowie das städtische „KlimaBonus Karlsruhe" der **Stadt** Karlsruhe (kreisfrei, nicht der Landkreis) | — | „ungeklärt" — hier steht keine Quelle, weil keine gefunden wurde, nicht weil sie ausgelassen wurde. |
| Förderung Gemeinde Karlsbad | **kein eigenes kommunales Förderprogramm gefunden** — nur Angaben zu vier „Energiequartieren" seit 2014 (`zeozweifrei.de/karlsbad/`) und einer kommunalen Wärmeplanung, keine Förderrichtlinie mit Zuschusshöhen | — | „ungeklärt" — bei Bedarf direkt bei der Gemeindeverwaltung Karlsbad erfragen. |
| Elektroinstallation | VDE-Normen (z. B. VDE 0100-Reihe) | VDE Verlag, `vde-verlag.de` | **Kostenpflichtig, urheberrechtlich geschützt.** VDE ist ein eingetragener Verein, kein amtliches Werk. Volltext **nicht** frei weitergebbar. |
| Wasserinstallation | DIN- und DVGW-Regelwerk (z. B. DIN 1988, DVGW W 551) | Beuth Verlag (`beuth.de`), wvgw-Shop | **Kostenpflichtig, urheberrechtlich geschützt** — auch wenn ein Gesetz (z. B. GModG) auf die Norm verweist, greift § 5 Abs. 3 UrhG: der Verweis macht die Norm **nicht** amtlich, er verpflichtet den Rechteinhaber nur zu angemessener Lizenzierung. |

**Zwei Quellen ausdrücklich verworfen, mit Grund:**

1. **„Landkreis Karlsruhe hat ein Klimaschutz-Förderprogramm"** — verworfen.
   Gefunden wurde nur die Klimaschutzstrategie zeozweifrei 2035 (Konzept,
   keine Fördertöpfe) und das städtische KlimaBonus-Programm der **Stadt**
   Karlsruhe, die als kreisfreie Stadt ein anderer Rechtsträger als der
   Landkreis Karlsruhe ist. Eine Verwechslung dieser beiden hätte im Speicher
   ein Förderprogramm für Karlsbad behauptet, das für Karlsbad nicht gilt —
   Karlsbad liegt im Landkreis, nicht in der Stadt Karlsruhe.
2. **Sekundärzusammenfassungen der Suchmaschine zum WEG-Gerichtsstand**
   (dejure/buzer/haufe-Kurztexte) — verworfen als Beleg für den
   Speicherinhalt selbst, nur als Fundhinweis auf den Normtext genutzt. Eine
   Zusammenfassung ist keine Fundstelle; § 43 WEG im Wortlaut ist es.

**Der harte Unterschied: amtliches Werk gegen kostenpflichtige Norm.**
Gesetzestexte sind nach § 5 Abs. 1 UrhG von Urheberrechtsschutz ausgenommen —
Volltext darf uneingeschränkt in den Speicher. VDE- und DIN-Normen sind
private Regelwerke privatrechtlicher Vereine; auch wenn ein Gesetz auf sie
verweist, bleiben sie geschützt (§ 5 Abs. 3 UrhG regelt nur eine
Lizenzierungspflicht des Rechteinhabers, keine Freistellung). **Für den
Speicher folgt daraus:** Fundstelle, Titel, Ausgabedatum und Bezugsweg dürfen
als Knoten geführt werden — der Normtext selbst nicht. Ein Knoten „VDE
0100-410, Ausgabe 2018-10, Schutz gegen elektrischen Schlag" mit Fundstelle
ist zulässig; der abgeschriebene Normtext ist es nicht.

**Förderprogramme ändern sich häufiger als Gesetze — Folge für die
Geltungsachse.** Ein BAFA- oder KfW-Programm hat typischerweise eine
Laufzeit von Monaten bis wenigen Jahren und wird durch Förderrichtlinien
novelliert, nicht durch Gesetzesverfahren — ohne feste Verkündungszyklen.
Ein Knoten zu einem Förderprogramm braucht darum `gilt_bis` **von Anfang an**
gesetzt (Programmlaufzeit lt. Richtlinie), nicht erst nachträglich wie bei
Gesetzen — sonst veraltet er schneller, als die Geltungsachse ihn nachführen
kann. Siehe Block 3.

## Block 3 · Die Geltungsachse je Quellenart

Aufgabe 88 lässt offen, **wer** `gilt_ab`/`gilt_bis` setzt und **woher** die
Werte kommen. Für diese Domäne, je Quellenart:

| Quellenart | Wer setzt `gilt_ab`/`gilt_bis` | Woher der Wert | Erkennungszeichen für falsch gesetzt |
|---|---|---|---|
| Gesetz (WoEigG, BGB, GModG, EEG) | Der Übernahmeschritt beim Einlesen, aus dem Verkündungstext | Inkrafttretensdatum lt. Verkündungsblatt (BGBl.), **nicht** das Ausfertigungs- oder Veröffentlichungsdatum — die drei fallen bei Novellen regelmäßig auseinander | `gilt_ab` liegt vor dem Verkündungsdatum, oder es fehlt trotz vorhandenem BGBl.-Verweis im Quelltext |
| Norm (VDE/DIN/DVGW) | Der Übernahmeschritt, aus dem Normkopf | Ausgabedatum der Norm (steht im Titel, z. B. „VDE 0100-410:2018-10") | `gilt_ab` ist das Datum des Einlesens statt das Ausgabedatum der Norm — verwechselt „wann wir es erfahren haben" mit „wann es galt" |
| Förderprogramm (BAFA/KfW/Land/Kreis/Gemeinde) | Der Übernahmeschritt, aus der Förderrichtlinie | Programmlaufzeit lt. Richtlinie (Start- **und** Enddatum stehen meist explizit drin) | `gilt_bis` fehlt, obwohl die Richtlinie ein Enddatum nennt — das ist bei Förderprogrammen der häufigste Fehler, weil man ihn bei Gesetzen nicht gewohnt ist |

**Die drei Zustände, die auseinandergehalten werden müssen:**

1. **gilt** — `gilt_ab` gesetzt, `gilt_bis` leer oder in der Zukunft.
2. **galt bis X** — `gilt_bis` gesetzt und in der Vergangenheit. Eine Abfrage
   von heute darf diesen Knoten nicht als geltend ausliefern.
3. **Geltung unbekannt** — weder `gilt_ab` noch eine verlässliche Quelle
   dafür vorhanden. **Das ist der Zustand, der heute bei 2095 von 2178
   Knoten vorliegt** (2178 minus 83 mit `gilt_ab`), und er fällt am
   häufigsten aus der Betrachtung, weil er wie „gilt" aussieht, solange er
   nicht als eigener Zustand geführt wird — ein leeres Feld wird sonst
   stillschweigend als „gilt uneingeschränkt" gelesen. Genau das war der
   Fehlerpfad in `L-2fa1e2`.

Ohne den dritten Zustand als **eigenen, abfragbaren Wert** (nicht: leeres
Feld) bleibt jede „gilt"-Antwort mehrdeutig zwischen „geprüft, gilt" und
„nie geprüft".

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

### Schritt D · Die Geltungsregel je Quellenart eintragen

| | |
|---|---|
| **Darf ändern** | `kern/` (neue Datei oder Erweiterung des Übernahmeschritts aus Schritt A), `tests/` (neue Datei) |
| **Fakten** | Block 3 dieses Plans legt fest, woher `gilt_ab`/`gilt_bis` je Quellenart kommt (Verkündungsdatum bei Gesetzen, Ausgabedatum bei Normen, Programmlaufzeit bei Förderungen) und benennt den dritten Zustand „Geltung unbekannt", der bei 2095 von 2178 Knoten vorliegt und heute nicht von „gilt" unterscheidbar ist. |
| **Abnahme** | Ein Förderprogramm-Knoten mit Enddatum in der Richtlinie liefert bei einer Abfrage nach Ablauf dieses Datums nicht mehr als geltend. Rot-Probe: derselbe Knoten muss vor dem Fix als „gilt" erscheinen, obwohl das Programm abgelaufen ist. Negativfall: ein Gesetzesknoten ohne erkennbares Verkündungsdatum wird als „Geltung unbekannt" markiert, nicht stillschweigend als „gilt". Grenzwert: der letzte Tag der Programmlaufzeit selbst — dieselbe Festlegung wie in Schritt A für `gilt_bis` gilt hier bindend mit, keine zweite Antwort für dieselbe Frage. |
| **Einsatz** | Block 2 zeigt, dass Förderprogramme sich schneller ändern als Gesetze — ohne diese Regel wird ausgerechnet der volatilste Teil der Domäne am unzuverlässigsten geführt. |

### Schritt E · Quellen mit Lizenzstatus registrieren, bevor Volltext einläuft

| | |
|---|---|
| **Darf ändern** | `pflege/` (neue Datei), `tests/` (neue Datei) |
| **Tabu zusätzlich** | Kein Volltext von VDE-, DIN- oder DVGW-Normen im Speicher — nur Fundstelle, Titel, Ausgabedatum, Bezugsweg (Block 2). Kein Netzabruf ohne gesondertes Wort des Betreibers. |
| **Fakten** | Block 2 unterscheidet amtliche Werke (§ 5 Abs. 1 UrhG, Volltext frei) von privaten Normen (§ 5 Abs. 3 UrhG, nur Lizenzierungspflicht, kein Freibrief) und listet je Thema Bezugsweg und Lizenzstatus, davon zwei Quellen ausdrücklich verworfen (Verwechslung Landkreis/Stadt Karlsruhe; Sekundärzusammenfassungen statt Normtext). |
| **Abnahme** | Ein Versuch, einen VDE-Normtext im Volltext einzulesen, wird vom Übernahmeschritt zurückgewiesen und nur als Metadaten-Knoten geführt. Rot-Probe: vor dieser Sperre lässt der bestehende `kern/fremdimport.py`-Pfad (Projektion statt Filterung, Schritt B) jeden Text unbesehen durch. Negativfall: ein WoEigG-Paragraf mit Volltext geht unverändert durch, weil er ein amtliches Werk ist. |
| **Einsatz** | Ein kostenpflichtiger Normtext im frei zugänglichen Speicher ist kein Planungsdetail, sondern ein Lizenzverstoß — und einer, der sich nicht durch „war doch nur intern" heilen lässt, sobald der Speicher geteilt wird. |

### Schritt F · Gerichtsstand als Landesrecht- und Förderfilter eintragen

| | |
|---|---|
| **Darf ändern** | `kern/` oder `pflege/` (neue Datei), `tests/` (neue Datei) |
| **Fakten** | Block 1 belegt Amtsgericht Ettlingen / Landgericht Karlsruhe für Karlsbad-Auerbach und leitet daraus ab, dass der Gerichtsstand kein Rechtsinhalt ist, sondern ein Indikator für den anzuwendenden Landesrecht- und Förderprogramm-Filter (Land Baden-Württemberg, Landkreis Karlsruhe, Gemeinde Karlsbad). Für die WEG-Zuständigkeit gilt zusätzlich § 43 WEG als eigene, streitwertunabhängige Zuweisung. |
| **Abnahme** | Ein Förder- oder Landesrecht-Knoten trägt ein Feld, das ihn auf „Land Baden-Württemberg" / „Landkreis Karlsruhe" / „Gemeinde Karlsbad" einschränkt, und eine Abfrage ohne diesen Ortsbezug liefert ihn nicht als bundesweit geltend aus. Rot-Probe: vor dieser Änderung wäre ein Landesrecht-Knoten ununterscheidbar von einem Bundesrecht-Knoten. Negativfall: ein Bundesgesetz (WoEigG, BGB, GModG, EEG) trägt **kein** Ortsfeld und bleibt bundesweit gültig — die Einschränkung gilt nur für originär landes-/kommunalrechtliche Knoten. |
| **Einsatz** | Ohne diesen Filter würde ein Förderprogramm der Stadt Karlsruhe (KlimaBonus) für ein Objekt in Karlsbad als anwendbar erscheinen — genau die Verwechslung, die Block 2 als ersten verworfenen Fund benennt. |

**Reihenfolge, bindend:** Schritt A (Geltungsachse trägt) vor D (Regel je
Quellenart) vor B (13 Dateien überführen) — eine Regel ohne tragfähige Achse
ist folgenlos. Schritt E steht **vor** jedem Volltextimport, auch vor einem
künftigen Import von Gesetzestexten, weil sie denselben Übernahmeschritt
durchläuft und die Sperre sonst nachträglich in bereits eingelesene Knoten
hineinredigiert werden müsste. Schritt F setzt Block 1 voraus, ist aber von
B, C, D unabhängig und darf parallel dazu laufen. Schritt C (Suche nach
Sachbegriff) entwertet nichts und wird von nichts entwertet — unabhängig
einsetzbar.

**Erfolgsmaß für den gesamten Block, vorher rot:** Eine Abfrage nach einem
Förderprogramm für ein Objekt in Karlsbad-Auerbach liefert ausschließlich
Programme, die für Karlsbad, den Landkreis Karlsruhe, das Land
Baden-Württemberg oder den Bund gelten — nicht das KlimaBonus-Programm der
Stadt Karlsruhe. Vor Schritt F ist das rot: der Speicher träfe heute keine
Unterscheidung, weil kein Ortsfeld existiert.

**Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.**
