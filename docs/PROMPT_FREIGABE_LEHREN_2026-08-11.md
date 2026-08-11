# Auftrag: Die Freigabestufe der Lehren bekommt einen Schreibweg

**Angelegt:** 2026-08-11T11:07:02+0200
**Arbeitsort:** `/Volumes/daten/Begod2026/brainlehr` (NICHT aus einem openlehr-Worktree heraus)
**Vorbedingung:** Claude neu starten — 23 MCP-Serverprozesse fahren veralteten Code.

---

## Fakten (gemessen 2026-08-11, nicht geschätzt)

| Messung | Wert |
|---|---|
| `knowledge_nodes.freigabe` im Eigenbestand (ohne NASA) | `intern` 353 · `offen` 106 |
| `lessons_learned.freigabe` | `intern` 753 von 753 |
| Spalte `lessons_learned.freigabe` in `schema.sql` | existiert, `NOT NULL DEFAULT 'intern'`, Vermerk „B4.5-Nachtrag 2026-08-10" |
| Werte-Trigger für Knoten | erlaubt `offen`, `intern`, `gesperrt` |
| MCP-Werkzeug `knowledge_freigeben` | nimmt `node_id` — Knoten, nicht Lehren |
| `freigabe` im Eingabeschema von `lesson_record`, `lesson_update`, `knowledge_add` | in keinem |
| Lehren je Projekt | fahrtenbuch 254 · openlehr 220 · hub 191 · systemweit 179 · brainlehr 99 · buckeberg 49 |

`migrationen/migrate_freigabe.py` hält im Kopf ausdrücklich fest:
„keine Massenzuweisung von 'offen' oder 'gesperrt' an vorhandene Knoten — jeder
Bestandsknoten bleibt 'intern', bis jemand ihn einzeln entscheidet."

**Daraus folgt die Aufgabe, und nur sie:** Die 100 % `intern` bei den Lehren sind
die entworfene Voreinstellung, kein Defekt. Der Defekt ist, dass es **keinen Weg
gibt, sie einzeln zu ändern**. Der Melder liest die Spalte als „gebaute Regel ohne
Wirkung"; das ist erst dann richtig, wenn ein Schreibweg existiert und trotzdem
niemand ihn nutzt.

## Auftrag

Ein Schreibweg für `lessons_learned.freigabe`, gleiche Bauform wie bei den Knoten.
Nicht mehr.

1. Werte-Trigger (bi/bu) für `lessons_learned.freigabe` analog zu den bestehenden
   Knoten-Triggern — `offen`, `intern`, `gesperrt`.
2. Ein Weg, eine einzelne Lehre zu entscheiden. Ob als eigenes Werkzeug oder als
   Feld an einem bestehenden, entscheidet der Code — sieh nach, wie
   `knowledge_freigeben` es für Knoten löst, und folge dem.
3. Der Vorgang gehört ins `access_log` wie jede andere Entscheidung.

## Grenzen

- **Keine Massenzuweisung.** Kein `UPDATE … SET freigabe='offen' WHERE …`. Jede
  Lehre wird einzeln entschieden oder bleibt `intern`.
- **Fremd gehalten, Stand 2026-08-11T11:08:27** — und dieser Stand veraltet in
  Minuten, siehe unten: `messungen/messlauf_abrufguete_v2.py`,
  `migrationen/lauf_titelverteidiger_2026-08-08.py`, `runs/messlauf_abrufguete_v2.json`,
  `tests/test_stammformen.py`. Keine davon wird für diesen Auftrag gebraucht.
  `knowledge_mcp_server.py`, `kern/ausweis.py` und
  `tests/test_enigma_hausmeister_contract.py` standen um 11:06 noch als fremd
  gehalten und waren um 11:07:34 committet (`fix(enigma): project credential-bound
  reads`) — **also frei, aber genau deshalb vor Arbeitsbeginn neu prüfen**, nicht
  aus dieser Liste ablesen:
  `git status --short` und Register über
  `python3 -c "import sys; sys.path.insert(0,'hub/scripts'); from agent_register_ort import pfad; print(pfad())"`.
  Der Melder für parallele Sitzungen hat am 2026-08-11 nachweislich Entwarnung
  gegeben, während eine fremde Sitzung dieselbe Datei umbaute — die Dateiliste
  gilt, nicht sein Urteil.
- **Sachliche Kollision beachten, nicht nur die Datei-Kollision.** Die laufende
  Sitzung arbeitet an der Zweckprojektion (Enigma, `project credential-bound
  reads`). Freigabe und Projektion entscheiden dieselbe Frage — wer was sehen
  darf. Zwei getrennt getroffene Antworten darauf zeigt kein Git-Konflikt an.
  Vor eigenen Entwürfen deren letzten Stand lesen.
- Nicht committen: `NODE_INDEX.md`, `antwort_treffer.json`, `auszug/*.jsonl`,
  `bereinigung_log.jsonl` — Melderausgaben, keine Arbeit.
- Kein Push.

## Abnahme

- **Rot vor grün:** ein Test, der eine Lehre auf `offen` setzt und zurückliest,
  muss gegen den heutigen Stand fehlschlagen (es gibt keinen Weg dorthin).
- **Gegenprobe in beide Richtungen:** `offen` → `intern` muss ebenso gehen.
- **Negativfall:** ein unzulässiger Wert wird abgelehnt, nicht stillschweigend
  gespeichert — gleiche Fehlerform wie bei den Knoten.
- **Grenzwert:** alle drei erlaubten Werte einzeln geprüft.
- Bestehende Suite bleibt grün (vor der Änderung: 786 grün / 2 xfail laut STAND).

## Einsatz

Solange die Lehren keinen Schreibweg haben, ist die Freigabeschicht für den Teil
des Bestands blind, der anderen Projekten am meisten helfen würde — 749 Lehren
gegen 452 eigene Knoten. Jede Zusammenlegung von Beständen ruht auf dieser
Schranke; ohne sie wird vermischt, was sich nachträglich nicht mehr entmischen
lässt, weil dann für jede Zeile geraten werden muss, ob sie einmal intern war.

---

**Sieht der Code anders aus als hier beschrieben, halte dich an den Code und melde
die Abweichung.**
