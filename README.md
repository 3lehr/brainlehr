# brainlehr 0.1.0

**Ein Wissensspeicher, der sich meldet.**

Übliche Speicher warten auf eine Frage und liefern ähnlichen Text. brainlehr tut
vier Dinge, die ein Archiv nicht tut:

**Es meldet sich ungefragt.** Bei jeder Antwort prüft es, ob darin ein Gesetz,
eine Norm oder eine interne Kennung zitiert wird — und ob dafür ein Beleg im
Bestand liegt. Fehlt er, sagt es das. Modellwissen ist eingefroren; eine präzise
Fundstelle aus dem Gedächtnis ist verdächtiger als eine vage.

**Es schlägt vor, was fehlt.** Es erkennt wiederkehrende Handgriffe und schlägt
dafür Werkzeuge und Prüfsteine vor — samt fertigem Auftrag. Wiederholt sich eine
Fehlerklasse dreimal, wird sie von selbst zur Regel.

**Es widerspricht.** Ein Eintrag ohne nachprüfbare Herkunft entsteht gar nicht
erst — das erzwingt ein Datenbank-Trigger, nicht eine Konvention. Wer eine
Hausregel setzen will, muss ein Mensch sein, und der Speicher prüft das.

**Es kennzeichnet fremden Text als Daten.** Jeder Bestandstext, der in ein
Modell fließt, wird abgegrenzt und als Daten beschriftet — nicht per Wortliste
(die ist prinzipiell unvollständig), sondern durch die Darstellung selbst, plus
sprachunabhängige Anomaliesignale.

**Es misst sich selbst.** Trefferquote, Nutzen, Rangfolge — gegen einen fremden
Prüfkorpus, blind bewertet. Die Zahlen fallen regelmäßig schlecht aus; das ist
der Zweck. Ein Speicher, der seine eigene Trefferquote nicht kennt, behauptet
seinen Nutzen.

Läuft offline als MCP-Server auf SQLite. Kein Dienst, kein Konto, keine Cloud.

> **Fassung 0.1.0.** Die führende Null ist die Aussage: keine stabile
> Schnittstelle, keine Zusage zur Aufwärtskompatibilität, Felder und Werkzeuge
> können sich ändern. Was funktioniert, ist belegt — was zugesagt wird, ist
> nichts. Die Fassung steht in `VERSION`; ein Test hält Datei, Server und diese
> Zeile zusammen.

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
- **Kein *vollständiger* Schutz gegen Promptinjektion — aber auch nicht nichts.**
  Gebaut ist `einschleusung.py`, dreistufig und am Schreibvorgang verdrahtet:
  jeder Bestandstext wird bei der Ausgabe als **Daten abgegrenzt und
  gekennzeichnet** (das ist der eigentliche Schutz), dazu kommen
  sprachunabhängige Anomaliesignale (Skriptmischung, kodierte Blöcke,
  verwechselbare Zeichen) und zuletzt Wortmuster. 16 Angriffsformen im
  Selbsttest erkannt, 9 harmlose Gegenbeispiele nicht.
  Was es **nicht** leistet, sagt das Modul selbst: eine Musterliste ist
  prinzipiell unvollständig, ein umformulierter Angriff fällt durch jedes
  Regex-Set. Und ein Fund **blockiert nicht** — sonst könnte eine geschickte
  Formulierung das Schreiben fremder, legitimer Einträge verhindern.
  Die Grenze darüber bleibt: Rechte begrenzen den *Radius*, nicht die
  *Möglichkeit* — wer den Kontext eines Modells steuert, handelt mit dessen
  Rechten, und die Prüfung sieht einen legitimen Aufruf
  (`docs/KONZEPT_BETEILIGUNG_UND_DATENPUNKTE_2026-08-09.md`, Kapitel 5b).
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

# Beispielbestand einspielen (1.733 Einträge, NASA-LLIS + Methodik)
python3 brainlehr.py rein auszug-offen/bestand.jsonl --db knowledge.db

# Selbsttests der Kernmodule — brauchen KEINE Abhängigkeiten
python3 ausweis.py --selftest
python3 werkzeugrechte.py --selftest
python3 normbezug.py --selftest

# als MCP-Server starten (stdio)
python3 knowledge_mcp_server.py
```

Ab hier ist die Volltextsuche benutzbar. Die drei Pakete aus
`requirements.txt` und `pytest` braucht erst der nächste Schritt.

### Vektoren: bewusst nicht mitgeliefert

Der Beispielbestand enthält **keine** Embeddings. Das ist kein Vergessen:

- **Ein Vektor gehört zu genau einem Modell.** Mitgelieferte Vektoren würden
  die Modellwahl vorwegnehmen — ein Datenbank-Trigger erzwingt ohnehin, dass
  alle Vektoren im Bestand vom selben Modell stammen.
- **Sie sind nicht nötig, um anzufangen.** FTS5 trägt die Suche allein; oben
  liefert sie ohne einen einzigen Vektor Treffer.
- **Sie sind reproduzierbar.** Wer sie will, rechnet sie selbst — das kostet
  einmal Rechenzeit und einen Modell-Download, aber niemand muss fremden
  Zahlenkolonnen vertrauen, deren Herkunft er nicht prüfen kann.

```bash
pip install -r requirements.txt
python3 build_embeddings.py          # einmalig, dauert je nach Gerät
```

Danach läuft die hybride Suche (FTS5 + Vektoren, per RRF verschmolzen). Ein
näherungsweiser Index (HNSW) ist bewusst **nicht** gebaut: er fände den besten
Treffer nicht garantiert und würde damit die Gütemessung entwerten, an der
dieses Projekt hängt.

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

**Zum BSI-Profil:** Quelle ist die
[BSI Stand-der-Technik-Bibliothek](https://github.com/BSI-Bund/Stand-der-Technik-Bibliothek)
unter **CC BY-SA 4.0** — kommerzielle Nutzung, Bearbeitung und Weitergabe sind
erlaubt. Die **Share-Alike-Bedingung** gilt und steht in `NOTICE`: Das
abgeleitete Profil bleibt CC BY-SA 4.0, unabhängig von der Lizenz des übrigen
Quelltextes.

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
vorschlag.py              schlägt Werkzeuge und Prüfsteine vor, mit fertigem Auftrag
docs/adr/                 Entscheidungen mit Begründung und Abbruchbedingung
migrationen/              historische Läufe — für eine Neuanlage nicht nötig
quellen/                  Lizenzampel der Fremdbestände
```

> **Das Wurzelverzeichnis ist zu voll — 88 Python-Dateien.** Das ist gewachsen,
> nicht entworfen, und für ein Repo, das jemand von außen lesen soll, ist es zu
> viel. Der Umbau auf `src/brainlehr/` plus `werkzeuge/` steht als nächster
> Schritt an; er berührt jede Pfadauflösung und braucht deshalb eine eigene
> Runde mit Testabsicherung, statt nebenbei zu passieren.

Was die vielen Dateien wenigstens einlösen: jedes Werkzeug ist für sich
aufrufbar, hat einen `--selftest` und einen Modulkopf, der seine **Fehlklasse**
benennt — wogegen es schützt und was ein Fehlalarm kostet.

---

---

## Lizenz

Der Code steht unter der **GNU Affero General Public License v3.0**
([`LICENSE`](./LICENSE)). Kurzfassung ohne Juristendeutsch:
[`LICENSE_FAQ.md`](./LICENSE_FAQ.md).

**Privat, in der Forschung und in Open-Source-Projekten: kostenlos, ohne
Einschränkung.** Wer eine veränderte Fassung weitergibt oder als Netzwerkdienst
betreibt, legt seinen Quelltext ebenfalls unter der AGPLv3 offen. Für den
Einbau in geschlossene Produkte gibt es eine kommerzielle Lizenz.

Zwei Dateien tragen eine **eigene** Lizenz — das ist ausgewiesen, nicht
versehentlich: siehe [`NOTICE`](./NOTICE).
