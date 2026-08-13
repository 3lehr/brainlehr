# STAND brainlehr — 2026-08-13T17:25:00+0200

**Offen beim Betreiber:** Der Klarname in der geschwaerzten PDF und Aufgabe 101
(App zeigt nur `offen`). Die drei Multiview-Fragen sind BEANTWORTET: 1,5 m,
grosser 4K-Fernseher als Zweitschirm · Schreibrecht in buckeberg erteilt ·
pdf.js nachladen. Alle drei erledigt, siehe unten.

**Erledigt seit 16:00 (App-Seite):** ADR-004 heisst jetzt
`docs/adr/ADR-004-anzeige-waechst-mit-der-flaeche.md` — der erste Entwurf
("kein Multiview") war methodisch sauber und im Ergebnis falsch, weil er die
Bauform an EINEM Termin gemessen hat. Der pdf.js-Betrachter LEBT wieder
(6.1.200 nachgeladen, `.gitignore`-Ausnahme, Gegenprobe in beide Richtungen).
buckeberg: markierbar 14 -> 30 von 48, bei HTML 0 von 20 -> 16.
`quellen_check.py` prueft jetzt alle Formate: 42 in Ordnung, 0 Fehler.

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

**Wartet weiter:** buckeberg-Termin morgen — laut Betreiber "nice to have, kein
Muss", die App soll ALLE Lagen tragen, nicht nur diese. Rueckfalllinie ohne
jeden Code bleibt: die vier PDFs in `dossier/` ausdrucken, 5 Minuten.

**Naechstes in `app/`:** die sichtbare Ansicht (PDFKit fuer PDF, NSTextView
fuer HTML/TXT — NICHT Quick Look, das kann weder aufschlagen noch hervorheben
noch einen Fehlschlag melden). Der oberflaechenfreie Teil steht: `Anzeigeform`
(Ausschnitt/ganze Seite/nebeneinander, folgt aus Flaeche und Abstand),
`Quelldokument` (vier Negativfaelle), `Fundstelle` (Dienst-Antwort).
55 XCTest-Faelle gruen, neun Mutationsproben gefahren, neun rot.

**Eine Handprobe steht aus, die ich NICHT selbst machen kann:** Ob
`#:~:text=` beim Betreiber greift. Der Pruefbrowser meldet visibilityState
"hidden", und Textfragmente verlangen echte Nutzeraktivierung. Geprueft:
Fragment wird unterstuetzt, Text steht exakt so im Dokument, URL korrekt
kodiert, per URL und per Klick — beide ohne Scroll. Grenze meines Aufbaus,
keine der Plattform. Rueckfall ist sicher: greift es nicht, oeffnet das
Dokument oben, nie an falscher Stelle.
