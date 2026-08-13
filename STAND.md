# STAND brainlehr — 2026-08-13T18:35:00+0200

**Haerteste Zahl des Tages:** Der Abruf liefert **nie**, was tatsaechlich gelesen wurde — 0 von 13 in der Klasse `lese`, gegen 16 von 52 in `pfad` (Vollerhebung ueber alle 45 Faelle, `90664e98`, `9d49fe1`). Nicht die Zielart entscheidet, sondern ob der Aufgabentext eine Bruecke zum Ziel enthaelt. Die guenstigere Klasse ist die selbsterfuellendere.

**Beispielbestand:** `docs/RECHERCHE_BEISPIELBESTAENDE_2026-08-13.md`. GermanQuAD ist der einzige Kandidat, der Schaufenster UND Pruefkorpus kann; `pruefstand/germanquad.py` liegt schon da und misst mit `count_oversized(2048)` die Kappung aus Aufgabe 69. Einlesen fertiger Texte kostet **null Modell-Token** — nur lokale Einbettung, gemessen 0,122 s je Eintrag.

**Offen:** Klarname in der geschwaerzten PDF · Aufgabe 101 (App zeigt nur `offen`) · Schritt 3 von `docs/PLAN_REGELDATEI_2026-08-13.md` (Aufteilung CLAUDE.md gegen `~/.claude/rules/*.md`).

**Naechstes:** App-Ansicht sichtbar machen — PDFKit fuer PDF, NSTextView fuer HTML/TXT, NICHT Quick Look (kann weder aufschlagen noch hervorheben noch scheitern melden). Oberflaechenfreier Teil steht, 55 XCTest gruen, 9 von 9 Mutationsproben rot.

**Wartet auf den Betreiber:** Handprobe, ob `#:~:text=` in seinem Browser greift — mein Pruefbrowser meldet visibilityState "hidden", Textfragmente brauchen echte Nutzeraktivierung. Rueckfall ist sicher (Dokument oeffnet oben, nie falsch).

**Nicht vergessen:** Massstab ist Wirksamkeit, nicht Zeilenzahl — 11 von 19 Hausregel-Abschnitten ohne greifenden Mechanismus. `ui_guard.py` lief seit 2026-07-30 nie, ist jetzt an `PostToolUse` verdrahtet. Beim Nachmessen nie das Kriterium neu erfinden (`L-9202c2`); toter Regelzweig durch Umlaut-Kodierung (`L-8fce9c`) — dieselbe Falle wie die 16 Belege in `quellen_check.py`. Aufgabe 8 geschlossen: die Enigma-Studien bleiben synthetisch, weil Studien und Speicher **verschiedene Modelle** fuehren (Erlaubnis je Vorgang gegen Rollenmodell) — jetzt ueberwacht statt behauptet (`647cedea`, `4d5f7a7`). Die Auftragsform fing heute **zweimal** eine Dublette an der Zeile Fakten, bevor der Auftrag rausging.

**Diese Datei war eben 56 Zeilen bei Pflichtformat 10** — von beiden Sitzungen unabhaengig verletzt, von keiner bemerkt. Selbst ein Beleg fuer den Massstab oben: die STAND-Regel hat keinen Waechter.
