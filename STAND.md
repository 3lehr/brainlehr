# STAND brainlehr — 2026-08-15T05:57:52+0200

**Offen:** H2, H3 und **O1** sind erledigt (H2/H3 in openlehr committet, nichts gepusht). O1: `escHtml()` in `entscheidungen.html`, Test `tests/test_entscheidungen_tooltip_escaping.py` (16/16, vorher 15/16 rot); der volle `pytest`-Lauf über brainlehr stand beim Abschluss noch aus — nachziehen. Vier weitere Funde aus `docs/SICHERHEITSFUNDE_2026-08-14.md` sind unangetastet.
**I4 entschieden durch Messung:** Ausweise kennen nur `gilt_bis`, keinen Widerruf — er ist zu bauen (Knoten `5124a160`). **G6 teilbelegt:** yswift läuft in der App-Sandbox, aber nur im `.app`-Bündel; gehärtete Laufzeit und Beglaubigung ungemessen (Knoten `fef0cb9d`).

**Nächstes:** H4 Prüfkorpus mit Fallen, H5 Bestandsaufnahme als E2E-Journey (H2 vor H10, H6 vor H5s Sortierung). Lieferform brainlehr → openlehr weiterhin ungeklärt: keine Paketform, Laden über `sys.path` — bewusst nicht erfunden.

**Wartet auf dich:** G5 Befehl mit deinem Passwort (eigener Systembenutzer, Bestand und Ausweisdatei auf `0600`) · Name der Steuerdomäne · Domänen-Repo bei GitHub? · Urheberschaft der atelier-Ergebnisse vor der ersten Weitergabe · F29/F30/F31/F19 · dürfen die 22 GB in `../brainlehr-archiv/db-sicherungen-2026-08-14/` weg (unumkehrbar).

**Nicht vergessen:** **`kern/domaene.py` bleibt gesperrt** — Wirkung Null muss stehen, bevor dort das erste Mal geschrieben wird (heute 0 Treffer für INSERT/UPDATE/commit, Vorbild `kern/regelpaket.py`). Der Haltepunkt-Haken verlangt die Fähigkeit `/learn`, die es hier nicht gibt — Pflicht direkt über `lesson_record`/`knowledge_add` erfüllen (`L-48ca4d`). Kein Bau an den beiden Dokumentausgaben, solange die Ablösung unbelegt ist.
