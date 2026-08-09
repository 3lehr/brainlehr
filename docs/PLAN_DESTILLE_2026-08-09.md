# Plan: Was brainlehr von der Destille lernt — und was es besser kann

Stand: 2026-08-09T06:05:00+0200 · Anlass: Betreiber, nach dem Video zu „Distill" (YouTube YU9GscXWK-E) · Grundlage: eigene Messungen vom 2026-08-08/09, alle unten mit Zahl

## Der gemessene Ist-Stand, nicht der vermutete

| Frage | gemessen | wo |
|---|---|---|
| Trifft der Abruf? | **0 von 35** Prüffällen, in jeder Schalterstellung | `abrufguete.py` |
| Was kostet er? | **2512 Zeichen je Prompt**, 40 % der Fälle leer | `liefermenge.py` |
| Warum trifft er nicht? | 12 von 15 Ziel-Lehren scheitern an `MIN_HITS=3`; im Bedeutungskanal liegt das Ziel auf Rang 7–597 von 668, `MAX_LESSONS=2` erreicht es nie | dito |
| Wer stuft Normen ein? | **62 von 71** Normen hat die Maschine selbst eingestuft (`claude-code/opus-5`) | `knowledge_nodes.norm_entschieden_von` |
| Wieviel Bestand ist Fremdimport? | 1638 NASA-Knoten gegen 376 eigene | `knowledge_nodes.path` |
| Kommt gesammelte Literatur an? | 56 Paper in zwei Zitationsnetzen, **10** als Knoten im Speicher, **1** Knoten mit PDF-Quelle | `citation-network.json` + `knowledge_nodes.source` |

**Der rote Faden durch alle sechs Zeilen:** Es fehlt nicht an Wissen und nicht an Werkzeugen. Es fehlt an **Stufen**. Alles liegt sofort gleich weit vorn, gleich gültig, gleich auffindbar — und deshalb findet der Abruf nichts.

## Was die Destille besser macht (drei Dinge, gemessen an unseren Zahlen)

**1. Entstehung nach Bereich, nicht nur Auslieferung nach Bereich.** Dort entsteht Wissen projektlokal und wandert erst nach Prüfung nach oben. Bei uns landet jeder Fund sofort im globalen Bestand. Das erklärt die 1638-zu-376-Zeile: Der NASA-Import verdünnt jede Suche, weil es keine Ebene gibt, auf der er nicht mitspielt.

**2. Promotion als eigener, bestätigter Vorgang.** Nicht „ist wichtig, kommt rein", sondern: das System schlägt vor, der Mensch bestätigt, dann wandert es. Wir haben nur den Sofort-Weg.

**3. Ein festes Muster je Typ.** Jedes Paper dort: Kernaussage, Methodik, Vergleich, Bewertung, Zitation — immer gleich. Unsere Knoten haben Freitext in `summary`/`content`, und genau deshalb sind sie so ungleich brauchbar.

## Was wir besser machen, und es ist nicht wenig

Zahlen. Sein System sieht funktionierend aus und er ist zufrieden; ob der Abruf das Richtige liefert, ist dort nicht gemessen. Unseres sah gestern auch funktionierend aus. Dazu: Herkunftspflicht mit Umschreibsperre, Geltungsdauer, Rücknahme mit Begründung, Zugriffsprotokoll, Eskalation wiederkehrender Lehren. Nichts davon aufgeben.

**Und eine Warnung aus seinem eigenen Mund, die er nicht misst:** „Je mehr man der KI gibt, desto mehr verwirrt man sie." Er hält das mit kurzen Texten klein. Wir haben die Zahl dafür — 2512 Zeichen je Prompt — und sollten sie zur Kennzahl machen, nicht zur Anekdote.

## Vier Schritte, in bindender Reihenfolge

### S1 · Reifegrad MESSEN statt zuweisen (zuerst, weil billig und weil es eine gemessene Fehlstelle schließt)

Der Deckel aus dem Video („Maschine darf höchstens *Entwurf*") ist die halbe Antwort. Die andere Hälfte, vom Betreiber eingewandt: *bei vielen Sachen kann ich den Reifegrad selbst nicht bestimmen.* Ein Deckel, der auf ein Urteil wartet, das niemand fällen kann, erzeugt eine Halde statt einer Prüfung.

**Darum abgeleitet statt vergeben.** Die Bauform existiert bereits in `konfidenz.py` mit drei Regimen: *beobachtbar* (Bezug ist eine Datei, Änderungen zählbar → Zahl), *deklariert* (Ausgangswert), *unbeobachtbar* (keine Zahl, dafür ein Fälligkeitsdatum). Reifegrad bekommt dieselbe Dreiteilung mit eigenen Belegquellen:

- **abgeleitet** — der Bezug ist beobachtbar (Datei existiert, Commits zählbar), die Aussage hat einen Prüfvermerk, oder sie ist mehrfach unabhängig aufgetreten (`occurrences`).
- **erklärt** — ein Mensch hat entschieden, mit Grund. Das bleibt möglich und schlägt jede Ableitung.
- **unbestimmt** — nichts davon. **Kein Makel, sondern eine Fälligkeit**: der Knoten kommt auf Wiedervorlage, nicht in den Papierkorb.

Der Deckel gilt dann nur noch für **Normrang 1 und 2**: Was für alle gelten soll, entscheidet ein Mensch. Alles andere leitet sich ab. Das trifft die gemessenen 62 Fälle, ohne den Betreiber zu Urteilen zu zwingen, die er nicht hat.

*Nicht getan:* Reifegrad rückwirkend auf 2020 Knoten rechnen. Erst der Mechanismus, dann ein Lauf.

### S2 · Sichtbarkeit: was der Speicher liest und schreibt, steht im Gespräch

Betreiberwunsch, und er trifft eine echte Blindstelle. Der Abruf ist heute sichtbar (`<knowledge-recall>`), **jeder Schreibvorgang ist unsichtbar**. Genau daraus entstand die gemessene Lehre L-706807: Ein Agent meldete „gespeichert", die Herkunftsschranke hatte abgewiesen, niemand sah es.

Eine Zeile je Vorgang, im Gespräch, mit Kennung: `abgelegt: A-d93330 (Annahme)` bzw. `abgewiesen: source_fehlt`. Die Kennung ist der Punkt — sie lässt sich schlechter erfinden als ein „erledigt".

*Grenze:* Der MCP-Server kann nicht in den Chat schreiben. Der Weg führt über den vorhandenen `PostToolUse`-Haken, der das Zugriffsprotokoll ohnehin liest.

### S3 · Die Brücke vom Papernetz in den Speicher

Gemessen: 56 Paper gesammelt, 10 im Speicher, 1 Knoten mit PDF-Quelle. Die Sammelhälfte steht seit Langem, die Destillationshälfte fehlt.

Zu bauen ist **kein zweites Papernetz**, sondern ein Übergang: aus `citation-network.json` werden Knoten mit festem Muster (Kernaussage, Methodik, Bewertung, Zitation — das Muster aus dem Video, es taugt). Herkunft ist die Netzdatei, Reifegrad kommt aus S1.

*Bindende Reihenfolge:* **nach S1.** Ohne abgeleiteten Reifegrad kippen 56 Paper unsortiert in einen Bestand, der schon an Verdünnung leidet — das verschlimmert die 0-von-35-Zeile, statt sie zu heilen.

### S4 · Promotion und Ebenen (der Umbau, zuletzt)

Projektlokale Entstehung, Beförderung nach Prüfung. Das ist der größte Hebel und der einzige echte Umbau. Er beantwortet zugleich das offene „Bereichsauslieferung gehört in den Server" — und zwar besser, als es dort formuliert war: nicht Auslieferung nach Bereich, sondern **Entstehung** nach Bereich.

*Warum zuletzt:* Er ändert die Ablage. Jede Messung davor bleibt vergleichbar, jede danach nicht. Und ohne S1 fehlt das Kriterium, wonach befördert wird.

## Alternativen mit Ablehnungsgrund

**Obsidian oder ein fertiges Zweitgehirn übernehmen.** Abgelehnt: löst Wiederfinden, nicht Widerspruchsfreiheit und nicht Geltung. Beides haben wir bereits härter.

**Reifegrad rein menschlich, wie im Video.** Abgelehnt auf Einwand des Betreibers: erzeugt eine Halde unentschiedener Knoten. Der Deckel bleibt nur dort, wo das Urteil zwingend menschlich ist (Normrang 1–2).

**Erst den Trichter feinjustieren (MIN_HITS, MAX_LESSONS, MAX_NODES).** Abgelehnt, und zwar gemessen — die Messreihe lief am 2026-08-09 über 36 Gitterpunkte (`runs/trichter_gitter_2026-08-09.txt`):

| MIN_HITS | Lehren | Knoten | Zeichen/Fall |
|---|---|---|---|
| 1 | 1/15 | 1–2/20 | **6299 – 12838** |
| 2 | 1/15 | 0/20 | — |
| 3 (Vorgabe) | 0/15 | 0/20 | 2512 |
| 4 | 0/15 | 0/20 | — |

Die Lockerung von 3 auf 1 kauft **einen** Treffer bei den Lehren und ein bis zwei bei den Knoten — für die zweieinhalb- bis fünffache Zeichenmenge je Prompt. **`MAX_LESSONS` und `MAX_NODES` bewegen die Trefferzahl praktisch überhaupt nicht** (nur Knoten 1→2 bei `MIN_HITS=1` und `MAX_NODES=8`); sie erhöhen ausschließlich die Liefermenge. Zwei von drei Reglern sind also wirkungslos, und das gehört benannt statt im Gitter versenkt.

Gegenprobe, dass die Messung überhaupt greift: `MIN_HITS=50` drückt auf 0/35 — das Setzen der Werte wirkt. Zwei Läufe desselben Punktes identisch.

**Daraus folgt die eigentliche Erkenntnis dieses Plans:** Der Abruf scheitert nicht am Trichter, sondern früher — an der Zuordnung selbst. Kein Punkt im Gitter liefert brauchbaren Abruf. Damit sind S1 und S4 nicht eine von mehreren Möglichkeiten, sondern der einzige verbliebene Weg.

*Vorbehalt, der bestehen bleibt:* Der Prüfkorpus ist absichtlich so formuliert, dass er wörtliche Überschneidung mit dem Ziel vermeidet. Er misst damit den schwersten Fall, nicht den durchschnittlichen. Echte Prompts überschneiden sich vermutlich stärker — belegt ist das nicht.

## Woran sich Erfolg messen lässt

Ausschließlich an den zwei Zahlen, die heute schon stehen: **Treffer auf dem Prüfkorpus** (heute 0 von 35) und **Zeichen je Prompt** (heute 2512). Jeder Schritt wird gegen beide gemessen, vorher und nachher. Ein Schritt, der die Trefferzahl hebt und die Zeichenmenge verdoppelt, ist kein Fortschritt, sondern ein Tausch — und wird als solcher benannt.

Zusatzkennzahl ab S1: Anteil der Knoten mit **abgeleitetem** Reifegrad. Steigt er nicht, misst die Ableitung nichts.

## Was bewusst nicht getan wird

Kein eigener Betrachter (der vorhandene reicht, und im Video ist er selbst „schön zum Zeigen, zum Arbeiten kaum relevant"). Keine PDF-Verarbeitung im Speicher — das Papernetz kann das, die Arbeitsteilung bleibt. Keine Rückrechnung alter Bestände vor dem jeweiligen Mechanismus.
