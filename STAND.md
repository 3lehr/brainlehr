# STAND brainlehr — 2026-08-12T07:00:00+0200

Massgeblich ist die Aufgabenliste der Sitzung, nicht diese Datei. Beim Sitzungsstart zeigt `melder/offene_arbeit.py` den offenen Teil von `docs/SPRINTS.md` — in jedem Arbeitsbaum.

## Sprints

21 gesamt: 9 erledigt, 6 teilweise, 6 offen. Status mit Beleg je Zeile in `docs/SPRINTS.md`.

## Erledigt seit 05:00

| | Commit |
|---|---|
| Sprint-Register mit Beleg je Zeile | `ce2524e` |
| Offene Arbeit beim Sitzungsstart, aus der Datei statt aus dem Sitzungsspeicher | `2daf68e` |
| Vier Haken-Skripte im hub waren seit dem Umzug still tot | hub `469c147f8` |
| Teilung fragt den Auflöser; Wache fängt jeden verdrahteten DB-Namen | `aa811ee` |
| Eingefrorene Teilung berichtigt — die Zahl passte nie zum Code | `fa33bf0` |
| Teilungstest prüft die Schranke statt der Zahl | `934e481` |

Suite: 857 grün, 1 übersprungen, 7 xfail, 0 rot.

## Der Befund der Nacht, in drei Gestalten

Dieselbe Fehlerklasse, dreimal anders verkleidet:

1. **Ein Werkzeug, das still nichts tut.** `kern/normbezug.py` meldete jedes Normzitat als unbelegt, weil sein Pfad ins Leere zeigte. `if not pfad.exists(): return "unbelegt"` — „geprüft und nichts gefunden" war von „gar nicht geprüft" nicht zu unterscheiden. Kriterium und zehn weitere Fundstellen: Knoten `73ed942f`.
2. **Ein Kanal, der still nicht zustellt.** Der Eilmeldungs-Haken war von 21:26 bis 06:00 tot, `exit 0`, kein Mucks — bei drei wartenden dringenden Meldungen. Vierter Fundort derselben Umbenennung, und der erste außerhalb von brainlehr: eine Wache endet an der Repo-Grenze, ein Dateiname nicht.
3. **Eine Aufzeichnung, die still etwas Falsches behauptet.** Die eingefrorene Teilung nannte 1008/1115, der Code im selben Commit liefert 1070/1055. Weil die Datei sich als unverändert*lich* ausgibt, wird sie gelesen statt nachgerechnet. „Unveränderlich" und „geprüft" sind zwei Eigenschaften; wer nur die erste herstellt, hat einen fälschungssicheren Irrtum (`L-747b33`).

## Offen, ohne Betreiber

Aufgaben 4 bis 11 der Liste. Nächste ohne Vorbedingung: #5 Korpus-Voreingenommenheit (72 Aufträge gegen 6 Fragen), #6 die zehn Fundstellen einzeln, #11 die 52 Selbsttests außerhalb jeder Suite (8 davon rot).

## Wartet auf den Betreiber

`BRAINLEHR_GEHEIMNIS` steht im Klartext in `~/.claude.json` und gilt als kompromittiert — **Rotation tippt er selbst**, Aufgabe #10 bereitet nur die Stelle vor. · Rang für die Arbeitsweise-Direktive `2c365d54` (Rang 1 und 2 verlangen einen menschlichen Entscheider, der Speicher hat mich zu Recht abgewiesen). · `actor` in `mcpServers.knowledge.env`. · NIST-Teilbestand unbenannt. · ASRS braucht einen Ausfuhrlauf. · Eine ältere dringende Meldung fragt nach openlehr.

## Nicht vergessen

Läufe über zehn Minuten gehören nicht in einen Subagenten — sie enden im Wartezustand (`L-1056bb`, dreimal). Agenten committen nur mit Pfadangabe (`L-73020e`). Tests gegen absolute Zahlen des Bestands sind rot, sobald jemand nebenan arbeitet — Eigenschaft prüfen, nicht Zahl.
