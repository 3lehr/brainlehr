# Regeldatei: Orchestrator statt Sammelband

Angelegt 2026-08-13T17:15:00+0200. Aufgabe 102, vom Betreiber dieser Sitzung
zugewiesen (*„das soll die andere sitzung erledigen!"*).

## Die Frage ist nicht, was zu lang ist

Der Anlass war die Betreiberfrage nach Regelhierarchien und Verweisen, wie das
Vorgängersystem begod sie hatte. Die naheliegende Antwort — 459 Zeilen kürzen —
ist die falsche. **Ein Abschnitt mit Wächter kostet dieselben Zeichen wie einer
ohne und wirkt trotzdem.** Der Befund der parallelen Sitzung, hier übernommen:
Was heute tatsächlich griff, waren ausschließlich die **verdrahteten**
Abschnitte — die Planform-Ratsche erzwang die Auftragsform, der Stop-Haken
erzwang die Wissenssicherung. Die unverdrahteten wurden mehrfach verletzt, ohne
dass irgendetwas anschlug.

Die tragende Frage lautet also nicht „was ist zu lang", sondern **„was hat
ohnehin nie gewirkt"**.

## Schritt 1 · Messung, nicht Änderung

Zwei Erhebungen, zwei Kriterien — die Differenz ist die eigentliche Aussage.

| Erhebung | Kriterium | Ergebnis |
|---|---|---|
| 2026-08-12, `runs/regelgriff_2026-08-12.json` | greift bei Verstoß etwas an? | **11 von 19 ohne Mechanismus** |
| 2026-08-13, hier | existiert eine Datei mit passendem Namen? | 8 von 20 ohne |

**Die strengere Zahl gilt.** Das heutige Kriterium zählt `test_caveman_*.py`
als Mechanismus für „Caveman mode" — die Datei prüft Kompression, sie erzwingt
kein knappes Antworten. Die 8 sind eine **Obergrenze der Wirksamkeit**, keine
Verbesserung gegenüber 11.

Ohne erkennbaren Mechanismus, nach beiden Kriterien: Beta-Direktive · WCAG ·
Abwesenheitsmodus · Keine Entwicklerinformation · Kurze Zustimmung · Zweimal ist
die Grenze · Walkthrough-Doktrin · Zwei Ausgangszustände.

## Schritt 2 · Drei Töpfe

### Topf A — gehört an einen Schritt gebunden (Trigger + Slot)

Diese Abschnitte beschreiben ein Verhalten an einer **benennbaren Stelle im
Ablauf**. Dort gehört der Wächter hin, nicht in die Datei.

- **Zwei Ausgangszustände** → Auslöser: Build/Release/Migration. Slot: vor der
  Auslieferung an einen Menschen. Prüfbar: läuft die Suite gegen eine *frisch
  angelegte* und eine *fortgeschriebene* Datenbank? Das ist eine Messung, kein
  Appell — und in brainlehr am 2026-08-08 einmal gemessen (`L-96db3e`).
- **Keine Entwicklerinformation in der Oberfläche** → `ui_guard.py` existiert,
  hat aber **null Treffer** in `~/.claude/settings.json`. Kein neuer Wächter
  nötig, nur ein Haken.
- **Walkthrough-Doktrin** → Auslöser: abgeschlossener Merkmalsblock. Slot: vor
  dem Commit, der ihn abschließt.
- **Kurze Zustimmung ist eine Entscheidung** → hat bereits vier klare
  Bedingungen; eine davon (unumkehrbar, Geld, Aufhebung einer Sperre,
  sitzungsübergreifend) ist maschinell erkennbar.

### Topf B — gehört in ein Werkzeug, nicht in die Regeldatei

Wissen, das beim **Nachschlagen** gebraucht wird, nicht beim Antworten. Es
gehört an den Ort der Verwendung — dann ist es dort auch verfügbar, wenn keine
Sitzung läuft.

- **WCAG 2.2 AA** — 24 Zeilen Kriterienkatalog. Gehört in den Prüfer, der eine
  Oberfläche liest, und in den Wissensspeicher. Im Systemprompt steht er bei
  jeder Antwort, auch bei denen ohne jede Oberfläche.
- **BSI-Compliance** — hat den Verweis-Aufbau bereits richtig: nur Trigger im
  Prompt, Katalog im Agenten. **Das ist die Bauform für alles in diesem Topf.**

### Topf C — gehört gestrichen, und das ist der wichtigste Topf

Ein Abschnitt, der weder greift noch nachschlagbar ist, kostet Kontext und
erzeugt den falschen Eindruck, die Sache sei geregelt.

- **Abwesenheitsmodus** — dreifach vorhanden: Fähigkeit `abwesend`, Abschnitt in
  der Regeldatei, plus Wiederholung im Selbstlauf-Prompt. Die Fähigkeit ist die
  einzige, die beim Aufruf tatsächlich lädt. Die Regeldatei-Fassung streichen,
  ein Verweis genügt.
- **Zweimal ist die Grenze** — 18 Zeilen für einen Satz. Der Rest ist die
  Begründung, und Begründungen gehören laut eigener Auftragsnorm gestrichen.
  Kürzen auf den Satz plus Fundstelle `L-dafc34`.
- **Beta-Direktive** — bleibt, aber der Umfang nicht. Der tragende Teil ist der
  Absatz „Der Bestand ist NIE ein Argument"; die Aufzählung davor folgt daraus.

## Schritt 3 · Aufteilung

Nach begod-Vorbild, aber nur was gemessen trägt:

```
~/.claude/CLAUDE.md          Orchestrator: je Regel EIN Satz + Trigger + Slot + Verweis
~/.claude/rules/*.md         Protokolle: der Text, geladen nur bei Trigger
```

`InstructionsLoaded` erfasst laut Referenz `CLAUDE.md` **und**
`.claude/rules/*.md` — die Aufteilung ist also plattformseitig vorgesehen und
kein Umweg.

**Was NICHT getan wird:** kein Kürzen nach Zeilenzahl. Ein Abschnitt mit Wächter
bleibt in voller Länge, auch ein langer. Der Preis: Die Datei wird nicht so kurz,
wie sie könnte.

**Erfolgsmaß:** Ein nachgestellter Verstoß gegen einen Abschnitt aus Topf A
schlägt an. Vor dem Umbau rot, danach grün — sonst war es Textpflege.
