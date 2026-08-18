# Plan nach dem Rundruf — was am 2026-08-18 gemessen wurde und was daraus folgt

Stand: 2026-08-18T18:05:00+0200 · Zweig `brainlehr/b4-ausweis` · 55 Commits an diesem Tag

Dieser Plan löst keinen anderen ab. Er ergänzt `PLAN_GESAMT_2026-08-13.md` um das,
was ein einzelner Tag an Messungen hergegeben hat, und macht daraus eine Reihenfolge.
Normative Quelle bleibt `REQUIREMENTS_BRAINLEHR.md`.

## §0 Gemessener Ist-Stand

Alles hier ist gemessen, nicht geschätzt. Der Weg steht jeweils dabei.

| Größe | Wert | Weg |
|---|---|---|
| Abrufgüte, fremder Maßstab | **R@5 0,96 · R@10 1,0 · MRR 0,937** | LongMemEval-S, n=25/500, `knowledge_search()` |
| — Vergleichswert Konkurrenz | R@5 0,952 | Selbstangabe `rohitg00/agentmemory` |
| Abrufgüte, eigener harter Korpus | top5 7/35 (20,0 %) | 35 Fälle, Median-Wortüberlappung 6,7 % |
| Katalog Root | **3 von 56 belegt** | `melder/gatestand.py` |
| Katalog Vertragsnaht | **17 von 17 belegt** | dito |
| Knoten / Lehren | 5.157 / 1.085 | Bestand |
| Ähnlichkeitskanten | 9.933 | `knowledge_relations` |
| **Abhängigkeitskanten** | **0** | dito, Typ `loest_ab` |
| Wirkung des Abrufs | **0 verhinderte Korrekturen in 4 Sitzungen** | Rundruf, Knoten `58da4895` |

Die letzten beiden Zeilen sind die wichtigsten des Tages und stehen absichtlich
nebeneinander: Das Modul für gerichtete Kanten ist gebaut und geprüft
(`BDW-P08`, Gate PASS) — der **Bestand** hat davon noch keine einzige. Gebaut ist
nicht wirksam, und dieser Plan existiert, um diesen Abstand zu schließen.

**Was am selben Tag getragen hat**, weil eine Bilanz ohne beide Seiten wertlos ist:
Der Rundruf an sieben Sitzungen brachte vier Antworten und fünf Befunde, von denen
**keiner** aus eigener Arbeit stammte; drei waren am selben Tag baubar. Zwei
Sitzungen korrigierten einander über Prozessgrenzen hinweg, eine zog drei eigene
Meldungen zurück, eine behob einen gemeldeten Defekt in zwei Minuten statt in einer
Untersuchung. Ein Konkurrenzvergleich, der morgens noch Ansichtssache war, ist
abends eine Zahl.

## §1 Der Befund, der alles andere ordnet

Vier von vier antwortenden Sitzungen meldeten dieselbe Klasse, unabhängig
voneinander und in verschiedenen Repos. In den Worten der openlehr-Sitzung:

> „Keine dieser Lücken ist eine Wissens-Lücke; alle sind Auslöser-Lücken. Was mich
> tatsächlich gestoppt hat, waren ausnahmslos verdrahtete Wachen. Kein einziger
> Recall-Treffer hat mich gestoppt."

Das trifft den Hauptmechanismus: Der passive Abruf **zeigt an** und **zwingt zu
nichts**. Als `BDW-P06` (`trigger-or-nothing`) im Katalog.

Zweiter Befund desselben Tages, dreimal aufgetreten (`L-f6c611`): Eine **Quittung**
wurde als Beleg für eine **Wirkung** genommen. Alle drei Quittungen waren wahr — es
gab nichts zu bemerken. Vierte Form, von der lehrAtelier-Sitzung nachgetragen: zwei
Messungen, die zufällig zusammenpassen, wirken wie eine Bestätigung.

## §2 Reihenfolge

Bindend ist nur, wo ein Schritt einen anderen entwertet. Das ist bei **A vor C**
der Fall und sonst nirgends.

**A — Was gebaut ist, wirksam machen.** Drei Module aus diesem Tag hängen an keinem
Auslöser: `rueckfrageschleife.py` (Verdrahtung liegt beim Betreiber, Klientsperre),
`gegenstand.py` (Erstbestand aus `git log --diff-filter=R` noch nicht eingelesen),
`abloesung.py` (0 Kanten im Bestand). Solange das offen ist, misst jede Kennzahl
über sie den Bauzustand und nicht die Wirkung.

**B — Den Rundruf takten.** Die Handprobe hat getragen; drei Züge nach der Antwort
entstand eine neue Abhängigkeitsänderung, die niemand gemeldet hätte, weil niemand
mehr fragte. Als zweite Aktion in `kern/ausloeser.py`, Ausschalter bleibt eine Datei.

**C — Die 53 offenen Gates sortieren, nicht abarbeiten.** Verfahren liegt vor
(`L-0c4880`): disjunkte Blöcke, je Agent eine eigene Ergebnisdatei mit namentlichem
Tabu auf die übrigen, erwartete Anzahl im Auftrag, Summenprobe am Ende. **Nach A**,
weil ein Gate, dessen Mechanismus nicht hängt, als PASS gezählt würde und die Zahl
verdürbe.

**D — LongMemEval-V2 nachmessen.** Der Plan nannte diesen Maßstab seit fünf Tagen
(Weltstand 48,3 %), gemessen wurde S. Kriterium `recall_any@k` wörtlich, volle
Fallzahl statt Stichprobe.

## §3 Was bewusst nicht getan wird

**Verfall nach Zeit.** Ausdrücklich verworfen gegen das Vorbild der Konkurrenz
(Ebbinghaus-Kurve). Ein Eintrag wird nicht falsch, weil er alt ist: `L-542a28` war
vier Stunden alt und hat an diesem Tag einen Fehler gefangen. **Preis:** Der Bestand
wächst weiter und enthält Überholtes. Getragen wird das von der Ablösung — sie
kennzeichnet, statt wegzuwerfen.

**Die 9.933 Ähnlichkeitskanten anfassen.** Sie sind dicht in der falschen Dimension,
aber sie schaden nicht. **Preis:** Der Graph bleibt vorerst symmetrisch, gerichtete
Aussagen entstehen nur dort, wo jemand sie ausdrücklich zieht.

**Die `*_path`-Fremdschlüssel auf IDs umstellen.** Umbau am Herzstück mit
ungemessenem Nutzen; innerhalb der Datenbank deckt `CASCADE` sie. **Preis:** Jede
Kennung, die nach außen geht, bleibt namensgebunden — genau der Fall, den ADR-028
beschreibt.

**Die Gate-Quote schnell verbessern.** 3 von 56 ist unangenehm und ehrlich. Bequeme
Gates zuerst zu nehmen wäre genau der Fehler, den `gatestand.py` aufdecken soll.

## §4 Woran sich Erfolg messen lässt

Nicht an gebauten Modulen, sondern an drei Zahlen:

1. **Verhinderte Korrekturen.** Heute 0 in vier Sitzungen. Der nächste Rundruf
   fragt dieselbe Frage; jede Korrektur, die ein Mechanismus abgefangen hat statt
   des Menschen, zählt.
2. **Abhängigkeitskanten im Bestand.** Heute 0 bei 9.933 Ähnlichkeitskanten.
3. **Belegte Katalogzeilen.** Heute 3 von 56 — und jede neue muss ihren Prüfbefehl
   nennen, der existiert (`gatestand.py` meldet Phantom-Gates).

## §5 Wartet auf den Betreiber

Nicht unter Annahme erledigt, weil es Stopp-Punkte sind:

- **Push.** 45 Commits ungepusht.
- **Die Wächter-Zeile** in `~/.claude/settings.json` — dreimal vom Berechtigungs-
  filter abgewiesen, auch das Lesen. Bis dahin ist `rueckfrageschleife.py` genau
  das, wogegen es gebaut ist.
- **LaunchAgent.** Die lehrAtelier-Sitzung führt die Richtung „fester Ort, nie ein
  Arbeitsbaum" ausdrücklich nicht als beschlossen — eine Peer-Sitzung kann das nicht
  an seiner Stelle entscheiden.
