"""Aufgriffsquote je SACHGEBIET -- die Auswertung, die als Rangfaktor
ausscheidet und als Diagnose taugt.

WARUM NICHT ALS RANGFAKTOR (Betreiber, 2026-08-20): "koennte aber beim 21.
Mal nuetzlich sein wenn die fragestellung anderst ist" -- und nachgeschaerft:
"oder von jemand anderen gefragt wuerde, oder zu einem anderen zeitpunkt".
Der Aufgriff ist eine Eigenschaft des PAARES aus Frage und Eintrag, nicht des
Eintrags. Dazu die Rueckkopplung, die der eigene Speicher zur selben Frage
lieferte (L-8b377b): "ein Signal, das aus dem eigenen Ausgabekanal
zurueckgespeist wird, braucht immer eine Normierung gegen die
Auslieferungshaeufigkeit -- sonst baut man eine Rueckkopplung und nennt sie
Lernen."

WOFUER ES TAUGT: als Bestandsaussage. Wenn ein ganzer Ast nie aufgegriffen
wird, waehrend ein anderer regelmaessig traegt, ist das eine Aussage darueber,
wie Eintraege GESCHRIEBEN sein muessen -- und die hat keine Rueckkopplung,
weil aus ihr keine Auswahl folgt, sondern eine Schreibweise.

VORBEHALT, der mitgetragen gehoert: Die Zahlen stammen aus zehn Tagen und im
Wesentlichen EINEM Fragenden. Ein Ast mit kleiner Fallzahl sagt nichts.

Nur lesend. Nutzt hauptlauf() aus messungen/aufgriffsquote_2026-08-20.py
unveraendert -- kein zweiter Messweg.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "kern")]
import rueckwirkung as _rw  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "aq", _w / "messungen" / "aufgriffsquote_2026-08-20.py")
aq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aq)

MINDESTZAHL = 20  # darunter wird nur gezaehlt, nicht gedeutet


def zweig(kennung: str, art: str = "") -> str:
    if art == "lehre" or kennung.startswith("L-"):
        return "(Lehren)"
    teile = [t for t in kennung.split("/") if t]
    return "/" + teile[0] if teile else "(ohne)"


def main() -> int:
    roh = aq.hauptlauf()
    je_kennung = roh.get("je_kennung") or {}
    art_je_kennung = roh.get("art_je_kennung") or {}
    if not je_kennung:
        print("ABBRUCH: hauptlauf() liefert keine Einzelkennungen -- "
              "Messweg weicht vom beschriebenen ab, nicht selbst umgangen.")
        print("vorhandene Schluessel:", sorted(roh))
        return 2

    gruppen = defaultdict(list)
    for kennung, satz in je_kennung.items():
        gruppen[zweig(kennung, art_je_kennung.get(kennung, ""))].append(satz)

    zeilen, tabelle = [], {}
    for ast, saetze in sorted(gruppen.items(), key=lambda x: -len(x[1])):
        b = _rw.zaehle(saetze, lambda s: bool(s.get("benutzt")),
                       lambda s: str(s.get("quelle")))
        gedeutet = b.nenner >= MINDESTZAHL
        tabelle[ast] = {"nenner": b.nenner, "treffer": b.treffer,
                        "quote_prozent": round(b.quote * 100, 1),
                        "deutbar": gedeutet}
        zeilen.append(b.zeile(f"Aufgriff {ast}", f"ueber {b.nenner} Kennungen dieses Astes")
                      + ("" if gedeutet else f"  [unter {MINDESTZAHL}, nicht deutbar]"))
    for z in zeilen:
        print(z)

    ziel = _w / "runs" / "aufgriff_je_zweig_2026-08-20.json"
    ziel.write_text(json.dumps({
        "messung": "Aufgriffsquote je Sachgebiet",
        "vorbehalt": ("Zehn Tage, im Wesentlichen ein Fragender. Der Aufgriff ist eine "
                      "Eigenschaft des Paares aus Frage und Eintrag -- NICHT als Rangfaktor "
                      "verwenden (Rueckkopplung, siehe L-8b377b)."),
        "mindestzahl_zum_deuten": MINDESTZAHL,
        "je_zweig": tabelle,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngeschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
