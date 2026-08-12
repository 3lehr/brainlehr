# STAND brainlehr — 2026-08-12T20:00:00+0200

Massgeblich ist die Aufgabenliste der Sitzung. `melder/offene_arbeit.py` zeigt beim Sitzungsstart den offenen Teil von `docs/SPRINTS.md`.

## Die Fehlerklasse dieses Tages, in acht Erscheinungsformen

Gemeinsam ist allen: nichts wurde gemeldet.

1. **Werkzeug tut still nichts** — `normbezug.py` meldete jedes Normzitat als unbelegt, weil sein Pfad ins Leere zeigte.
2. **Kanal stellt still nicht zu** — der Eilmeldungs-Haken war neun Stunden tot, `exit 0`.
3. **Aufzeichnung behauptet still Falsches** — die eingefrorene S12-Teilung. Widerrufen: der Fehler lag in *meiner* Gegenrechnung.
4. **Prüfer bestätigt das Gegenteil** — „§ 71 GEG" galt als *belegt*, obwohl der Treffer die Streichung dokumentiert. Behoben: Status `ausser_kraft`.
5. **Melder spricht über ein Siebtel** — `planbindung.py` sah 23 von 139 Abschnitten. Behoben, und beim Beheben entstand derselbe Fehler eine Ebene höher (`L-65d33e`, 2×).
6. **Eskalation ohne Empfänger** — 65 Einträge über vier Tage in eine Datei, die niemand liest (`L-14acea`).
7. **Regel schreibt, Prüfung fehlt** — auf den ersten Modellwissen-Vorfall folgte ein Dokument statt eines Testfalls. Vier Stunden später derselbe Fehler (`L-122b1c`).
8. **Bremse läuft nie** — die Kalibrierbremse wird mit `project_id=None` aufgerufen; die Schwellenprüfung erreicht kein Projekt. Im Code dokumentiert, im Selbsttest als Widerspruch sichtbar geworden.

## Erledigt seit 14:00

| | Commit |
|---|---|
| Regeln als wählbare Pakete, Rang kommt nie mit | `7013c04` |
| Lehren zwischen Instanzen, Prüfung an der Tür | `f6e0e63` |
| Eilmeldungen verfallen, Eskalation erreicht den Sitzungsstart | hub `336d32dfd`, `007630c` |
| Zweckprojektion: unbeschriebene Rolle bekommt nichts | `ec3a443` |
| Zweckprojektion wirkt in Suche und Blättern | `64bd010` |
| Diagnose: RRF gewichtet Rang, nicht Güte des Kanals | `06bb156` |
| `planbindung` sieht 79 statt 23 und nennt, was es nicht sieht | `f0f2c88` |

Suite: 945 grün, 2 übersprungen, 12 xfail, 0 rot. Vektoren vollständig neu gerechnet (2963, 0 Fehler) — 0 Änderungen, aber jetzt gemessen statt geschlossen (`L-bc1499`).

## Wartet auf den Betreiber

Aufgabe 20 und 23 gehören zusammen (Ausweisordner sichern, Geheimnis rotieren, Eintrag aus `~/.claude.json`).
Aufgabe 7: MAUDE-Import lädt über das Netz — Download braucht das ausdrückliche Wort.
Aufgabe 31: alle 808 Lehren stehen auf `intern`; der Austausch läuft leer, bis jemand freigibt.
Aufgabe 29/34: öffentlicher Schnitt erst nach beiden Ausgangszuständen der Fremdinstallation.

## Nicht vergessen

Ein Melder nennt **drei** Zahlen: vorhanden, geprüft, beanstandet (`L-65d33e`).
Ein Prüflauf, der nichts ändert, verwandelt eine Annahme in eine Messung (`L-bc1499`).
Wenn die Antwort auf einen Vorfall ein Dokument ist und kein Testfall, ist die Wiederholung eingeplant (`L-122b1c`).
Kein `git stash` für Rot-Proben (`L-56a352`). Läufe über zehn Minuten nicht in Subagenten (`L-1056bb`).
