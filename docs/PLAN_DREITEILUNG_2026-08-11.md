# Plan: Antwortlauf dreiteilen, Freigabe in der Projektion, Vermerke nachziehen

Stand 2026-08-11T13:35:00+0200 · Zweig `claude/wie-geht-es-weiter-3f4066`

Beauftragt vom Betreiber mit „1 bis 3" auf drei vorgelegte Punkte. Kein Push —
der braucht laut seiner eigenen Ansage ein ausdrueckliches Wort, „1 bis 3" ist
keines.

## Gemessener Ist-Stand

- Modellsperre aktiv seit `178df5e`; vier Antwortlaeufe damit blockiert:
  `bedeckung.py`, `wissensnutzen.py`, `wissensnutzen_blind.py`,
  `pruefkorpus_v3.py::answer`.
- `tests/` gesamt: 679 gruen, 14 rot, 6 Fehler (die 14/6 vorbestehend, per
  `git stash` gegengeprueft, keiner beruehrt den Modellweg).
- 17 Ergebnisdateien ohne Gegenprobe-Vermerk, 30 ohne Rastervermerk (Startmelder).
- Zweckprojektion: prueft `freigabe` nicht (Knoten
  `/brainlehr/claude-checkpoint-2026-08-11-mittag`). Alle 2036 Knoten stehen
  auf `intern`, es gibt heute also keinen gesperrten Eintrag, der leckt — die
  Luecke ist strukturell, nicht aktuell.

## S1 · Antwortlauf dreiteilen (zuerst, weil er die Kernschleife blockiert)

Nur `wissensnutzen_blind.py`. Drei Schritte statt einem Lauf:

1. `--aufgaben <datei>` — Abruf + Promptbau, KEIN Modellaufruf. Schreibt je
   Zelle `{key, task, condition, prompt, n_runs}`.
2. Hauptfaden beantwortet per Subagent mit dem Betriebsmodell und legt
   `{model, antworten: {key: [text, ...]}}` ab.
3. `--auswerten <antworten>` — `check` je Antwort, `wn.aggregate`, schreibt
   dieselbe Ergebnisdatei wie bisher.

**Alternativen und Ablehnungsgrund:**
- *Sperre fuer diesen Lauf aufheben* — hebt die Entscheidung auf, statt sie
  umzusetzen. Genau die Bequemlichkeit, gegen die die Sperre steht.
- *Haiku-Aufruf ins Skript einbauen* (HTTP gegen die API) — ginge technisch,
  legt aber einen zweiten Modellweg neben den Subagenten und braucht einen
  Schluessel im Skript. Der Hauptfaden hat den Subagenten schon.
- *Alle vier Laeufe zugleich umbauen* — vierfacher Umbau, bevor der Weg
  einmal belegt ist. Erst einen, dann nachziehen.

**Bindende Reihenfolge:** S1 vor allem anderen — jede Messung haengt daran.

## S2 · Freigabe in der Zweckprojektion

Die Projektion filtert `freigabe` nicht. Fix an der Engstelle, nicht je
Aufrufer. Abnahme: Test mit einem auf `gesperrt` gesetzten Knoten, der vor dem
Fix in der Projektion erscheint und danach nicht.

**Abgelehnt:** Filter im Aufrufer — dieselbe Fehlklasse wie L-44a838
(Choke-Point umgangen).

## S3 · Vermerke: Stichtag statt Nacharbeit

17 + 30 fehlende Vermerke stammen aus der Zeit VOR `S1c`. Ein nachtraeglich
gesetzter Vermerk behauptet Wissen, das niemand mehr hat — was damals
abgesucht wurde, steht nirgends. Also: Stichtag im Melder, Altbestand
ausdruecklich als „ohne Vermerk, vor Einfuehrung" ausweisen statt zu erfinden.

**Abgelehnt:** 47 Vermerke nachtragen — waere Erfindung, und ein Raster ohne
echten Umfang ist schlimmer als keines.

## Was bewusst nicht getan wird

Kein Push. Die anderen drei Antwortlaeufe bleiben gesperrt, bis S1 den Weg
belegt hat — Preis: `bedeckung`, `wissensnutzen`, `pruefkorpus_v3` messen bis
dahin nicht.

## Woran sich Erfolg messen laesst

S1: eine Zahl zu „nuetzt eingespieltes Wissen der Antwort", erzeugt mit dem
Betriebsmodell, mit Artefakt unter `runs/`. S2: ein Test, der vor dem Fix rot
ist. S3: der Startmelder schweigt zum Altbestand und schlaegt beim naechsten
neuen Lauf ohne Vermerk trotzdem an.
