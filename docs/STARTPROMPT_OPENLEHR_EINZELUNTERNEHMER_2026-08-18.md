# Startprompt: openlehr_einzelunternehmer (ab 2026-08-18)

**Ort.** `cd /Volumes/daten/Begod2026/openlehr_einzelunternehmer`, Zweig
`merge/daten-features`. Eigenes Repo mit eigener Historie (847 Commits).
Testlauf dort IMMER `.venv/bin/python -m pytest`, nie `python3 -m pytest`
(`L-bdfeef`).

**Neu seit 2026-08-18, betrifft dich sofort.**
- `wissen/einzelunternehmer.domaene.json` trägt `contract_version: 1`. Brainlehr
  weist seit `cdef550b` **jedes** Paket ohne bekannte Major-Version ab.
- `dienst/tests/test_euer_vorschlag.py` skippt nicht mehr, wenn Brainlehr fehlt
  (`INT-GATE-001`). Rot-Probe: `BRAINLEHR_PFAD=/tmp/gibtsnicht` → 1 failed.
- Reimport aktualisiert seit `2ea89fe6` gleiche Kennungen; der `dienst`-Teil wird
  abgelegt, aber **nie gestartet** (`INT-DNST-001`).

**Stand, gemessen 2026-08-18** (die Zahlen in `STAND.md` sind älter und stimmen
nicht mehr): 6 Dateien mit absoluten `/Volumes/daten/Begod2026`-Pfaden (nicht
24), 43 `begod/`-Fundstellen (nicht 70), `pyproject.toml` **ist vorhanden**
(STAND sagt, es sei im Monorepo geblieben). Wer STAND weiterträgt, trägt drei
falsche Zahlen weiter.

**Offen, in dieser Reihenfolge.**
1. Die 6 Dateien mit absoluten Pfaden lösen — sie zeigen seit dem Schnitt
   teilweise ins Leere.
2. Kein Upstream für `merge/daten-features`: zwei Commits (`cc750e3`, `544da2a`)
   liegen lokal. Ein `push -u` legt einen neuen Fernzweig an — **Außenwirkung,
   gehört dem Betreiber**, nicht dir.
3. Fachlich: B4 ist fertig (10 Tests grün), der Bildschirm ist beschrieben und
   wird nirgends gezeichnet — das hängt am Atelier, nicht hier.

**Was hier NICHT entschieden wird.** Zuordnung, Reihenfolge und Bauform stehen in
den ADRs von brainlehr (ADR-007 zwei Schichten, ADR-013 drei Teile). Vor dem
Satz „das entscheidet der Betreiber" erst dort nachschlagen (`L-5eb8df`).
