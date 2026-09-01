# Teilplan 03 — alle MUST/MUST-NOT und P67

## Ziel

Jede kanonische MUST/MUST-NOT-Zeile besitzt ein gegen Primärevidenz geprüftes
Verdict. Kein älteres Nicht-PASS-Gate wird durch den Bereich P71-P104 verdeckt.

## Schritte

1. Candidate HEAD/Status prüfen.
2. Root-Zeilen maschinell auflisten. Für jede MUSS/MUSS-NICHT-Zeile AC,
   Produktgate und Testbefehl erfassen. Keine neue normative Liste schreiben.
3. `PASS`: aktuellen Primärtest ausführen. `TEILWEISE/FAIL/NOT RUN`: Karte.
   `DEFERRED/PILOT`: Trigger, Owner und Aktivierungsbedingung prüfen; ein bloßes
   Label genügt nicht.
4. Vorrangig P04, P05, F05, P60, P67 und jedes weitere tatsächliche Nicht-PASS.
   Aussagen zur Retrieval-Wirkung benötigen echte Aktions-/No-Memory-Baseline;
   Zufuhr allein ist keine Wirkung.
5. Jede Karte höchstens zwei Produktdateien plus Tests. Red aus richtigem Grund,
   Root-Cause-Fix, Positiv- und Negativgegenprobe, atomarer Kandidatencommit.
6. P67 nur auf frischen/temporären DBs: CPU-, Schema-, Trigger-, Backup/Restore-,
   Korruptions-, Pfad-, Privacy- und Paketgates. Nach Schemaänderung Trigger-SQL
   aus `sqlite_master` prüfen.
7. Niemals Produktiv-DB/MCP/Backup öffnen oder Freeze aufheben. Deshalb bleibt
   P67 höchstens `CANDIDATE PASS / LIVE VALIDATION OPEN`.
8. Fahrtenbuch-Blindfund nicht als unabhängigen Wiederfund zählen; P88-
   Kardinalitätsfixture nur als synthetischen Erkennungsbeleg führen.
9. Am Ende vollständiges Ledger ausgeben: jede Nicht-FINAL-PASS-ID einzeln.

## Abschlussgate

```text
PHASE=03
VERDICT=PASS|FAIL
HEAD_OUT=<hash>
MUST_TOTAL=<n>
REVERIFIED_PASS=<IDs>
CANDIDATE_PASS=<IDs>
LEGIT_DEFERRED=<ID:defer-gate>
OPEN=<ID:exact-AC:next-probe>
P67=LIVE_VALIDATION_OPEN
DB=UNTOUCHED/FROZEN
PUSH=NOT_DONE
```

## Neues Kontextfenster öffnen

Laufstate mit Abschlussblock, Cachemetriken und
`next_phase_path=/Volumes/daten/Begod2026/brainlehr/docs/qwen_abschluss/04_HERMES_ZWEI_REPOS.md`
atomar aktualisieren und validieren. Neues Hermes-Kontextfenster öffnen und
exakt den unveränderten Inhalt von `STARTPROMPT_STABLE.md` senden.
