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

Anbindung an einen MCP-Klienten über dessen Konfiguration; der Server spricht
JSON-RPC über Standardein- und -ausgabe.

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
