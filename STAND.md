# STAND brainlehr — 2026-08-13T23:35:00+0200

**Haerteste Zahlen:** `melder/schemastand.py` findet **19 Abweichungen** zwischen `schema.sql` und installierter DB (7 nur installiert, 12 abweichendes SQL, darunter `knowledge_nodes`, `knowledge_embeddings`) — eine Erstinstallation erzeugt NICHT den Bestand, gegen den alle Tests laufen (Aufgabe 110). Und: S12-Umschrift von 225 Knoten zeigt **keine messbare Wirkung**, DiD +0,93 Prozentpunkte bei Rauschboden 4, der Pilot reproduziert nicht (`e66b43a5`).

**Gebaut:** Vektor-Identitaet `bge-m3@ctx2048`, Bestand neu gerechnet statt umbenannt (`cd56071`) · drei Waechter: Herkunftsnormierung, Schemaabgleich, STAND-Format (`88aaf73`) · Zitatpruefer byte-gleich (`f1a6f51`) · sechs Schranken im Umschriftwerkzeug. Laeuft: Regelwechsel-Urheber (107), Zeitfilter (88), abfaerbender Testfehler. 110 Aufgaben, 66 erledigt.

**Rot:** `test_planform_ratsche` wegen `docs/PLAN_GRUNDARCHITEKTUR_2026-08-13.md` (fremde Sitzung, nicht angefasst) · 2 Tests in `test_vektor_identitaet.py` nur in der VOLLEN Suite, allein gruen, 7 Kandidaten ausgeschlossen — Zusicherung darf NICHT stillgelegt werden (Ollama braucht den rohen Namen, sonst 404).

**Fallen:** Pruefstein nur auf Verlust → durch Hinzufuegen immer zu bestehen (`L-a4f6dd`) · Massenbehandlung fasste bindende Norm und DSGVO-Wortlaut an (`L-22131c`, `L-5d2fe1`) · Vorher/Nachher ueber verschiedene Korpora (`L-3bf6c7`) · Restmenge in Losen gerechnet verdeckt, WORAUS sie besteht. **Wartet auf den Betreiber:** Klarname geschwaerzte PDF · 101 · 105 · 77 (beruehrt hub) · Push.
