# STAND brainlehr — 2026-08-13T17:25:00+0200

**Offen beim Betreiber:** Drei Entscheidungen zum Multiview-Termin, siehe
`docs/adr/ADR-004-keine-multiview-app-fuer-den-termin.md` (Sitzabstand,
Schreibrecht in buckeberg, pdf.js nachladen oder Umweg streichen). Dazu der
Klarname in der geschwaerzten PDF und Aufgabe 101 (App zeigt nur `offen`).

**Laeuft hier:** Aufgabe 102, vom Betreiber dieser Sitzung zugewiesen. Plan
`docs/PLAN_REGELDATEI_2026-08-13.md` (3939e2d), Schritte 1 und 2 erledigt.
Offen ist Schritt 3, die Aufteilung `~/.claude/CLAUDE.md` gegen
`~/.claude/rules/*.md`.

**Der Massstab, der sich heute geaendert hat:** Nicht Zeilenzahl, sondern
Wirksamkeit. Ein Abschnitt mit Waechter kostet dieselben Zeichen und wirkt
trotzdem. 11 von 19 Hausregel-Abschnitten haben keinen greifenden Mechanismus
(Messung 2026-08-12). Eine eigene Nachmessung ergab 8 von 20, ist aber das
schwaechere Kriterium und gilt nicht (`L-9202c2`).

**Nicht vergessen, drei Fallen von heute:**
- `ui_guard.py` lief seit dem 2026-07-30 **nie** (null Treffer in
  `settings.json`). Jetzt als `ui_guard_hook.py` an `PostToolUse` auf
  `Edit|Write` verdrahtet. Sicherungen: `settings.json.bak-2026-08-13T1720`,
  `ui_guard.py.bak-2026-08-13`.
- In demselben Waechter war ein Zweig der Regel `selbsterklaerung` tot: das
  Muster traf 'bekannte Lcke', nie 'bekannte Lücke'. Der Selbsttest war gruen,
  weil seine Testzeile ueber einen anderen Zweig traf (`L-8fce9c`). Rot-Probe
  gefahren, Zweig repariert, eigene Testzeile ergaenzt.
- Beim Nachmessen NIE das Kriterium neu erfinden. Eine bessere Zahl aus einem
  billigeren Verfahren ist keine Verbesserung, sondern eine andere Groesse.

**Wartet weiter:** buckeberg-Termin heute/morgen Abend. Rueckfalllinie ohne
jeden Code: die vier PDFs in `dossier/` ausdrucken, 5 Minuten. Der pdf.js-
Betrachter der buckeberg-Homepage ist TOT (`vendor/pdfjs-viewer/build/` fehlt),
graue Flaeche ohne Meldung, `quellen_check.py` gruen.
