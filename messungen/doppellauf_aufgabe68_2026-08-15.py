"""Aufgabe 68 Abnahme: Doppellauf auf einer Teilmenge des V1-Korpus (5 von
45 Faellen -- voller 3-Zustand-Lauf braucht laut Zeitmessung vom 2026-08-15
(120s / 5 Faelle / 2 Wiederholungen im Zustand B) hochgerechnet ueber alle
45 Faelle und 3 Zustaende weit mehr als das Zeitlimit dieses Auftrags; daher
Teilmenge, wie im Auftrag als Ausweg vorgesehen).

Faehrt run_case() fuer dieselben 5 Faelle (3 solvable + 2 negative, feste
Reihenfolge aus load_cases()) zweimal durch alle drei STATES und vergleicht
Knoten-Pfade + explore-Flag + Lesson-IDs byteweise (JSON-Dump). Schreibt das
Ergebnis nach runs/.

Ausfuehren: python3 messungen/doppellauf_aufgabe68_2026-08-15.py
"""
from __future__ import annotations

import json
import sys as _sys
import time
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import messlauf_abrufguete as m  # noqa: E402

SHARED_KNOWLEDGE = _w
RESULT = SHARED_KNOWLEDGE / "runs/doppellauf_aufgabe68_2026-08-15.json"


def teilmenge(cases: list) -> list:
    solvable = [c for c in cases if c["category"] != "negative"][:3]
    negative = [c for c in cases if c["category"] == "negative"][:2]
    return solvable + negative


def einen_lauf(cases: list) -> dict:
    out = {}
    for name, env in m.STATES.items():
        with m._with_state(env):
            zeile = []
            for c in cases:
                nodes, lessons = m.run_case(c)
                zeile.append({
                    "task": c["task"],
                    "nodes": [(n.get("path"), n.get("explore", False)) for n in nodes],
                    "lessons": [l.get("id") for l in lessons],
                })
            out[name] = zeile
    return out


def main() -> None:
    cases = teilmenge(m.load_cases())
    t0 = time.time()
    lauf1 = einen_lauf(cases)
    t1 = time.time()
    lauf2 = einen_lauf(cases)
    t2 = time.time()

    j1 = json.dumps(lauf1, sort_keys=True, ensure_ascii=False)
    j2 = json.dumps(lauf2, sort_keys=True, ensure_ascii=False)
    identisch = j1 == j2

    abweichungen = []
    if not identisch:
        for zustand in lauf1:
            for i, (a, b) in enumerate(zip(lauf1[zustand], lauf2[zustand])):
                if a != b:
                    abweichungen.append({"zustand": zustand, "fall_index": i,
                                          "lauf1": a, "lauf2": b})

    ergebnis = {
        "zweck": "Aufgabe 68 -- Doppellauf-Beleg auf 5-Fall-Teilmenge (3 solvable + 2 negative)",
        "identisch": identisch,
        "abweichungen": abweichungen,
        "dauer_lauf1_s": round(t1 - t0, 2),
        "dauer_lauf2_s": round(t2 - t1, 2),
        "faelle_je_zustand": len(cases),
        "zustaende": list(m.STATES),
        "laufmetadaten": m.laufmetadaten(m.load_cases(), m.CORPUS),
        "grenze": (
            "Nur 5 von 45 Faellen (kein voller Korpuslauf, Zeitlimit). "
            "Belegt Determinismus des _maybe_explore-Mechanismus im echten "
            "query()-Pfad, NICHT die Trefferguete-Zahlen des vollen Korpus -- "
            "dafuer ist ein separater, laenger laufender Vollrun noetig. "
            "laufmetadaten.commit ist fuer beide Teil-Laeufe gleich (selber "
            "Prozess, kein Commit dazwischen) -- das ist beabsichtigt, kein "
            "Fehler im Vergleich."
        ),
        "lauf1": lauf1,
        "lauf2": lauf2,
    }
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"identisch={identisch} dauer1={t1-t0:.1f}s dauer2={t2-t1:.1f}s")
    print(f"geschrieben: {RESULT}")


if __name__ == "__main__":
    main()
