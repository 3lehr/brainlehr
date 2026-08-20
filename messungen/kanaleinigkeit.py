"""Wie oft sind sich die beiden Suchkanaele ueberhaupt einig?

ANLASS 2026-08-20: Zwei Konsilrollen (Meteorologie, Skeptiker) hoben
unabhaengig voneinander eine Nebenzeile der Kreuztabelle hervor -- die Zahl
uebereinstimmender Kanaele war dort "durchweg 0". Ihre Folgerung: die
Fusion ist wirkungslos, die Ensemble-Pflicht kein Filter, sondern ein
Aus-Schalter.

Belegt war das aber nur fuer 24 der 45 Faelle (die zwei Gruppen der
Trennungsmessung). Dieses Skript misst es fuer ALLE 45 -- und zwar in
BEIDEN Betriebsarten, weil eine Aussage ueber den Betrieb im
Auslieferungszustand erhoben gehoert (L-c94630).

Ueberschneidung heisst hier dasselbe wie im Betrieb: die obersten
ENSEMBLE_TOP_N Kennungen des Stichwortkanals gegen dieselbe Zahl des
Bedeutungskanals, Schnittmenge gezaehlt. Kein neuer Messweg -- die
Funktionen kommen aus messungen/kreuztabelle_bc.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken"), str(_w / "messungen")]

import kreuztabelle_bc as kb  # noqa: E402
import messlauf_abrufguete as ml  # noqa: E402
import rueckwirkung as _rw  # noqa: E402

ZUSTAENDE = ["B_2Kanal_an_Pflicht_aus", "C_beide_an"]


def main() -> int:
    cases = ml.load_cases()
    ergebnis = {}
    with ml._gegen_schnappschuss():
        for zustand in ZUSTAENDE:
            je_fall = []
            with ml._with_state(ml.STATES[zustand]):
                for c in cases:
                    roh = kb.instrumented_run(c)
                    kanal = roh.get("kanal_node") if c["target_kind"] != "lesson" else roh.get("kanal_lesson")
                    k = kb.kennzahlen(roh["bedeutungswerte"], kanal, c["target_kind"])
                    je_fall.append({
                        "target_id": c.get("target_id"),
                        "target_kind": c["target_kind"],
                        "category": c["category"],
                        "kanaele_uebereinstimmend": k["kanaele_uebereinstimmend"],
                        "trefferzahl": k["trefferzahl"],
                    })
            messbar = [f for f in je_fall if f["kanaele_uebereinstimmend"] is not None]
            b = _rw.zaehle(messbar, lambda f: f["kanaele_uebereinstimmend"] > 0,
                           lambda f: f"{f['target_id']}: {f['kanaele_uebereinstimmend']}")
            ergebnis[zustand] = {
                "je_fall": je_fall,
                "messbar": len(messbar),
                "ohne_kanalsignal": len(je_fall) - len(messbar),
                "mit_uebereinstimmung": b.treffer,
                "zeile": b.zeile("Faelle mit mindestens einer Ueberschneidung der Top-5 beider Kanaele",
                                 f"ueber {len(messbar)} messbare der 45 Pruefkorpus-Faelle in Zustand {zustand}"),
            }
            print(ergebnis[zustand]["zeile"])
            if ergebnis[zustand]["ohne_kanalsignal"]:
                print(f"    (ohne Kanalsignal, nicht messbar: {ergebnis[zustand]['ohne_kanalsignal']})")
    ziel = _w / "runs" / "kanaleinigkeit_2026-08-20.json"
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngeschrieben: {ziel}")
    return 0


def _fehlt(was: str) -> int:
    print(f"ABBRUCH: {was} gibt es nicht -- Messweg weicht vom beschriebenen ab, nicht selbst umgangen.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
