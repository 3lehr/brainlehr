# STAND brainlehr — 2026-08-12T08:30:00+0200

Massgeblich ist die Aufgabenliste der Sitzung. Beim Sitzungsstart zeigt `melder/offene_arbeit.py` den offenen Teil von `docs/SPRINTS.md` — in jedem Arbeitsbaum.

## S12: Teilungsschlüssel gewechselt, Pfad → Kennung

Der Pfad ist veränderlich, und das ist belegt: `migrationen/nachziehung_pfad_hygiene_2026-08-07.py` hat Pfade bereits einmal in großer Zahl umgeschrieben. Ein Knoten hätte lautlos die Hälfte wechseln können. Gewechselt in `655baf1`, bevor ein einziger Text neu formuliert war — danach wäre der Wechsel unmöglich gewesen.

Verschiebung durch den Wechsel: 572 Knoten von unbehandelt nach behandelt, 511 in die Gegenrichtung, 1042 unverändert. Neue Verteilung 1070 / 1055. Die alte Aufzeichnung bleibt wortgleich stehen, die neue liegt daneben (`runs/teilung_s12_2026-08-12_id.json`).

**Läuft gerade:** Ausgangsmessung unter dem neuen Schlüssel. Die alte (`8f3ae01`) galt für die Pfad-Teilung und ist als Vergleichsbasis wertlos.

## Zurückgezogen

Der Befund „eingefrorene Teilung stimmt nicht mit dem Code überein" war **falsch** (`0cd159e`). Meine Gegenrechnung baute `bestand()` nach und nahm die Kennung, während der Code den Pfad nahm. Ein Test, der die Rechnung des Codes nachbaut, prüft seine eigene Nachbildung — und ist dann nicht bloß falsch, sondern überzeugend. Lehre `L-747b33`, umgeschrieben.

## Suite

860 grün, 1 übersprungen, 7 xfail, 0 rot.

Zwischenzeitlich beschädigt und repariert: Ein `git stash push … && … ; git stash pop` in einem verketteten Befehl kollidierte mit einem drei Stunden alten Stash — Konfliktmarker in zwei Testdateien, ein doppelter Tabellenblock in `schema.sql`. Aus HEAD zurückgeholt, alter Stash entsorgt, Lehre `L-56a352`. Für Rot-Proben künftig `git show <commit>:<datei>` in eine Datei außerhalb des Baums.

## Offen, ohne Betreiber

Aufgaben 4 bis 11 der Liste. Nächste ohne Vorbedingung: #5 Korpus-Voreingenommenheit (72 Aufträge gegen 6 Fragen), #6 die zehn Fundstellen einzeln, #11 die 52 Selbsttests außerhalb jeder Suite (8 davon rot).

## Wartet auf den Betreiber

`BRAINLEHR_GEHEIMNIS` steht im Klartext in `~/.claude.json` und gilt als kompromittiert — **Rotation tippt er selbst**, Aufgabe #10 bereitet nur die Stelle vor. · Rang für die Arbeitsweise-Direktive `2c365d54` (Rang 1 und 2 verlangen einen menschlichen Entscheider, der Speicher hat mich zu Recht abgewiesen). · `actor` in `mcpServers.knowledge.env`. · NIST-Teilbestand unbenannt. · ASRS braucht einen Ausfuhrlauf. · Eine ältere dringende Meldung fragt nach openlehr.

## Nicht vergessen

Läufe über zehn Minuten gehören nicht in einen Subagenten — sie enden im Wartezustand (`L-1056bb`, dreimal). Agenten committen nur mit Pfadangabe (`L-73020e`). Tests gegen absolute Zahlen des Bestands sind rot, sobald jemand nebenan arbeitet — Eigenschaft prüfen, nicht Zahl.
