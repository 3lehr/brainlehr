# Teilplan 04 — Hermes und zwei Repositories

## Ziel

Brainlehr und Hermes-Adapter besitzen getrennte Kandidatenhistorien; der lokale
Hermes-Hostpatch ist separat getestet. P20/P21/P74 sind gegen reale Adapter-
Klassen und die unterstützte Python-Matrix belegt.

## Schritte

1. HEAD/status/cached diff aller drei Grenzen prüfen.
2. Brainlehr P20, P21, P74 und Adapter README/provider/tests vollständig lesen.
3. Im Hermes-Adapter einen eigenen sauberen Kandidatenworktree/-branch auf dem
   verifizierten Adapter-HEAD verwenden. Hauptbaum-dirty Pfade nicht kopieren.
4. Red→green Providervertrag gegen echte Hermes-`MemoryManager`-/Provider-
   Klassen mit Fake-Transport:
   foreground genau ein Recall; cron/oneshot/background/subagent/unknown null
   Brainlehr-Writes; empty/timeout/error sichtbar; Retry keine Duplikate.
5. Built-in Hermes Memory und externer Brainlehr-Provider getrennt halten.
   Keine Prompts, Transkripte, Rohcode, Secrets oder temporäre Produktiv-DB.
6. Adaptertests unter Python 3.11, 3.12, 3.13. Erwartete Skips begründen, nicht
   verstecken.
7. Lokalen `/Users/lehrmacbook/.hermes/hermes-agent` Acht-Dateien-Patch nur
   testen: Context-Resolver, ACP/Agentinit und relevante Matrix. Datei-/Diffhash
   dokumentieren; kein Commit in Adapter, kein upstream Push.
8. Hermes kontrolliert einmal neu starten, wenn seit Phase 00 Code/Config
   geändert wurde. PID/Startzeit, effective context und P74 foreground-/deny-
   Matrix nach Neustart wiederholen.
9. Brainlehr- und Adaptercommit strikt getrennt; cached numstat/full diff je Repo.

## Abschlussgate

```text
PHASE=04
VERDICT=PASS|FAIL
BRAINLEHR_HEAD=<hash>
ADAPTER_HEAD=<hash>
HOST_HEAD=<hash>
HOST_DIRTY_HASHES=<separate list>
PY311=<count/verdict>
PY312=<count/verdict>
PY313=<count/verdict>
P74=<foreground/deny/retry matrix>
EFFECTIVE_CONTEXT=<n>
HERMES_PID_STARTED=<pid/time>
DB=UNTOUCHED/FROZEN
PUSH=NOT_DONE
```

## Neues Kontextfenster öffnen

Laufstate mit Abschlussblock, Cachemetriken und
`next_phase_path=/Volumes/daten/Begod2026/brainlehr/docs/qwen_abschluss/05_PAKET_DIFF_UEBERGABE.md`
atomar aktualisieren und validieren. Neues Hermes-Kontextfenster öffnen und
exakt den unveränderten Inhalt von `STARTPROMPT_STABLE.md` senden.
