# Plan: Dokumente in den Speicher, und ein deklarierter Ablauf — 2026-08-16T08:25:00+0200

**Verhältnis zum geltenden Plan:** unabhängig neben `docs/PLAN_GESAMT_2026-08-13.md`
und `docs/PLAN_DIAGRAMME_2026-08-16.md`. Löst nichts ab.

**Anlass, wörtlich:** *„warum verweist die datenbank nicht darauf und oder warum legen
wir sowas nicht automatisch in die datenbank ab? Es ist ja wissen ‚pur'?!"* — und
zweitens: *„ja deklarieren, insgesamt coding agent besser orchestrieren nach morpheus
art"*.

## Der gemessene Ist-Stand

| | |
|---|---|
| `docs/*.md` in brainlehr | **121** |
| davon im Speicher als Quelle genannt | **18** |
| **nicht auffindbar** | **103** |
| darunter | 38 Pläne, 5 Startprompts, 3 Recherchen, 2 Konsile, 2 Videoauswertungen |

Das ist keine Nachlässigkeit im Einzelfall, sondern eine fehlende Brücke: der Abruf
liest die Datenbank, die Arbeit landet im Dateisystem.

## Linie A — Dokumente bekommen einen Zugang

**Ein Verweisknoten je Dokument, erzeugt statt gepflegt.** Der Knoten trägt Titel,
den ersten Absatz und den Pfad; die Datei bleibt das Langformat. Genau die Bauform der
Landkarten: aus der Quelle abgeleitet, deterministisch, im `pre-push` gegen Abweichung
gesichert.

- *Verworfen: den vollen Text in die Datenbank kopieren.* Zwei Fassungen desselben
  Inhalts laufen auseinander, und der Speicher würde mit Fließtext geflutet, den
  niemand als Wissen sucht. **Preis:** wer den Volltext will, muss die Datei öffnen —
  der Knoten sagt ihm, welche.
- *Verworfen: nur ein Melder, der die Lücke anzeigt.* „Gebaut, meldend, wirkungslos"
  ist die Fehlerklasse dieses Hauses. Ein Hinweis, den man wegklicken kann, schließt
  keine Lücke.
- *Verworfen: ein Modell die Zusammenfassung schreiben lassen.* Kostet bei jeder
  Änderung erneut und erzeugt eine zweite, ungeprüfte Wahrheit. Erste Überschrift und
  erster Absatz stehen im Dokument und sind vom Autor.

**Die offene Frage, die vor dem Bau zu klären ist:** Pläne ändern sich ständig. 38
Planknoten, die bei jeder Fortschreibung neu entstehen, könnten den Abruf verrauschen.
Deshalb wird **zuerst gemessen**, wie sich die Trefferquote des Abrufs mit und ohne
diese Knoten verhält — nicht geschätzt.

## Linie B — den eigenen Ablauf deklarieren

Der Abgleich mit dem Morpheus-Video (Knoten `ad37ff12`) ergab: Ein Quality Gate
existiert, ein **deklarierter Ablaufgraph** nicht. Unsere Abläufe sind implizit —
verteilt über Hausregeln, Haken und Gewohnheit. Deshalb kann keine Karte sie zeigen.

**Was deklariert wird:** der Ablauf, den dieses Haus beim Bauen tatsächlich fährt —
Auftrag → Existenzprobe → Plan → Bauen → Gate (Tests, Wächter) → bei Rot zurück → bei
Grün Prüfung → Commit. Als **Datei**, nicht als Vorsatz.

**Bindende Reihenfolge:** erst A, dann B. Ein deklarierter Ablauf, den der Speicher
nicht kennt, wiederholt genau den Fehler, den A behebt.

## Was bewusst NICHT getan wird

- **Kein Orchestrierungs-Werkzeug bauen**, das Agenten selbsttätig nach Graph startet.
  Erst muss der Ablauf beschrieben und geprüft sein. **Preis:** die Parallelisierung
  der Prüfer (im Video: Faktor 4) bleibt vorerst aus.
- **Keine Zahl aus dem Video übernehmen.** Wird bei uns gemessen oder gar nicht
  behauptet.

## Woran sich Erfolg messen lässt

1. Nach A findet eine Suche nach „Videoauswertung", „Konsil" oder dem Titel eines
   Plans den zugehörigen Knoten — heute: null Treffer.
2. Die Abruf-Trefferquote wird **nicht schlechter** (gemessen, nicht behauptet).
3. Ein neues Dokument ohne Knoten lässt den `pre-push` anschlagen.
