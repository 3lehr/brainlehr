# Plan I3 — die Tabellenkalkulation als Bestandteil

**Stand** 2026-08-15T15:25:00+0200
**Betrifft** `app/Sources/`, `kern/bestandteile.py`, `spikes/univer_i3_min/`
**Grundlage** ADR-014 (Kern/Bestandteil/Domäne), ADR-016 (Univer, vier Auflagen), ADR-013 (Fachbildschirme)
**Freigabe** Betreiber, 2026-08-15: auf die Frage „soll ich `I3` anfangen?" — *„Ja"*

## Der gemessene Ist-Stand, nicht der vermutete

| | |
|---|---|
| Bündel im Spike | 10 MB unkomprimiert · 2,74 MB gzip mit React · 896 KB als reine UMD-Datei |
| Vorbild für die Einbettung | `app/Sources/Atelier/WissensraumWebView.swift` — dieselbe Klasse „Fachbildschirme" (ADR-013) |
| Mechanismus für Bestandteile | **existiert** — `BestandteilRegistry.swift` + `kern/bestandteile.py`, Commit `87064fad` |
| Lauf ohne Netz | belegt, macOS-Seatbelt, Gegenprobe in beide Richtungen (`curl` nach außen exit 7, auf `127.0.0.1` 200) |
| `new Function` aus dem Dokumentmodell | **0 von 2 Fundstellen erreichbar**, vier Angriffsversuche ohne Treffer (`4f9428c6`) |
| `WEBSERVICE` | hat **keinen Executor** im installierten Paketbaum — ergibt `#NAME?`, kein Netzzugriff |
| Benannte Bereiche | **getragen** — `insertDefinedName` zweimal im gebauten Bündel, nicht nur im Typskript |
| Import fremder Dateien | seit `4f9428c6` **entsperrt**, gebunden an eine Bauvorschrift |

## Der Widerspruch in ADR-016, und wie er aufgelöst wird

**Auflage 1 verlangt eine Positivliste** — *„Jede Verbotsliste hat ein Loch, und bei
eingelesenen fremden Dateien liegt in diesem Loch der Schaden."*

**Gemessen am 2026-08-15: Univer bietet technisch nur eine Verbotsliste.**
`ALL_IMPLEMENTED_FUNCTIONS.concat(config.function)` hängt an, ersetzt nie; einzelne
Funktionen lassen sich nur nachträglich per `unregisterExecutors` entfernen.

**Auflösung — die Auflage bleibt, der Weg ändert sich:** Eine Positivliste ist auf
einer Verbotsliste **konstruierbar**. Man zählt `ALL_IMPLEMENTED_FUNCTIONS` auf,
zieht die erlaubte Menge ab und meldet den Rest ab. Das Ergebnis ist eine
Positivliste; der API-Aufruf ist eine Abmeldung.

**Ohne Test wäre das eine Behauptung.** Der Test lautet: *Die Menge der nach der
Einrichtung tatsächlich verfügbaren Funktionen ist gleich der erlaubten Menge* —
nicht „die verbotenen sind weg". Der Unterschied ist der ganze Punkt: Kommt in
einer künftigen Fassung eine Funktion dazu, fällt sie bei der ersten Formulierung
durch und bei der zweiten auf.

## Bindende Reihenfolge

1. **Anmeldung als Bestandteil** (`kern/bestandteile.py`, `BestandteilRegistry`) —
   **vor** jedem Bildschirm. Sonst bekommt jede Domäne die Tabelle, und das ist
   genau der Fehler, den `I1` behoben hat.
2. **Positivliste scharf** — **vor** dem ersten Lesen einer fremden Datei. Das ist
   Auflage 2 wörtlich. Nachher wäre der Schaden schon möglich gewesen.
3. **Benannte Bereiche erzwingen** — **vor** dem ersten gespeicherten Blatt.
   Dieselbe Klasse wie die fünf Entscheidungen aus ADR-019: heute ein
   Suchen-und-Ersetzen, nach dem ersten Blatt eine Migration. Es ist die
   Reihenfolge, nicht die Menge.
4. Erst danach: Einbettung, Bildschirm, Bedienung.

## Verworfen, mit Grund

- **Eine eigene Tabellenkalkulation bauen.** Der Rechenkern ist der teure Teil, und
  Univer bringt ihn mit. Preis der Ablehnung: eine Abhängigkeit mehr.
- **Das React-Preset** (`@univerjs/presets`, 2,74 MB). Es zieht 27 Pakete
  `@univerjs-pro/*` **ohne Lizenzfeld und ohne Lizenzdatei** — nicht eine
  abweichende Lizenz, sondern keine (Auflage 1 der ADR). Stattdessen die reine
  UMD-Datei, 896 KB. Preis: die `createUniver()`-API entfällt, die Einrichtung
  wird von Hand geschrieben.
- **Den Import sofort mitbauen.** Er ist entsperrt, aber er ist nicht der erste
  Schritt — eine leere Tabelle, die rechnet, ist mehr wert als eine, die fremde
  Dateien liest und noch nichts kann.

## Was bewusst NICHT getan wird, samt Preis

- **Kein `xlsx`-Rundlauf.** SheetJS ist nicht installiert, und ADR-016 führt die
  Frage als eigene offene. **Preis:** Wer eine Tabellendatei aus einem anderen
  Programm hat, kann sie zunächst nicht öffnen. Das trifft genau den
  Steuerfall und ist der nächste Schritt danach, nicht dieser.
- **Keine Formeln, die auf den Wissensbestand zugreifen.** Eine Zelle, die einen
  Knoten liest, wäre ein neuer Weg in den Speicher hinein, an Ausweis und
  Belegvertrag vorbei. **Preis:** Die Tabelle kann vorerst nur rechnen, nicht
  nachschlagen.
- **Keine Zusammenarbeit zweier Personen an einem Blatt.** Das CRDT trägt heute
  Dokumente, nicht Tabellen. **Preis:** ein Blatt hat einen Bearbeiter.

## Woran sich Erfolg messen lässt

Nicht „der Bildschirm erscheint". Sondern:

1. Eine Domäne **ohne** angeforderte Tabelle bekommt keine — belegt am Katalog,
   nicht an der Oberfläche.
2. Die Menge der verfügbaren Funktionen **ist gleich** der erlaubten Menge.
3. Eine Formel mit Zellbezug statt benanntem Bereich wird **sichtbar beanstandet**.
4. Eine Rechnung, die der Betreiber sonst als Skript bekommen hätte, entsteht als
   Blatt — und ihre Herleitung ist ein Klick, nicht eine Codelesung.

## Fortschreibung

Nach der Umsetzung: was anders kam als geplant, und warum.
