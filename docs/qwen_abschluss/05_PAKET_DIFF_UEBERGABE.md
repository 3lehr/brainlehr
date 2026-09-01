# Teilplan 05 — kombinierte Gates, Paket und Diffgrenze

## Ziel

Ein reproduzierbarer Kandidat ist aus frischem Checkout installierbar; alle
MUST/MUST-NOT-Verdicts und beide Repo-Grenzen sind vollständig für Codex
übergeben. Keine Implementierung mehr beginnen.

## Schritte

1. Beide Candidate HEADs und saubere Candidate-Worktrees prüfen.
2. Fokussierte P71-P104-Suite, Katalog-/Plan-/Handofftests und anschließend die
   vollständige deterministische CPU-Suite auf frischer temporärer DB.
3. Fehler nicht über Skip/xfail/Allowlist glätten. Ersten echten Fehler bis zur
   Root Cause verfolgen; fällt er in eine frühere Karte, dorthin zurück, eigener
   Commit, betroffene Suites erneut.
4. `uv build --offline`; Wheel und sdist SHA-256. Beide in je frische Umgebung
   installieren; Kernimporte, CLI und MCP-Schema-Smoke ohne Produktiv-DB.
5. Karten/Currentness, allowlisted Public Export und Pfad-/Secret-/Prompt-/
   Transcript-Leakscan gegen Fixtures. Kein echter MCP/DB-Aufruf.
6. Eigentumsgrenze je Repo:

   ```bash
   git status --short
   git diff --cached --name-status
   git diff --cached --numstat
   git log --oneline <base>..HEAD
   git diff --stat <base>..HEAD
   git diff --check <base>..HEAD
   ```

7. Jeden Commit gegen erwartete BDW-IDs, Pfade und Zeilenzahl prüfen. Kein P2,
   DB, Backup, Korpus, fremdes untracked Material oder Hostpatch.
8. Qwen pusht/restartet nicht mehr und erklärt nicht FINAL PASS.

## Abschlussgate

```text
PHASE=05
VERDICT=CANDIDATE_PASS|CANDIDATE_FAIL
BRAINLEHR_BASE=<hash>
BRAINLEHR_HEAD=<hash>
ADAPTER_BASE=<hash>
ADAPTER_HEAD=<hash>
COMMITS=<ordered hashes with BDW IDs>
FOCUSED=<commands/count/duration>
FULL_SUITE=<command/count/duration/verdict>
WHEEL=<path/sha256/install-smoke>
SDIST=<path/sha256/install-smoke>
LEAKSCAN=<verdict>
OWNERSHIP=<exact included paths/counts>
PROTECTED=<verified untouched classes>
OPEN_MUST=<each ID or none>
P67=LIVE_VALIDATION_OPEN
DB=UNTOUCHED/FROZEN
PUSH=NOT_DONE
```

## Neues Kontextfenster öffnen

Laufstate mit Abschlussblock und
`next_phase_path=/Volumes/daten/Begod2026/brainlehr/docs/qwen_abschluss/06_CODEX_ENDABNAHME.md`
atomar aktualisieren und validieren. Qwen beenden und den Laufstate-Pfad an
Codex übergeben. Der Qwen-Startprompt wird nicht als Codex-Prompt missbraucht;
Codex liest Teilplan 06 und validiert unabhängig aus Primärevidenz.
