"""Einmal-Arbeitsskript, Auftrag 2026-08-20: braucht der Pruefkorpus
Mehrfachziele? Holt fuer alle 35 loesbaren Faelle die in Zustand
B_2Kanal_an_Pflicht_aus TATSAECHLICH ausgelieferte Menge (bis 10 Knoten /
7 Lehren, Titel+Zusammenfassung) -- reine Messung, keine Bewertung.

Nutzt DENSELBEN Weg wie kern/messlauf_abrufguete.py: load_cases()/
_with_state()/STATES/_gegen_schnappschuss()/target_hit()/run_case()
importiert, kein zweiter Messweg. Nur lesend.

Ausfuehren: python3 messungen/mehrfachziele_2026-08-20.py
Ergebnis: runs/mehrfachziele_2026-08-20.json (nur die Rohdaten je Fall --
Zweitziel-Beurteilung und Auszaehlung sind ein eigener, menschlicher Schritt
nach dem Lauf, laut Auftrag nicht automatisch zu entscheiden).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "melder", "migrationen")]

import messlauf_abrufguete as ml  # noqa: E402

RESULT = _w / "runs/mehrfachziele_2026-08-20.json"
STATE_B = "B_2Kanal_an_Pflicht_aus"


def node_kurz(n: dict) -> dict:
    return {"id": n.get("path"), "titel": n.get("title"), "zusammenfassung": n.get("summary")}


def lesson_kurz(l: dict) -> dict:
    return {"id": l.get("id"), "titel": l.get("description"), "zusammenfassung": l.get("resolution")}


def main() -> None:
    cases = ml.load_cases()
    solvable = [c for c in cases if c["category"] != "negative"]
    assert len(solvable) == 35

    faelle = []
    with ml._gegen_schnappschuss() as stand:
        with ml._with_state(ml.STATES[STATE_B]):
            for c in solvable:
                nodes, lessons = ml.run_case(c)
                treffer_heute = ml.target_hit(c, nodes, lessons)
                faelle.append({
                    "task": c["task"],
                    "target_kind": c["target_kind"],
                    "target_id": c["target_id"],
                    "target_label": c.get("target_label"),
                    "treffer_heute": treffer_heute,
                    "ausgeliefert_nodes": [node_kurz(n) for n in nodes],
                    "ausgeliefert_lessons": [lesson_kurz(l) for l in lessons],
                    "anzahl_nodes": len(nodes),
                    "anzahl_lessons": len(lessons),
                })
        stand_info = {"kennung": stand.kennung, "aufgenommen": stand.aufgenommen}

    treffer_heute_zahl = sum(1 for f in faelle if f["treffer_heute"])

    ergebnis = {
        "beschreibung": "Rohdaten fuer die Mehrfachziel-Frage: je Fall (35 "
                        "loesbare) die volle in Zustand B ausgelieferte Menge "
                        "(Titel+Zusammenfassung). Beurteilung Zweitziel/Zaehlung "
                        "ist ein separater Schritt, hier NICHT automatisiert.",
        "zustand": STATE_B,
        "nenner_solvable": 35,
        "treffer_heute": [treffer_heute_zahl, 35],
        "faelle": faelle,
        "stand": stand_info,
        "laufmetadaten": ml.laufmetadaten(cases, ml.CORPUS),
    }
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"geschrieben: {RESULT}")
    print(f"treffer_heute: {treffer_heute_zahl}/35")


if __name__ == "__main__":
    main()
