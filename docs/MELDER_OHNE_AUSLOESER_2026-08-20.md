# Melder ohne Auslöser — 2026-08-20

Grundlage: `python3 melder/ohne_mechanismus.py --melder` meldet 25 von 48
Meldern ohne Eintrag in `.claude/settings.json` und ohne `haken/git/pre-push`.
Diese Tabelle entscheidet je Melder, an welches Ereignis er gehören WÜRDE —
verdrahtet wird hier nichts, das entscheidet der Hauptchat.

Kostenspalte: gemessen mit `time python3 melder/<modul>.py --selftest`
(bzw. der sicheren Vorgabe-Ausführung, wo `--selftest` fehlte), auf diesem
Rechner, 2026-08-20. Reale Sekunden (`real`/`total`), nicht geschätzt.

| Modul | was er prüft (ein Halbsatz) | woran er hängen MÜSSTE | Kosten je Lauf |
|---|---|---|---|
| abrufwirkung.py | wie gut eingespieltes Wissen tatsächlich benutzt wird, über einen vorgelegten Transkriptlauf | keiner, weil er einen vom Menschen vorgelegten Lauf auswertet, kein automatischer Ausgangspunkt | 0,04 s |
| agentendauer.py | Dauer und Kosten je Subagentenlauf, aus Sitzungsprotokollen ausgezählt | keiner, weil Bericht auf Anfrage ("wie teuer war der Lauf") | 0,03 s |
| auftragsregister.py | zieht echte Nutzereingaben aus Transkripten, hält sie in `auftraege.jsonl` fest | keiner, weil Subcommands eine Menschenfrage oder -entscheidung brauchen | 0,07 s |
| ausloeserlos.py | welche Mechanismen unter melder/haken/berichte an keinem Ereignis hängen | SessionStart, weil sich der Bestand an Mechanismen nur zwischen Sitzungen ändert | 0,06 s |
| eilmeldung_etikett.py | ob ein Knotentitel Dringlichkeit behauptet, ohne den Tag zu tragen | SessionStart, weil der Befund vom DB-Bestand abhängt, nicht vom laufenden Gespräch | 0,04 s |
| faehigkeiten.py | Fähigkeitsbestand von brainlehr, aus messbaren Quellen erzeugt | keiner, weil Bericht, der beim Lesen erzeugt wird, kein Wächter | 0,04 s |
| foederation.py | wer diese Instanz ist und welcher fremden sie traut | keiner, weil ein Mensch gezielt Vertrauen einträgt oder abfragt | 0,05 s |
| gatestand.py | wie viele Katalogzeilen im Lastenkatalog wirklich durch ein Gate belegt sind | keiner, weil auf Abruf vor einer eigenen Aussage konsultiert, kein Text-Check | 0,02 s |
| kantenstillstand.py | ob die Kantenberechnung aus Embeddings stillsteht | SessionStart, weil der Rückstand sich über Tage aufbaut, nicht pro Prompt | 0,10 s |
| kennungskollision.py | ob dieselbe Kennung (S12, B4.3, …) zwei verschiedene Abschnitte in docs/ trägt | pre-push, weil es den Dokumentzustand vor dem Verlassen des Rechners prüft | 0,02 s |
| klassenausfall.py | ob eine ganze Zielklasse in einem Messkorpus nie trifft | keiner, weil Auswertungswerkzeug nach einem Messlauf, kein Dauerwächter | 0,02 s |
| landkarten.py | erzeugt fünf Landkarten (Verbund/Anwendung/Code/Bestand/Agenten) | keiner, weil Generator/Bericht auf Abruf — bei 44,65 s ohnehin nicht hookfähig | 44,65 s (Vorgabe schreibt Dateien; sicher mit `--json` gemessen) |
| ohne_mechanismus.py | welche Lehren sich wiederholen und trotzdem keinen Mechanismus haben | keiner, weil Analysewerkzeug auf Abruf — genau das Werkzeug dieser Tabelle | 0,02 s |
| plan_bestandsabgleich.py | ob eine Planzeile laut Code schon erledigt ist, obwohl der Plan sie offen führt | keiner, weil vor dem Formulieren eines neuen Auftrags gezielt konsultiert | 0,03 s |
| rotprobe.py | ob ein Commit eine Behebung behauptet, ohne Testdatei oder Rot-Beleg zu nennen | commit-msg, weil er den Commit-Text selbst prüft | 0,02 s |
| schemastand.py | ob `schema.sql` von der installierten Datenbank abweicht | pre-push, weil Schema-Drift vor dem Verlassen des Rechners auffallen muss | 0,14 s |
| selbstbeschreibung.py | legt das eigene Handbuch von brainlehr als Wissen ab | keiner, weil Generator auf Abruf (`--anlegen`/`--zeigen`) | 0,03 s |
| spaltenabgleich.py | Spaltenabgleich je Tabelle zwischen `schema.sql` und installierter DB | pre-push, dieselbe Fehlerklasse und derselbe Zeitpunkt wie schemastand.py | 0,16 s |
| speicherherkunft.py | ob eine Antwort eine Aussage aus dem Speicher trägt, ohne ihn zu nennen | Stop, weil er den Text der Assistentenantwort gegen das Recall-Log prüft | 0,04 s |
| systembenutzer_probe.py | ob der Bestand einem anderen Systembenutzer gehört und nicht mehr beschreibbar ist | keiner, weil einmalige Vorbereitungsprobe vor einer Umstellung (G5), kein Dauerwächter | 0,03 s |
| vektorstand.py | ob ein Embedding einen Text beschreibt, den es so nicht mehr gibt | SessionStart, weil veraltete Vektoren sich über Tage ansammeln | 0,06 s |
| verbundkarte.py | erzeugt die Karte des Verbunds (Repos, Datenspeicher, Ports, Startwege) | keiner, weil Generator/Bericht auf Abruf — bei 39,97 s ohnehin nicht hookfähig | 39,97 s (Vorgabe ohne `--out` schreibt nichts, druckt nach stdout) |
| vier_nenner.py | vier Kennzahlen mit Nenner statt einer Zahl ohne Kontext, für die laufende Sitzung | keiner, weil auf Abruf, wenn ein Mensch nach der Abrufgüte der Sitzung fragt | 0,10 s |
| vorschlagsmelder.py | nur die NEUEN Vorschläge aus `berichte/vorschlag.py` seit dem letzten Lauf | Stop, laut eigenem Modulkopf für das Stop-Ereignis mit Neuheitsfilter gebaut | 0,04 s |
| wirkkette.py | ob ein Mechanismus wirklich verdrahtet ist, am richtigen Ereignis, und die Meldung nicht verschluckt wird | keiner, weil ein Mensch gezielt nachfragt; zusätzlich bei 14,95 s ohnehin über der 2-s-Schwelle für jeden Text-Hook | 14,95 s |

## Zusammenfassung

- SessionStart: 4 (ausloeserlos, eilmeldung_etikett, kantenstillstand, vektorstand)
- UserPromptSubmit/Stop: 2 (speicherherkunft, vorschlagsmelder)
- pre-push/commit-msg: 4 (kennungskollision, schemastand, spaltenabgleich, rotprobe)
- keiner, weil Werkzeug für Menschen: 15 (abrufwirkung, agentendauer, auftragsregister, faehigkeiten, foederation, gatestand, klassenausfall, landkarten, ohne_mechanismus, plan_bestandsabgleich, selbstbeschreibung, systembenutzer_probe, verbundkarte, vier_nenner, wirkkette)


## Nachtrag des Hauptchats, 2026-08-20 (nach Prüfung des Berichts)

**Vier verdrahtet** an `SessionStart`, alle unter 0,10 s: `ausloeserlos`,
`eilmeldung_etikett`, `kantenstillstand`, `vektorstand`. Alle vier laufen ohne
Argumente, schreiben nichts und liefern Rückgabecode 0 — geprüft vor dem
Einhängen.

**Zwei NICHT verdrahtet, obwohl der Bericht sie an `Stop` vorschlägt:**
`speicherherkunft` und `vorschlagsmelder` lesen **kein stdin**. An `Stop`
eingehängt geben sie ihren Hilfetext aus und tun nichts — sie wären
„verdrahtet, aber wirkungslos", genau die Klasse, gegen die dieses Repo
gebaut ist. Sie waren kurz eingetragen und sind zurückgenommen. Erst braucht
jeder von ihnen einen stdin-Pfad wie `melder/rueckfrageschleife.py`, dann die
Verdrahtung.

**Ein Befund am Melder selbst, nicht am Bericht:** `rotprobe` steht hier als
unverdrahtet, hängt aber seit demselben Tag als `commit-msg` und hatte gerade
zwei Commits angehalten. `melder/ohne_mechanismus.py` las nur
`~/.claude/settings.json` und `haken/git/pre-push` — nicht die
**installierten** Haken unter `.git/hooks/`. Behoben; dieselbe Klasse wie
`L-600726`: das wirksame Artefakt ist nicht das, das im Quelltext steht.

**Stand nach dieser Runde: 20 von 48 ohne Auslöser** (vorher 25). Von den
verbleibenden sind 15 ausdrücklich Werkzeuge für Menschen und brauchen keinen.
