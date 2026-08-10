# brainlehr

Ein lokaler Wissensspeicher für Sprachmodelle, der nicht nur festhält, **was
gesagt wurde**, sondern **was gilt** — und der misst, ob er dabei hilft.

Läuft offline als MCP-Server auf SQLite. Kein Dienst, kein Konto, keine Cloud.

---

## Wofür das gut ist

Ein Sprachmodell vergisst zwischen zwei Sitzungen alles. Übliche Abhilfen legen
Text in eine Vektordatenbank und holen ihn ähnlichkeitsbasiert zurück. Das
beantwortet „worüber haben wir gesprochen" — aber nicht:

- **Wer** hat das behauptet, und wurde es je geprüft?
- Gilt es **noch**, oder ist es abgelöst?
- Was, wenn **zwei Einträge sich widersprechen**?
- Und: **wirkt** der Speicher überhaupt, oder liefert er nur Treffer?

brainlehr beantwortet diese vier Fragen mit Feldern und Messungen statt mit
Zuversicht.

---

## Was wirklich drin ist

### Herkunft ist Pflicht, nicht Konvention
`source` ist ein Pflichtfeld, erzwungen per **Datenbank-Trigger** — nicht per
Konvention im Anwendungscode. Ein Eintrag ohne nachprüfbare Herkunft entsteht
gar nicht erst. Herkunftsfelder sind nach dem Schreiben unveränderlich.

### Geltung als eigene Achse
Jede Aussage kann eine Norm sein: `norm_rang` (1 globale Regel, 2
Projektentscheidung, 3 ADR), `gilt_ab` / `gilt_bis`, und die ausdrückliche
Entscheidung `keine_norm | norm_befristet | norm_unbefristet` — ohne
Vorgabewert, weil ein stiller Vorgabewert genau die Mehrdeutigkeit
zurückbringt, die das Feld beseitigen soll.

### Identität wird gemessen, nicht behauptet
Wer schreibt, weist sich mit einem Ausweis aus (scrypt, Datei mit `0600`
außerhalb der Datenbank). Ein Aufrufer kann seine Identität **nicht mehr im
Aufruf behaupten**; ohne Ausweis trägt die Zuschreibung dauerhaft das Präfix
`unbeglaubigt:`. Rollen folgen dem Muster `modul:aktion:bezug` — die dritte
Stelle (`own`, `published`) macht Sichtbarkeit vom Bezug zum Datensatz
abhängig statt von der Rolle allein. Siehe `docs/adr/ADR-002`.

### Zwei Sorten Wissen
**Knoten** tragen Sachverhalte, **Lehren** tragen Fehlerklassen samt Ursache,
Behebung und Vermeidung. Wiederholt sich eine Lehre dreimal, eskaliert sie
automatisch zur Regel.

### Hybride Suche
FTS5-Volltext (inkl. Trigramm) zusammen mit lokalen Vektor-Embeddings (bge-m3),
per RRF verschmolzen. Beides läuft auf dem Gerät.

### Assoziative Kanten
`hebb_kanten.py` verstärkt Verbindungen zwischen Einträgen, die gemeinsam
abgerufen werden. Eine Kante bedeutet dabei ausdrücklich **„kam zusammen vor"**,
nicht „hängt zusammen" und schon gar nicht „führt zu".

### Der Speicher misst sich selbst
`abrufguete.py`, `pruefkorpus.py`, `wissensnutzen_blind.py`: A/B-Läufe gegen
einen Prüfkorpus, blinde Nutzenbewertung, Rangfolge-Diagnose. Die Zahlen fallen
regelmäßig schlecht aus — das ist der Zweck. Ein Speicher, der seine eigene
Trefferquote nicht kennt, behauptet seinen Nutzen.

### Zugriffsprotokoll mit Hashkette
Jeder Lese- und Schreibvorgang landet in `access_log`, verkettet per SHA-256.
Damit ist eine **nachträgliche Änderung nachweisbar** — sie ist dadurch nicht
verhindert (keine Signatur, kein zweiter Rechner: wer Schreibrechte auf die
Datei hat, kann die Kette neu rechnen).

---

## Was es ausdrücklich NICHT ist

Diese Liste ist wichtiger als die obere, weil sie das Vertrauen bestimmt:

- **Keine Anonymisierung.** `kanonymitaet.py` *misst* k-Anonymität und
  verwendet das Wort „anonym" bewusst nie — ob ein gemessenes k genügt, ist
  eine Rechtsfrage und hängt von Kontextwissen ab, das keine Datenbank hat.
  Das Werkzeug liefert die Zahl, den Schluss zieht ein Mensch.
- **Keine Verschlüsselung.** Die Hashkette weist Änderungen nach, sie verhindert
  sie nicht.
- **Keine BSI-Zertifizierung.** Es gibt ein Prüfprofil und harte Verbote
  (keine Secrets im Code, kein `eval` auf Nutzereingaben, Passwort-Hashing).
  „Erfüllt den Stand der Technik" wäre eine Behauptung, kein Nachweis.
- **Kein Schutz gegen Promptinjektion.** Rechte begrenzen den *Radius*, nicht
  die *Möglichkeit*: Wer den Kontext eines Modells steuert, handelt mit dessen
  Rechten, und die Prüfung sieht einen legitimen Aufruf. Siehe
  `docs/KONZEPT_BETEILIGUNG_UND_DATENPUNKTE_2026-08-09.md`, Kapitel 5b.
- **Kein Mehrbenutzerbetrieb.** Ausweise und Rollen existieren, aber der
  Transport ist stdio: ein Prozess, ein Rechner. HTTP ist entschieden
  (`ADR-001`), nicht gebaut.

---

## Schnellstart

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Datenbank anlegen
sqlite3 knowledge.db < schema.sql
sqlite3 knowledge.db < herkunft_unveraenderlich.sql

# Selbsttests der Kernmodule
python3 ausweis.py --selftest
python3 werkzeugrechte.py --selftest
python3 normbezug.py --selftest
pytest -q

# als MCP-Server starten (stdio)
python3 knowledge_mcp_server.py
```

### Bestand sichern und wiederherstellen

Die Datenbank selbst gehoert **nicht** in die Versionsverwaltung: Git fuehrt eine
Binaerdatei nicht zusammen, es ueberschreibt sie — ein Arbeitstag der Gegenseite
verschwindet dann ohne Konflikthinweis. Versioniert wird stattdessen ein
zeilenweiser Textauszug, aus dem sich der Bestand vollstaendig wiederherstellen
laesst:

```bash
python3 brainlehr.py raus     # Bestand -> auszug/ (Text, vergleichbar)
python3 brainlehr.py rein     # auszug/ -> Bestand
python3 brainlehr.py init     # leere Datenbank anlegen
python3 brainlehr.py haken    # Hooks im Klienten verdrahten
```

Anbindung an einen MCP-Klienten über dessen Konfiguration; der Server spricht
JSON-RPC über Standardein- und -ausgabe.

---

## Fremdbestände: was drin ist und was noch fehlt

brainlehr enthält einen fremden Prüfkorpus, damit die Abrufmessungen nicht nur
gegen den eigenen, selbst geschriebenen Bestand laufen — sonst misst man die
eigene Schreibweise statt der Suchgüte.

| Quelle | Betreiber | Ampel | Stand |
|---|---|---|---|
| [NASA LLIS](https://llis.nasa.gov/) | NASA | 🟢 grün | **1.637 Einträge importiert**, in `auszug-offen/` enthalten |
| [ESA Lessons Learned](https://www.esa.int/) | ESA | ⚪ ungeprüft | offen |
| [ASRS](https://asrs.arc.nasa.gov/search/database.html) | NASA/FAA | ⚪ ungeprüft | offen |
| [FAA Lessons Learned](https://lessonslearned.faa.gov/) | FAA | ⚪ ungeprüft | offen |
| [NRC Licensee Event Reports](https://www.nrc.gov/reading-rm/doc-collections/event-status/) | US NRC | ⚪ ungeprüft | offen |
| [CROSS](https://www.cross-safety.org/) | CROSS-UK/US | ⚪ ungeprüft | vertrauliche Meldungen — Weitergabe voraussichtlich nicht gedeckt |
| [NIST](https://www.nist.gov/) | NIST | ⚪ ungeprüft | Teilbestand noch zu benennen |
| [FDA MAUDE](https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfmaude/search.cfm) | FDA | ⚪ ungeprüft | **Art.-9-Risiko**: Gesundheitsdaten möglich |
| [IAEA IRS](https://www.iaea.org/) | IAEA | ⚪ ungeprüft | Zugang beschränkt — voraussichtlich rot |
| [BSI Stand-der-Technik-Bibliothek](https://github.com/BSI-Bund/Stand-der-Technik-Bibliothek) | BSI | 🟢 grün | CC BY-SA 4.0 — `bsi-dev-profile.json` liegt bei, **Share-Alike** siehe `NOTICE` |

Die Ampel steht in `quellen/fremdquellen.json` mit Prüfauftrag je Quelle.
**Vorgabe ist deny:** Was nicht ausdrücklich grün ist, wird weder importiert noch
weitergegeben.

Warum überall „ungeprüft": Lizenzangaben aus einem Modellgedächtnis sind wertlos
— es ist eingefroren, und Nutzungsbedingungen ändern sich. Die Felder
`lizenz_vermutet` und `url` tragen diesen Vorbehalt ausdrücklich; grün wird eine
Zeile erst, wenn jemand die Lizenzseite aufgerufen und Datum plus Fundstelle
eingetragen hat.

**Zum BSI-Profil im Besonderen — und zu einem Fehler, den ich dabei gemacht
habe:** Ich hatte es zunächst auf gelb gesetzt und die Datei aus dem Repo
entfernt, gestützt auf die Nutzungsbedingungen von `bsi.bund.de` (kommerzielle
Verwendung des IT-Grundschutzes ist dort lizenzpflichtig). Die tatsächliche
Quelle stand aber **in der Datei selbst**: `BSI-Bund/Stand-der-Technik-Bibliothek`
unter **CC BY-SA 4.0** — kommerzielle Nutzung, Bearbeitung und Weitergabe
erlaubt. Die Lehre daraus steht in `quellen/fremdquellen.json`: erst am Artefakt
nachsehen, dann die Website suchen.

Die **Share-Alike-Bedingung** bleibt und ist in `NOTICE` vermerkt: Das
abgeleitete Profil steht unter CC BY-SA 4.0, unabhängig davon, unter welcher
Lizenz der übrige Quelltext steht.

Und der Katalog hat eine gemessene
Lücke: **keine Controls zu Negativtests, Grenzwertprüfung, Nachweis der
Testwirksamkeit und statischer Analyse.** Wer diese vier Bereiche regelt, trifft
eine eigene Entscheidung — „Stand der Technik laut BSI" deckt sie nicht.

---

## Aufbau

```
knowledge_mcp_server.py   MCP-Schnittstelle, 23 Werkzeuge, ein Choke-Point
ausweis.py                Identität, Rollen, Mandate, Einladungen
werkzeugrechte.py         Durchsetzung an tools/call, Bezug own/published
foederation.py            Instanzkennung, Vertrauensliste zwischen Instanzen
normbezug.py              meldet Normzitate ohne Beleg in eigenen Antworten
embeddings.py             lokale Vektoren + RRF-Fusion
hebb_kanten.py            assoziative Kanten aus gemeinsamem Abruf
kanonymitaet.py           misst k-Anonymität (misst, anonymisiert nicht)
haken/                    Hooks für Abruf und Erfassung
schreibpruefstand/        Messläufe gegen lokale Modelle
docs/adr/                 Entscheidungen mit Begründung und Abbruchbedingung
```

---

## Herkunft dieser Datei

Die Struktur folgt einem Vorschlag, der aus einer Analyse des Repos entstand.
Drei Aussagen daraus wurden beim Gegenlesen am Quelltext **nicht bestätigt** und
sind hier korrigiert: automatische Anonymisierung (findet nicht statt),
„kryptografisch verankert" (SHA-256 ohne Signatur), sowie zwei genannte Dateien,
die es nicht gibt. Das ist kein Nebensatz, sondern die Arbeitsweise dieses
Projekts: **eine Aussage über den Code wird am Code geprüft, bevor sie
weitergetragen wird.**
