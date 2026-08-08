# STAND brainlehr — 2026-08-08T13:20:00+0200
**Fertig heute:** eigenes Repo mit voller Historie · `brainlehr.py` init/raus/rein/haken · Automatik in `haken/` samt `haken/ort.py` · `doctor.py` (5 Proben) · erster Aufsatz `aufsaetze/agenten.py` · `README.md` und `START.md` (letzterer gegen Verrottung getestet).
**Offen:** Uebergangsverweis `hub/shared-knowledge` entfernen, sobald alle alten Sitzungen neu gestartet sind — danach die vier Melder ERNEUT pruefen.
**Wartet auf Betreiber:** Push (hub 32, brainlehr 9 Commits ueber der uebernommenen Historie) · fuenf Knoten mit Rang 4/6 ohne Entscheidung · eine abgelaufene Norm im Bestand · `_VERWAIST_shared-knowledge-2026-08-08` loeschen oder behalten.
**Nicht vergessen:** `knowledge.db` ist NICHT versioniert — nach groesseren Aenderungen `python3 brainlehr.py raus auszug/bestand_<datum>.jsonl` und committen.
`compliance` ist definiert und lief NIE, obwohl hub/CLAUDE.md ihn als erzwungen fuehrt (Audit 2026-07-25 mass dasselbe). Eine Regel im Klartext aendert kein Verhalten.
Agentenregister liegt jetzt unter `hub/laufzeit/agent-register.jsonl` (ueberlebt Neustart), Pfad in `hub/scripts/agent_register_ort.py`.
Zugriffsprotokoll: die 1310 Zeilen ohne `actor` sind alle vom 2026-08-06 oder aelter — seit dem 07.08. ist die Zuordnung lueckenlos. Kein Handlungsbedarf, nicht rueckwirkend reparierbar.
Testlauf: 675 gruen, 7 rot — alle sieben vorbestehend (instructions, caveman-policy, Umlautfaltung).
