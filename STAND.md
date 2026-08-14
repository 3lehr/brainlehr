# STAND brainlehr — 2026-08-14T21:36:26+0200

**Offen:** Linie H (openlehr als erste Instanz, `docs/PLAN_OPENLEHR_2026-08-14.md`): H2 `classifier.py` an den Belegvertrag, H3 Naht `ingest.py`/`api.py`, H4 Prüfkorpus mit Fallen, H5 Bestandsaufnahme als E2E-Journey. Bindend: H1 war Voraussetzung von H2 und H3.
Die Lieferform brainlehr → openlehr ist ungeklärt: keine Paketform (kein `pyproject.toml`, kein `kern/__init__.py`, Laden über `sys.path`). Bewusst nicht erfunden.

**Nächstes:** H2 — zuerst der Test, der gegen den heutigen Stand rot ist (Regelmenge ohne Fundstelle lädt in `classifier.py` klaglos), dann die 12 Regeln an `kern/belegvertrag.py`.

**Wartet auf dich:** F29 Steuerberater (gibt es einen, darf er die Sachen sehen) · F30 welche Finanzamtsbriefe liegen vor · F31 echter Testkorpus oder erfinden · F19 dürfen Belege fürs Modell das Haus verlassen · dürfen die 22 GB in `../brainlehr-archiv/db-sicherungen-2026-08-14/` weg (unumkehrbar) · #105 · #29 · #101 · #20.

**Nicht vergessen:** Startprompt nannte `wiring_check.py` (Dart-only) und 102/40 651 Zeilen — gemessen 128/43 237, im Plan §0 korrigiert (`L-cd1ef0`). Messrohdaten im Zielrepo: `openlehr/docs/openlehr/messung_steuer_{verdrahtung,fachwissen}_2026-08-14.json`, nicht neu messen.
