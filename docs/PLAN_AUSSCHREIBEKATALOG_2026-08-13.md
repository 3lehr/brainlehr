# Ausschreibekatalog — die Kurzform findet nichts, die lange Form steht 133-mal da

Stand 2026-08-13T07:26:07+0200. Aufgabe 65, erweitert um die Betreiberforderung:
der Katalog soll **mitlernen und sich selbständig erweitern**.

## Der gemessene Ist-Stand

**Der Schaden ist belegt** (Commit `339eaee`, 2969 Dokumente). Je Abkürzung, wie
oft sie selbst im Bestand steht gegen die ausgeschriebene Form:

| kurz | steht selbst | lange Form | Urteil |
|---|---|---|---|
| `db` | 187 | 111 | harmlos, kommt selbst vor |
| `auth` | 31 | 3 | harmlos |
| `config` | 25 | 242 | schwach |
| `req` | 4 | 134 | schwach |
| `res` | 1 | 264 | fast tot |
| `fn` | 1 | 269 | fast tot |
| `impl` | **0** | **133** | **wertlos als Suchbegriff** |

**Der Schaden tritt heute aber nicht ein**, und das ist der zweite, wichtigere
Befund. Über 7649 protokollierte Suchen mit Text (`access_log.query`) kommen die
Abkürzungen praktisch nicht vor:

```
impl 2   req 1   fn 1   res 0   msg 0   err 0   val 0   param 0
db 80    repo 74   ctx 15   auth 8   config 6
```

Die einzigen häufigen (`db`, `repo`, `ctx`) sind genau die, die im Bestand
ohnehin vorkommen. Grund: **Caveman ist nicht verdrahtet** (0 Treffer in
`~/.claude/settings.json`, gemessen in derselben Nacht). Die 7649 Suchen
stammen aus unkomprimierten Antworten.

**Folge für den Bau:** Der Katalog ist **Vorsorge für einen Zustand, den es noch
nicht gibt**. Das macht ihn nicht falsch — der Betreiber hat Caveman angeordnet,
und sobald es wirkt, beißt `impl` 0 gegen 133. Es entscheidet aber die Bauform:
**Aus dem Protokoll lässt sich der Katalog heute nicht lernen, weil dort keine
Beispiele stehen.** Ein Lernverfahren ohne Signal lernt nichts und meldet
Erfolg — genau die Fehlerklasse dieser Nacht.

## Die Alternativen

**A — Handgepflegte Liste.** Abgelehnt als *einzige* Quelle: sieben Einträge
altern, niemand pflegt sie, und sie steht in derselben Reihe wie
`PROJECT_NOISE_OVERRIDES` („GERATEN, NICHT GEMESSEN"), die heute Nacht deshalb
ausgebaut wurde.

**B — Nur aus dem Suchprotokoll lernen.** Abgelehnt: gemessen 2 Vorkommen von
`impl` in 7649 Suchen. Kein Signal.

**C — Aus dem Bestand rechnen, aus dem Protokoll nachschärfen (gewählt).**
Der Zähler oben — Kurzform-Vorkommen gegen Langform-Vorkommen — ist bereits das
Erkennungsverfahren. Er braucht kein Protokoll und keine Pflege. Das Protokoll
kommt als **zweiter** Kanal dazu, sobald Caveman verdrahtet ist und echte
Kurzform-Suchen entstehen.

## Die drei Teile, in bindender Reihenfolge

**1 · Saat aus der Ursache, nicht aus dem Gedächtnis.** Die Abkürzungsliste
steht wörtlich in der Caveman-Fertigkeit (`DB/auth/config/req/res/fn/impl`).
Sie ist die *Ursache* der Kurzformen und damit die einzige nicht geratene
Quelle. Nicht selbst welche erfinden.

**2 · Bewertung aus dem Bestand.** Je Paar der Zähler oben. Aufnahme erst ab
einem Verhältnis, das gemessen wird statt gesetzt zu werden — `db` (187:111)
darf nicht in denselben Topf wie `impl` (0:133).

**3 · Erweiterung aus dem Protokoll**, erst wenn sie etwas findet: Suchbegriffe
mit **0 Treffern**, die Kurzform einer im Bestand häufigen Langform sind. Heute
liefert dieser Kanal nichts — das ist die **Nullmessung**, gegen die sich später
belegen lässt, dass er anspringt.

## Die Anwendung — und die eine Grenze, die nicht verhandelbar ist

**Übersetzt wird nur die ANFRAGE, niemals der gespeicherte Text.** Die Suche
läuft mit **beiden** Formen (`impl` ODER `Umsetzung`), sie ersetzt nicht.

Der Grund ist ein bezahlter Fehler, nicht Vorsicht: `L-d8c5fb`. In buckeberg
wurde die Abkürzung „TG" beim Einlesen stillschweigend zu „Tiefgarage"
aufgelöst und in ein **Quellfeld** geschrieben. Von dort wanderte sie in sieben
abgeleitete Fundstellen, davon zwei öffentlich erreichbare Seiten. Das Objekt
hat keine Tiefgarage, sondern 9 Einzelgaragen und 7 Stellplätze. Gefunden hat
es der Nutzer, nicht eine der Verarbeitungsstufen.

Zweite Grenze, aus derselben Nacht: **Der Katalog schlägt vor, er setzt nicht.**
Ein sich selbst erweiternder Katalog, der ungefragt Suchen umschreibt, ist
wieder eine Regel, die wirkt und die niemand bemerkt. Neue Paare gehen als
Vorschlag ein, wie `norm_entscheidung` es bereits vormacht.

## Was bewusst nicht getan wird, samt Preis

- **Keine Stammformreduktion, kein Synonymwörterbuch.** Preis: `Umsetzung`
  findet `umsetzen` nicht. Gewinn: der Katalog bleibt an sieben belegten Paaren
  messbar statt an einer Sprachtheorie.
- **Kein Umschreiben beim Einbetten.** Preis: Der Bestand behält seine
  Kurzformen. Gewinn: `L-d8c5fb` wiederholt sich nicht.
- **Keine Verdrahtung von Caveman in diesem Schritt.** Die Anordnung des
  Betreibers steht; sie ist ein eigener Schritt und darf nicht nebenbei
  passieren.

## Woran sich Erfolg misst

- **Rot vor grün an `impl`:** Eine Anfrage mit `impl` findet vorher 0 der 133
  Dokumente und nachher mehr als 0. Ein Verfahren, das diesen Fall nicht
  bewegt, ist nicht gebaut.
- **Negativfall:** Eine Anfrage mit `db` darf sich **nicht** messbar
  verschlechtern — 187 eigene Vorkommen sind ein echtes Signal, das eine
  Erweiterung verwässern kann.
- **Der gespeicherte Text ist byteweise unverändert.** Gezählt, nicht
  angenommen.
- **Der Protokollkanal meldet heute null Paare.** Das ist der erwartete Wert
  und wird als Nullmessung festgehalten, nicht als Fehler behandelt.

## Aufträge, fertig zum Übergeben

**Für alle Aufträge gleichermaßen gilt:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis` — ein
Startverzeichnis unter `.claude/worktrees/` ist ein alter Stand. Zuerst
`CLAUDE.md` lesen, dann diesen Plan. „Sieht der Code anders aus als hier
beschrieben, halte dich an den Code und melde die Abweichung." Kein `git add
-A`, kein Push, kein `git stash`. Committen mit expliziter Pfadliste
(`git commit -- pfad1 pfad2`), weil mehrere Agenten im selben Baum arbeiten.
Volle Suite **im Vordergrund** mit `timeout=600000` — sie braucht rund 230
Sekunden. Datenbanknamen nie fest verdrahten, immer über `kern/speicher`.

### Schritt 1 · Saat und Bewertung aus dem Bestand

| | |
|---|---|
| **Darf ändern** | eine neue Datei für den Katalog, dazu ihr Test unter `tests/` |
| **Tabu zusätzlich** | `haken/antwort_abruf.py`, `kern/embeddings.py`, `knowledge_mcp_server.py`, `schema.sql`, alles unter `runs/` |
| **Fakten** | Bestand 2969 Dokumente. `impl` 0 eigene Vorkommen gegen 133 lange, `fn` 1:269, `res` 1:264, `req` 4:134, `config` 25:242, `auth` 31:3, `db` 187:111. Die Kurzformenliste steht wörtlich in der Caveman-Fertigkeit und ist die einzige nicht geratene Quelle. |
| **Abnahme** | Die Aufnahmeschwelle wird **gemessen**, nicht gesetzt: `db` (187:111) darf nicht denselben Rang bekommen wie `impl` (0:133). Negativfall: eine Abkürzung, die im Bestand häufig selbst vorkommt, wird **nicht** aufgenommen. |

### Schritt 2 · Anwendung nur auf der Anfrage

| | |
|---|---|
| **Darf ändern** | den Abrufpfad an der Stelle, an der die Anfrage zerlegt wird, dazu dessen Test |
| **Tabu zusätzlich** | jede Stelle, die Text **speichert** oder **einbettet** — `kern/build_embeddings.py`, `kern/embeddings.py` |
| **Fakten** | `L-d8c5fb`: „TG" wurde beim Einlesen still zu „Tiefgarage" aufgelöst und wanderte in sieben abgeleitete Fundstellen, zwei davon öffentlich erreichbar; das Objekt hat 9 Einzelgaragen und 7 Stellplätze. Gefunden hat es der Nutzer. |
| **Abnahme** | Rot vor grün an `impl`: vorher 0 der 133 Dokumente, nachher mehr als 0. Negativfall: `db` verschlechtert sich nicht. Und der gespeicherte Text ist danach **byteweise unverändert** — gezählt, nicht angenommen. |

### Schritt 3 · Der Protokollkanal, samt seiner Nullmessung

| | |
|---|---|
| **Darf ändern** | ein Melder unter `melder/`, dazu sein Test |
| **Tabu zusätzlich** | der Katalog aus Schritt 1 und der Abrufpfad aus Schritt 2 — Schritt 3 liest nur |
| **Fakten** | 7649 protokollierte Suchen mit Text in `access_log.query`. Darin `impl` 2, `req` 1, `fn` 1, `res`/`msg`/`err`/`val`/`param` je 0. Häufig nur `db` 80, `repo` 74, `ctx` 15 — genau die, die im Bestand ohnehin stehen. |
| **Abnahme** | Der Kanal meldet heute **null** Paare. Das ist der erwartete Wert und wird als Nullmessung festgehalten, nicht als Fehler behandelt. Rot vor grün gegen einen **nachgestellten** Protokolleintrag mit einer echten Kurzform: dort muss er anschlagen. |
