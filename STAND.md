# STAND brainlehr — 2026-08-14T10:30:00+0200

**BLOCKIERT ALLES ANDERE: Sitzungen neu starten.** Die laufenden MCP-Prozesse tragen den Code von 21:44. Sie schreiben (a) keine Vektoren, (b) Ortszeit statt UTC. Belegt: juengster Knoten `+02:00`, `access_log` schon `Z` (dessen Vorgabewert sitzt in der DB, nicht im Prozess). **Aufgabe 111 Schritt 3 ist dadurch gesperrt** — Umrechnen wuerde sofort wieder mischen.

**UTC (111), Schritt 1+2 fertig:** eine Quelle (`kern/zeitmarke.jetzt`), zwei Ratschen, 46 Erzeuger umgestellt, Spalten-Vorgabewerte migriert. Schritt 3 ist geschrieben und geprueft (13 Proben, beide Umstellungstermine), wartet auf den Neustart.

**S12 (108) — das Ergebnis ist ein Nicht-Ergebnis, und das ist der Ertrag:** Der Nenner war falsch. Ueber die tatsaechlich behandelten Ziele bleiben 34 von 205 Faellen, behandelte Zelle n=14. Urteil: **mit diesem Korpus nicht entscheidbar**, ausdruecklich nicht „keine Wirkung". Die Rohzahlen (5/14 gegen 11/20) deuten sogar auf Verschlechterung — reines Rauschen. Naechster Schritt: groesserer Korpus, keine feinere Rechnung. Knoten `0e6adb6c`.

**Haken (98):** `worktree_identitaet.py` war gebaut, zweimal repariert, nie verdrahtet — jetzt an `WorktreeCreate`, vorher end-to-end geprueft. Neue Ratsche prueft **Existenz, nicht Tauglichkeit** — `mcp_veraltet.py` ist verdrahtet und trotzdem blind (drei Stufen in `L-b3eb79`).
**Erledigt heute:** 69 · 80 · 86 · 88/1 · 91 · 98 · 107 · 108 · 110 · beide Eilmeldungsdefekte. **Rot:** `test_zeitform_utc` (gewollt bis Schritt 3) · `kandidatendiagnose` (Bestandsdrift, vorbestehend). **Wartet auf dich:** Neustart · Push · #105 · #29 · #101 · #20.
