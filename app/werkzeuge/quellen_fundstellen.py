#!/usr/bin/env python3
"""quellen_fundstellen.py -- traegt fehlende Fundstellen in ein Quellenverzeichnis nach.

Nimmt kern/normfundstelle.py und laesst es ueber ein dossier/quellen.json
laufen: wo eine Quelle eine Normangabe im Beschriftungsfeld traegt, aber
keinen `suchtext`, wird der Wortlaut aus dem hinterlegten Dokument geholt.

DREI SCHRANKEN, und die dritte ist die, die man vergisst:

1. Nichts wird ueberschrieben. Wo schon ein `suchtext` steht, bleibt er --
   von Hand gepflegt schlaegt gerechnet.
2. Nur was belegt ist. Findet normfundstelle die Stelle nicht, wird der Grund
   berichtet und NICHTS eingetragen. Eine erfundene Fundstelle ist schlechter
   als keine, weil sie im Raum wie ein Beleg aussieht.
3. Nur was EINDEUTIG ist. Ein Suchtext, der zweimal im Dokument steht, laesst
   den Betrachter die erste Stelle markieren -- und das ist dann mit 50 %
   Wahrscheinlichkeit die falsche. Solche Treffer werden verlaengert, bis sie
   eindeutig sind, und sonst verworfen.

Ohne --schreiben passiert nichts: der Lauf zeigt nur, was er taete.

Aufruf:
    python3 app/werkzeuge/quellen_fundstellen.py                # Vorschau
    python3 app/werkzeuge/quellen_fundstellen.py --schreiben
    python3 app/werkzeuge/quellen_fundstellen.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kern"))
import normfundstelle as NF  # noqa: E402

STANDARD_KORPUS = Path("/Volumes/daten/Begod2026/buckeberg")
MAX_SUCHTEXT = 160


def _glatt(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().casefold()


def eindeutig_machen(dokumenttext: str, kandidat: str, voll: str) -> tuple[str | None, int]:
    """Verlaengert den Suchtext, bis er genau einmal vorkommt.

    Gibt (suchtext, vorkommen) zurueck. suchtext ist None, wenn auch der volle
    Wortlaut mehrdeutig bleibt -- dann taugt die Stelle nicht zum Markieren,
    und das ist eine Aussage, kein Fehler.
    """
    text = _glatt(dokumenttext)
    obergrenze = min(len(voll), MAX_SUCHTEXT)
    # Die Obergrenze gehoert IMMER in die Liste, sonst wird der vollstaendige
    # Wortlaut nie geprueft: bei 40er-Schritten springt die Schleife sonst
    # ueber ihn hinweg und meldet "nicht eindeutig", obwohl er es waere.
    # Vom Selbsttest gefunden, bevor der erste Datensatz geschrieben war.
    laengen = sorted({min(l, obergrenze)
                      for l in range(len(kandidat), obergrenze + 40, 40)} | {obergrenze})
    n = 0
    for laenge in laengen:
        probe = voll[:laenge].strip()
        n = text.count(_glatt(probe))
        if n == 1:
            return probe, 1
        if n == 0:
            return None, 0
    return None, n


def durchgang(korpus: Path) -> dict:
    pfad = korpus / "dossier" / "quellen.json"
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    quellen = {k: v for k, v in roh.items() if k.isdigit()}

    eintrag, befund, unberuehrt = [], [], []
    for nr, q in sorted(quellen.items(), key=lambda x: int(x[0])):
        datei = q.get("datei", "")
        if q.get("suchtext"):
            unberuehrt.append((nr, "hat bereits einen Suchtext"))
            continue
        if not datei.lower().endswith((".html", ".htm")):
            unberuehrt.append((nr, f"kein HTML ({datei or 'keine Datei'})"))
            continue

        ort = korpus / "homepage" / "public" / "quellen" / datei
        e = NF.loese(q.get("kurz", ""), ort)
        if not e.get("gefunden"):
            befund.append((nr, q.get("kurz", "")[:50], e.get("grund", "")))
            continue

        text = NF.text_aus_html(ort.read_bytes())
        voll = e.get("wortlaut") or e["suchtext"]
        such, n = eindeutig_machen(text, e["suchtext"], voll)
        if such is None:
            befund.append((nr, q.get("kurz", "")[:50],
                           f"Wortlaut kommt {n}x vor, nicht eindeutig markierbar"))
            continue
        eintrag.append({"nr": nr, "norm": e["norm"], "ebene": e["ebene"], "suchtext": such})

    return {"pfad": pfad, "roh": roh, "eintrag": eintrag,
            "befund": befund, "unberuehrt": unberuehrt, "gesamt": len(quellen)}


def schreibe(erg: dict) -> int:
    roh = erg["roh"]
    for e in erg["eintrag"]:
        roh[e["nr"]]["suchtext"] = e["suchtext"]
        roh[e["nr"]]["suchtext_herkunft"] = f"gerechnet aus {e['norm']} ({e['ebene']})"
    erg["pfad"].write_text(
        json.dumps(roh, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(erg["eintrag"])


def _selftest() -> int:
    doc = ("Praeambel. Die Frist betraegt einen Monat. Sonstiges. "
           "Die Frist betraegt einen Monat und endet dann.")
    # Mehrdeutiger Anfang wird verlaengert, bis er eindeutig ist.
    such, n = eindeutig_machen(doc, "Die Frist betraegt einen Monat",
                               "Die Frist betraegt einen Monat und endet dann.")
    assert n == 1 and such.endswith("endet dann."), (such, n)
    # Eindeutiger Kandidat bleibt, wie er ist.
    such, n = eindeutig_machen(doc, "Praeambel.", "Praeambel.")
    assert (such, n) == ("Praeambel.", 1)
    # Negativfall: was nicht dasteht, ergibt keinen Suchtext.
    assert eindeutig_machen(doc, "Kernfusion", "Kernfusion")[0] is None
    # Und was auch voll ausgeschrieben mehrdeutig bleibt, wird verworfen.
    zwilling = "Gleicher Satz. Gleicher Satz."
    assert eindeutig_machen(zwilling, "Gleicher Satz.", "Gleicher Satz.")[0] is None
    print("quellen_fundstellen: Selbsttest bestanden")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--korpus", type=Path, default=STANDARD_KORPUS)
    p.add_argument("--schreiben", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return _selftest()

    erg = durchgang(a.korpus)
    print(f"Quellen gesamt: {erg['gesamt']}")
    print(f"eintragbar:     {len(erg['eintrag'])}")
    print(f"Befunde:        {len(erg['befund'])}")
    print()
    for e in erg["eintrag"]:
        print(f"  [{e['nr']:>2}] {e['norm']:<28} {e['ebene']:<9} {e['suchtext'][:60]}")
    if erg["befund"]:
        print("\nBEFUNDE (nichts eingetragen, jeder ist eine echte Aussage):")
        for nr, kurz, grund in erg["befund"]:
            print(f"  [{nr:>2}] {kurz:<52} {grund}")
    if a.schreiben:
        n = schreibe(erg)
        print(f"\n{n} Fundstelle(n) in {erg['pfad']} eingetragen.")
    else:
        print("\n(Vorschau -- mit --schreiben wird eingetragen.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
