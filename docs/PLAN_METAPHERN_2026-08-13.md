# Metaphern als Bauform — und wie wir ihre Wirkung selbst messen

Stand 2026-08-13T10:05:00+0200. Betreiberfrage: Hilft es einem Sprachmodell,
wenn Regeln und Bauformen mit Metaphern belegt sind? Und gibt es Belege?

## Der Stand der Belege — fremd, nicht selbst gemessen

**Gegen die Metapher, wenn es um Richtigkeit geht.** 162 Rollen, 2410
Faktenfragen, 4 Modellfamilien: Personas im Systemprompt verbessern die
Genauigkeit **nicht**. Nimmt man nachträglich je Frage die beste Rolle, wird es
deutlich besser — die beste *vorher* zu bestimmen gelang nicht besser als
Zufall.
(*When „A Helpful Assistant" Is Not Really Helpful*, EMNLP Findings 2024,
arXiv:2311.10054)

**Für die Metapher, wenn es um Übertragung geht.** Metaphern wirken als **Brücke
zwischen Domänen** — kausal gemessen, nicht beobachtet: Lyrik im Vortraining
hob die Übertragung von Verhalten in fremde Gebiete (bei einem Modell 13,5 % →
45,0 %); Maskieren der Metaphern senkte sie wieder (47,1 % → 28,8 %), während
zufälliges Maskieren als Kontrolle fast nichts tat. Und die Gegenrichtung:
Maskiert man Metaphern in den **korrigierenden** Daten, wird die Korrektur
schwächer.
(*Metaphors are a Source of Cross-Domain Misalignment*, Hu et al.,
arXiv:2601.03388, Januar 2026)

**Die Lücke, die wir selbst schließen müssen.** Die zweite Arbeit misst
Metaphern in **Trainingsdaten**, nicht Rollennamen im Prompt. Dass sich das
überträgt, ist plausibel und **nicht gezeigt**. Genau diese Lücke ist unser
Messgegenstand — nicht die Frage, ob Metaphern „gut" sind.

## Die Arbeitsthese, ausdrücklich als zu widerlegende formuliert

> Eine metaphorisch benannte Regel wird auf **mehr Fälle** angewandt als eine
> wörtlich formulierte gleichen Inhalts — auch auf solche, die in ihr nicht
> aufgezählt sind. Der Preis ist, dass sie auch auf Fälle angewandt wird, die
> **nicht gemeint** waren.

Zwei Größen, nicht eine: **Reichweite** und **Fehlanwendung**. Eine Messung, die
nur die erste erhebt, wird die Metapher immer gewinnen lassen.

## Der Messaufbau

**Paare statt Einzelfassungen.** Je Regel zwei Fassungen, gleicher Inhalt:

| | Beispiel |
|---|---|
| wörtlich | „Wer Grenzwerte festlegt, setzt sie nicht selbst durch." |
| metaphorisch | „Umweltamt schreibt Grenzwerte, Polizei setzt sie durch." |

**Drei Fallmengen je Paar, und die dritte entscheidet:**

1. **Genannte Fälle** — in der Regel wörtlich aufgezählt. Beide Fassungen müssen
   sie treffen; tut eine es nicht, ist das Paar ungültig, nicht die Metapher
   schlecht.
2. **Ungenannte, aber gemeinte Fälle** — hier soll sich die Reichweite zeigen.
3. **Ungenannte und NICHT gemeinte Fälle** — hier soll sich der Preis zeigen.
   Beispiel zu „Umweltamt": ein Fall, in dem dieselbe Stelle Grenzwert **und**
   Durchsetzung tragen soll, weil es keine zweite gibt. Die Metapher legt nahe,
   das zu trennen; die Regel meint es nicht.

Ohne Menge 3 misst der Versuch nur, ob eine Metapher breiter greift — und das
tut sie laut Fremdbefund ohnehin.

**Negativkontrolle:** dieselbe Regel mit einer **unpassenden** Metapher
(„Zirkusdirektor schreibt Grenzwerte"). Steigt die Reichweite auch dort, misst
der Versuch die Anwesenheit eines Bildes, nicht seine Passung.

**Blind gegen die Fassung.** Wer die Fälle bewertet, darf nicht wissen, welche
Fassung sie erzeugt hat.

## Was bewusst nicht gemessen wird, samt Preis

- **Keine Genauigkeitsmessung auf Faktenfragen.** Preis: Wir wiederholen den
  fremden Befund nicht. Gewinn: Wir messen die Größe, die uns betrifft —
  **Anwendungsbreite einer Regel**, nicht Wissen.
- **Kein Umbau bestehender Regeln vor der Messung.** Zuerst messen, dann
  entscheiden. Andernfalls wäre die Umstellung ihre eigene Begründung.
- **Keine Aussage über Modellfamilien hinweg.** Gemessen wird, was hier läuft.

## Woran sich Erfolg misst

- **Beide Größen liegen als Zahl vor**, je Paar: Reichweite auf Menge 2 **und**
  Fehlanwendung auf Menge 3. Eine Zahl allein ist kein Ergebnis.
- **Die Negativkontrolle trennt.** Passende und unpassende Metapher
  unterscheiden sich messbar — sonst ist der Aufbau untauglich, unabhängig vom
  Ergebnis.
- **Ein Nullergebnis ist ein Ergebnis** und wird als solches festgehalten. Nach
  dem Personas-Befund ist es der wahrscheinlichere Ausgang.

## Die Entscheidung, die danach ansteht

Fällt die Messung **für** die Metapher aus, gilt trotzdem die Grenze aus dem
Fremdbefund: **Eine harte Sperre hängt nie allein an einem Bild.** Was eine
Metapher sonst noch mitbringt, hat niemand ausgesucht — genau das ist der
gemessene Mechanismus. Metapher für Breite, wörtliche Regel plus Mechanismus
für Grenzen.

## Aufträge, fertig zum Übergeben

**Für alle Aufträge gleichermaßen gilt:** Arbeitsort
`/Volumes/daten/Begod2026/brainlehr`, Zweig `brainlehr/b4-ausweis`. Zuerst
`CLAUDE.md` lesen, dann diesen Plan. „Sieht der Code anders aus als hier
beschrieben, halte dich an den Code und melde die Abweichung." Kein `git add
-A`, kein Push, kein `git stash`. Committen mit expliziter Pfadliste. Volle
Suite im Vordergrund mit `timeout=600000`. Datenbanknamen über `kern/speicher`.

### Schritt 1 · Regelpaare und Fallmengen anlegen

| | |
|---|---|
| **Darf ändern** | eine neue Datei unter `messungen/` für die Fallmengen, dazu ihr Test |
| **Tabu zusätzlich** | `haken/` (gesamt), `knowledge_mcp_server.py`, `schema.sql`, `kern/ausschreibekatalog.py` |
| **Fakten** | Fremdbefunde oben, beide mit Fundstelle. Die zweite Arbeit misst Trainingsdaten, nicht Prompts — dieser Unterschied gehört in den Kopf der Datei, nicht in eine Fußnote. |
| **Abnahme** | Je Paar existieren alle **drei** Fallmengen, Menge 3 nicht leer. Ein Paar ohne nicht gemeinte Fälle wird abgewiesen, als Test. |

### Schritt 2 · Blinder Durchlauf und Auswertung

| | |
|---|---|
| **Darf ändern** | das Messskript unter `messungen/`, die Ergebnisdatei unter `runs/` |
| **Tabu zusätzlich** | die Fallmengen aus Schritt 1 — wer misst, ändert die Fälle nicht |
| **Fakten** | `kern/codestand.py` liefert Commit und Verschmutzungsgrad; beides gehört in die Ergebnisdatei. Jede Zahl mit Nenner. |
| **Abnahme** | Die Bewertung kennt die Fassung nicht — nachweisbar, nicht behauptet. Negativkontrolle mit unpassender Metapher läuft mit. Reichweite **und** Fehlanwendung stehen getrennt in der Ergebnisdatei. |

## Fortschreibung nach der Umsetzung — 2026-08-14T01:15:00+0200

Beide Schritte gefahren (`386bbf2`, `c275280`). Ergebnis in
`runs/metaphern_ergebnis_2026-08-14.json`, Knoten `8bfca151`.

**Es kam das heraus, was der Plan als wahrscheinlicher benannt hatte: ein
Nullergebnis.** Die passende Metapher gewinnt bei zwei von vier Paaren genau
einen Fall Reichweite, bei den anderen beiden nichts. Fehlanwendung
unterscheidet sich in keinem Paar. Bei Zellgrößen von ein bis drei Fällen ist
ein Fall Unterschied die kleinste darstellbare Regung, kein Effekt.

**Was anders kam als geplant, und es ist der eigentliche Ertrag:**

- Die Negativkontrolle trennt **schärfer** als vorgesehen. Die unpassende
  Metapher erreicht nicht nur weniger Reichweite — sie trifft nicht einmal die
  wörtlich *genannten* Fälle und ist damit in allen vier Paaren ungültig. Der
  Aufbau misst also Passung, nicht die Anwesenheit eines Bildes. Als
  Nebenbefund: eine unpassende Metapher transportiert auch den genannten
  Inhalt nicht mehr.
- Bei `zweimal_ist_die_grenze` liegt die Fehlanwendung in **beiden** Fassungen
  bei 2/2. Ursache ist nicht das Bild, sondern der **herausgelöste** Regeltext:
  ihm fehlen die vier Stopp-Punkte, die andernorts in `CLAUDE.md` stehen. Das
  ist ein Fund über isolierte Regeln und gehört getrennt gewertet — er trifft
  jede Regel, die man aus ihrem Umfeld nimmt, auch die wörtliche.

**Die Grenze der Messung, benannt statt verschwiegen:** ein Urteiler, Urteile
sind Fließtext-Einschätzungen, kein mechanischer Test. Die Blindheit ist mit
vier Tests belegt (Vorlage trägt weder Fassung noch Menge noch Paar, die
Kennung kodiert sie nicht, die Zuordnung liegt getrennt, die Reihenfolge hängt
deterministisch am protokollierten Seed). Ein zweiter Urteiler wäre der
nächste Schritt — er steht **nicht** an, solange die Zellen so klein sind: was
zuerst fehlt, sind Fälle, nicht Urteile.

**Die Entscheidung, die damit gefallen ist:** Regeln werden **nicht** auf
Metaphern umgestellt. Die Umstellung hätte sich nur auf diese Zahlen stützen
können, und die tragen es nicht. Unberührt bleibt die Grenze aus dem
Fremdbefund: eine harte Sperre hängt nie allein an einem Bild.
