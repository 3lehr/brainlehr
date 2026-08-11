#!/usr/bin/env python3
"""Ein Bestwert aus vielen Versuchen ist keine Messung — und das prueft jetzt Code.

ANLASS, 2026-08-11: An einem Tag mussten drei eigene Messungen zurueckgenommen
werden. Die dritte war die lehrreichste: vier Suchbauformen und sechs Gewichte
wurden an denselben 35 Faellen durchprobiert und der beste Wert berichtet. Auf
einer Haltemenge fiel der Sieger von 5/22 auf 2/13 zurueck, waehrend der
Ausgangsstand dort 4/13 erreichte -- der Vorsprung war Auswahl, nicht Guete.

Der Handel hat dafuer einen Namen und ein Gegenmittel: Backtest-Overfitting,
korrigiert durch die Deflated Sharpe Ratio (Bailey/Lopez de Prado 2014, SSRN
2460551). Sie rechnet aus, wie gut der beste von N Versuchen allein durch
Zufall aussehen musste. Sie braucht weder Geld noch grosse Fallzahl.

WARUM DAS HIER CODE IST UND KEINE REGEL IM TEXT: Weil an genau diesem Tag
belegt wurde, dass eine Regel im Klartext das Verhalten nicht aendert
(L-a69129: dreimal verletzt, einmal direkt nach woertlicher Ermahnung), und
weil die Sortierregel diese Lehre selbst in den Codepfad einsortiert -- Schaden
hoch, wiederholt, als Bedingung schreibbar. Das ist die erste Lehre, die diesen
Weg vollstaendig geht: Vorfall -> Lehre -> Sortierung -> Bedingung.

DREI REGELN, jede an einer Beobachtung dieses Tages:

  1. VERSUCHSZAHL. Eine Ergebnisdatei, die mehrere Bauformen oder Parameter
     vergleicht, nennt, wie viele probiert wurden. Ohne diese Zahl ist ein
     Bestwert nicht einzuordnen.
  2. HALTEMENGE. Wurde mehr als eine Bauform verglichen, gehoert der Sieger an
     einem Satz bestaetigt, der beim Tunen nicht dabei war.
  3. TRENNVERFAHREN. Steht eine Haltemenge in der Datei, steht auch dabei, WIE
     getrennt wurde. Eine Trennung, die der Messende frei waehlt, ist keine.

WAS DIESE PRUEFUNG NICHT KANN: Sie liest Felder, nicht Absichten. Wer
`versuche: 1` schreibt und in Wahrheit zwanzig probiert hat, kommt durch. Sie
verhindert das Vergessen, nicht die Taeuschung -- und das Vergessen war der
Fehler dieses Tages.

Aufruf:
    python3 messregeln.py --pruefen        # alle Ergebnisdateien unter runs/
    python3 messregeln.py --melder         # nur sprechen, wenn etwas fehlt
    python3 messregeln.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import ort  # noqa: E402

RUNS = ort.WURZEL / "runs"

# Woran eine Ergebnisdatei als VERGLEICH erkannt wird: sie fuehrt mehrere
# benannte Bauformen oder eine Parameterreihe. Beides sind Schluessel, die nur
# entstehen, wenn jemand mehr als eine Moeglichkeit durchprobiert hat.
_VERGLEICHSSCHLUESSEL = ("varianten", "reihe", "bauformen", "gewichte",
                         "tuning_ergebnisse")
# 'tuning_ergebnisse' kam nachtraeglich dazu, und zwar aus einem Befund gegen
# die eigene Pruefung: runs/haltemenge_2026-08-11.json galt zunaechst als
# unbeanstandet -- nicht weil es die Regel erfuellt, sondern weil es als
# Vergleich gar nicht erkannt wurde. Eine Pruefung, die eine Datei durchlaesst,
# weil sie sie nicht versteht, ist ein Fehlalarm mit umgekehrtem Vorzeichen.
_VERSUCHSFELD = ("versuche", "n_versuche", "anzahl_versuche")
_HALTEFELD = ("haltemenge", "holdout", "haltemenge_beste")
_TRENNFELD = ("verfahren", "trennung", "teilung")


def ist_vergleich(daten: dict) -> tuple[bool, int]:
    """Vergleich? Und wenn ja, ueber wie viele Moeglichkeiten? Gezaehlt wird,
    was tatsaechlich in der Datei steht -- nicht, was jemand behauptet."""
    for schluessel in _VERGLEICHSSCHLUESSEL:
        wert = daten.get(schluessel)
        if isinstance(wert, dict) and len(wert) > 1:
            return True, len(wert)
        if isinstance(wert, list) and len(wert) > 1:
            return True, len(wert)
    return False, 1


def pruefe_datei(pfad: Path) -> dict | None:
    """Gibt einen Befund zurueck oder None, wenn nichts zu beanstanden ist."""
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if not isinstance(daten, dict):
        return None

    vergleich, moeglichkeiten = ist_vergleich(daten)
    if not vergleich:
        return None

    fehlt = []
    if not any(f in daten for f in _VERSUCHSFELD):
        fehlt.append(f"Versuchszahl (gezaehlt: {moeglichkeiten} Moeglichkeiten in der Datei)")
    if not any(f in daten for f in _HALTEFELD):
        fehlt.append("Haltemenge -- der Sieger ist an keinem eigenen Satz bestaetigt")
    elif not any(f in daten for f in _TRENNFELD):
        fehlt.append("Trennverfahren -- es steht nicht dabei, WIE getrennt wurde")

    if not fehlt:
        return None
    return {"datei": pfad.name, "moeglichkeiten": moeglichkeiten, "fehlt": fehlt}


def pruefen(runs: Path = RUNS) -> dict:
    if not runs.exists():
        return {"geprueft": 0, "befunde": []}
    dateien = [f for f in sorted(runs.glob("*.json"))
               if not f.name.endswith((".gegenprobe.json", ".rasterblick.json"))]
    befunde = [b for b in (pruefe_datei(f) for f in dateien) if b]
    return {"geprueft": len(dateien), "befunde": befunde}


def melden(runs: Path = RUNS) -> dict | None:
    """URTEIL im Sinne von pruefer.py. FEHLKLASSE: Bestwert aus vielen
    Versuchen als Ergebnis ausgegeben.
    PREIS EINES FEHLALARMS: gering -- eine Datei, die mehrere Zeilen fuehrt
    ohne ein Vergleich zu sein (etwa eine Aufstellung), wird mitgezaehlt. Wer
    das sieht, traegt die Versuchszahl 1 ein und die Meldung ist weg."""
    e = pruefen(runs)
    if not e["befunde"]:
        return None
    return {
        "pruefung": "messregeln:bestwert_ohne_haltemenge",
        "befund": f"{len(e['befunde'])} Vergleichsmessung(en) ohne Versuchszahl oder "
                  "Haltemenge: " + ", ".join(b["datei"] for b in e["befunde"][:4])
                  + (" ..." if len(e["befunde"]) > 4 else ""),
        "fehlklasse": "ein Bestwert aus vielen Versuchen ist keine Messung "
                      "(Backtest-Overfitting, Bailey/Lopez de Prado 2014)",
        "fehlalarm_kostet": "ein Feld nachtragen",
    }


def _selftest() -> None:
    import tempfile

    runs = Path(tempfile.mkdtemp())

    # 1) Vergleich ohne alles -> beanstandet, und zwar beides.
    (runs / "a.json").write_text(json.dumps(
        {"varianten": {"x": {"treffer": 5}, "y": {"treffer": 7}}}))
    b = pruefe_datei(runs / "a.json")
    assert b and len(b["fehlt"]) == 2 and b["moeglichkeiten"] == 2, b

    # 2) Gegenprobe: vollstaendige Datei -> KEIN Befund. Ohne diesen Fall
    #    beanstandet die Pruefung alles und wird abgeschaltet.
    (runs / "b.json").write_text(json.dumps(
        {"varianten": {"x": 1, "y": 2}, "versuche": 2,
         "haltemenge": {"x": 2}, "verfahren": "Hash der Zielkennung, Drittel"}))
    assert pruefe_datei(runs / "b.json") is None

    # 3) Haltemenge ohne Trennverfahren -> beanstandet. Eine Trennung, die der
    #    Messende frei waehlt, ist keine.
    (runs / "c.json").write_text(json.dumps(
        {"varianten": {"x": 1, "y": 2}, "versuche": 2, "haltemenge": {"x": 2}}))
    c = pruefe_datei(runs / "c.json")
    assert c and any("Trennverfahren" in f for f in c["fehlt"]), c

    # 4) EINE Bauform ist kein Vergleich -> gar keine Pflicht.
    (runs / "d.json").write_text(json.dumps({"varianten": {"x": 1}, "treffer": 9}))
    assert pruefe_datei(runs / "d.json") is None

    # 5) Eine Datei ohne Vergleichsschluessel bleibt unberuehrt.
    (runs / "e.json").write_text(json.dumps({"treffer": 9, "faelle": 35}))
    assert pruefe_datei(runs / "e.json") is None

    # 6) Melder schweigt, wenn nichts fehlt.
    nur_gut = Path(tempfile.mkdtemp())
    (nur_gut / "b.json").write_text((runs / "b.json").read_text())
    assert melden(nur_gut) is None
    assert melden(runs) is not None

    print("selftest ok (6 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pruefen", action="store_true")
    p.add_argument("--melder", action="store_true")
    p.add_argument("--runs", type=Path, default=RUNS)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return
    if a.melder:
        m = melden(a.runs)
        if m:
            print(f"⚠️ Messregeln: {m['befund']} ({m['fehlklasse']})")
        return

    e = pruefen(a.runs)
    print(f"{e['geprueft']} Ergebnisdatei(en) geprueft, {len(e['befunde'])} beanstandet")
    for b in e["befunde"]:
        print(f"\n  {b['datei']}  ({b['moeglichkeiten']} Moeglichkeiten verglichen)")
        for f in b["fehlt"]:
            print(f"    fehlt: {f}")
    sys.exit(1 if e["befunde"] else 0)


if __name__ == "__main__":
    main()
