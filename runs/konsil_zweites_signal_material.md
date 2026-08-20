# Konsil-Material: das zweite Signal

Stand 2026-08-20T14:15:00+0200. Dieses Dokument ist für alle Rollen identisch.
Keine Rolle kennt die anderen oder deren Antworten.

---

## Das System, um das es geht

Ein lokaler Wissensspeicher mit rund 5200 Einträgen (Sachverhalte und
Fehlerlehren). Er wird bei jeder Anfrage automatisch befragt und spielt
Treffer in den Arbeitskontext ein — ungefragt, ohne dass ein Mensch die
Suche auslöst.

Zwei Suchkanäle:

- **Stichwortkanal** — SQLite-Volltext (fts5, bm25, inklusive Trigramm)
- **Bedeutungskanal** — lokale Einbettungen (bge-m3, 1024 Dimensionen),
  Kosinusähnlichkeit

Beide werden per Reciprocal Rank Fusion verschmolzen. Alles rechnet auf dem
Gerät, ohne Netz. **Ein Modellaufruf pro Anfrage ist ausgeschlossen** — der
Abruf hängt an jedem einzelnen Prompt, ein Aufschlag von Sekunden ist nicht
tragbar.

Es gibt zusätzlich eine Filterstufe („Ensemble-Pflicht"): Sie liefert nur
aus, wenn beide Kanäle sich hinreichend einig sind. Sonst schweigt das
System.

## Der Prüfkorpus

45 Fälle. 35 davon haben eine hinterlegte richtige Antwort im Bestand
(„lösbar"), 10 sind Fragen aus fremden Sachgebieten, deren Antwort
nachweislich **nicht** im Bestand liegt — dort ist Schweigen die richtige
Reaktion.

Die Anfragen sind in Alltagssprache formuliert, die Ziele technisch. Die
Wortüberlappung zwischen Anfrage und Ziel liegt im Median bei 8,7 Prozent.
Zum Vergleich: bei einem gängigen Standardkorpus (GermanQuAD) sind es 40,0
Prozent. Gemessen an echten Anfragen aus dem Betriebsprotokoll (n=3759)
liegt der Median bei 6,7 Prozent — der eigene Korpus ist also realistisch,
eher noch etwas zu leicht.

## Die Messung, um die es geht

Zwei Betriebsarten, die sich in genau einem Schalter unterscheiden:

- **B** — ohne Ensemble-Pflicht, das System spricht immer
- **C** — mit Ensemble-Pflicht, heutiger Auslieferungszustand

Kreuztabelle über alle 45 Fälle:

| | Anzahl |
|---|---|
| B trifft, C trifft | 1 |
| B trifft, C schweigt (von der Pflicht verworfene Treffer) | 14 |
| B antwortet falsch, C schweigt (verhinderte Fehler) | 10 |
| beide daneben, obwohl die Frage lösbar wäre | 20 |

Vier Fächer, alle 45 Fälle, drei Betriebsarten:

| | richtig geliefert | falsch geliefert | richtig geschwiegen | falsch geschwiegen |
|---|---|---|---|---|
| B | 15 | 30 | 0 | 0 |
| C (heute ausgeliefert) | 1 | 0 | 10 | 34 |
| Schwellenschicht (s.u.) | 15 | 20 | 10 | 0 |

## Der Befund, der die Frage auslöst

Von fünf geprüften Größen trennt genau eine: der **beste Kosinuswert** des
Bedeutungskanals.

| | n | min | Median | max |
|---|---|---|---|---|
| verworfene Treffer | 14 | 0,5497 | 0,5970 | 0,6375 |
| verhinderte Fehler (Fragen ohne Antwort im Bestand) | 10 | 0,4435 | 0,4843 | 0,5410 |
| **Fehlgriffe bei lösbaren Fragen** | **20** | **0,5555** | **0,6030** | **0,6374** |

Die ersten beiden Zeilen trennt eine Schwelle bei 0,545 fehlerfrei. Die
dritte Zeile liegt **vollständig darüber** — 20 von 20 gehen durch.

Ihr Median (0,6030) liegt sogar **über** dem der echten Treffer (0,5970).

Nicht trennend waren: Abstand zum zweitbesten Treffer, Abstand zum Median
der Trefferliste, Zahl übereinstimmender Kanäle (durchweg 0), Trefferzahl.

**In einem Satz:** Der Ähnlichkeitswert sagt zuverlässig, ob überhaupt etwas
Passendes im Bestand liegt. Er sagt nichts darüber, ob das Gelieferte
richtig ist.

## Die 20 Fehlgriffe, von Hand nachgesehen

Bevor nach einem Signal gesucht wurde: Was liefert das System in diesen 20
Fällen eigentlich? Jeder Fall wurde einzeln gelesen — Anfrage, vorgesehenes
Ziel, tatsächlich ausgelieferte Titel und Zusammenfassungen.

| | Anzahl | Kosinus min–max |
|---|---|---|
| **brauchbar, nur anders** — ein anderes Ergebnis beantwortet die Frage sachlich genauso | 3 | 0,6195–0,6354 |
| **teilweise** — berührt das Thema, beantwortet die Frage nicht | 12 | 0,5555–0,6192 |
| **daneben** — nichts Geliefertes hat mit der Anfrage zu tun | 5 | 0,5900–0,6374 |
| Ziel selbst strittig | 0 | — |

Damit ist die Lage genauer als „20 Fehler": **3 sind Fehlurteile des
Prüfkorpus**, der auf exakte Kennungen prüft. **5 sind echte Ausfälle.** Die
Mehrheit — 12 — liegt dazwischen: thematisch in der Nähe, sachlich nutzlos.

Und der Kosinuswert trennt auch diese Klassen nicht: die Mediane liegen bei
0,635 (brauchbar), 0,593 (teilweise) und 0,597 (daneben). Die fünf echten
Ausfälle streuen über das ganze Band, ein Ausfall liegt bei 0,6374 — dem
höchsten Wert der ganzen Gruppe.

## Was das einschlägige Fach dazu sagt

Die Frage hat einen Namen: **Query Performance Prediction**, seit rund 2002
ein eigener Zweig des Information Retrieval.

| | |
|---|---|
| Score-Prädiktoren (NQC/WIG-Familie), klassische Stichwortsuche | r = 0,41–0,46 · τ = 0,32 |
| dieselben, auf Einbettungssuche übertragen | r = 0,15 · **τ = 0,10** |
| Schwelle, ab der das Fach von Brauchbarkeit spricht | τ ≥ 0,5 |

Die jüngste Übersichtsarbeit (arXiv 2504.01101, 2025) schließt selbst, dass
Entscheidungen auf Basis dieser Vorhersagen „nur marginale Gewinne" bringen.

Arbeiten, die deutlich höhere Korrelationen melden (bis 0,89, arXiv
2604.07985), erreichen das nur, indem der Prädiktor die **erzeugte Antwort**
mitliest — das kostet einen Modellaufruf pro Anfrage und ist hier
ausgeschlossen.

Zwei Richtungen gelten als am ehesten übertragbar auf Einbettungssuche:

- **Kohärenz der Nachbarschaft** (arXiv 2310.11405): nicht der eine beste
  Wert, sondern die Geometrie der ganzen Trefferwolke — liegen die Treffer
  eng beieinander oder streuen sie? Verbesserung wird relativ gemeldet (bis
  92 % bzw. 188 % gegenüber Vorgängern), eine absolute Korrelation war nicht
  belegbar.
- **Störungsrobustheit** (Zhou & Croft, CIKM 2006; für Einbettungssuche
  fortgeführt 2024): Anfrage oder Repräsentation stören, zweiten Lauf
  fahren, Stabilität der Trefferliste messen. Braucht mehrfache Läufe.

## Die harten Randbedingungen

1. **Kein Modellaufruf pro Anfrage.** Der Abruf hängt an jedem Prompt.
2. **Alles lokal.** Kein Netz, keine fremden Dienste.
3. **Vorhanden und kostenlos nutzbar:** beide Kanäle mit ihren Scores, die
   Einbettungen aller Einträge, ein Betriebsprotokoll mit rund 21 000
   Zugriffen, ein zweiter Prüfkorpus mit über 12 000 Fällen.
4. **Ein zweiter Lauf pro Anfrage wäre vertretbar**, ein zehnter nicht.
5. Falsch liefern und falsch schweigen sind **nicht gleich teuer** — aber
   wie ungleich, ist nicht festgelegt. Das ist ausdrücklich eine offene
   Frage an das Konsil.

## Die Frage

**Ein System liefert eine Antwort, kennt die richtige nicht, und soll sagen,
wie sehr es sich irren könnte. Das einschlägige Fach kommt auf τ = 0,10 und
nennt den Gewinn marginal.**

**Was übersieht es — aus Sicht deines Fachs?**
