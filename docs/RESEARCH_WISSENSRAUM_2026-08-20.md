# Wissensraum: warum er verklumpt, und was andere Felder dagegen haben

Stand: 2026-08-20T08:05:00+0200. Anlass: Betreiberauftrag — „mir fehlt es an
Farbigkeit, mir fehlt die Möglichkeit live zu sehen welche Knoten und Kanten
miteinander interagieren, mir ist alles zu verklumpt". Vier Zwecke gleichzeitig
gewünscht (Struktur · Bewegung live · Zeitverlauf · Navigieren), Gegenmittel
gegen die Verklumpung ausdrücklich als **Regler**, mit denen der Nutzer selbst
einstellt, wie viel er sieht.

## 1. Der gemessene Ist-Stand — und er beantwortet die Frage schon halb

Alle Zahlen aus der Betriebsdatenbank, 2026-08-20:

| | |
|---|---:|
| Knoten | 5 205 |
| Kanten | 10 389 |
| Dichte | 0,000767 |
| Knoten ohne jede Kante | 728 (14 %) |
| Knoten mit genau einer Kante | 942 |
| Grad: Median / Mittel / Max | 4 / 4,6 / 43 |
| Komponenten | 347, größte 2 264 (43 %) |

**Der eine Befund, der alles andere ordnet — die Kantenarten:**

| Art | Anzahl | Anteil |
|---|---:|---:|
| `aehnlich_bedeutung` | 10 067 | **96,9 %** |
| `abgeleitet_von` | 257 | 2,5 % |
| `lesson_mentions_file` | 43 | 0,4 % |
| `derived_from`, `implements`, `loest_ab`, `produces`, `supersedes` | 14 | 0,1 % |

**Das ist die Ursache der Verklumpung, und sie ist keine Darstellungsfrage.**
Ein Ähnlichkeitsnetz *hat* keine Struktur — es ist per Bauart ein Filz, in dem
jeder mit jedem hinreichend Ähnlichen verbunden ist. Die Kanten, die eine
Aussage tragen („X wurde abgelöst durch Y", „A ist abgeleitet aus B"), sind
darin **40 : 1 ertränkt**. Wer den Graphen so zeichnet, zeichnet 97 % Rauschen
und 3 % Bedeutung übereinander.

**Und die Schwelle ist bereits ein fertiger Regler.** Die
Ähnlichkeitskanten tragen `confidence` zwischen 0,65 und 1,0 — heute wird
davon nichts genutzt, gezeigt wird alles ab 0,65:

| Schwelle | Kanten | Anteil |
|---:|---:|---:|
| ≥ 0,65 | 10 067 | 100 % |
| ≥ 0,70 | 4 541 | 45 % |
| ≥ 0,75 | 1 594 | 16 % |
| ≥ 0,80 | 541 | 5 % |
| ≥ 0,85 | 197 | 2 % |
| ≥ 0,90 | 84 | 1 % |

Ein einziger Schieberegler über dieser Spalte nimmt dem Bild in einem Zug 84 %
seiner Kanten. Das kostet **keine** Forschung und keine neue Bibliothek.

**Was für die anderen drei Zwecke schon vorliegt und ungenutzt ist:**

- **Bewegung:** `access_log` trägt **21 389 Ereignisse** seit 2026-03-25, davon
  **1 484 in den letzten 24 Stunden**, über 103 Sitzungen, mit `action`
  (`search` 15 867, `add` 1 596, `update` 1 323, `read` 1 007), `actor`,
  `session` und Zeitstempel. Das *ist* die Live-Schicht — sie wird nur nirgends
  gezeigt.
- **Zeit:** `created_at`/`updated_at` an jedem Knoten, `gilt_ab` (164),
  `gilt_bis` (2), `zurueckgezogen` (8), `access_count` (nur 190 von 5 205
  Knoten je abgerufen — auch das ist eine Aussage).
- **Zweite Kantenschicht:** `mycel_naehe` (6 288) und `mycel_narbe` (2 065)
  existieren neben `knowledge_relations` und tauchen in keiner Darstellung auf.

## 2. Was andere gegen den Filz tun

Der Fachbegriff für unser Bild ist **hairball**. Die Literatur ist sich
einig, dass er sich nicht weglayouten lässt — nur wegrechnen oder wegfiltern.

**a) Rückgrat statt Schwelle (Netzwerkwissenschaft, Statistik).** Eine globale
Schwelle löscht schwach verbundene Regionen ganz. Der **Disparitätsfilter**
(Serrano, Boguñá, Vespignani, PNAS 2009) normiert **pro Knoten** und behält
nur Kanten, die gegen eine Gleichverteilung an ihrem Endpunkt statistisch
auffällig sind. Typisch bleiben 5–30 % der Kanten und 50–90 % des Gewichts,
und zwar über *alle* Größenordnungen hinweg. Das ist der methodisch saubere
große Bruder unseres Schwellenreglers.

**b) Progressive Enthüllung.** Startbild 20–50 Knoten, alles weitere auf
Anforderung. Nicht „zeig alles und lass den Nutzer suchen", sondern
„zeig wenig und lass ihn ausklappen".

**c) Semantischer Zoom / Bündelung.** Regionen als **Superknoten** einklappen,
Kantenbündel als **Superkante** zusammenfassen; die Darstellung wechselt mit
der Zoomstufe die Bedeutung, nicht nur die Größe. Neuere Arbeiten lassen die
Bündelung von einem Sprachmodell benennen (*Semantic Bundling*, arXiv 2026) —
für uns naheliegend, wir haben das Modell ohnehin.

**d) Matrix statt Knoten-Kanten-Bild.** Oberhalb weniger Dutzend Knoten
schlägt eine sortierte Adjazenzmatrix das Netzbild bei fast jeder Aufgabe
außer Pfadverfolgung. Sie verklumpt prinzipiell nicht.

## 3. Die Fremdfelder — und ja, es gibt echte Schnittpunkte

Die Frage war, ob Proteinfaltung, Materialkunde und ähnliche Felder
Berührungspunkte mit unserem Wissenssystem haben. **Ja, vier — und drei davon
sind keine Analogie, sondern dasselbe Verfahren.**

**1. Die Kontaktkarte ist unsere Matrixdarstellung.** Die Strukturbiologie
zeigt ein Protein routinemäßig **nicht** als 3D-Knäuel, sondern als
*contact map*: eine N×N-Matrix, Zelle hell, wenn zwei Aminosäuren nahe
beieinander liegen. Der Grund ist wörtlich unserer — das Knäuel ist unlesbar,
die Matrix nicht. Was dort Aminosäure und Abstand ist, ist bei uns Knoten und
Ähnlichkeit. Dieselbe Darstellung, ein anderer Gegenstand.

**2. Die PAE-Matrix beantwortet eine Frage, die wir gar nicht stellen.**
AlphaFold liefert neben der Struktur eine *Predicted Aligned Error*-Matrix:
nicht „wo liegt das Atom", sondern **„wie sicher bin ich mir, dass diese
beiden Teile zueinander so liegen"**. Übertragen: nicht „welche Knoten sind
ähnlich", sondern „wie belastbar ist diese Nachbarschaft". Wir haben die Zahl
dafür bereits — `confidence` je Kante — und zeigen sie nirgends. Genau daraus
entsteht die Farbigkeit, die fehlt: Farbe nach **Sicherheit**, nicht nach
Ordnerzugehörigkeit.

**3. Faltung und Layout sind dasselbe Optimierungsproblem.** Ein
kraftbasiertes Layout minimiert eine Energie über Knotenpositionen; eine
Faltungssimulation minimiert eine Energie über Atompositionen. Gleiche
Algorithmenfamilie, gleiche Falle: viele lokale Minima, und das gefundene
hängt vom Startpunkt ab. Praktische Folge für uns: **zwei Läufe desselben
Graphen ergeben zwei verschiedene Bilder.** Solange das so ist, darf niemand
aus der *Lage* eines Knotens etwas ablesen — und wer es doch tut, liest
Rauschen. Wer stabile Bilder will, braucht einen festgeschriebenen Startzustand
oder ein deterministisches Verfahren.

**4. Materialkunde: Kristallgraphen (CGCNN).** Kristalle werden als Graph aus
Atomen und Bindungen dargestellt und mit Graph-Netzen auf **Eigenschaften**
hin ausgewertet. Belegt ist dort auch Transferlernen zwischen Materialklassen.
Für uns ist das die Antwort auf eine Frage jenseits der Darstellung: Aus
Struktur + Einbettung lässt sich eine Eigenschaft **vorhersagen** — etwa
welcher Knoten als Nächstes abgerufen wird, oder welche zwei Knoten verbunden
gehören, ohne dass es je jemand eingetragen hat. Wir haben beide Zutaten
(Vektoren für alle 5 205 Knoten, Kantenliste); genutzt wird davon heute nur
die Ähnlichkeit.

**Was NICHT trägt:** Der Vergleich mit Faltung *als Bild* („Wissen faltet
sich") ist hübsch und leer. Der Wert liegt in Punkt 1 bis 4, und die sind
allesamt konkret genug, um sie zu bauen oder zu verwerfen.

## 4. Die Regler, mit gemessenen Rastpunkten

Nicht „Schieberegler für alles", sondern fünf, die je eine gemessene Größe
steuern. Die Zahlen daneben sind heutige Werte, keine Schätzungen:

1. **Kantensicherheit** `0,65 … 0,90` → 10 067 … 84 Kanten. Der wirksamste.
2. **Kantenart** — Ähnlichkeit aus/an. Aus: 322 Kanten bleiben, und die tragen
   alle eine Aussage. Das ist der Regler, der aus dem Filz ein Netz macht.
3. **Mindestgrad** — 728 Knoten haben Grad 0, 942 haben Grad 1. Ein Regler bei
   2 nimmt ein Drittel der Punkte aus dem Bild, ohne eine einzige Verbindung
   zu verlieren.
4. **Zeitfenster** — „nur was seit X angefasst wurde". Bei 24 Stunden bleiben
   die Knoten aus 1 484 Ereignissen.
5. **Ebene** — Ast (29), Unterast, Einzelknoten. Semantischer Zoom über den
   Pfad, den wir ohnehin führen.

Jeder Regler braucht **die Zahl, die er gerade bewirkt, direkt daneben**
(„Kanten: 1 594 von 10 067"). Ohne sie ist ein Regler ein Ratespiel, und der
Nutzer stellt ihn einmal falsch und nie wieder an.

## 5. Was das für die Darstellung heißt

Kein einzelnes Bild kann die vier gewünschten Zwecke tragen. Vorschlag: **eine
Fläche, vier Schichten, ein Reglerbrett.**

- **Grundriss** = Karte aus den Einbettungen (UMAP), nicht aus Kräften. Feste
  Lage, kein Zufall zwischen zwei Läufen, kein Filz — Nähe bedeutet dort
  Bedeutung, und das ist genau das, was wir zeigen wollen.
- **Kanten** darüber, nur die eingestellten (Regler 1 und 2).
- **Bewegung** als Aufleuchten aus `access_log` — ein Abruf lässt seine Treffer
  kurz glühen. Das ist die „Live"-Schicht und sie ist datenseitig fertig.
- **Zeit** als Zeitleiste unter der Fläche, die Regler 4 steuert.
- **Farbe** nach Sicherheit und Alter, nicht nach Ordner. Farbe muss eine
  Aussage tragen, sonst ist sie Dekoration (und WCAG 2.2: nie Bedeutung
  allein über Farbe — es braucht zusätzlich Form oder Beschriftung).

## 6. Nächster Schritt, verhältnismäßig

Zwei Handgriffe, bevor irgendetwas Großes gebaut wird:

1. **Regler 1 und 2 in die bestehende Darstellung** — eine Nachmittagsarbeit,
   und sie beweist oder widerlegt die These aus Abschnitt 1 am echten Bestand.
2. **Eine UMAP-Karte aus den vorhandenen 5 205 Vektoren rechnen** und neben das
   heutige Kraftbild legen. Zwei Bilder desselben Bestands nebeneinander sind
   der billigste Weg, die Grundsatzfrage zu entscheiden — und die
   **Latte** dafür ist das heutige Bild.

**Nicht getan wird** vorerst: Disparitätsfilter, Superknoten, Matrixansicht,
Eigenschaftsvorhersage. Alle vier sind begründet, aber keiner lohnt, bevor
Schritt 1 und 2 gezeigt haben, wie viel schon die Regler bringen.

## Quellen

- Serrano, Boguñá, Vespignani: *Extracting the multiscale backbone of complex
  weighted networks*, PNAS 106(16), 2009 — https://www.pnas.org/doi/10.1073/pnas.0808904106
- *Knowledge Graphs in Practice: Characterizing their Users, Challenges, and
  Visualization Opportunities* — https://arxiv.org/html/2304.01311v4
- *Semantic Bundling: Interactive Node and Edge Bundling to Simplify Knowledge
  Graphs using Large Language Models* — https://arxiv.org/html/2608.04002v1
- Cambridge Intelligence, *Graph visualization UX* —
  https://cambridge-intelligence.com/blog/designing-intuitive-data-experiences-with-graph-visualizations/
- SPIN-CGNN (Kontaktkarten als Graphgrundlage) —
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10729952/
- AlphaFold2, Grenzen und PAE-Deutung —
  https://pmc.ncbi.nlm.nih.gov/articles/PMC11956457/
- CGCNN und Transferlernen in der Materialinformatik —
  https://www.sciencedirect.com/science/article/abs/pii/S0927025621000392
