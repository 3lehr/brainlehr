"""Einmal-Arbeitsskript, Auftrag S4 (docs/PLAN_ZWEITES_SIGNAL_2026-08-20.md):
Erzeugt eine BLINDE Fallliste fuer die Handbeurteilung -- Anfrage plus
ausgeliefertes Ergebnis (Titel+Zusammenfassung), OHNE Kosinuswert, OHNE
Gruppenzugehoerigkeit (Treffer/Fehlgriff), OHNE Korpus-Zielangabe. Reihenfolge
gemischt per Hash der target_id, nicht nach Gruppe.

Nutzt kreuztabelle_bc.instrumented_run() (importiert, nicht neu gebaut) im
Zustand B_2Kanal_an_Pflicht_aus (der Zustand, den runs/beurteilung_bf_cf_2026-08-20.json
misst -- ADR S4 verlangt denselben Weg, nicht einen zweiten). Schreibt zwei
Dateien:
  runs/beurteilung_blind_faelle_2026-08-20.json  -- die blinde Liste (zum Urteilen)
  runs/beurteilung_blind_aufloesung_2026-08-20.json -- Gruppe/Ziel je Fall, NICHT
    vor dem Urteilen lesen (Schritt 5 im Auftrag)
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "melder", "migrationen")]

import kreuztabelle_bc as kb  # noqa: E402
import messlauf_abrufguete as ml  # noqa: E402

BLIND = _w / "runs/beurteilung_blind_faelle_2026-08-20.json"
AUFLOESUNG = _w / "runs/beurteilung_blind_aufloesung_2026-08-20.json"


def item_titel(n: dict, art: str) -> dict:
    if art == "node":
        return {"art": "node", "titel": n.get("title", ""), "zusammenfassung": n.get("summary", "")}
    return {"art": "lesson", "titel": n.get("description", ""), "zusammenfassung": n.get("root_cause", "")}


def main() -> None:
    cases = ml.load_cases()
    solvable = [c for c in cases if c["category"] != "negative"]
    assert len(solvable) == 35, f"{len(solvable)} loesbare Faelle, erwartet 35"

    # Blinde Reihenfolge: Hash der target_id, nicht Gruppenzugehoerigkeit.
    solvable.sort(key=lambda c: hashlib.sha256(c["target_id"].encode("utf-8")).hexdigest())

    blind = []
    aufloesung = []
    with ml._gegen_schnappschuss():
        for i, c in enumerate(solvable):
            with ml._with_state(ml.STATES[kb.STATE_B]):
                r = kb.instrumented_run(c)

            ausgeliefert = (
                [item_titel(n, "node") for n in r["nodes"]] +
                [item_titel(n, "lesson") for n in r["lessons"]]
            )
            top3 = ausgeliefert[:3]

            blind.append({
                "lfd": i + 1,
                "anfrage": c["task"],
                "ausgeliefert_top3": top3,
                "ausgeliefert_gesamt_anzahl": len(ausgeliefert),
            })

            richtig = ml.target_hit(c, r["nodes"], r["lessons"])
            aufloesung.append({
                "lfd": i + 1,
                "category": c["category"],
                "target_kind": c["target_kind"],
                "target_id": c["target_id"],
                "target_label": c.get("target_label"),
                "b_richtig_treffer": richtig,
            })

    BLIND.write_text(json.dumps({
        "hinweis": "BLIND -- keine Kosinuswerte, keine Gruppe, kein Korpusziel. "
                   "Reihenfolge nach Hash der target_id, nicht nach Gruppe.",
        "anzahl": len(blind),
        "faelle": blind,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    AUFLOESUNG.write_text(json.dumps({
        "hinweis": "TABU bis Schritt 5 der Beurteilung -- vorher nicht lesen.",
        "faelle": aufloesung,
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{len(blind)} Faelle geschrieben nach {BLIND}")
    print(f"Aufloesung geschrieben nach {AUFLOESUNG} (TABU bis Schritt 5)")


if __name__ == "__main__":
    main()
