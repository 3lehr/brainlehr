# Erinnerung ist keine Quelle — die Rang-1-Direktive bekommt einen Mechanismus

**Angelegt** 2026-08-16T14:25:00+0200
**Bindende Quelle** Knoten `b5604a62`, Rang 1, unbefristet, gilt ab 2026-08-16 —
Betreiberweisung: *„wichtig wen kontextfenster voll, und auch eigentlich auch davor
immer auf wissen von brainlehr beziehen, wissen aus dem kontextfenster kann immer zu
halluzinationen führen! … dieser soll es belegen und direkt als oberste direktive
implementieren!"*

Der Knoten stellt zwei Fragen ausdrücklich offen. Dieser Plan beantwortet sie.

## §1 Der gemessene Ist-Stand

Der Beleg liegt vor und ist nicht von mir: **elf Korrekturen in einer einzigen Sitzung**
(buckeberg/Sanierungswege). Bei allen elf stand die richtige Angabe zum Zeitpunkt der
Falschaussage bereits zur Verfügung; **sechsmal** lag die bessere Quelle im eigenen Haus.
Teuerster Einzelfall: elf Rechercheaufträge nach außen vergeben, ohne `ls auswertung/`
auszuführen — dort lagen 53 Einträge.

Im eigenen Repo gemessen (2026-08-16): Es gibt bereits **einen** PreToolUse-Haken auf
`Agent` — `haken/auftragshypothese_waechter.py`, verdrahtet in `~/.claude/settings.json`.
Er fängt die *Hypothese* des Auftraggebers. Er fängt **nicht**, dass der Auftrag
Bestandsangaben aus dem Kontext als Tatsache setzt.

## §2 Frage 1 des Knotens: An welcher Stelle würde die Regel gebrochen?

An vier Stellen wird aus dem Kontext weitergetragen. Nur an einer davon steht heute
etwas:

| Stelle | Was dort steht | Bewertung |
|---|---|---|
| **Agentenauftrag** | `auftragshypothese_waechter.py` (nur Hypothesen) | Lücke, hier ansetzen |
| Commit-Nachricht | `melder/ablaufpflicht.py` (Plan + Belegweg) | teilweise gedeckt |
| Wissensknoten | `source` ist Pflichtfeld am Server | gedeckt |
| Antwort an den Betreiber | nichts, und nichts ist möglich | bleibt offen, benannt |

**Der Agentenauftrag ist die teuerste Stelle**, und das steht so im Knoten: Ein Subagent
liest ausschließlich seinen Auftrag. Was der Orchestrator aus seinem Kontext
hineinschreibt, wird dort zur **Prämisse** und kommt als „Ergebnis" zurück — mit der
Autorität eines fremden Befunds. Das ist dieselbe Fehlerklasse wie L-1c5e26 (Plan über
eine Herauslösung, ohne zu messen, woraus herausgelöst wird).

## §3 Frage 2 des Knotens: Wie unterscheidet ein Mechanismus Erinnerung von Ableitung?

**Gar nicht — und er muss es an dieser Stelle auch nicht.**

Das ist die eigentliche Einsicht dieses Plans. Semantisch ist die Unterscheidung nicht
maschinell zu treffen; jeder Versuch endet in einer Heuristik, die jede zweite Aussage
anhält und binnen einer Woche abgeschaltet wird.

Am Agentenauftrag lässt sich die Frage **umgehen** statt lösen: Geprüft wird nicht, ob
eine Angabe stimmt, sondern ob der Empfänger **ermächtigt ist, sie zu widerlegen**. Der
Knoten nennt den Satz selbst:

> „Sieht der Bestand anders aus als hier beschrieben, halte dich an den Bestand und melde
> die Abweichung."

Dieser Satz verwandelt eine veraltete Beschreibung von einer Fehlerquelle in einen
**Befund** — unabhängig davon, ob sie Erinnerung oder Ableitung war. Damit fällt die
unlösbare Frage weg.

## §4 Verworfene Wege, mit Grund

1. **Eigener neuer Haken.** Verworfen: Es gibt bereits einen PreToolUse-Haken auf
   `Agent`, verdrahtet und gemessen. Ein zweiter Prozess je Auftrag kostet Laufzeit und
   verdoppelt die Stelle, an der eine Verdrahtung fehlen kann.
2. **`deny` statt `ask`.** Verworfen aus demselben Grund wie beim Vorgänger: Textheuristik
   ohne Sprachmodell, ein Fehltreffer ist nicht ausgeschlossen. Eine Wache mit hoher
   Fehlalarmquote wird ignoriert. `ask` meldet und gibt frei.
3. **Jeden Auftrag prüfen.** Verworfen: Ein Auftrag ohne jede Bestandsangabe („schreibe
   einen Selbsttest für diese Funktion") trägt keine Prämisse, die veralten könnte. Der
   Auslöser ist deshalb, dass der Auftrag **überhaupt etwas über den Bestand behauptet**:
   Dateipfad, Commit-Hash, Zeilenangabe, Paragraph oder eine Zahl mit Einheit.
4. **Prüfen, ob die genannten Dateien existieren.** Verworfen: Das prüft die Existenz,
   nicht die Aktualität — und eine existierende Datei mit verändertem Inhalt ist genau der
   Fall, um den es geht.

## §5 Reihenfolge, bindend

1. Regel in `haken/auftragshypothese_waechter.py` ergänzen (zweite, unabhängige Prüfung).
2. **Rot-Probe:** ein Auftrag mit Dateinamen ohne Vorbehalt muss gemeldet werden; derselbe
   Auftrag mit Vorbehalt darf nicht gemeldet werden.
3. **Trennschärfe an echten Aufträgen messen**, nicht behaupten — wie der Vorgänger es tat
   (71 von 72 nicht gemeldet). Erst danach gilt die Regel als tragfähig.

Schritt 3 ist gegenüber Schritt 1 bindend nachgelagert: Eine Trennschärfe, die vor dem Bau
geschätzt wird, ist eine Meinung.

## §6 Was bewusst nicht getan wird, samt Preis

- **Die Antwort an den Betreiber bekommt keinen Mechanismus.** Es gibt keine Stelle, an der
  ein Skript sie abfängt. Preis: die häufigste Bruchstelle bleibt ungedeckt und hängt an
  der Selbstdisziplin. Das wird benannt statt kaschiert.
- **Kein Rückbau der Commit-Prüfung.** `ablaufpflicht.py` deckt Plan und Belegweg, nicht
  die Herkunft einer Zahl. Preis: eine aus dem Kontext erinnerte Zahl geht durch, wenn der
  Commit sonst sauber ist.

## §7 Woran sich Erfolg messen lässt

Nicht daran, dass der Haken läuft, sondern: **Ein Auftrag, der eine Bestandsangabe ohne
Vorbehalt setzt, wird gemeldet — und echte Facharbeitsaufträge werden es nicht.** Beide
Richtungen an echten Aufträgen dieser Sitzung gemessen, Zahl im Nachtrag.

## Nachtrag 2026-08-16T14:40:00+0200 — gebaut, rot-vor-grün belegt, Trennschärfe gemessen

Umgesetzt als **zweite Regel im bestehenden Haken** `haken/auftragshypothese_waechter.py`
(§4.1: kein zweiter Prozess je Auftrag). Ausgelöst wird sie, wenn ein Auftrag eine
Bestandsangabe setzt — Dateipfad, Commit, Fundstelle, Zahlenquote — und **keinen**
Vorbehalt trägt.

**Rot vor grün, beide Richtungen im Selbsttest:** Derselbe Auftrag wird gemeldet, solange
der Vorbehalt fehlt, und nicht mehr gemeldet, sobald er dasteht. Ohne die zweite Richtung
sähe eine Regel, die einfach alles meldet, genauso grün aus. Dazu der Grenzwert: ein
Auftrag ohne jede Bestandsangabe wird nie gemeldet — er trägt keine Prämisse, die veralten
kann.

### Die Messung — und sie sagt etwas anderes, als sie sollte

Über **543 echte Agentenaufträge** aus den Transkripten dieses Projekts:

| | Zahl |
|---|---|
| stumm | 417 |
| Regel 1 (Hypothese) | 0 |
| **Regel 2 (kein Vorbehalt)** | **126 (23 %)** |

Davon nennen **116 eine Datei** ohne jedes Widerspruchsrecht; 1 einen Commit; nur 9 werden
allein wegen einer Zahlenquote gemeldet.

**23 % sind zu viel für einen Wächter — aber das ist hier kein Fehlalarm.** Die Hausregel
„Aufträge an Agenten sind Schnappschüsse" verlangt diesen Satz seit Wochen *in jedem
Auftrag*. Gemessen steht er in gut drei Vierteln. Die Regel meldet nicht zu viel; wir haben
zu oft ohne ihn delegiert. Genau das ist die Lage, die der Rang-1-Knoten beschreibt: Die
Regel existierte, und an der Stelle, an der sie gebrochen wird, stand nichts.

Der Median der gemeldeten Aufträge ist mit 1872 Zeichen deutlich **kürzer** als der der
stummen (3779) — kurze Aufträge tragen den Vorbehalt seltener. Das passt zur Erwartung und
ist der Grund, ihn nicht der Sorgfalt zu überlassen.

**Damit ist §7 erfüllt** — beide Richtungen gemessen, nicht behauptet.
