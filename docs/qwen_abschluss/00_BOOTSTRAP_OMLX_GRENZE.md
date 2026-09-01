# Teilplan 00 — Bootstrap, OMLX und sichere Eigentumsgrenze

## Ziel

Hermes/Qwen startet mit wirksamen mindestens 64K Kontext, die drei
Arbeitsgrenzen sind inventarisiert und ein isolierter lokaler Kandidatenzweig
existiert. Keine Produktdatei wird geändert.

## Einmalige Inputs

Vollständig lesen:

1. `/Volumes/daten/Begod2026/brainlehr/AI_HANDOFF.md`
2. `/Volumes/daten/Begod2026/brainlehr/docs/REQUIREMENTS_BRAINLEHR.md`
3. `/Volumes/daten/Begod2026/brainlehr/docs/PLAN_QWEN_HERMES_ABSCHLUSS_2026-08-27.md`
4. diesen Teilplan

Danach Recall/MCP wegen P67 nicht aufrufen.

## Schritte

1. `/Volumes/daten/brainlehr-qwen-run` mit Modus `0700` anlegen. Fehlt
   `state.json`, `RUN_STATE.initial.json` dorthin kopieren und Modus `0600`
   setzen; existiert es, nur validieren und niemals überschreiben. Schema,
   Bootstrap-/Startprompt-Hashes und Candidate-HEAD prüfen.
2. Vor Produktmutation zwei frische Hermes-Sessions mit demselben Modell,
   CWD, Toolset, unverändertem Laufstate und exakt dem Inhalt von
   `STARTPROMPT_STABLE.md` starten. Aus den oMLX-Primärlogs je Request
   Prompttokens, `reused`, `re-prefills` und erste Divergenz erfassen. Der
   zweite Lauf muss `reused > 0` zeigen; Request-ID und Gesamt-`cached_tokens`
   sind kein Hit/Miss-Beleg. Keine Blockgröße tunen und keine vollständige
   Settingsdatei oder Secrets ausgeben.
3. Read-only Git-Inventar für Brainlehr, Hermes-Adapter und lokalen
   Hermes-Host aufnehmen: HEAD, Branch, `status --short`, cached name-status und
   cached numstat. Nichts darf gestaged sein; sonst terminal FAIL.
4. Vorhandene untracked und dirty Pfade als `PROTECTED` klassifizieren. Nicht
   öffnen, kopieren, löschen oder stage-en.
5. `/Users/lehrmacbook/.hermes/config.yaml` ausschließlich auf die Felder
   `model.default`, `model.provider`, `model.context_length`, `model.base_url`
   prüfen. Keine vollständige Konfiguration/Secrets ausgeben. Erwartet:
   `Qwen3.8-27B-MLX-4bit`, `omlx`, `262144`.
6. OMLX `/v1/models` prüfen. Genau das Modell muss verfügbar sein. Kein Modell
   laden/pullen und kein zweites großes Modell starten.
7. Im lokalen Hermes-Host fokussiert ausführen:

   ```bash
   python3 -m pytest -q tests/test_ctx_halving_fix.py
   rg -n 'config_context_length|model.context_length|context_length' agent model_tools.py hermes_cli tests
   ```

8. Bestehenden Resolver-Test finden oder minimal ergänzen: explizite `262144`
   schlägt den Serverbericht `49152`. Erst rot belegen, dann kleinsten Fix in
   der vorhandenen Resolverfunktion. Lokaler Hostpatch bleibt getrennt und
   uncommitted/upstream-gesperrt.
9. Hermes erst nach grünem Resolvergate kontrolliert neu starten. Vorher/nachher
   PID und Startzeit; danach leerer Agentstart plus ein kurzer read-only Toolcall.
10. Ressourcen beobachten: ein großes Modell, Batch 1, ein Worker. Abbruch bei
   Swapout-Anstieg, Throttle, freiem RAM <25 Prozent oder zweitem großen Modell.
11. Kandidatenarbeit niemals im gemischten Hauptbaum beginnen. Einen separaten
   Git-Worktree unter `/Volumes/daten` von Brainlehr-HEAD `640ceca7` auf lokalem
   Branch `qwen/brainlehr-finish` anlegen. Existiert er bereits, erst HEAD und
   Sauberkeit prüfen; nicht überschreiben.

## Abschlussgate

PASS nur mit:

- effective context >=64K und config `262144` respektiert;
- neuer Hermes PID/Startzeit und erfolgreichem Agent-Init;
- drei Git-Inventaren, cached index leer;
- Kandidatenworktree sauber auf `640ceca7`;
- DB/MCP/Backups unberührt;
- validierter Laufstate und zwei request-lokale Cachemessungen;
- technische Übergabe:

```text
PHASE=00
VERDICT=PASS|FAIL
BRAINLEHR_CANDIDATE_HEAD=<hash>
HERMES_HOST_HEAD=<hash>
EFFECTIVE_CONTEXT=<zahl>
HERMES_PID_STARTED=<pid/time>
PROTECTED_COUNTS=<tracked-dirty/untracked je Grenze>
DB=UNTOUCHED/FROZEN
PUSH=NOT_DONE
GAP=<exakt oder none>
CACHE=<prompt_tokens/reused/re-prefills/first_divergence>
```

## Neues Kontextfenster öffnen

Bei PASS: Laufstate mit Abschlussblock, Cachemetriken und
`next_phase_path=/Volumes/daten/Begod2026/brainlehr/docs/qwen_abschluss/01_KATALOG_GRAPH_P60_P62.md`
atomar aktualisieren und validieren. Neues Hermes-Kontextfenster öffnen und
exakt den unveränderten Inhalt von `STARTPROMPT_STABLE.md` senden.

Bei FAIL: kein neues Ausführungsfenster; nur den exakten Blocker an Codex geben.
