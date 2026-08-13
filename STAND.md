# STAND brainlehr — 2026-08-13T16:08:18+0200

**Offen:** Drei Entscheidungen beim Betreiber, siehe `docs/adr/ADR-004-keine-multiview-app-fuer-den-termin.md`:
Sitzabstand (2 m oder 1,2 m?), Schreibrecht in buckeberg, pdf.js nachladen (Download) oder Umweg streichen.

**Nächstes:** Nach der Entscheidung Schritt A (Betrachter, ~10 min) und B (HTML-Fundstellen aus `kurz`, ~1 h). Aufträge in `docs/PLAN_MULTIVIEW_GESAMT_2026-08-13.md` §7.

**Wartet auf:** buckeberg-Termin heute/morgen Abend. Rückfalllinie ohne jeden Code: die vier PDFs in `dossier/` ausdrucken, 5 Minuten.

**Nicht vergessen:** Der pdf.js-Betrachter der buckeberg-Homepage ist TOT (`vendor/pdfjs-viewer/build/` fehlt, `.gitignore` Zeile 21) — graue Fläche ohne Meldung, `quellen_check.py` grün. 14 exakte Fundstellen, keine sichtbar.
Alle 14 markierbaren Quellen sind PDF; keine der 20 HTML-Quellen trägt eine Stelle, bei 19 steht sie im Feld `kurz`. Bestand: 48 Quellen, 14/1/33.
`kern/fundstelle.py` + `tests/` liegen in der Dateimenge der parallelen Python-Sitzung — von mir angelegt, Grenze verletzt, dort gemeldet. Ab jetzt bestellen statt bauen.
