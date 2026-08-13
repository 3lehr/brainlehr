# brainlehr

Angelegt 2026-08-13T13:05:00+0200. Bis dahin war brainlehr das **einzige** Repo
des Verbunds ohne eigene Beschreibung — hub 143 Zeilen, buckeberg 77, openlehr
42, fahrtenbuch 30, brainlehr keine. Ausgerechnet das System, das über Regeln
und Wissen wacht.

## Was das hier ist

Der Name sagt „Wissensspeicher", und das ist die kleinere Hälfte.

Gemessen liegen hier 2166 Knoten, 833 Lehren, über 6100 Kanten und 10 000
protokollierte Zugriffe. Daneben stehen 16 Melder, ein Prüfkorpus mit
Messläufen, Ratschen, Wächter, ein Ausweiswesen mit Rollen, Regelpakete für
fremde Instanzen und eine Mac-Anwendung.

**Was diese zweite Hälfte tut: Sie prüft, ob das, was wir uns vornehmen,
tatsächlich wirkt.** Der beherrschende Befund des 2026-08-13 — zwölfmal
„gebaut, laufend, meldend, wirkungslos" — stammt nicht von einem Menschen,
sondern von brainlehr über brainlehr. Ein Speicher tut das nicht. Das ist eine
**Aufsicht über die eigene Arbeitsweise**, und der Wissensbestand ist ihr
Gedächtnis, nicht ihr Zweck.

## Wozu

Der Hebel ist nicht bessere Suche, sondern die Fähigkeit zu **belegen**, dass
eine Sorgfaltspflicht erfüllt wurde (Knoten `9f14c5f2`). Für buckeberg und
openlehr ist das der Unterschied zwischen einem Werkzeug und einer Akte.

## Die vier Fragen, die jede Instanz beantwortet

Die Form ist gemeinsam, die Antworten sind es nicht — das ist der Kern für jede
Ausweitung über das Programmieren hinaus:

1. **Wer fragt hier?** — der Ausweis beantwortet es (`kern/ausweis.py`).
2. **Worüber wird hier Wissen geführt?** — Code · Rechtslage · Steuer · Lehre.
3. **Was ist ein Treffer wert?** — **offen.** Ein falscher Rechtssatz kostet
   anders als ein falscher Funktionsname; heute gilt die Schwelle `0,65` für
   beides. Diese Lücke ist der Grund für mehrere offene Aufgaben.
4. **Was darf nach außen?** — die Freigabe (`offen`/`intern`/`gesperrt`).
   Vorgabewert ist `intern`; `offen` ist der bewusste Akt.

## Wie hier gearbeitet wird

Die Hausregeln stehen in `~/.claude/CLAUDE.md` und gelten unverändert. Was
**hier** dazukommt:

- **Datenbankpfade nie fest verdrahten.** Immer über `kern/speicher`. Es gibt
  eine Ratsche dagegen (`tests/test_naht_ratsche.py`), sie schlägt zuverlässig
  an, auch bei mir.
- **Schwellen und Parameter sind gemessen, nicht gesetzt.** Wer eine Zahl
  ändert, entwertet die Messung, die sie begründet — `0,65` stammt aus einer
  Erhebung vom 2026-08-08 über zwei Millionen Paare.
- **Guards gehören als Datenbank-Trigger**, nicht in den Serverprozess. MCP über
  stdio heißt: jeder Klient startet seinen eigenen Prozess, es gibt **keinen
  zentralen Neustart**. Eine Codeänderung erreicht laufende Sitzungen nie.
- **Ein korrigierter Trigger erreicht eine gewachsene Datenbank nicht von
  selbst.** `CREATE TRIGGER IF NOT EXISTS` ergänzt, es ersetzt nicht. Nach jeder
  Änderung die **installierte** Fassung lesen (`select sql from sqlite_master`),
  nicht die Datei (`L-55075a`).
- **Ein Melder ohne Auslöser zählt als keiner.** `melder/ausloeserlos.py` prüft
  das inzwischen selbst — und meldet regelmäßig Melder, die zwei Stunden vorher
  gebaut wurden.

## Wo man anfängt zu lesen

| | |
|---|---|
| Lage und Fallen | `STAND.md` |
| Reihenfolge und Sperren | `docs/PLAN_GESAMT_2026-08-13.md` |
| Was dieser Klient nicht kann | `docs/EIGENER_KLIENT.md` |
| Was das System über sich sagt | `python3 melder/selbstbeschreibung.py` |
| Was fällig wäre | `python3 berichte/vorschlag.py --bericht` |

Die letzten beiden werden **erzeugt, nicht gepflegt** — eine gepflegte
Beschreibung altert, und der alte Agentenindex des Vorgängersystems nennt bis
heute drei verschiedene Zahlen für sich selbst (81 Dateien, 75 Einträge, 77
Zeilen). Genau deshalb steht in dieser Datei so wenig Zählbares: Zahlen gehören
dorthin, wo sie berechnet werden.

## Die Grenze, die hier härter ist als anderswo

Der Bestand trägt **Daten Dritter** — WEG-Rechtsfälle aus buckeberg,
Steuerdaten aus openlehr. Die Freigabe ist deshalb keine Formalie. Der
Vorgabewert `intern` ist Absicht: Nichts entweicht aus Versehen, geöffnet wird
einzeln und begründet.
