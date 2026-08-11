# STAND brainlehr — 2026-08-12T00:15:00+0200

## SCHREIBSPERRE auf den Bestand, solange die S12-Ausgangsmessung läuft

Kein `knowledge_add`, kein `lesson_record`, kein Import in `brainlehr.db`, bis die Messung je Hälfte vorliegt. Wer während der Messung schreibt, misst einen anderen Speicher als den, auf dem die Teilung gezogen wurde — und die Teilung ist der ganze Sinn des Aufbaus. Betrifft besonders den vorbereiteten MAUDE-Import (Planpunkt 4), der sonst der naheliegende nächste Schritt wäre.

## Erledigt in dieser Nacht

| | Commit |
|---|---|
| Datenbank heißt `brainlehr.db`, Bestand unverändert 2125/775 | Umzug + `464ec3f` |
| Freigabe wirkt in allen drei Lesewegen | `bb9bc7f` |
| Prüffall-Sammler abgesichert, 78 Fälle mit Nenner | `d43fece` |
| Testumgebung fragt den Auflöser — 14 stumme Tests sprechen wieder | `762293b` |
| Erstanlage trägt `code_kanten` und `pruefsprueche` | `1d64458` |
| Sechs Produktivdateien fragen den Auflöser | `349e738`, `cdaaafd`, `2c9890c` |
| S12 neu geplant: Hebel liegt auf der Schreibseite | `3447ba1` |
| Gesamtplan fortgeschrieben, zwei Punkte abgehakt | `02f2da5` |

Suite: 853 grün, 1 übersprungen, 7 xfail, **0 rot**.

## Der Befund der Nacht

`kern/normbezug.py` meldete seit dem Umzug **jedes** Normzitat als unbelegt — ohne Fehler, ohne Warnung. Ursache war nicht der Dateiname, sondern die Bauform: `if not pfad.exists(): return "unbelegt"` unterscheidet „geprüft und nichts gefunden" nicht von „gar nicht geprüft". Behoben durch einen dritten Zustand `ungeprueft`. Knoten `73ed942f` trägt das Unterscheidungskriterium und **zehn weitere Fundstellen derselben Form**, die absichtlich nicht pauschal geändert wurden — ob leer dort richtig ist, entscheidet die Rolle der jeweiligen Datei.

Die neun angeblich roten Umlauttests waren nie kaputt. Gegen den Suchcode von vor der Freigabe-Änderung und gegen die Datenbank-Sicherung von 21:26 einzeln nachgemessen, beide Male grün. Es gab nie einen Umlautfehler.

## Offen

`migrationen/lauf_titelverteidiger_2026-08-08.py` trägt weiter den alten Dateinamen — gehört einer fremden Sitzung, nicht angefasst, nur gemeldet.
Korpus-Zusammensetzung: 72 Aufträge gegen 6 Fragen. Ein Abruf, der an Aufträgen gut abschneidet, sagt wenig über Fragen.
Wartet auf den Betreiber: `~/.claude.json` → actor · NIST-Teilbestand unbenannt · ASRS braucht Ausfuhrlauf statt Schnittstelle.

## Nicht vergessen

Code-Edits und Messläufe gehen an Sonnet (Norm 75ef2145). Aufträge mit Läufen über eine Minute: ausdrücklich **Vordergrund** verlangen — drei Agenten haben heute ihren Zug im Wartemodus beendet (`L-1056bb`).
Bei gemeinsam benutztem Baum committen Agenten nur mit Pfadangabe (`L-73020e`).

Pläne: `docs/PLAN_GESAMT_2026-08-11.md` · `docs/PLAN_S12_ZWEITER_ANLAUF_2026-08-11.md` · Enigma: `docs/ENIGMA_LANDKARTE_2026-08-11.md`
