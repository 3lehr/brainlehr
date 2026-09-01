# Teilplan 01 — Katalogdrift, P60 und P62

## Ziel

P99-P104 spiegeln aktuelle Primärevidenz; P60 schützt Graphen fail-closed;
P62 beweist, dass Embedding-Treffer keine Kanten erzeugen und BGE-M3 aktiv
bleibt. Graphify bleibt
nichtnormativer Zeuge und keine Abhängigkeit.

## Erlaubte Karte/Pfade

Vor Änderung mit `rg` tatsächliche Aufrufer finden. Höchstens:

- `docs/REQUIREMENTS_BRAINLEHR.md`
- bestehender Graph-Store und höchstens eine direkte Hilfsdatei
- fokussierter Graph-Store-Test
- `tests/test_requirements_brainlehr.py`
- `tests/test_code_retrieval_benchmark.py`
- neuer Master-/Teilplan nur bei nachweislichem Vertragsfehler

## Schritte

1. Candidate HEAD/Status gegen Phase-00-Block prüfen. Fremder Diff => FAIL.
2. Anforderungen- und Retrievaltests ausführen. Alte Erwartungen
   `NOT IMPLEMENTED`, `FAIL (V5)` oder `H0 undecided` müssen aus dem richtigen
   Grund rot sein.
3. P99-P104 gegen Produktdateien/committete Tests prüfen. Status nur mit echter
   Evidenz setzen. P103 bindet ausschließlich V9 raw
   `0d08110a4ba249ee2a080dd32154b3ce02de355206333ec02e9247cf382ef954`
   und collector
   `dbda275582eb179ea0a439f6009903578e8d94953e26cc8a323f89763e3f8626`.
   Kein Score-Rerun.
4. P60 Red-Tests im bestehenden Graph-Store:
   kleiner/partieller Neubau, unlesbarer nichtleerer Altgraph, Abbruch vor
   atomarem Replace, explizit legitimer Tombstone, Backup/Restore-Hash.
5. Gemeinsamen Write-Pfad reparieren. Originalbytes bleiben bei Reject gleich;
   kein neuer Store, keine Dependency.
6. P62 Gegenprobe: ein semantischer BGE-Treffer ohne belegte Graphkante darf
   keine Kante erzeugen; fehlendes CodeRank lässt BGE plus strukturellen Pfad
   unverändert. Stale Revision/Budgetende bleiben Gap.
7. Fokussiert grün, dann direkte Geschwistertests, `diff --check`, staged
   name-status/numstat/full diff.
8. Atomare Kandidatencommits: zuerst Katalog-/Testdrift, dann P60/P62-Code.
   Keine P2-Datei.

## Abschlussgate

```text
PHASE=01
VERDICT=PASS|FAIL
HEAD_IN=<hash>
HEAD_OUT=<hash>
COMMITS=<hash:BDW-IDs:path-count>
RED=<commands/results>
GREEN=<commands/count/duration>
P103=H0/INACTIVE/NOT_RERUN
GRAPHIFY=NONNORMATIVE/NO_DEPENDENCY
DB=UNTOUCHED/FROZEN
PUSH=NOT_DONE
GAP=<exakt oder none>
```

## Neues Kontextfenster öffnen

Laufstate mit Abschlussblock, Cachemetriken und
`next_phase_path=/Volumes/daten/Begod2026/brainlehr/docs/qwen_abschluss/02_P42_ANALYZER_OSS.md`
atomar aktualisieren und validieren. Neues Hermes-Kontextfenster öffnen und
exakt den unveränderten Inhalt von `STARTPROMPT_STABLE.md` senden.
