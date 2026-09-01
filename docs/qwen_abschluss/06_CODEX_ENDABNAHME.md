# Teilplan 06 — unabhängige Codex-Endabnahme

## Ziel

Qwen-Kandidaten werden nicht vertraut, sondern aus frischen Checkouts gegen den
kanonischen Katalog wiederholt. Nur Codex kann FINAL PASS, Live-P67-Freigabe,
Integration und privaten Push erklären.

## Schritte

1. Candidate-Hashes und Commitobjekte auf Existenz prüfen; keine Working-tree-
   Dateien als Beleg verwenden.
2. Jeden Commit lesen: Diff, BDW-ID, Teständerungen, Produktänderung, numstat,
   Handoff. Self-proof und zusammen mit Produktcode gelockerte Tests ablehnen.
3. Fokussierte Red-/Green-Behauptungen durch Mutations-/Negativgegenprobe
   unabhängig prüfen.
4. Volle deterministische Suite, Paketbau und frische Wheel-/sdist-Installation
   wiederholen.
5. Hermes-Adaptermatrix 3.11-3.13 und P74 nach kontrolliertem Neustart
   wiederholen; Hostpatch separat lassen.
6. Vollständiges MUST/MUST-NOT-Ledger gegen aktuelle Produktgate-Zellen.
7. P67-Liveaudit erst jetzt: benannte Backup-/Restore-Grenze, DB-Integrität,
   installierte Trigger-SQL, Auditkette, Pfadhygiene, Project ensure/context/
   change, Currentness und allowlisted Export. Keine Reparatur ohne neue
   Copy-first-Redprobe.
8. Nur vollständig isolierbare Commits integrieren. Cached name-status,
   numstat und full diff vor jedem Commit/Push; `git show --stat` danach.
9. Private Origin-URL verifizieren, pushen, fetch, Remote-HEAD exakt gegen
   lokalen Hash vergleichen. Niemals lokalen Hermes-Hostpatch upstream pushen.
10. FINAL PASS nur wenn kein kanonisches MUST/MUST-NOT offen ist. Andernfalls
    exakte ID und nächste Probe, kein Teilabschluss.

## Abschlussgate

```text
FINAL_VERDICT=PASS|FAIL
BRAINLEHR_HEAD=<hash>
ADAPTER_HEAD=<hash>
REVERIFIED_TESTS=<commands/counts>
PACKAGE_HASHES=<wheel/sdist>
P67=<live verdict/evidence>
MUST_OPEN=<IDs or none>
INTEGRATION=<commits>
PUSH=<remote/branch/hash or NOT_DONE>
REMOTE_HEAD_MATCH=<yes/no/not_done>
PROTECTED_MATERIAL=<unchanged verdict>
```

## Neues Kontextfenster öffnen

Falls der technische Endlauf selbst den Kontext füllt, öffne ein letztes
reines Berichtsfenster mit diesem Prompt:

```text
Erstelle ausschließlich den knappen Brainlehr-Endbericht aus diesem
Endabnahmeblock: <BLOCK>. Keine Tools, keine neue Implementierung, keine
Statusverbesserung. Nenne FINAL PASS nur bei MUST_OPEN=none, P67=PASS,
REMOTE_HEAD_MATCH=yes und unverändertem Schutzmaterial; sonst FINAL FAIL mit
exakter BDW-ID und nächster Probe.
```
