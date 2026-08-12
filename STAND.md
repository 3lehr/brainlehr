# STAND brainlehr — 2026-08-12T14:00:00+0200

Massgeblich ist die Aufgabenliste der Sitzung. `melder/offene_arbeit.py` zeigt beim Sitzungsstart den offenen Teil von `docs/SPRINTS.md` — in jedem Arbeitsbaum.

## Der Faden dieses Vormittags

Eine Fehlerklasse, fünf Erscheinungsformen. Gemeinsam ist ihnen, dass nichts gemeldet wurde:

1. **Ein Werkzeug, das still nichts tut** — `kern/normbezug.py` meldete jedes Normzitat als unbelegt, weil sein Pfad ins Leere zeigte.
2. **Ein Kanal, der still nicht zustellt** — der Eilmeldungs-Haken war neun Stunden tot, `exit 0`, bei drei wartenden Meldungen.
3. **Eine Aufzeichnung, die still etwas Falsches behauptet** — die eingefrorene S12-Teilung. Widerrufen: der Fehler lag in **meiner** Gegenrechnung.
4. **Ein Prüfer, der das Gegenteil bestätigt** — „§ 71 GEG" wurde als *belegt* gemeldet, obwohl der Treffer die Streichung dokumentiert. Behoben, neuer Status `ausser_kraft`.
5. **Ein Melder, der über ein Siebtel spricht und wie über das Ganze klingt** — `planbindung.py` sieht 23 von 139 Planabschnitten (`L-65d33e`).

## Erledigt seit 08:30

| | Commit |
|---|---|
| Teilungsschlüssel Pfad → Kennung, 1083 Knoten verschoben | `655baf1` |
| Messung teilt über dieselbe Kennung wie die Behandlung | `32d4e0a`, `715de14` |
| Normbezug unterscheidet Erwähnung von Geltung | `a793432` |
| Doktrin: was aus Modellwissen entstehen darf | `1eaf581` |
| Dritter Melder: Zahl aus Annahme statt aus Quelle | `e57216b` |
| Zweckprojektion trägt mehrere Rolle/Zweck-Paare | `b20a58a` |
| Ausweis-Geheimnis aus eigener Datei, verträgt Kommentare | `776e338`, `bb3f644` |
| Entscheidende Planabschnitte werden Knoten | `9b1d932`, `8a99a88` |

Suite: 882 grün, 1 übersprungen, 0 rot.

## Wartet auf den Betreiber

**Aufgabe 20 und 23 gehören zusammen** — derselbe Ordner: Ausweisordner aus der Reichweite des Prozesses nehmen (`selbstbedienung_moeglich()` meldet weiterhin True), Geheimnis rotieren, Eintrag aus `~/.claude.json` entfernen.
Aufgabe 7: MAUDE-Import holt Daten über das Netz — ein Download braucht das ausdrückliche Wort.
Aufgabe 14: entschieden (Korpus erweitern), aber die Machbarkeit ist knapp — 31 Knotenziele gegen die gerechneten 38 je Hälfte.

## Nicht vergessen

Ein Melder nennt die geprüfte Menge, nicht nur die Befunde — Vorbild `melder/messregeln.py` mit `{"geprueft": 0}`.
Läufe über zehn Minuten gehören nicht in einen Subagenten (`L-1056bb`).
Kein `git stash` für Rot-Proben — `git show <commit>:<datei>` in eine Datei außerhalb des Baums (`L-56a352`).
Wenn die Antwort auf einen Vorfall ein Dokument ist und kein Testfall, ist die nächste Wiederholung eingeplant (`L-122b1c`) — heute innerhalb von vier Stunden eingetreten.
