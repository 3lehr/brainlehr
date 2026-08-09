# Hilft eingespieltes Wissen der Antwort — was heute ehrlich messbar ist

Datum: 2026-08-09T00:00:00+0200 (Auswertungszeitpunkt dieses Laufs)
Messauftrag, keine Datei geändert außer dieser. Gelesen, nicht angefasst: `wissensnutzen.py`,
`wissensnutzen_blind.py`, `abrufguete.py`, `haken/knowledge_recall_hook.py`,
`runs/wissensnutzen_blind.json`, `runs/wissensnutzen_blind.jsonl`,
`runs/negativkontrolle_standard_2026-08-09.md`, Knowledge-Knoten `34ef6d8e`.

## 1. Welche Messung ist heute ehrlich möglich

Zwei Werkzeuge im Wurzelverzeichnis, Zweck im Namen:

- `wissensnutzen.py` — holt den Wissensblock per `lesson_query(query=...)`, wobei die Suchanfrage
  **von Hand aus der bekannten Lösung gebaut** ist (z. B. `"AlertDialog showDialog ActionScreen
  Vollbild fahrtenbuch_legacy"` für Aufgabe A — Docstring Zeile 121). Der eingespielte Text
  enthält laut Knowledge-Knoten `34ef6d8e` den Lösungswortlaut selbst.
- `wissensnutzen_blind.py` — holt denselben Block über den echten Produktionspfad:
  `knowledge_recall_hook.keywords()` zerlegt den unveränderten Aufgabentext, `knowledge_recall_hook.query()`
  sucht damit (Docstring Zeile 3–9). Keine Handauswahl.

**Der Selbstbezug des früheren Laufs** (Knoten `34ef6d8e`, Lauf vom 2026-08-07,
`schreibpruefstand/runs/wissensnutzen-2026-08-07.json`): Die MIT-Bedingung wurde nicht aus einer
Suche erzeugt, sondern aus einer Anfrage, die bereits wusste, welche Lehre die richtige ist — der
Prompt enthielt daher wörtlich die Lösung ("NICHT AlertDialog+showDialog verwenden ... Stattdessen
ActionScreen(expandPrimaryAction: true)"). Gemessen wurde damit "hilft es, die richtige Antwort in
den Prompt zu schreiben" — nicht "findet der Speicher bei einer Aufgabe, die er nicht kennt, das
Passende". Zitat aus dem Knoten: *"Der Aufbau umgeht sie, weil die Treffer per lesson_query gezielt
zur Aufgabe geholt wurden statt aus einer echten Suchanfrage zu stammen."*

**Lässt sich das mit dem vorhandenen Werkzeug vermeiden? Ja** — `wissensnutzen_blind.py` ist genau
dafür gebaut und existiert bereits (commits `797257f`/`dc66380`, 2026-08-07; Importpfad-Fix
`719787a`, 2026-08-08, keine Messlogik-Änderung laut `git show 719787a -- wissensnutzen_blind.py`).
Beleg, dass die Vermeidung wirkt und nicht nur behauptet ist: in Aufgabe B fand die echte Suche die
Ziel-Lehre `L-68ff10` **nicht** (`trefferguete: false`, Datei `runs/wissensnutzen_blind.json`,
Feld `retrieval.B`) — ein echter Fehlschlag, den der handkuratierte Aufbau von `wissensnutzen.py`
per Konstruktion gar nicht erzeugen konnte, weil er die richtige Lehre immer traf. Das ist der
Unterschied, der zählt: Trefferguete kann jetzt scheitern.

**Einschränkung, die bleibt:** Der eingespielte Block enthält bei Treffer weiterhin
Lehrentext/-prävention im Klartext (Feld `description`/`prevention` derselben Lehre) — das ist
unverändert gegenüber dem alten Aufbau. Vermieden ist nur, DASS der Treffer garantiert war, nicht,
WAS im Treffer steht.

**Ergebnis Punkt 1:** Die heute ehrlich mögliche Messung ist **keine neue Ausführung**, sondern die
Auswertung des bereits vorhandenen, nicht-tautologischen Laufs `runs/wissensnutzen_blind.json`
(2026-08-07, 03:06 Uhr laut Dateidatum) — dessen Messlogik seither unverändert ist.

## 2. Auflage aus der Negativkontroll-Recherche umgesetzt

Quelle: `runs/negativkontrolle_standard_2026-08-09.md`. Kernvorschlag dort: keine geliehene
Prozentzahl übernehmen, sondern vor der Messung eine Vorlaufmessung mit eindeutig unähnlichen
Negativpaaren fahren und die Ausschlussgrenze aus der eigenen Fehlerquote ableiten (Zeilen 147–162).
Der Vorschlag setzt einen **LLM-Richter** voraus, der beurteilt, ob ein Treffer geholfen hätte.

**Geprüft, nicht angenommen:** Weder `wissensnutzen.py`/`wissensnutzen_blind.py` noch `abrufguete.py`
enthalten einen solchen Richter — `grep -n "richter\|Richter\|judge" *.py` liefert dazu nichts
Einschlägiges. Jede Entscheidung ist deterministisch: Aufgabenerfolg über feste Substring-Checks
(`TASKS[...]["check"]`, z. B. `"ActionScreen" in text and "showDialog" not in text`), Trefferqualität
über exakten ID-Vergleich (`target in lesson_ids`). Damit trifft die Voraussetzung des
Recherche-Vorschlags (ein Richter mit einer Fehlerquote, die kalibriert werden muss) auf dieses
Repo **nicht direkt zu**.

Sinngemäß übertragen auf das, was hier tatsächlich als Klassifikator arbeitet — die 15
`check()`-Funktionen aus `wissensnutzen.py` — wurde die Vorlaufmessung trotzdem gefahren, mit
eindeutig unähnlichen Negativpaaren aus dem Bestand selbst (Domänen: Swift-Build, Plattform-Channel-
Test, Schwesterdatei-Grep, QR-Scanner, Codesign-Sandbox, SQLite-WAL, Session-Gate, fake_async,
Port-Konflikt, User-ID-Normalisierung, Poll-Loop, Play-Billing, iOS-Crash-Diagnose — 15 Aufgaben aus
9 verschiedenen Projekten/Sprachen, siehe `wissensnutzen.py` Zeilen 117–245):

- Aufbau: für jede der 15 Aufgaben X wurde `TASKS[X]["check"]` auf die bekannte korrekte Antwort
  jeder der 14 anderen Aufgaben Y angewendet (Antworttexte 1:1 aus den `_selftest()`-Assertions in
  `wissensnutzen.py`, Zeilen 378–403 — dieselben Referenzstrings, mit denen das Werkzeug sich selbst
  prüft).
- **210 Negativpaare** (15 × 14), **0 Falsch-Positive**, Fehlerquote **0/210 = 0,00 %**.
- Kein Modellaufruf, Laufzeit < 1 Sekunde.

**Grenze aus der eigenen Fehlerquote statt einer geliehenen Zahl:** 0,00 % (0/210) — nicht die
Recherche-Faustregel von ~5 %. Das ist kein Widerspruch, sondern eine andere Klasse Prüfobjekt:
ein exakter String-/ID-Vergleich hat auf eindeutig unähnlichen Texten keine Fehlerquote im
statistischen Sinn (kein Rauschen, kein Toleranzband nötig) — die Vorlaufmessung bestätigt das
empirisch, ersetzt aber keine Kalibrierung, die es hier nicht gibt.

**Was damit unbeantwortet bleibt:** Ob ein künftiger LLM-Richter (falls je gebaut) dieselbe Güte
hätte, sagt diese Prüfung nichts — sie prüft die vorhandenen deterministischen Checks, nicht ein
hypothetisches Werkzeug.

## 3. Volle Messung heute durchführen?

Batterie für einen vollständigen `wissensnutzen_blind.py`-Lauf: 3 Aufgaben (A, B, C) × 2 Modelle
(`gemma4:12b`, `gemma4:e4b`) × 2 Bedingungen (OHNE/MIT) × 3 Wiederholungen (`N_RUNS`) = **36
Ollama-Aufrufe**.

Belegte Laufzeit für exakt diese Batterie: Feld `runtime_seconds_total` in
`runs/wissensnutzen_blind.json` = **2854,8 Sekunden = 47,6 Minuten** (Summe der Einzelaufruf-Zeiten
`call_seconds` über alle 36 Antworten ergibt denselben Wert: 2854,7 s — stimmt überein).

47,6 Minuten > 10-Minuten-Grenze aus dem Auftrag → **nicht neu ausgeführt.**

Was stattdessen innerhalb des Zeitbudgets lief, alles belegt:

- `python3 wissensnutzen.py --selftest` → grün ("Bewertungslogik aller 15 Aufgaben + Aggregation").
- `python3 wissensnutzen_blind.py --selftest` → grün ("Blockformat + Trefferguete-Logik +
  Aufgabe-C-Check").
- Negativkontroll-Kreuztest (Punkt 2), 210 Paare, < 1 s.
- Ein einzelner Positivkontroll-Ollama-Aufruf (Punkt 4 unten), 13,1 s.

**Was für eine echte Neuausführung nötig wäre:** ~48 Minuten reine Ollama-Zeit auf diesem Rechner
für einen einzelnen Durchlauf der bestehenden Batterie — ein eigenes Zeitfenster, nicht innerhalb
dieses Messauftrags. Eine zweite Wiederholung des GESAMTlaufs (um Streuung über Läufe hinweg zu
sehen, nicht nur über die 3 `N_RUNS` je Zelle) bräuchte entsprechend ein weiteres ~48-Minuten-Fenster.

## 4. Positivkontrolle

Ein Fall, den der Aufbau sicher finden muss: Aufgabe C (`wissensnutzen_blind.py`, domänenfremd,
"Nenne den kubectl-Befehl, um alle Pods im Namespace default aufzulisten") — Allgemeinwissen, das
kein Speicherzugriff braucht.

Live-Aufruf, ein Modell, eine Wiederholung (Modell `gemma4:12b`, Bedingung OHNE, direkter Aufruf von
`schreiblauf._call_with_retry`, derselbe Pfad, den `wissensnutzen_blind.run_cell` nutzt):

```
Antwort:  kubectl get pods -n default
check():  True
Zeit:     13,1 s, 0 Retries, kein Fehler
```

**Aufbau findet den sicher lösbaren Fall.** Fortsetzung (Interpretation des bestehenden Laufs,
Punkt 1) ist damit zulässig — ein Aufbau, der schon den trivialen Fall verfehlt, hätte gar nichts
gemessen.

## Zahlen aus dem bestehenden ehrlichen Lauf, mit Nenner

Quelle für alle folgenden Werte: `runs/wissensnutzen_blind.json`, `cells`-Feld, je Zelle 3 Läufe
(`n=3`, `N_RUNS`).

| Aufgabe | Modell | OHNE (n=3) | MIT (n=3) | Trefferguete (echte Suche) |
|---|---|---|---|---|
| A (Dialog-Falle) | gemma4:12b | 0/3 | 1/3 | ja (Ziel `L-c0e910` gefunden) |
| A (Dialog-Falle) | gemma4:e4b | 0/3 | 0/3 | ja (Ziel `L-c0e910` gefunden) |
| B (stummer Testlauf) | gemma4:12b | 0/3 | 0/3 | **nein** (Ziel `L-68ff10` verfehlt, stattdessen `L-c0e910` geliefert) |
| B (stummer Testlauf) | gemma4:e4b | 0/3 | 0/3 | **nein** (dito) |
| C (kubectl, Gegenprobe) | gemma4:12b | 3/3 | 3/3 | entfällt (kein Ziel definiert) |
| C (kubectl, Gegenprobe) | gemma4:e4b | 3/3 | 3/3 | entfällt (kein Ziel definiert) |

**Lesart, ohne Ersatzzahl zu erfinden:** Bei Aufgabe A hilft der echte Treffer beim größeren Modell
teilweise (0/3 → 1/3), beim kleineren nicht messbar (0/3 → 0/3, n=3 zu klein für eine Aussage über
1 von 3). Bei Aufgabe B verfehlt die echte Suche das Ziel bei beiden Modellen — dort ist der
MIT-Arm gar keine Prüfung von "hilft Wissen", sondern von "hilft das falsche Wissen, das die Suche
tatsächlich brachte" (beide 0/3, unverändert). Aufgabe C zeigt, dass Modelle domänenfremdes
Allgemeinwissen unabhängig vom Speicher lösen (3/3 in allen vier Zellen) — das ist die Gegenprobe,
kein Wissensnutzen-Befund.

## Wo der Aufbau die eigentliche Frage nicht beantworten kann

- **n=1 Gesamtlauf.** Die Tabelle stammt aus genau einer Ausführung der Batterie (2026-08-07). Ob
  0/3 vs. 1/3 bei Aufgabe A ein stabiler Unterschied oder Rauschen zwischen zwei Gesamtläufen ist,
  lässt sich mit einem Lauf nicht sagen — dafür bräuchte es die zweite ~48-Minuten-Ausführung aus
  Punkt 3, die heute nicht gefahren wurde.
- **Unkontrollierte Zufallsquelle im Abrufweg.** `wissensnutzen_blind.blind_retrieve()` ruft
  `knowledge_recall_hook.query()` ohne festen `rand`-Parameter auf — `EXPLORE_RATE=0,15`
  (`haken/knowledge_recall_hook.py` Zeile 251) kann den schwächsten Regeltreffer durch einen
  Erkundungskandidaten ersetzen. `abrufguete.py` schaltet genau das bewusst ab
  (`rand=lambda: 1.0` injiziert, Zeile 8–10 dort), `wissensnutzen_blind.py` nicht. Ob das die
  Trefferguete von A/B in diesem einen Lauf beeinflusst hat, lässt sich aus einem einzigen Lauf
  nicht von echtem Signal unterscheiden — offene Frage, keine Ersatzzahl.
- **Nur 2 Aufgaben mit Ziel-Lehre (A, B).** Zu wenig, um "hilft Wissen generell" zu beantworten,
  nur "hilft Wissen bei diesen zwei konkreten Fallen" — das ist der gemessene Anspruch von
  `wissensnutzen_blind.py` selbst (Docstring nennt nur A/B mit Ziel, C als Gegenprobe ohne Ziel).
- **Ob MIT-Wissen-Antworten qualitativ besser sind, nicht nur binär bestehen**, ist mit diesem
  Aufbau absichtlich nicht messbar — die Checks sind bewusst binär/deterministisch, kein
  Modellurteil (`wissensnutzen.py` Zeilen 40–41: *"Jede andere Bewertung (Teilpunkte,
  Wortlaut-Aehnlichkeit) waere ein Modellurteil durch die Hintertuer"*). Das ist eine bewusste
  Grenze des Werkzeugs, keine Lücke dieses Messauftrags.
