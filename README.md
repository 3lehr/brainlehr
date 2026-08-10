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

Läuft offline als MCP-Server auf SQLite. Kein Dienst, kein Konto, keine Cloud.

> **Fassung 0.1.0.** Die führende Null ist die Aussage: keine stabile
> Schnittstelle, keine Zusage zur Aufwärtskompatibilität. Was funktioniert, ist
> belegt — was zugesagt wird, ist nichts.

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
python3 ausweis.py --selftest
python3 werkzeugrechte.py --selftest
python3 normbezug.py --selftest

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
