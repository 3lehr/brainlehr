# brainlehr

Ein projektübergreifender Wissensspeicher — genauer: **kein Speicher für Wissen, sondern eine erzwungene Disziplin, an der Wissen anfällt.**

Der Unterschied ist nicht sprachlich. Er entscheidet, was hier drin ist:

| als Speicher gedacht | als Disziplin gedacht |
|---|---|
| Erfolg = viele Einträge | Erfolg = keine Aussage ohne Herkunft |
| fehlende Inhalte sind der Mangel | umgehbare Regeln sind der Mangel |
| der Abruf ist das Herz | die Schranke ist das Herz |
| portabel heißt: Daten mitnehmen | portabel heißt: **Regeln** mitnehmen |

Die Regeln stehen als **31 Trigger in der Datenbank**, nicht im Anwendungscode. Sie binden jeden Schreiber — auch `sqlite3` von Hand, auch ein fremdes Werkzeug, auch ein Skript, das diese Zeilen nie gelesen hat. Wer ohne Herkunft schreibt, wird abgewiesen. Wer eine Herkunft umschreiben will, wird abgewiesen; nachtragen darf er.

## Installieren

```bash
python3 brainlehr.py init /pfad/zum/ort
```

Legt an einem beliebigen Ort eine leere, vollständig regelbewehrte Datenbank an und sagt, was sie enthält. Ein vorhandener Bestand wird nie überschrieben.

Dann die Automatik anschließen — **ohne sie ist es nur ein Speicher**:

```bash
python3 brainlehr.py haken
```

Zeigt, welche vier Haken fehlen und was jeder tut. Mit `--einbauen` trägt der Befehl sie in `~/.claude/settings.json` ein (Sicherung vorher, zweiter Lauf ändert nichts).

| Haken | Wann | Was er erzwingt |
|---|---|---|
| `haken/knowledge_recall_hook.py` | bei jedem Prompt | passendes Wissen wird eingespielt, ohne dass jemand es abruft |
| `haken/auftrag_recall_hook.py` | bei jedem Prompt | offene Aufträge werden gemeldet |
| `haken/mcp_veraltet.py` | bei jedem Prompt | Warnung, wenn ein laufender Server älteren Code hält als die Datei |
| `haken/knowledge_capture_hook.py` | am Sitzungsende | Dauerhaftes wird abgelegt, statt im Gesprächsverlauf zu verfallen |

Turnusmäßig, kein Haken: `python3 haken/kurator_taeglich.py` (Verdichtung, einmal täglich).

## Bestand mitnehmen

```bash
python3 brainlehr.py raus auszug.jsonl
```
```bash
python3 brainlehr.py rein auszug.jsonl --db /neuer/ort/knowledge.db
```

Zeilenweise statt Dateikopie, aus einem Grund: **eine SQLite-Datei lässt sich nicht zusammenführen, git überschreibt sie.** Zeilen lassen sich vergleichen, zusammenführen und lesen.

Der Auszug trägt Knoten, Lehren, Kanten, Einstellungen, das Zugriffsprotokoll und die Eskalationen. Nicht mit gehen die Vektoren und der Volltextindex — beide ableitbar. Den Volltext bauen die Trigger beim Einlesen selbst auf; die Vektoren rechnet `build_embeddings.py` neu. Ein Vektor aus einem anderen Einbettungsmodell wäre still falsch, und still falsch ist schlimmer als fehlend.

**`knowledge.db` ist absichtlich nicht versioniert.** Versioniert wird `schema.sql`, `herkunft_unveraenderlich.sql` und ein Auszug unter `auszug/`. Grund: git führt eine Binärdatei nicht zusammen, es überschreibt sie — und am 2026-08-07 lag hier bereits eine beschädigte Fassung im Commit, womit die Versionsverwaltung als Rettungsweg wertlos war.

## Prüfen

```bash
python3 -m pytest tests -q
```

Der Test, der am meisten über dieses Vorhaben sagt, heißt `test_erstanlage_traegt_dasselbe_schema_wie_der_betrieb`. Er darf nur in eine Richtung ausschlagen: **der Betrieb darf nichts kennen, was eine Erstanlage nicht bekommt.** Am 2026-08-08 schlug er aus — eine frische Installation trug zwei Trigger, sechs Tabellen und zwei Spalten weniger als die gewachsene Datenbank, darunter ausgerechnet die Herkunftsschranke. Wer damals klonte, bekam brainlehr ohne die Regel, die brainlehr ist.

## Wo was liegt

```
knowledge_mcp_server.py     der Server (MCP über stdio) und zugleich die Bibliothek
schema.sql                  einzige Schemaquelle — Regeln gehören hierher, nicht in ein Skript
herkunft_unveraenderlich.sql die Herkunftsschranke
brainlehr.py                init / raus / rein / haken
haken/                      die Automatik samt haken/ort.py (ein Ort für den Pfad)
auszug/                     versionierte Auszüge des Bestands
tests/                      pytest
```

`BEGOD_KNOWLEDGE_DB` sticht den Vorgabepfad — geachtet von `haken/ort.py` und vom Server.
