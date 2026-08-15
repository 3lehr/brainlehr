# Sicherheitsfunde aus dem Konsil, 2026-08-14T21:36:26+0200

Aus zwei unabhängigen Linsen (Angreifer, Durchsetzbarkeit). **Keiner wurde
ausgenutzt** — alle stammen aus Codelesung bzw. `codesign`/`stat`. Reihenfolge
nach Schaden.

## Behoben

**B1 · Die leere Fundstelle galt als Beleg.** `kern/belegvertrag.py`:
`"" in text` ist in Python immer wahr, also galt ausgerechnet die Regel als
belegt, die keine Fundstelle angibt. Selbst nachgemessen, behoben, Rot-Probe
gefahren (Commit `3bc7cef`).

## Offen, nach Schaden geordnet

**O1 · Fremder Text aus der Datenbank landet roh in der Oberfläche.**
`entscheidungen.html:1546` setzt `p.a`, `p.p`, `p.d` unmaskiert per
`innerHTML`; die Werte stammen aus `kern/raum_daten.py` und tragen
`knowledge_nodes.path` bzw. die Lehren-Kennung. Auf `path` gibt es keine
Zeichenprüfung.
**Warum es schwer wiegt:** Die Ansicht läuft in `WissensraumWebView`
**gleichursprünglich** mit `http://127.0.0.1:8799` — ein Skript dort kann alle
`/api/*` lesen und schreiben, inklusive Regelbeförderung. Kein CSP-Kopf, keine
Navigationsregel.
**Und genau dieser Ort soll die Tabellenkalkulation bekommen** (ADR-016): Jede
Zelle und jeder Zellname wäre dieselbe Senke.
**Halbe Maskierung ist dabei schlechter als keine** — in derselben Zeile wird
`p.t` escapt, was beim Lesen wie Sorgfalt aussieht.

**O2 · Kein Absender-Schutz auf 8799 und 4599.** `berichte/entscheidungen_server.py`
prüft bei `POST` weder Herkunft noch Kennung (0 Treffer für
`ausweis|Authorization|token`). Eine beliebige Seite im Browser des Betreibers
genügt für einen Schreibzugriff — kein Rechnerzugang nötig.
Schwerer wiegt 4599: Der Befehl zum Verbinden des Dokuments prüft nur, ob die
Adresse mit `ws` beginnt — **jede fremde Adresse wird angenommen**, und die App
synchronisiert das Dokument dorthin. *Einschränkung: die Datei liegt in
`#if DEBUG`. Nicht gemessen, welchen Bau der Betreiber startet.*

**O3 · Der Belegvertrag prüft Selbstkonsistenz, nicht Herkunft.** Regeln und
Quellen kommen aus derselben Paketdatei (`kern/domaene.py`). Gemessen: erfundene
Quelle plus wörtlich passende Fundstelle wird angenommen. Kein
Ausführungsschaden — aber eine **Zahl, die belegt aussieht**, und das ist bei
Steuer-, Kranken- und Bonitätsdaten der teuerste Fall. Entwurfsfrage, in ADR-018
behandelt.

**O4 · Der Bestand gehört dem angemeldeten Benutzer.** `brainlehr.db` liegt als
`0644` unter der eigenen Kennung; ein `sqlite3`-Aufruf umgeht Ausweis, Rollen,
Mandat und Torwächter vollständig. `kern/ausweis.py::selbstbedienung_moeglich`
benennt genau das — als Diagnose, nicht als Schranke.

**O5 · Die App-Sandbox ist nicht aktiv.** `codesign -dv`: `adhoc`,
`TeamIdentifier=not set`, kein Entitlement-Block. Damit steht keine vom
Betriebssystem erzwungene Grenze zur Verfügung, auf die sich ADR-017 berufen
hatte.

## Die eine Änderung mit dem größten Hebel

**Ein eigener Systembenutzer; `brainlehr.db` und die Ausweisdatei gehören ihm
(`0600`); der Dienst läuft unter ihm.** Kein Zeilencode im Kern.

**Warum diese und nicht der Schutz der Ausweisdatei:** Der Ausweis ist nicht das
größte Merkmal, der **Bestand** ist es. Solange die Datenbank dem angemeldeten
Benutzer gehört, ist jede Rolle, jedes Mandat und jeder Widerruf eine
Empfehlung, die ein einziger `sqlite3`-Aufruf überschreibt. Mit fremdem Eigner
wird die Loopback-Bindung von einer halben zur ganzen Grenze — und **erst
dadurch** wird das fehlende `Authorization` am Server (O2) zu einer Lücke, die
etwas verschließt, statt zu einer Zierleiste vor einer offenen Wand.

**Was sie nicht löst:** O1 (gleicher Ursprung von Ansicht und Schnittstelle) und
das fehlende Manifestfeld für die Werkzeugherkunft aus ADR-012.

## Kosten, die dabei genannt wurden

Ein Sandbox-Entitlement wäre die andere naheliegende Grenze — es würde aber den
Start des Python-Dienstes durch die App und die freie Suche über
`BRAINLEHR_REPO_ROOT` sofort brechen. Eine Grenze mit Preis, keine
Gratisleistung. *Nicht gemessen: ob es den Ladepfad des CRDT-Rahmenwerks bricht.*

## Stand 2026-08-15T11:05:00+0200 — vier von fünf bearbeitet

Und zur oben genannten Kostenfrage die Auflösung: **beide Befürchtungen sind
überholt.** Der Dienststart durch die App ist seit `648432e` weg (die App ist
sein Klient), und der Ladepfad des CRDT-Rahmenwerks ist gemessen — er trägt in
der Sandbox, sobald ein `.app`-Bündel vorliegt (Knoten `fef0cb9d`).

| Fund | Stand | Beleg |
|---|---|---|
| **O1** roher `innerHTML` | **behoben** | `ee4645a` — `escHtml()`, dazu dieselbe Fehlerklasse ein zweites Mal im Abrufweg-Tooltip gefunden und mitbehoben. 15 von 16 Tests rot gegen den Stand davor |
| **O2** kein Absender-Schutz | **behoben** | `91f096a` — Herkunftsprüfung auf 8799; auf 4599 Beschränkung auf Loopback statt `hasPrefix("ws")`. Vorher gemessen, dass der Fund scharf ist: `bauen.sh` baut ohne `-c release`, `#if DEBUG` ist also aktiv |
| **O3** Herkunft statt Selbstkonsistenz | **sichtbar gemacht, nicht verhindert** | `447b7b5` — eine Quelle, die einen unabhängigen Bestandsknoten behauptet, wird gegen die Datenbank geprüft. **Mitgeliefert bleibt angenommen, weil es von erfunden automatisch nicht unterscheidbar ist** — der ursprüngliche Angriffsfall steht als Test mit genau diesem Vermerk. `setze_in_kraft()` wurde bewusst NICHT zugesperrt: alle echten Pakete sind mitgeliefert, ein Zwang hätte sie unbrauchbar gemacht |
| **O4** Bestand gehört dem Benutzer | **halb** | `brainlehr.db` von `0644` auf `0600`, Ausweisverzeichnis auf `0700`. **Wirkt gegen andere lokale Benutzer, nicht gegen den eigenen** — der eigene Systembenutzer bleibt der Hebel und braucht das Passwort des Betreibers (G5) |
| **O5** Sandbox nicht aktiv | **scharf** | `app-sandbox` + `network.client`, am echten Bündel über LaunchServices belegt, nicht nur signiert. `bauen.sh` weiter 209 grün |

**Was O5 gekostet hat, und es ist kein Nebensatz:** Der Ausweis-Helfer startet
ein Skript außerhalb des Bündels und ist unter der Sandbox blockiert. Die
naheliegende Datei-Ausnahme wurde **nicht** gesetzt — sie hätte die Sandbox
genau dort aufgehoben, wo sie schützt. Der Weg ist stattdessen derselbe wie bei
den Quellen: über den eigenständigen Dienst, dessen Herkunftsprüfung seit O2
steht.
