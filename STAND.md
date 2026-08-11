# STAND brainlehr — 2026-08-11T09:05:00+0200

**Zuerst lesen:** `docs/PLAN_KLIENTENDOKU_2026-08-10.md` §6 (widerruft §5), dann
`docs/adr/ADR-003-erstanlage-gleicht-dem-betrieb.md`.
**Alles lokal, NICHTS gepusht.** Zweig `brainlehr/b4-ausweis`.

**Die Kaskaden-Wache setzte sechs Tage lang die abgelöste Regel durch.**
`hub/scripts/cascade_guard_hook.py` blockte Code-Edits im Hauptfaden und verwies
auf Sonnet-Subagenten — also auf v2, obwohl `hub/CLAUDE.md` seit
2026-08-05T09:40:00+0200 auf v3 (Opus-Hauptfaden, ADR-023) steht. Wer der Wache
folgte, arbeitete gegen die geltende Regel. Jetzt an ihre Voraussetzung gebunden:
Modell aus dem Transkript, Opus 5 frei, Sonnet weiter gebremst, unbekanntes
Modell bremst. Sechs Tests (`tests/test_cascade_guard_modell.py`), vorher hatte
sie seit dem 2026-07-24 keinen einzigen. Dieselbe Klasse auf der Codex-Seite in
`~/.codex/AGENTS.md` behoben: Delegation darf nicht zum Stillstand führen
(`L-cd95a1`).

**`gattung` ist über den MCP-Weg schreibbar** — aber die im Plan angekündigte
Umklassifizierung **entfällt und war falsch.** `nachschlagewerk` heißt Heuhaufen
(Knoten `096669de`), nie Ziel eines Prüffalls. Die Klientendoku-Destillate tragen
ihren Wert im Abgleich („31 Haken-Ereignisse, 7 verdrahtet") und sollen gefunden
werden. Nicht die Herkunft entscheidet über die Gattung, sondern die Bauform:
Volltextabzug ist Heuhaufen, Destillat mit Abgleich ist Arbeitsbestand
(`L-051d71`). Der Schreibpfad wird trotzdem gebraucht, sobald ESA/ASRS/FAA aus
der Lizenzampel kommen.

**18 % der Betreibernachrichten erreichen den Haltepunkt nie** (Knoten
`8215ac0d`, gemessen an der ganzen Sitzung `c5d06d04`: 15 von 82). Alle wurden
vom Modell empfangen und beantwortet — kein Zustellungsproblem, sondern Ausfall
des Haltepunkts. **Drei Erklärungen gemessen und ausgeschlossen:** Abgleichfehler
des Messwerkzeugs, Einreihung während laufender Arbeit (sagt das Gegenteil
voraus: 62 erreichten ihn trotz Arbeit, 11 verfehlten ihn in Ruhe), zeitliches
Cluster. Der Grund bleibt **offen** — keine neue Vermutung in `ausloeser.py`
schreiben, ohne sie gemessen zu haben.

**Testsuite: 786 grün / 2 rot / 2 xfailed** vor den heutigen Änderungen; die
beiden roten (`test_caveman_integration`) sind aufgelöst. Einer war überholt
(forderte `lite`, Betreibervorgabe ist `ultra`), der andere deckte einen echten
Widerspruch IN der Policy auf (`AGENTS.md` gesperrt, `*.agent.md` erlaubt) und
steht jetzt als `xfail(strict=True)` — sichtbar rot statt gelöscht, und er
schlägt Alarm, sobald jemand die Policy repariert. Die Policy liegt in
`hub/begod/knowledge/meta/caveman_policy.json` und ist dort **nicht versioniert**
(`L-54b09d`).

**Falle:** Ein Test über eine Fremddatei kann nicht zwischen „Anlage kaputt" und
„Anlage geändert" unterscheiden — beides ist rot. Ist die Datei zusätzlich
untracked, fehlt auch git log als Auskunft. Startmelder sind Befunde, keine
Aufgaben (`L-f1fcb9`) — `NODE_INDEX.md`, `antwort_treffer.json`, `auszug/*.jsonl`
nicht committen.

**Wartet auf den Betreiber:** `~/.claude.json` → `mcpServers.knowledge.env`
(actor — tippt er selbst) · Push-Freigabe (alles liegt lokal).
