# Teilplan 02 — P42-Wahrheit und OSS-Zeugen

## Ziel

Konfiguration, Registry, Runner und Katalog sagen dieselbe Wahrheit über
SCIP/Semgrep/tree-sitter. Alle OSS-Finalisten sind explizit klassifiziert.

## Schritte

1. Candidate HEAD/Status prüfen.
2. Vollständig lesen: P36, P41-P43, P50-P54, P57, P91, P95, P98 sowie
   `.brainlehr.json`, Analyzer-Registry, Attestation, Runner und ihre Tests.
3. Rot-Test: eine Quelle ist `callable`, obwohl ausführbarer registrierter
   Runner/Version/Hash/Sandbox/Erfolgsbeleg fehlt; Gegenrichtung ebenfalls.
4. Kleinster Wahrheitsfix: entweder vollständig registrieren und real bounded
   ausführen oder sichtbar `planned/non-callable/gap`. Kein Tool darf durch
   Dokumentation promoted werden.
5. Nach Schema-/Serveränderung installierte Trigger-SQL in `sqlite_master` nur
   auf frischer Test-DB prüfen; Produktiv-DB bleibt zu.
6. Offizielle Primärquellen und lokale Messung je Zeuge:
   OpenSpec, Spec Kit, Graphify, GUAC, Syft/Grype, DevLake/GrimoireLab.
   Ergebnis je `integriert`, `gemessener Gap` oder `DEFERRED` mit belegtem
   Defer-Gate. Größe allein nie Grund. Keine Installation ohne nachgewiesene
   fehlende vorhandene Naht.
7. Graphify v8 nur als Zeuge dokumentieren: OSS-Renderer 2D vis.js/ForceAtlas2,
   query/path/explain, Provenienz, Community-Aggregation, fail-closed overwrite.
8. Fokussierte Registry/Analyzer/Attestation/Requirementtests grün; keine
   Absenzbehauptung aus fehlendem Finding.
9. Atomarer Kandidatencommit nur über eigene Pfade.

## Abschlussgate

```text
PHASE=02
VERDICT=PASS|FAIL
HEAD_OUT=<hash>
P42=<callable channels with evidence | planned gaps>
OSS=<tool:classification:primary-source:local-gap>
TESTS=<commands/count/duration>
DB=UNTOUCHED/FROZEN
PUSH=NOT_DONE
GAP=<exakt oder none>
```

## Neues Kontextfenster öffnen

Laufstate mit Abschlussblock, Cachemetriken und
`next_phase_path=/Volumes/daten/Begod2026/brainlehr/docs/qwen_abschluss/03_ALLE_MUST_P67.md`
atomar aktualisieren und validieren. Neues Hermes-Kontextfenster öffnen und
exakt den unveränderten Inhalt von `STARTPROMPT_STABLE.md` senden.
