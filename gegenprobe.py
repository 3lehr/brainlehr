#!/usr/bin/env python3
"""Zweite Instanz fuer Messergebnisse unter runs/ -- rechnet nach, statt zu nicken.

`hub/scripts/gegenprobe_faellig.py` meldet Ergebnisdateien ohne Vermerk. Ein
Vermerk von Hand zu schreiben ("angesehen, sieht gut aus") waere genau die
Bewegung, gegen die der Melder gebaut wurde: er wuerde die Meldung
abschalten, ohne die Frage zu beantworten.

Was diese zweite Instanz stattdessen tut: aus den Rohzahlen DERSELBEN Datei
das nachrechnen, was sich nachrechnen laesst, und die Selbstauskuenfte der
Datei ernst nehmen. Sie prueft nicht, ob die Messung KLUG war -- das kann
kein Skript. Sie prueft, ob die Datei mit sich selbst uebereinstimmt.

Die vier Fragen, jede aus einem echten Fund entstanden:

1. Hat der Lauf sich selbst abgebrochen? `aborted: true` steht in zwei der
   zwoelf Dateien, in einer mit `grund:
   positivkontrolle_mitten_im_lauf_fehlgeschlagen`. Ein abgebrochener Lauf
   ist kein Ergebnis, sieht als Datei aber genauso aus wie eines.
2. Lag der Bestand still? `bestand_unveraendert: false` in
   ab_vergleich_abruf: waehrend eines A/B-Vergleichs wuchs der Bestand von
   1971 auf 1974. Ein Vergleich, dessen Grundgesamtheit sich mitbewegt,
   misst zwei Dinge gleichzeitig.
3. Sind Zaehler und Nenner vertraeglich? Treffer duerfen den Nenner nicht
   uebersteigen, und kein Nenner darf null sein.
4. Enthaelt ein Vertrauensbereich seinen eigenen Punktschaetzer? Tut er das
   nicht, ist eine der beiden Zahlen aus einem anderen Lauf.

Aufruf:
    python3 gegenprobe.py                    # alle offenen Faelle pruefen, nichts schreiben
    python3 gegenprobe.py --vermerken        # Ergebnis als Beistelldatei ablegen
    python3 gegenprobe.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CET = timezone(timedelta(hours=2))
RUNS = Path(__file__).resolve().parent / "runs"


def _jetzt() -> str:
    return datetime.now(CET).strftime("%Y-%m-%dT%H:%M:%S%z")


def _paare(knoten, pfad="") -> list[tuple[str, int, int]]:
    """Alle [treffer, n]-Paare im Baum, mit ihrem Pfad. Die Messskripte legen
    Anteile durchgaengig so ab; ein Paar ist damit ueberall nachrechenbar,
    ohne dass diese Datei die Struktur jedes einzelnen Laufs kennen muss."""
    fund = []
    if isinstance(knoten, dict):
        for k, v in knoten.items():
            fund += _paare(v, f"{pfad}.{k}" if pfad else k)
    elif isinstance(knoten, list):
        if (len(knoten) == 2 and all(isinstance(x, int) for x in knoten)):
            fund.append((pfad, knoten[0], knoten[1]))
        else:
            for i, v in enumerate(knoten):
                fund += _paare(v, f"{pfad}[{i}]")
    return fund


def _ci_faelle(knoten, pfad="") -> list[tuple[str, float, list]]:
    """(pfad, punktschaetzer, ci95) -- nur wo beides nebeneinander liegt."""
    fund = []
    if isinstance(knoten, dict):
        if "ci95" in knoten and isinstance(knoten["ci95"], list) and len(knoten["ci95"]) == 2:
            treffer, n = knoten.get("treffer"), knoten.get("n")
            if isinstance(treffer, int) and isinstance(n, int) and n:
                fund.append((pfad, treffer / n, knoten["ci95"]))
        for k, v in knoten.items():
            fund += _ci_faelle(v, f"{pfad}.{k}" if pfad else k)
    elif isinstance(knoten, list):
        for i, v in enumerate(knoten):
            fund += _ci_faelle(v, f"{pfad}[{i}]")
    return fund


def pruefe(daten: dict) -> dict:
    """Befunde einer Datei. Leere Liste = nichts widerspricht sich; das ist
    KEINE Aussage darueber, ob die Messung taugte."""
    befunde = []

    if daten.get("aborted") is True:
        grund = daten.get("grund", "kein Grund vermerkt")
        befunde.append(f"Lauf hat sich selbst abgebrochen ({grund}) -- kein verwertbares Ergebnis")

    if daten.get("bestand_unveraendert") is False:
        v, n = daten.get("bestand_vorher"), daten.get("bestand_nachher")
        befunde.append(f"Bestand aenderte sich waehrend des Laufs ({v} -> {n}) -- "
                       "Vergleich misst zwei Dinge gleichzeitig")

    for pfad, treffer, n in _paare(daten):
        if n == 0:
            befunde.append(f"{pfad}: Nenner 0 -- Anteil nicht definiert")
        elif treffer > n:
            befunde.append(f"{pfad}: {treffer} von {n} -- Zaehler groesser als Nenner")
        elif treffer < 0 or n < 0:
            befunde.append(f"{pfad}: negative Zahl ({treffer}/{n})")

    for pfad, punkt, ci in _ci_faelle(daten):
        if not (ci[0] <= punkt <= ci[1]):
            befunde.append(f"{pfad}: Punktschaetzer {punkt:.3f} liegt ausserhalb "
                           f"des eigenen Vertrauensbereichs [{ci[0]:.3f}, {ci[1]:.3f}]")

    return {"befunde": befunde, "bestanden": not befunde}


def sidecar(datei: Path) -> Path:
    return datei.with_suffix(datei.suffix + ".gegenprobe.json")


def offene(runs: Path) -> list[Path]:
    return [f for f in sorted(runs.glob("*.json"))
            if not f.name.endswith(".gegenprobe.json") and not sidecar(f).exists()]


def lauf(runs: Path, schreiben: bool) -> int:
    beanstandet = 0
    for datei in offene(runs):
        try:
            daten = json.loads(datei.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  {datei.name}: NICHT LESBAR ({e})")
            beanstandet += 1
            continue
        e = pruefe(daten) if isinstance(daten, dict) else {"befunde": [], "bestanden": True}
        zeichen = "ok " if e["bestanden"] else "!! "
        print(f"  {zeichen}{datei.name}")
        for b in e["befunde"]:
            print(f"       {b}")
        if not e["bestanden"]:
            beanstandet += 1
        if schreiben:
            sidecar(datei).write_text(json.dumps({
                "geprueft_am": _jetzt(),
                "geprueft_von": "gegenprobe.py (zweite Instanz, rechnerisch)",
                "bestanden": e["bestanden"],
                "befunde": e["befunde"],
                "umfang": ("Rechnerische Selbstkonsistenz: Abbruchkennzeichen, Stillstand des "
                           "Bestands, Zaehler gegen Nenner, Punktschaetzer im eigenen "
                           "Vertrauensbereich. NICHT geprueft: ob die Messung die richtige "
                           "Frage stellte, und ob das Modell dasselbe noch einmal liefern wuerde."),
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return beanstandet


def _selftest() -> None:
    assert pruefe({"a": {"x": [3, 5]}})["bestanden"]
    assert not pruefe({"a": {"x": [7, 5]}})["bestanden"], "Zaehler > Nenner muss auffallen"
    assert not pruefe({"a": {"x": [1, 0]}})["bestanden"], "Nenner 0 muss auffallen"
    assert not pruefe({"aborted": True, "grund": "x"})["bestanden"]
    assert pruefe({"aborted": False})["bestanden"], "sauber beendet ist kein Befund"
    assert not pruefe({"bestand_unveraendert": False, "bestand_vorher": 1, "bestand_nachher": 2})["bestanden"]
    assert pruefe({"bestand_unveraendert": True})["bestanden"]

    drin = {"z": {"treffer": 34, "n": 36, "ci95": [0.81, 0.98]}}
    draussen = {"z": {"treffer": 3, "n": 36, "ci95": [0.81, 0.98]}}
    assert pruefe(drin)["bestanden"]
    assert not pruefe(draussen)["bestanden"], "Punktschaetzer ausserhalb des CI muss auffallen"

    # Negativfall: eine Liste aus zwei Zahlen, die KEIN Anteil ist, darf nicht
    # als Zaehler/Nenner gelesen werden, wenn sie plausibel bleibt.
    assert pruefe({"num_ctx_values": [4096, 8192]})["bestanden"]
    print("selftest ok (10 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vermerken", action="store_true", help="Ergebnis als Beistelldatei ablegen")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--runs", type=Path, default=RUNS)
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    offen = offene(a.runs)
    print(f"{len(offen)} Ergebnisdatei(en) ohne Vermerk:")
    n = lauf(a.runs, a.vermerken)
    print(f"\n{len(offen) - n} ohne Widerspruch, {n} beanstandet."
          + (" Vermerke geschrieben." if a.vermerken else " Nichts geschrieben (--vermerken)."))
    sys.exit(0)


if __name__ == "__main__":
    main()
