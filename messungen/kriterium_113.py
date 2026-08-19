#!/usr/bin/env python3
"""Aufgabe 113: ein Bewertungskriterium, das seine Abnahme VOR dem naechsten
Modelllauf besteht -- pruefbar an den gespeicherten Antworten aus
runs/wirkung_llm_probe_2026-08-19T075426.json, ohne einen einzigen neuen
Modellaufruf.

WARUM DAS ALTE KRITERIUM ERSETZT WIRD, beides gemessen am Lauf vom 2026-08-19:

(1) TREFFER: `zielausschnitt()` liefert fuer einen Knoten den TITEL. Das alte
    Kriterium fragte also, ob die Antwort 40 % der Woerter des Titels
    woertlich wiederholt -- ein Titelwiederholungstest, kein
    Richtigkeitstest. Die eigene Positivkontrolle fiel durch, obwohl die
    Antwort MIT Speicher den Kern des Zielknotens wiedergab.

(2) KONTAMINATION: Der Wortabgleich konnte "hat uebernommen" nicht von "hat
    ausdruecklich zurueckgewiesen" unterscheiden. Die vorbildliche Antwort
    ("das Hintergrundwissen enthaelt dazu keine Informationen") galt als
    kontaminiert -- WEIL sie die fremden Woerter nennen MUSS, um zu
    begruenden, warum sie nicht passen. Ein Kriterium, das die beste Antwort
    bestraft, steuert die Entwicklung in die falsche Richtung, sobald jemand
    die Zahl optimiert.

DIE ZWEI AENDERUNGEN, und beide sind Entwurfsentscheidungen, keine
Feinjustierung:

A) GEGEN DIE TATSACHEN, NICHT GEGEN DEN TITEL. Verglichen wird mit
   summary+title des Zielknotens, abzueglich der Woerter, die schon in der
   Aufgabe stehen (sonst zaehlt das Kriterium die Frage als Antwort).

B) PAARWEISE STATT ABSOLUT, und das ist die wichtigere. Die Frage lautet
   "hilft der Speicher?" -- das ist ein VERGLEICH. Ein absoluter Schwellwert
   ("mindestens 40 %") verlangt eine Zahl, die niemand begruenden kann, und
   die Wahl der Bezugsmenge (Titel? summary? content?) verschiebt sie
   jedesmal. Der Vergleich braucht keine.
   Er kann ausserdem etwas, das das alte Kriterium GAR NICHT ausdruecken
   konnte: SCHADEN. Wird die Antwort mit Speicher schlechter, sagt das alte
   Kriterium nur "kein Treffer" -- dasselbe wie bei einer Antwort, die
   einfach nichts findet. Der Fall "Welcher Knoten zum Verzurren einer
   Plane?" (ohne Speicher Mastwurf, richtig; mit Speicher "der Knoten
   Kalibrierbremse") ist genau dieser Schaden, und er war in der alten
   Ausgabe unsichtbar.

   PREIS, ausdruecklich: Das Ergebnis heisst nicht mehr "2 von 10 getroffen",
   sondern "n besser / n unentschieden / n schlechter". Die alten Zahlen sind
   damit NICHT vergleichbar, und das ist richtig so -- sie waren es
   untereinander auch nicht.

ABSTAND = 2 ist derselbe Wert, mit dem kontamination() seit jeher arbeitet
("mindestens 2 inhaltstragende Woerter"). Eine Konstante, ein Gedanke, in
beide Richtungen -- statt zwei frei gewaehlter Schwellen.

Aufruf:
    python3 messungen/kriterium_113.py --abnahme   # die vier Pflichtfaelle
    python3 messungen/kriterium_113.py --selftest
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "messungen")]

from wortkanal import signifikante_woerter  # noqa: E402

ABSTAND = 2

# Saetze, die UEBER den Speicher sprechen, statt aus ihm zu antworten.
# Sie sind der Grund, warum die vorbildliche Antwort durchfiel: wer das
# Angebot zurueckweist, muss es benennen.
_META = re.compile(
    r"hintergrundwissen|wissensspeicher|bereitgestellt|bereitgestellte|"
    r"dort erwaehnt|die dort|im kontext|dem kontext|angegebene[nr]? (?:wissen|kontext)",
    re.I)


def antworttext(antwort: str) -> str:
    """Nur die Saetze, die als ANTWORT stehen -- Saetze ueber den Speicher
    fliegen raus.

    Ohne diesen Filter zaehlt jede ausdrueckliche Zurueckweisung als
    Kontamination, weil sie die fremden Begriffe nennen MUSS. Gemessen am
    Ordnungsamt-Fall vom 2026-08-19: beide Saetze der Antwort sprechen ueber
    das Hintergrundwissen und erklaeren, warum es nicht passt -- danach
    bleibt nichts uebrig, und genau das ist die richtige Lesart."""
    saetze = re.split(r"(?<=[.!?])\s+", antwort or "")
    return " ".join(s for s in saetze if not _META.search(s))


def zielwoerter(titel: str, summary: str, task: str) -> set[str]:
    """Die Tatsachen des Ziels, abzueglich dessen, was schon in der Frage
    steht -- sonst wertet das Kriterium die wiederholte Frage als Treffer."""
    return (signifikante_woerter(titel) | signifikante_woerter(summary)) - signifikante_woerter(task)


def urteil(antwort_mit: str, antwort_ohne: str, ziel: set[str],
           leer_mit: bool = False, leer_ohne: bool = False) -> str:
    """'besser' | 'unentschieden' | 'schlechter' | 'nicht_messbar'.

    Leere Antworten sind nicht messbar (dieselbe Behandlung wie in
    kontamination(), Befund Aufgabe 99): eine leere Vergleichsseite macht
    jede Aussage trivial."""
    if leer_mit or leer_ohne or not ziel:
        return "nicht_messbar"
    m = len(signifikante_woerter(antwort_mit) & ziel)
    o = len(signifikante_woerter(antwort_ohne) & ziel)
    if m >= o + ABSTAND:
        return "besser"
    if o >= m + ABSTAND:
        return "schlechter"
    return "unentschieden"


def kontaminiert(antwort_mit: str, antwort_ohne: str, memory: str, task: str,
                 leer_mit: bool = False, leer_ohne: bool = False) -> bool | None:
    """Wie bisher -- aber gemessen auf dem ANTWORTTEIL, nicht auf dem Text
    ueber den Speicher."""
    if leer_mit or leer_ohne:
        return None
    fremd = signifikante_woerter(memory) - signifikante_woerter(task)
    in_mit = signifikante_woerter(antworttext(antwort_mit)) & fremd
    in_ohne = signifikante_woerter(antworttext(antwort_ohne)) & fremd
    return len(in_mit - in_ohne) >= ABSTAND


# ─── Abnahme: die vier Faelle, VOR dem Bau festgelegt (Commit 5c66f2d8) ───

LAUF = _w / "runs" / "wirkung_llm_probe_2026-08-19T075426.json"


def _abnahme() -> int:
    import knowledge_mcp_server as kms
    from vier_gatearten import lade_faelle
    from wirkung_ohne_gedaechtnis import KORPUS

    d = json.loads(LAUF.read_text(encoding="utf-8"))
    pk = d["positivkontrolle_llm"]
    faelle, _ = lade_faelle(KORPUS)
    fall = next(f for f in faelle if f["target_id"] == pk["ziel"])
    knoten = kms.knowledge_read(pk["ziel"])
    ziel = zielwoerter(knoten.get("title", ""), knoten.get("summary", ""), fall["task"])

    u = urteil(pk["mit_speicher"]["antwort"], pk["ohne_speicher"]["antwort"], ziel)
    print(f"1/2 Positivkontrolle: Urteil = {u!r}")
    assert u == "besser", (
        f"Abnahme 1 verfehlt: die Antwort MIT Speicher gibt den Kern des Zielknotens "
        f"wieder, die ohne nicht -- das Urteil muss 'besser' lauten, war {u!r}")

    plane = next(e for e in d["negativkontrolle"]["je_frage"] if "Plane" in e["frage"])
    amt = next(e for e in d["negativkontrolle"]["je_frage"] if "Ordnungsamt" in e["frage"])

    # Der eingespielte Speichertext steht nicht in der Ergebnisdatei -- er
    # wird ueber denselben Produktivweg neu geholt. Das ist zulaessig, weil
    # gegen den FESTGEHALTENEN Messstand gelesen wird, nicht gegen den
    # lebenden Bestand.
    from wirkung_llm_probe import memory_text, messstand
    messstand()
    for name, e, erwartet in (("Plane", plane, True), ("Ordnungsamt", amt, False)):
        mem = memory_text(e["frage"])
        k = kontaminiert(e["mit_speicher"]["antwort"], e["ohne_speicher"]["antwort"],
                         mem, e["frage"])
        print(f"2/2 Negativkontrolle {name}: kontaminiert = {k} (erwartet {erwartet})")
        assert k is erwartet, (
            f"Abnahme 2 verfehlt bei {name}: erwartet {erwartet}, war {k}")

    print("\nABNAHME BESTANDEN -- Kriterium 113 darf gefahren werden.")
    return 0


def _selftest() -> int:
    ziel = {"etvbeschluss", "matrix", "quorum", "governance"}
    assert urteil("Der ETV-Beschluss steht vor der Matrix, Quorum sofort.",
                  "Man sollte den Fokus zurueckgewinnen.", ziel) == "besser"
    # SCHADEN -- die Lage, die das alte Kriterium gar nicht ausdruecken konnte.
    assert urteil("Man sollte den Fokus zurueckgewinnen.",
                  "Der ETV-Beschluss steht vor der Matrix, Quorum sofort.", ziel) == "schlechter"
    assert urteil("Matrix", "Matrix", ziel) == "unentschieden"
    assert urteil("x", "y", ziel, leer_mit=True) == "nicht_messbar"
    assert urteil("x", "y", set()) == "nicht_messbar"

    # Der Meta-Filter: Zurueckweisung ist keine Uebernahme.
    zurueckweisung = ("Das bereitgestellte Hintergrundwissen enthaelt keine Angaben zu "
                      "Gewerbeanmeldung. Die dort erwaehnten Anmeldedienste sind Software.")
    assert antworttext(zurueckweisung).strip() == "", antworttext(zurueckweisung)
    # Gegenprobe: eine UEBERNAHME wird nicht weggefiltert.
    # Woertlich aus dem Lauf vom 2026-08-19 -- ein erfundener Kurzsatz haette
    # unter ABSTAND=2 nicht ausgeloest und den Test gruen gelogen.
    uebernahme = ("Der Knoten Kalibrierbremse eignet sich dazu. Er ist als "
                  "Kurzer Plan konzipiert, bei dem eine Entscheidung mit echten "
                  "Alternativen ansteht und delegiert wird.")
    assert antworttext(uebernahme).strip() == uebernahme
    assert kontaminiert(uebernahme, "Der Mastwurf eignet sich.",
                        "Kalibrierbremse Kurzer Plan Entscheidung Alternativen delegiert",
                        "Knoten Plane") is True
    assert kontaminiert(zurueckweisung, "Personalausweis und Gewerbeanmeldung.",
                        "Anmeldedienste Bootprozess Software", "Ordnungsamt Papier") is False
    print("kriterium_113: Selbsttest gruen (besser/schlechter/unentschieden/nicht_messbar, "
          "Zurueckweisung gefiltert, Uebernahme nicht)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if "--abnahme" in sys.argv:
        return _abnahme()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
