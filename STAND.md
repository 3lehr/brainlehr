# STAND brainlehr — 2026-08-09T20:15:00+0200

Offen: Der Abruf trifft (16/35, robust auch gegen 2024 Ablenkungen statt 386),
aber er feuert zur falschen Zeit — nur 3 von 8 Betreibernachrichten loesten
einen Recall aus, 4 von 7 Einspielungen kamen auf Systemmeldungen
(Feldbericht, Knoten `1d2e6458`). Eine Suche, die nicht gefragt wird, hat
keine Trefferquote.
Naechstes: `recall_log.jsonl` auswerten (89 Zeilen von heute, jede mit
ausloesendem Prompt) — bei welcher Art Eingabe feuert der Haken, bei welcher
nicht. Dieselbe Diagnose wie heute frueh, eine Station frueher in der Kette.
Danach: Pruefkorpus vergroessern (35 Faelle rauschen, belegt), Antwortqualitaet
messen (`wissensnutzen.py`), Planschritte S3/S4/S5/S7.
Wartet auf: `~/.claude.json` -> `mcpServers.knowledge.env` (actor) · Papernetz-
Umfang · sechs Knoten Rang 4/6 · Projektliste aus dem Verbundverzeichnis statt
aus dem Bestand (`51f3695e`, 12 buckeberg-Knoten bleiben sonst 'shared').
Nicht vergessen: Rueckweg ist `snapshots/knowledge_2026-08-09.db` plus 350
Zeilen `knowledge_fassungen`; Deckel steht auf 10/7 (9409 statt 2604 Zeichen
je Prompt) — ob mehr Kontext die ANTWORT verbessert, ist nicht gemessen.
