# STAND brainlehr — 2026-08-14T00:55:00+0200

**Haerteste Zahlen:** `melder/schemastand.py` findet **19 Abweichungen** zwischen `schema.sql` und installierter DB (7 nur installiert, 12 abweichendes SQL, darunter `knowledge_nodes`, `knowledge_embeddings`) — eine Erstinstallation erzeugt NICHT den Bestand, gegen den alle Tests laufen (Aufgabe 110). Und: S12-Umschrift von 225 Knoten zeigt **keine messbare Wirkung**, DiD +0,93 Prozentpunkte bei Rauschboden 4 (`e66b43a5`).

**Suite ist wieder ganz gruen: 1336 passed, 1 skipped, 11 xfailed** (`654992e`). Der ordnungsabhaengige Fehler in `test_vektor_identitaet.py` lag NICHT dort: `pruefstand/messlauf.py` und `vergleichslauf.py` bogen `embeddings.embed_text`, `kms.DB_PATH`, `hook.DB` um und stellten sie nie zurueck; `test_paretolauf.py` faehrt sie im selben Prozess. Behoben ueber `messlauf.gesicherte_globale()`, rot vor gruen belegt.

**Gebaut:** Waechter gegen die eigene Hypothese im Agentenauftrag, an PreToolUse/Agent verdrahtet, 0 Fehlalarme auf 72 echten Auftraegen (`028bd97`) · Vektor-Identitaet `bge-m3@ctx2048` (`cd56071`) · drei Waechter Herkunft/Schema/STAND (`88aaf73`) · Zitatpruefer (`f1a6f51`). 110 Aufgaben, 67 erledigt.

**Rot:** nur noch `test_planform_ratsche` wegen `docs/PLAN_GRUNDARCHITEKTUR_2026-08-13.md` (fremde Sitzung, nicht angefasst). **Fallen:** zsh zerlegt unquotierte Variablen NICHT — `pytest $A` meldet „no tests ran" statt eines Fehlers, eine Bisektion beginnt so nie (`L-103548`) · verschmutzter Wert nach seiner Herkunft fragen statt bisezieren: `__code__.co_filename` (`L-305730`) · Pruefstein nur auf Verlust (`L-a4f6dd`) · Vorher/Nachher ueber verschiedene Korpora (`L-3bf6c7`). **Wartet auf den Betreiber:** Klarname geschwaerzte PDF · 101 · 105 · 77 (beruehrt hub) · Push.
