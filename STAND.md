# STAND brainlehr — 2026-08-11T21:55:00+0200

Erledigt seit 21:40: Die Datenbank heißt jetzt `brainlehr.db` (Probe: `brainlehr-probe.db`), Variable `BRAINLEHR_DB`, alter Name bleibt gültig mit einmaligem Hinweis. Bestand unverändert 2125/775, Sicherung `knowledge.db.vor-umzug-20260811T212654`. Alle Vektoren aktuell (0 fehlend, 0 veraltet).
Dabei aufgefallen: `.gitignore` kannte nur den alten Namen, dadurch war die Datenbank kurzzeitig versionsverwaltet — behoben in 464ec3f, Lehre L-2b5f6f.

Offen: 18 % der Betreibernachrichten erreichen den Haltepunkt nie (15 von 82, Knoten 8215ac0d) — drei Erklärungen gemessen und ausgeschlossen, der Grund bleibt offen. Keine neue Vermutung ohne Messung.
`freigabe` fehlt in `knowledge_search`/`knowledge_browse` — gesperrter Knoten bleibt auffindbar; zweimal unabhängig gefunden (cda47024, Enigma-Landkarte). **Läuft gerade** bei einem Sonnet-Agenten, ebenso das Entrauschen des Prüfkorpus.

Neun Tests sind rot und waren es vor dem Merge schon: `test_knowledge_search_fold` (7), `test_lesson_query_fold` (2). Alle neun suchen gegen die echte Datenbank. Eine zehnte wäre neu.

Naechstes nach den beiden Agenten: S12 zweiter Anlauf — die Anfrage in den Wortschatz der Antwort übersetzen (L-3ba807). Erst danach Abrufgüte gegen die Nulllinie 15/178, sonst misst sie sich selbst.

Wartet auf: `~/.claude.json` → actor (tippt der Betreiber selbst) · NIST-Teilbestand unbenannt · ASRS braucht Ausfuhrlauf statt Schnittstelle.

Nicht vergessen: `gattung=nachschlagewerk` heißt Heuhaufen, nie Ziel eines Prüffalls (L-051d71). Code-Edits und Messläufe gehen an Sonnet (Norm 75ef2145). `migrationen/lauf_titelverteidiger_2026-08-08.py` nennt weiterhin `knowledge.db` — die Datei gehört einer fremden Sitzung, nicht angefasst.
Gesamtplan: docs/PLAN_GESAMT_2026-08-11.md · Enigma-Landkarte: docs/ENIGMA_LANDKARTE_2026-08-11.md · Fremdbestände: docs/LIZENZPRUEFUNG_FREMDBESTAENDE_2026-08-11.md
