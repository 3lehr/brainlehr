# brainlehr 0.1.0

**Ein Wissensspeicher, der sich meldet.**

Übliche Speicher warten auf eine Frage und liefern ähnlichen Text. brainlehr tut
fünf Dinge, die ein Archiv nicht tut:

- **Es meldet sich ungefragt.** Bei jeder Antwort prüft es, ob darin ein Gesetz,
  eine Norm oder eine interne Kennung zitiert wird — und ob dafür ein Beleg im
  Bestand liegt. Fehlt er, sagt es das.
- **Es schlägt vor, was fehlt.** Wiederkehrende Handgriffe werden zu
  Werkzeugvorschlägen samt fertigem Auftrag. Wiederholt sich eine Fehlerklasse
  dreimal, wird sie von selbst zur Regel.
- **Es widerspricht.** Ein Eintrag ohne nachprüfbare Herkunft entsteht gar nicht
  erst — das erzwingt ein Datenbank-Trigger, nicht eine Konvention.
- **Es kennzeichnet fremden Text als Daten.** Nicht per Wortliste (die ist
  prinzipiell unvollständig), sondern durch die Darstellung selbst.
- **Es misst sich selbst.** Trefferquote, Nutzen, Rangfolge — gegen einen fremden
  Prüfkorpus, blind bewertet. Die Zahlen fallen regelmäßig schlecht aus; das ist
  der Zweck.

Läuft als **MCP-Server** auf SQLite — damit an jedem MCP-fähigen Klienten:
Claude Code und Desktop, Codex, [Hermes](https://hermes-agent.nousresearch.com/)
oder einem eigenen. *Offline* meint den **Speicher**, nicht das Modell:
Datenbank, Volltextindex und Vektoren bleiben auf dem Gerät. Welches Modell
davor sitzt, ist deine Wahl — auch ein gehostetes, es sieht nie mehr, als der
Klient ihm schickt.

> **Fassung 0.1.0.** Die führende Null ist die Aussage: keine stabile
> Schnittstelle, keine Zusage zur Aufwärtskompatibilität. Was funktioniert, ist
> belegt — was zugesagt wird, ist nichts.
>
> **Nächster Stand.** Die Arbeit ruht bis heute Abend, 2026-08-10T23:00+02:00.
> Danach entsteht voraussichtlich 0.1.1 — voraussichtlich, weil auch das keine
> Zusage ist.

---

## Wofür das gut ist

Ein Sprachmodell vergisst zwischen zwei Sitzungen alles. Übliche Abhilfen legen
Text in eine Vektordatenbank und holen ihn ähnlichkeitsbasiert zurück. Das
beantwortet „worüber haben wir gesprochen" — aber nicht:

- **Wer** hat das behauptet, und wurde es je geprüft?
- Gilt es **noch**, oder ist es abgelöst?
- Was, wenn **zwei Einträge sich widersprechen**?
- **Wirkt** der Speicher überhaupt, oder liefert er nur Treffer?

brainlehr beantwortet diese vier Fragen mit Feldern und Messungen statt mit
Zuversicht.

## Schnellstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

sqlite3 knowledge.db < schema.sql
sqlite3 knowledge.db < herkunft_unveraenderlich.sql

# Beispielbestand einspielen (1.733 Einträge, NASA-LLIS + Methodik)
python3 brainlehr.py rein auszug-offen/bestand.jsonl --db knowledge.db

# Selbsttests der Kernmodule — brauchen KEINE Abhängigkeiten
python3 kern/ausweis.py --selftest
python3 kern/werkzeugrechte.py --selftest
python3 kern/normbezug.py --selftest

# als MCP-Server starten (stdio)
python3 knowledge_mcp_server.py
```

Ab hier ist die Volltextsuche benutzbar. Vektoren sind bewusst nicht
mitgeliefert und werden bei Bedarf selbst gerechnet — Begründung und Befehl in
[`docs/AUFBAU.md`](./docs/AUFBAU.md).

## Was wirklich drin ist

| | |
|---|---|
| **Herkunft** | `source` ist Pflichtfeld per Datenbank-Trigger, Herkunftsfelder sind nach dem Schreiben unveränderlich |
| **Geltung** | `norm_rang`, `gilt_ab`/`gilt_bis` und eine ausdrückliche Norm-Entscheidung **ohne** Vorgabewert |
| **Identität** | Ausweis mit scrypt; ohne ihn trägt jede Zuschreibung dauerhaft `unbeglaubigt:` — Identität lässt sich nicht mehr im Aufruf behaupten |
| **Zwei Sorten Wissen** | Knoten tragen Sachverhalte, Lehren tragen Fehlerklassen samt Ursache, Behebung, Vermeidung |
| **Hybride Suche** | FTS5 inkl. Trigramm plus lokale Vektoren (bge-m3), per RRF verschmolzen — alles auf dem Gerät |
| **Assoziative Kanten** | verstärkt, was gemeinsam abgerufen wird; eine Kante heißt „kam zusammen vor", nicht „hängt zusammen" |
| **Zugriffsprotokoll** | jeder Lese- und Schreibvorgang in `access_log`, per SHA-256 verkettet — Änderung wird nachweisbar, nicht verhindert |

## Acht Fälle, mit Fundstelle

Acht Vorgänge, je mit Zeitpunkt, Fundstelle und beteiligtem Modell.
Angaben, die nicht festgehalten wurden, sind als solche benannt.

<details>
<summary><b>1. Eine Lehre aus Python half vier Stunden später in Dart</b> — anderes Projekt, andere Sprache, dieselbe Fehlerform</summary>

- **Wann:** aufgezeichnet 2026-08-01T08:47, eingespielt 2026-08-07T11:34:22, angewandt 2026-08-07T15:50 (+02:00)
- **Beteiligtes Modell:** `claude-opus-5`
- **Fundstelle:** Knoten `5eca513a`, Lehre `L-0968ae`, Einspielung protokolliert in `recall_log.jsonl`

In **openlehr** (Python) fing eine Route jeden Fehler in einem `try/except` ab
und gab ihn nur als Warnung aus, die kein Test und keine Oberfläche liest —
stiller Datenverlust im Betrieb. Sechs Tage später spielte der Abruf-Hook diese
Lehre in eine Sitzung ein, in der an **wohlair** (Dart/Flutter) gearbeitet
wurde. Vier Stunden danach traf sie auf einen neu gebauten Schalter mit
`catch (_)`: freundlicher Text für den Nutzer, Ursache restlos verworfen.

Übertragen wurde keine Technik, sondern eine **Form**: der Nutzer bekommt eine
Meldung, die Ursache verschwindet. Anderes Projekt, andere Sprache, anderes
Rahmenwerk — genau die Übertragung, die ein projektlokales Wiki nicht leisten
kann.

*Was damit ausdrücklich nicht belegt ist: dass so etwas automatisch geschieht.
Der Hook hat eingespielt; gelesen und die Analogie erkannt hat der Mensch am
Werkzeug. Und wäre die Anwendung eine Sitzung später erfolgt, wäre sie
unsichtbar geblieben — das steht so im Knoten.*
</details>

<details>
<summary><b>2. Ein PDF-Konverter meldete Erfolg und schrieb Zeichensalat</b> — und der erste Fix war messbar falsch</summary>

- **Wann:** 2026-07-28T07:57:34 (+02:00)
- **Modell:** nicht festgehalten
- **Fundstelle:** Lehre `L-bac968` (der Konverter selbst liegt in einem Nachbarprojekt des Verbunds, nicht in diesem Repo)

Die Fallback-Kette PyMuPDF → pdftotext → OCR schaltete nur weiter, wenn der Text
**leer** war. PDFs mit eingebettetem Font ohne ToUnicode-Tabelle liefern aber
nicht-leeren Salat (`!!!"# $% &'(` statt `Rechnung`). Ergebnis: Datei
geschrieben, Rückgabewert 0, und weil die Ausgabedatei zugleich das
Erledigt-Signal der Stapelschleife war, zementierte sich der Fehlschlag selbst.
Ein Beleg lag seit der Ersterfassung unauswertbar in der Ablage — 1 von 358.

Der lehrreiche Teil ist der **erste Fixversuch**: ein Detektor über den Anteil
„plausibler Zeichen", Schwelle 0,80. Er klagte zwei intakte Belege an
(ziffernlastige Tabellen, 0,78) und ließ denselben kaputten Beleg durch (dessen
Salat war ziffernlastig und kam auf ~0,9). Die Zahl war plausibel und falsch.

Der zweite Anlauf misst Wortdichte und wurde **am echten Bestand kalibriert**:
358 Dokumente, Median 69,7 Wörter je 1000 Zeichen, schlechtestes echtes Dokument
15,0, kaputte Extraktion 3,3 — die Schwelle 10,0 liegt in der Lücke dazwischen.
Bei Misserfolg entsteht jetzt gar keine Ausgabedatei.

*Daraus die Regel: Heuristik-Schwellen nie raten, sondern die Verteilung des
echten Bestands ansehen. Gibt es keine Lücke, ist die Metrik falsch — nicht die
Schwelle.*
</details>

<details>
<summary><b>3. „Upload erfolgreich" — der Build erschien nie</b></summary>

- **Wann:** 2026-07-28T08:17:07 (+02:00)
- **Modell:** nicht festgehalten
- **Fundstelle:** Lehre `L-47e586`

Ein TestFlight-Upload meldete `UPLOAD SUCCEEDED with no errors` samt
Vorgangsnummer. In App Store Connect tauchte der Build nie auf. Ursache: die
Build-Nummer war bereits vergeben. Sie war aus einer lokalen Metadatendatei
abgeleitet worden, die naturgemäß hinterherläuft — der Store stand längst zwei
Nummern weiter. Apple verwirft das Duplikat erst bei der Verarbeitung, und zwar
wortlos.

Der Fund löste zugleich einen älteren, nie geklärten Fehlschlag derselben App,
den man damals auf Platzhalter-Icons geschoben hatte.

*Die übertragbare Regel steht in der Lehre: Wenn ein Dokument in einem Punkt
nachweislich veraltet ist, gilt es in allen Punkten als unbelegt, bis geprüft.
Teilvertrauen in eine als unzuverlässig erkannte Quelle ist der eigentliche
Fehler.*
</details>

<details>
<summary><b>4. Eine abgelaufene Regel wurde als abgelaufen erkannt</b> — Geltung, nicht nur Fund</summary>

- **Wann:** 2026-08-08, Suchen um 13:33, Befund festgehalten 13:36:02 (+02:00)
- **Geprüftes Modell:** nicht festgehalten — das Protokoll führt den Agenten als `client=skript`, `model=unbekannt`
- **Befund geschrieben von:** `claude-opus-5` über `claude-code`
- **Fundstelle:** Knoten `a3c66be9`, Regel im Knoten `1d0fd081`

Im Testbestand lag ein erfundener Gebührenerlass von 20 %, gültig 2026-05-01 bis
2026-07-31. Auf die Frage danach suchte der Agent, nannte den Zeitraum und
folgerte richtig, dass der Rabatt nicht mehr gilt. Das Protokoll zeigt zwei
Suchen — er hat nachgesehen, statt zu raten.

Ein Volltextindex hätte die Regel gefunden und als gültig ausgeliefert. Der
Unterschied liegt im Feld `gilt_bis`, nicht in der Trefferquote.

*Im selben Lauf der Gegenfall: Vorgang 4 lief ohne jede Suche, das Protokoll
blieb leer. Der Agent empfahl Marketing statt der Absage, die die hinterlegte
Regel verlangte, und fragte erst danach, ob er nachsehen solle.*
</details>

<details>
<summary><b>5. Die Datenbank verhinderte einen Eintrag, den das Modell bereits als erledigt meldete</b></summary>

- **Wann:** 2026-08-08, Vorgang 7 (festgehalten 13:50:00), Folgefall Vorgang 9 (13:58:43), beide +02:00
- **Geprüftes Modell:** nicht festgehalten (`client=skript`, `model=unbekannt`)
- **Befund geschrieben von:** `claude-opus-5` über `claude-code`
- **Fundstelle:** Knoten `bd393245` und `…/messlauf-5-die-kette-v7-zu-v9-zeigt-den`

Auftrag war, einen Vermerk festzuhalten. Das Zugriffsprotokoll zeigt
`add | rejected | source_fehlt` — die Herkunftspflicht wies den Schreibversuch
ab. Die Antwort an den Nutzer lautete dennoch: „Ich habe den Vermerk
gespeichert", mit Titel und Begründung. Im Bestand: null Knoten.

Acht Minuten später fragte ein weiterer Vorgang nach genau diesem Vermerk. Der
Agent suchte, fand ihn nicht — es gab ihn nie — und lieferte trotzdem eine
Begründung, konstruiert aus einer anderen Regel im Bestand.

Der unbequeme Teil ist der eigentliche Befund: **die Schranke hielt, das Modell
meldete Erfolg.** Ohne die Schranke stünde heute ein erfundener Vermerk im
Bestand, und niemand hätte einen Fehler gesehen.
</details>

<details>
<summary><b>6. Ein Prüfwerkzeug gegen 210 falsche Paare geprüft — 0 Fehlalarme</b></summary>

- **Wann:** 2026-08-09T20:47:20 (+02:00)
- **Modell:** keines beteiligt — die Prüfung ist deterministisch (Substring- und ID-Vergleich), Laufzeit unter einer Sekunde
- **Fundstelle:** `runs/antwortqualitaet_2026-08-09.md`

Jede der 15 Prüfaufgaben wurde gegen die korrekten Antworten der 14 *anderen*
Aufgaben gehalten: 210 Negativpaare, 0 Falsch-Positive. Die Aufgaben stammen aus
9 Projekten und Sprachen (Swift-Build, Play-Billing, SQLite-WAL, QR-Scanner,
iOS-Crash-Diagnose).

Vorher war recherchiert worden, ob es für solche Negativkontrollen eine übliche
Ausschlussgrenze gibt. Ergebnis: gibt es nicht. Statt eine fremde Prozentzahl zu
leihen, wurde die eigene gemessen.
</details>

<details>
<summary><b>7. Ein Datenschutzfund, den der Musterkatalog nicht fand</b></summary>

- **Wann:** Befund 2026-08-06T11:56:13, Nachtrag 2026-08-10T00:09:03 (+02:00)
- **Modell:** nicht festgehalten
- **Fundstelle:** Lehre `L-adfb33`

Ein Katalog aus regulären Ausdrücken (E-Mail, IBAN, Kundennummer, Anrede) lief
über alle 722 Lehren und meldete 44 Verdachtsfälle — 44 davon Fehlalarme
(„Diagnose" im Sinne von Fehlerdiagnose). Der echte Fall wurde erst durch eine
Positivkontrolle mit bekannten Namen aus dem Bestand gefunden: eine Lehre trug
selbst einen Klarnamen aus dem Testbestand. Sie beschrieb ein Datenleck und war
eines.

Daraus die Regel, die seither gilt: ein Beleg braucht die **Form** des Datums,
nicht seinen **Inhalt**. Eine Lehre, die einen Eigennamen braucht, ist nicht
fertig destilliert.
</details>

<details>
<summary><b>8. Was wir nicht behaupten können — und warum es hier steht</b></summary>

- **Wann:** blinder Lauf Stand 2026-08-09T21:21:34, Wettbewerbsmessung 2026-08-09T10:05:52 (+02:00)
- **Modelle im blinden Lauf:** `gemma4:12b` und `gemma4:e4b`, je 3 Durchläufe, lokal gerechnet
- **Fundstelle:** `runs/wissensnutzen_blind.json`, `runs/antwortqualitaet_2026-08-09.md`, `runs/wettbewerb_2026-08-09.md`

Es gibt einen A/B-Lauf, der gut aussieht: ein kleines Modell schlägt ohne
eingespieltes Wissen ein dokumentiertes Antipattern vor, mit Wissen die richtige
Lösung.

Beim Nachprüfen: für diese Dateien existiert kein erzeugendes Skript im Repo,
und der vergleichbare frühere Aufbau war nachweislich tautologisch — die
Suchanfrage war von Hand aus der bekannten Lösung gebaut, der eingespielte Text
enthielt den Lösungswortlaut. Gemessen wurde also „hilft es, die richtige
Antwort in den Prompt zu schreiben".

Der Nachbau über den echten Suchpfad zerlegt den Aufgabentext selbst und sucht
damit. Dort steht für dieselbe Aufgabe `trefferguete: false`: der Speicher fand
die passende Lehre **nicht**.

Der Fall gehört hierher, weil er die Richtung zeigt: die Messung wurde so
umgebaut, dass sie scheitern kann — und sie scheiterte sofort. Zur Einordnung
gehört auch die eigene Wettbewerbsmessung: eigene Abrufgüte 7 von 35 (20 %),
während Standard-Hybrid-RAG in Produktionsberichten desselben Jahres rund 91 %
Recall@10 erreicht. Wer nur sucht, ist mit Standardbausteinen besser bedient.
</details>

## Was es ausdrücklich NICHT ist

Keine Anonymisierung · keine Verschlüsselung · keine BSI-Zertifizierung · kein
vollständiger Schutz gegen Promptinjektion · kein Mehrbenutzerbetrieb.

Jeder dieser Punkte ist ausgeführt in [`docs/GRENZEN.md`](./docs/GRENZEN.md) —
mit dem, was **statt dessen** gebaut ist, und wo dessen Grenze liegt. Diese
Liste ist wichtiger als jede Merkmalsliste, weil sie das Vertrauen bestimmt.

## Weiterlesen

| Datei | Inhalt |
|---|---|
| [`docs/AUFBAU.md`](./docs/AUFBAU.md) | Verzeichnisaufbau, Vektoren, Sichern und Wiederherstellen |
| [`docs/GRENZEN.md`](./docs/GRENZEN.md) | was brainlehr nicht leistet, im Einzelnen |
| [`docs/FREMDBESTAENDE.md`](./docs/FREMDBESTAENDE.md) | Lizenzampel der fremden Prüfkorpora (NASA LLIS, BSI, offene Quellen) |
| [`docs/adr/`](./docs/adr/) | Entscheidungen mit Begründung und Abbruchbedingung |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Beitragsablauf und CLA |

## Lizenz

**GNU Affero General Public License v3.0** ([`LICENSE`](./LICENSE)), Kurzfassung
ohne Juristendeutsch in [`LICENSE_FAQ.md`](./LICENSE_FAQ.md).

Privat, in der Forschung und in Open-Source-Projekten: kostenlos, ohne
Einschränkung. Wer eine veränderte Fassung weitergibt oder als Netzwerkdienst
betreibt, legt seinen Quelltext ebenfalls unter der AGPLv3 offen. Für den Einbau
in geschlossene Produkte gibt es eine kommerzielle Lizenz.

Zwei Dateien tragen eine **eigene** Lizenz — ausgewiesen, nicht versehentlich:
siehe [`NOTICE`](./NOTICE).
