# Inventur Verbund /Volumes/daten/Begod2026 — 2026-08-09T21:40:00+0200

Nur-Lesen-Bestandsaufnahme. Alle Zahlen unten mit Werkzeugaufruf nachgemessen (`sqlite3`, `find`, `python3 json.load`), keine übernommen ohne Prüfung.

## Vorab: Zahlen aus der Ausgangslage geprüft

- **38 Verzeichnisse oberste Ebene** — NICHT bestätigt. `find . -maxdepth 1 -mindepth 1 -type d` liefert **41** (inkl. `.claude`), **40** ohne versteckte Verzeichnisse. Befund, nicht übernommen.
- **knowledge.db Knoten je project_id** — bestätigt, exakt: `sqlite3 brainlehr/knowledge.db "SELECT project_id, COUNT(*) FROM knowledge_nodes GROUP BY project_id"` → nasa-llis 1638, shared 254, brainlehr 49, begod 32, openlehr 32, fahrtenbuch 25, stadtwerke 2, aka 1, bebetter 1, wohlair 1. Summe 2035.
- **"9 Netze, 297 Paper, 1624 belegte Zitationskanten"** — NICHT bestätigt. `grep -rl "297 Paper\|1624\|9 Netze\|neun Netze"` über den ganzen Verbund (Ausschlüsse s. Rastervermerk) findet **keinen einzigen Treffer** außerhalb von Zufallstreffern in unabhängigen JSON-Dateien (Trainingsläufe in `afrika/apps/beatdetection/...`, die die Zeichenkette "1624" o.ä. rein numerisch enthalten, kein Bezug zu Papernetzen). Die Übergabenotiz-Zahl ist im Repo nicht auffindbar — das IST das Ergebnis für diesen Punkt.

## TEIL 1 — welches Material liegt wo

### Zitationsnetze / Papernetze (`citation-network.json`, tiefensuche über den ganzen Baum, Ausschlüsse s. u.)

Tiefe-4-Suche (wie in der Aufgabenstellung) findet nur 2 Treffer, weil die meisten Netze tiefer liegen (`docs/papers/<domäne>/citation-network.json`, 5 Ebenen). Vollständige Suche (ohne Tiefenbegrenzung, mit Ausschlüssen) findet **7 inhaltlich unterschiedliche Netze**, davon eines massenhaft als Kopie über ~20 Projektverzeichnisse und mehrere `.claude/worktrees`-Kopien gespiegelt (identischer Inhalt, `begod/knowledge/apps/afrika-desktop-protokoll/papers/citation-network.json` — Teil der `begod/knowledge`-Mirror-Struktur, die praktisch jedes Fleet-Projekt trägt):

| Pfad (primärer Fundort) | Papers (nodes) | Kanten (edges) | Domäne |
|---|---|---|---|
| `setfunk/docs/papers/citation-network.json` | 25 | 3 | Set-Kommunikation WLAN/PTT |
| `openlehr/docs/papers/citation-network.json` | 31 | 31 | Steuerrecht Fotograf/WEG (§18 EStG, §35a EStG) |
| `hub/docs/papers/brainlehr/citation-network.json` | 29 | 6 | Wissensspeicher-Architektur (Nanopubs, TMS/ATMS) |
| `fahrtenbuch/apps/openhood/docs/papers/citation-network.json` | 7 | 5 | HU/AU-Prüfkriterien (Rechtsnormen statt Papers) |
| `afrika/docs/papers/lyrics-stt/citation-network.json` | 12 | 28 | Lyrics/STT/Song-ID |
| `openlehr.worktrees/agents-curved-wolf/docs/papers/akademia-fortbildung-evidence/citation-network.json` | 8 | 10 | AKA-Fortbildung/CPD-Zahnmedizin |
| `begod/knowledge/apps/afrika-desktop-protokoll/papers/citation-network.json` (gespiegelt in ~20 Projekten + Worktrees, z. B. `hub/`, `openlehr/`, `snake/`, `wpdrop/`, `steueroase-asien/`, `stiftshuette/`, `begem/`, `begem2026/`, `buckeberg/`, `design-lab/`, `drobo-nas/`, `schwarmwacht/`) | 63 | 517 | "BEGOD Universum (P24 global)" |

**Summe: 175 Papers, 600 Kanten, 7 Netze** — nicht 297/1624/9. Weder Paper- noch Kantenzahl noch Netzzahl der Übergabenotiz treffen zu.

`aka-raumstation` und `afrika` gezielt geprüft:
- **`aka-raumstation`**: KEIN `citation-network.json`, kein `docs/papers`-Verzeichnis. Vorhanden: `begod/knowledge/deep-research/` mit 8 Dateien (Marktanalyse, Fortbildungspflicht-Zahlen, ROI-Modell, Einwände-Synthese — Recherche-Rohmaterial, keine Zitationsnetz-Struktur). → **kein Papernetz gefunden**, Vermutung widerlegt.
- **`afrika`**: EIN eigenes Papernetz vorhanden (`docs/papers/lyrics-stt/citation-network.json`, 12 Papers/28 Kanten), plus 9 PDF-Volltexte direkt unter `docs/papers/` ohne eigenes Netz-JSON (Beat-Tracking-Domäne) und 3 lose Markdown-Paper (`paper-begod-vs-moltbot.md`, `paper-methodik-mathematik.md`, `paper-security-analysis.md`). Vermutung bestätigt, aber kleiner als vielleicht erwartet.

### ADR / Konsil je Verzeichnis (`docs/adr`, `docs/konsil`, `begod/knowledge/konsil`, `begod/desktop/lib/features/adr` — .md/.json gezählt)

| Verzeichnis | ADR-Dateien | Konsil-Dateien | Bemerkung |
|---|---|---|---|
| afrika | 26 | 23 | eigenständig, kein Mirror |
| aka-raumstation | 0 | 0 | stattdessen `begod/rfcs/` (1 Template) |
| begem | 28 | 213 | inkl. `begod/knowledge/konsil`-Mirror |
| begem2026 | 0 (nur leerer adr-Ordner unter desktop/lib) | 199 | |
| brainlehr | 1 | 0 | eigenes `docs/adr/`, kein Konsil-Ordner |
| buckeberg | 28 | 215 | |
| design-lab | 27 | 147 | |
| drg | 25 | 14 | |
| drobo-nas | 26 | 105 | |
| fahrtenbuch | 58 | 198 | größter reiner ADR-Bestand |
| hub | 155 (davon meiste in `.claude/worktrees`-Kopien) | 836 (davon meiste Worktree-Kopien) | Mirror-Explosion |
| legacylink | 26 | 18 | |
| markusx25 | 27 | 14 | |
| openhood | 25 | 15 | |
| openlehr | 43 (echt, ohne Worktrees) / 155 (mit 4 Worktree-Kopien) | 293 (echt) / 1137 (mit Worktrees) | größter Konsil-Bestand |
| openlehr.worktrees | 0 | 89 | |
| openlehr_stale_2026-07-22 | 29 | 288 | Altstand, dupliziert |
| pflegelotse | 25 | 15 | |
| phoenix | 25 | 14 | |
| schwarmwacht | 31 | 127 | |
| setfunk | 5 | 19 | |
| sigmaforge | 1 | 0 | |
| snake | 29 | 225 | |
| steueroase-asien | 28 | 213 | |
| stiftshuette | 26 | 119 | |
| UsbKabelTester | 26 | 14 | |
| wohlair | 9 | 0 | |
| wpdrop | 28 | 196 | |
| **kein Material** | 308, MosaikplanLegacy, _ANALYSE, begod, docs, mosaikplan, schnaeppvalid, simulatoren, wordpress.nosync | — | „kein Wissensmaterial gefunden" |

Muster: fast jedes Fleet-Projekt trägt eine vollständige `begod/knowledge/{konsil,deep-research,meta,apps}`-Spiegelstruktur mit identischem Inhalt (gleiche Konsil-Dateien, gleiche `paper-network-global.json`, gleiche `phoenix-dr-24-…csam-network…json` — vermutlich zentral verteilt/synchronisiert). Die hohen Konsil-Zahlen in begem/begem2026/buckeberg/steueroase-asien/design-lab/snake/wpdrop/drobo-nas/stiftshuette (100–225 je Projekt) sind zu einem erheblichen Teil dieselbe gespiegelte Sammlung, kein 1:1-Maß für eigenständiges Wissen dieses Projekts — nicht einzeln dedupliziert, hier als Rohzahl ausgewiesen.

## TEIL 2 — Material gegen Wissensspeicher, größte Lücken

Gegenüberstellung Material (Teil 1) vs. `knowledge.db`-Knoten nach project_id/Pfadpräfix (s. Tabelle oben unter „Vorab"). Von den 27 Projektverzeichnissen mit ADR/Konsil-Material haben nur **4** einen project_id-Eintrag in der zentralen `knowledge.db`: brainlehr (49), begod (32, größtenteils Pfade `/apps/<name>/…` für Fremdprojekte), openlehr (32), fahrtenbuch (25). Alle übrigen 23 Projekte mit eigenem `docs/adr`/`docs/konsil` — afrika, begem, begem2026, buckeberg, design-lab, drg, drobo-nas, legacylink, markusx25, openhood, pflegelotse, phoenix, schwarmwacht, setfunk, snake, steueroase-asien, stiftshuette, UsbKabelTester, wpdrop u. a. — haben **keinen einzigen** zentralen Knoten (Ausnahme: `stadtwerke` 2, `wohlair` 1, `aka` 1, `bebetter` 1 — Einzelnotizen, kein systematischer Bestand).

**Die drei größten Lücken:**

1. **afrika** — 26 ADR-Dateien, 23 Konsil-Dateien, ein eigenes Papernetz (12 Papers/28 Kanten), 8 lange Recherche-/Strategie-Dokumentverzeichnisse (`docs/research`, `docs/strategy`, `docs/validation`, `docs/beta`, …) — **0 Knoten** unter project_id `afrika` oder Pfadpräfix `/afrika` in `knowledge.db`. Größte Einzellücke: eigenständiges, nicht gespiegeltes Material ohne jede zentrale Erfassung.
2. **openlehr (Konsil-Tiefe)** — 293 eigene Konsil-Dateien (ohne Worktree-Duplikate) plus 43 ADR gegen nur 32 Knoten in `knowledge.db`. Selbst wenn nur ein Bruchteil der Konsil-Dateien wissenswert ist, liegt die Erfassungsquote deutlich unter 15 %.
3. **Die ~15 begod-Fleet-Apps ohne jeden zentralen Knoten** (begem, begem2026, buckeberg, design-lab, drg, drobo-nas, legacylink, markusx25, openhood, pflegelotse, phoenix, schwarmwacht, setfunk, snake, steueroase-asien, stiftshuette, UsbKabelTester, wpdrop) — jede trägt 14–225 Konsil- und 25–31 ADR-Dateien, zusammen mehrere Tausend Dateien, aber **project_id kommt in `knowledge.db` bei keiner davon vor** (setfunk taucht nur indirekt über einzelne `begod/apps/setfunk-*`-Knoten unter project_id `begod` auf — 8 Knoten für ein Projekt mit 5 ADR/19 Konsil-Dateien). Diese Projekte führen ihr Wissen lokal (`begod/knowledge/konsil` je Projekt), ohne Anschluss an den zentralen brainlehr-Speicher.

## TEIL 3 — wie fremdes Wissen hereinkommt

**Präzedenzfall NASA-LLIS, nachvollzogen:**

- Import-Skript: `brainlehr/nasa_llis_import.py`. Liest `llis.csv` (MIT-lizenziert, NASADatanauts/llis_topicModel), schreibt `project_id='nasa-llis'`, `parent_path='/nasa-llis'`, `id='nasa-llis-<LessonId>'` (idempotent, `INSERT OR IGNORE`). Trockenlauf ist Voreinstellung, `--write` für echten Import, `--delete` für restlose Entfernung (project_id + Tag `nasa-llis-import`). Explizit **kein** Eintrag in `lessons_learned` — „das sind fremde Lehren, keine eigenen".
- Einordnung als Nachschlagewerk: `brainlehr/migrate_gattung.py`. Fügt Spalte `gattung` (`arbeitsbestand` default, `nachschlagewerk` als zweiter erlaubter Wert, per BEFORE-Trigger erzwungen) additiv per `ALTER TABLE` hinzu. Erkennungsregel für „ist Nachschlagewerk": `(source LIKE '%nen.nasa.gov%' OR source LIKE '%llis.csv%') AND anlass='skript'` — **source** (Herkunfts-URL/Datei, unveränderlich) UND **anlass='skript'** (automatisiert erzeugter Inhalt, nicht bloß erwähnt) zusammen, weil `source` allein einen Ausreißer mitgezogen hätte (eigene Notiz, die llis.csv nur zitiert). Nachgemessen: 1640 Knoten tragen `anlass='skript'`+source-Treffer, davon 1638 echte NASA-Datensätze (project_id nasa-llis) und 2 fachfremde Stadtwerke-Testdaten (project_id shared) — 0 Differenz zur Zielzahl.
- Zugriff getrennt vom Regelbetrieb: `brainlehr/nachschlagewerk_suche.py` — eigenständiges CLI-Modul (kein MCP-Werkzeug), durchsucht **ausschließlich** `gattung='nachschlagewerk'` per FTS5/bm25. Der automatische Recall-Hook (`haken/knowledge_recall_hook.py` + `gattung_filter.py`) schließt `nachschlagewerk`-Knoten dagegen aus dem automatischen Abruf aus — Nachschlagewerke sind durchsuchbar, aber stumm, bis jemand gezielt fragt.

**Daraus abgeleiteter wiederverwendbarer Weg für neues, noch nicht konformes Wissen:**

1. Eigenes Importskript nach Vorbild `nasa_llis_import.py`: eigene `project_id`, ein eigener Tag zur restlosen Entfernbarkeit, Trockenlauf als Voreinstellung, Idempotenz über eine stabile ID aus dem Quelldatensatz.
2. Pflichtfelder, die sich **maschinell ableiten lassen**: `id` (aus Quell-ID), `path`/`parent_path` (aus Namensschema), `title`/`summary` (aus Rohdaten, ggf. gekürzt), `source` (Quell-URL/-Datei, aus dem Importvorgang bekannt), `anlass='skript'` (weil automatisiert erzeugt), `created_at`/`updated_at` (Zeitstempel des Laufs).
3. Pflichtfelder, die eine **menschliche Entscheidung verlangen** und sich nicht ableiten lassen: `gattung` (arbeitsbestand vs. nachschlagewerk — ist das fremde Material zitierfähiges Wissen oder nur Rohdatensammlung?), `norm_entscheidung` (offen/keine_norm/norm_befristet/norm_unbefristet — ist der Inhalt eine geltende Norm/Regel oder ein Fakt?) mit den davon abhängigen Pflichtfeldern `norm_entschieden_von`/`norm_entschieden_grund`, sowie bei befristeten Normen `norm_rang`/`gilt_ab`. Diese Felder sind per BEFORE-Trigger in `schema.sql` hart erzwungen (`RAISE(ABORT,…)` bei leer/widersprüchlich) — ein Import kann sie nicht umgehen, muss sie aber bewusst setzen, nicht raten.
4. Trennung vom Regelbetrieb: neuer Import bekommt eine eigene `gattung='nachschlagewerk'`-Markierung und bleibt außerhalb des automatischen Abrufs, bis jemand ihn ausdrücklich prüft und ggf. auf `arbeitsbestand` umstuft — genau das Muster, das NASA-LLIS vorgibt.

## Rastervermerk

**Durchsucht:** alle 40 sichtbaren Verzeichnisse oberster Ebene unter `/Volumes/daten/Begod2026` (plus `.claude`, nicht relevant für Material), bis Tiefe 4–6 je nach Suchmuster.

**Muster:** `find … -iname "citation-network*.json"` (Tiefe 4, wie vorgegeben) und ohne Tiefenbegrenzung; `find … -type d -iname adr`, `-iname konsil`; `find … -iname "*network*.json"`; `grep -rl "297 Paper\|1624\|9 Netze\|neun Netze"`; `sqlite3 brainlehr/knowledge.db` diverse `SELECT … GROUP BY project_id/gattung`; `python3 json.load` auf alle 7 gefundenen `citation-network.json` für `meta`/`nodes`/`edges`-Zählung.

**Bewusst ausgelassen** (wie vorgegeben, plus eigene Ergänzung): `_LOCAL_CACHE.nosync`, `archive`, `wordpress.nosync`, `node_modules`, `.venv*`, `.git`, zusätzlich `_LEGACY_QUARANTINE` (Legacy-Quarantäne, kein aktives Material) nur oberflächlich geprüft (keine Datei-Einzelsichtung). Nicht einzeln geöffnet: der volle Inhalt der 293 openlehr-Konsil-Dateien und der Hunderten begod/knowledge-Konsil-Spiegel-Dateien in den anderen Fleet-Projekten — nur gezählt, nicht gelesen; Aussage „eigenständig vs. gespiegelt" beruht auf Dateipfad-/Namensgleichheit (z. B. identischer Dateiname `konsil-global-paper-network-2026-03-01.json` in 10+ Projekten), nicht auf Byte-für-Byte-Diff.

---

Fünf-Sätze-Fazit: Die drei größten Lücken sind afrika (eigenständiges Material, null zentrale Knoten), openlehr (293 eigene Konsil-Dateien gegen 32 Knoten) und rund 15 begod-Fleet-Apps, die je 14–225 Konsil- und 25–31 ADR-Dateien lokal führen, ohne dass ihre project_id in der zentralen `knowledge.db` je auftaucht. Die neun Papernetze mit 297 Papern und 1624 Kanten existieren nicht — gefunden wurden 7 unterschiedliche Netze mit zusammen 175 Papern und 600 Kanten, die Zahl aus der Übergabenotiz ist im ganzen Verbund per Volltextsuche nicht auffindbar. Der NASA-LLIS-Weg (Importskript mit eigener project_id/Tag, additive `gattung`-Spalte mit hart erzwungener Zwei-Werte-Entscheidung, separates Suchmodul außerhalb des Regelbetriebs) ist als wiederverwendbares Muster für neues, unkonformes Wissen direkt kopierbar. Maschinell ableitbar sind id/path/title/summary/source/anlass/Zeitstempel; menschlich zu entscheiden bleiben gattung (Nachschlagewerk oder Arbeitsbestand) und die komplette Normschicht (norm_entscheidung + Begründung + ggf. Rang/Gültigkeit). Auch die Ausgangszahl „38 Verzeichnisse" stimmt nicht exakt (gemessen 40 sichtbare, 41 mit `.claude`).
