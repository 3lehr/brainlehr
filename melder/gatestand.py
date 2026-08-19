#!/usr/bin/env python3
# ausloeser: auf-abruf -- beantwortet vor jeder Aussage ueber den Produktstand, wie viele Katalogzeilen wirklich belegt sind
"""Haelt den Lastenkatalog gegen seine eigenen Produktgates: wie viele
Entscheidungen sind belegt, wie viele stehen auf NOT RUN, und nennt ein Gate
einen Pruefbefehl, den es gar nicht gibt?

ANLASS, und er kommt von aussen. Am 2026-08-18 antwortete die
Fahrtenbuch-Sitzung auf den Rundruf mit ihrem teuersten Vorfall des Tages: Sie
hatte "U1 bis U7 abgearbeitet" als fertige App gemeldet. Der Betreiber:
"was ist mit family sync usw, im lastenkatalog steht doch viel mehr?"
Gemessen danach: 6 von 40 belegt, 259 offene Katalogeintraege. Ihr Befund
woertlich: "ein Fortschrittsbericht ohne NENNER wird als Aussage ueber das
Ganze gelesen".

Derselbe Zustand liegt hier: der Root-Katalog fuehrt 55 BDW-Entscheidungen,
alle DECIDED, und die Produktgates stehen fast durchweg auf NOT RUN.
"Entschieden" und "belegt" sind zwei verschiedene Aussagen -- eine
Entscheidung kostet einen Satz, ein Gate kostet Arbeit.

DIE ZWEITE FRAGE IST DIE SCHAERFERE. Ein Gate, das einen Pruefbefehl nennt,
den es nicht gibt, ist schlimmer als ein ehrliches NOT RUN: es liest sich wie
ein Beleg. Deshalb prueft dieser Melder jede genannte Datei auf Existenz. Das
ist dieselbe Fehlerklasse wie ein Melder ohne Ausloeser -- gebaut, benannt,
wirkungslos.

HINWEISRECHT, KEIN VETO: immer exit 0. Die Zahl ist der Zweck, nicht die
Sperre.

Aufruf:
    python3 gatestand.py                 # Quote je Katalog
    python3 gatestand.py --bericht       # dazu jede offene Zeile
    python3 gatestand.py --selftest
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
KATALOGE = sorted((WURZEL / "docs").glob("REQUIREMENTS_*.md"))

# Eine Katalogzeile: | ID | ... | Produktgate | Quelle |
ZEILE = re.compile(r"^\|\s*(BDW-[A-Z]+-?\d+|INT-[A-Z]+-\d+)\s*\|")
# Ein Pruefbefehl im Gate-Text: Pfad mit Endung, in Backticks oder nackt.
DATEI = re.compile(r"`?((?:[\w./-]+/)?[\w.-]+\.(?:py|sh|swift|json|md))`?")


def _spalten(zeile: str) -> list[str]:
    return [t.strip() for t in zeile.strip().strip("|").split("|")]


def lies(pfad: Path) -> list[dict]:
    """Zeilen eines Katalogs mit Kennung, Gate-Text und genannten Dateien."""
    zeilen = []
    for text in pfad.read_text(encoding="utf-8").splitlines():
        if not ZEILE.match(text):
            continue
        s = _spalten(text)
        if len(s) < 3:
            continue
        # Das Produktgate ist die vorletzte Spalte (danach die Quelle).
        gate = s[-2]
        zeilen.append({
            "id": s[0],
            "gate": gate,
            "offen": gate.upper().startswith("NOT RUN") or not gate,
            # DEFERRED ist WEDER offen NOCH belegt. Ohne diese dritte
            # Kategorie haette die Vertagung von 22 Zeilen am 2026-08-18 die
            # Quote von 19/56 auf 41/56 gehoben, ohne dass irgendetwas
            # gemessen worden waere -- eine Schoenung durch Umetikettierung,
            # und genau die Sorte Zahl, gegen die dieser Melder gebaut ist.
            "vertagt": gate.upper().startswith("DEFERRED"),
            # VIERTE KATEGORIE, ergaenzt 2026-08-19. Bis dahin zaehlte
            # TEILWEISE voll als "belegt" -- gemessen sechs Zeilen (P04, P06,
            # E07, E13, E15, F05). Die Quote 33/56 las sich damit besser als
            # der Bestand: TEILWEISE heisst, dass ein Gate lief UND dass es
            # etwas gefunden hat. Genau die Sorte Zahl, gegen die dieser
            # Melder gebaut ist -- und er war blind dafuer, weil "hat ein Gate
            # gelaufen" und "ist belegt" hier stillschweigend gleichgesetzt
            # waren. Aufgefallen, als E18 von TEILWEISE auf PASS ging und die
            # Quote sich nicht bewegte.
            "teilweise": gate.upper().startswith("TEILWEISE"),
            "dateien": [d for d in DATEI.findall(gate)],
        })
    return zeilen


def beurteile(zeilen: list[dict], wurzel: Path = WURZEL) -> dict:
    fehlend = []
    for z in zeilen:
        for d in z["dateien"]:
            if not (wurzel / d).exists() and not list(wurzel.glob(f"**/{Path(d).name}")):
                fehlend.append((z["id"], d))
    offen = [z["id"] for z in zeilen if z["offen"]]
    vertagt = [z["id"] for z in zeilen if z.get("vertagt")]
    teilweise = [z["id"] for z in zeilen if z.get("teilweise")]
    return {
        "gesamt": len(zeilen),
        "offen": len(offen),
        "vertagt": len(vertagt),
        "teilweise": len(teilweise),
        "belegt": len(zeilen) - len(offen) - len(vertagt) - len(teilweise),
        "offene_ids": offen,
        "vertagte_ids": vertagt,
        "teilweise_ids": teilweise,
        "phantom": fehlend,
    }


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp)
        (w / "docs").mkdir()
        (w / "echt.py").write_text("x")
        k = w / "docs" / "REQUIREMENTS_PROBE.md"
        k.write_text(
            "| ID | x | Produktgate | Quelle |\n|---|---|---|---|\n"
            "| BDW-X01 | y | NOT RUN | q |\n"
            "| BDW-X02 | y | PASS: `echt.py --selftest` gruen | q |\n"
            "| BDW-X03 | y | PASS: `gibtsnicht.py --selftest` | q |\n"
            "| BDW-X04 | y | DEFERRED: aktiviert mit dem ersten Piloten (`BDW-C03`) | q |\n"
            "| BDW-X05 | y | TEILWEISE: `echt.py` gruen, aber Index nicht erreicht | q |\n",
            encoding="utf-8")
        z = lies(k)
        assert len(z) == 5, z
        e = beurteile(z, wurzel=w)
        # DIE DRITTE KATEGORIE, ergaenzt 2026-08-18: vertagt zaehlt WEDER als
        # offen NOCH als belegt. Ohne diese Zeile haette die Vertagung von 22
        # Katalogzeilen die Quote von 19/56 auf 41/56 gehoben, ohne dass
        # irgendetwas gemessen worden waere.
        assert e["gesamt"] == 5 and e["offen"] == 1 and e["belegt"] == 2 and e["vertagt"] == 1, e
        # DIE VIERTE KATEGORIE. Rot gegen den Stand vor 2026-08-19: dort war
        # `belegt` 3, weil TEILWEISE mitgezaehlt wurde, und `teilweise` gab es
        # nicht. Ohne diese Zeile blieben sechs halbfertige Katalogzeilen als
        # Beleg gezaehlt.
        assert e["teilweise"] == 1 and e["teilweise_ids"] == ["BDW-X05"], e
        assert e["offene_ids"] == ["BDW-X01"], e
        assert e["vertagte_ids"] == ["BDW-X04"], e
        # Der eigentliche Fund: ein Gate, das eine nicht existierende Datei nennt.
        assert e["phantom"] == [("BDW-X03", "gibtsnicht.py")], e
        # Gegenprobe: die existierende Datei wird NICHT gemeldet.
        assert all(p[0] != "BDW-X02" for p in e["phantom"]), e
    print("gatestand: Selbsttest gruen (Quote 2/5 belegt, 1 offen, 1 vertagt, 1 teilweise, "
          "ein Phantom-Gate gefunden, echtes Gate nicht gemeldet)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    bericht = "--bericht" in sys.argv
    for pfad in KATALOGE:
        zeilen = lies(pfad)
        if not zeilen:
            continue
        e = beurteile(zeilen)
        quote = f"{e['belegt']}/{e['gesamt']}"
        vertagt = f", {e['vertagt']} vertagt" if e.get("vertagt") else ""
        teilweise = f", {e['teilweise']} nur teilweise" if e.get("teilweise") else ""
        print(f"{pfad.name}: {quote} belegt, {e['offen']} ohne Gate-Lauf{vertagt}{teilweise}")
        if bericht and e.get("teilweise_ids"):
            print("  nur teilweise: " + ", ".join(e["teilweise_ids"]))
        for kennung, datei in e["phantom"]:
            print(f"  PHANTOM-GATE {kennung}: nennt {datei} -- existiert nicht")
        if bericht and e["offene_ids"]:
            print("  ohne Beleg: " + ", ".join(e["offene_ids"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
