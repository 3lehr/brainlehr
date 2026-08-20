"""Einmal-Arbeitsskript, Auftrag 2026-08-20 (Handbeurteilung der 20 BF_CF-
Faelle aus runs/kreuztabelle_bc_2026-08-20.json::schritt2_dritte_gruppe_bf_cf).

Nur lesend: fuehrt run_case() (kern/messlauf_abrufguete.py, unveraendert
importiert) im Zustand B gegen einen Schnappschuss aus und schreibt Titel/
Zusammenfassung der TATSAECHLICH ausgelieferten Treffer weg, damit ein
Mensch (bzw. hier: der Agent von Hand) beurteilen kann, statt nur Kennungen
zu vergleichen. bester_kosinus wird NICHT neu berechnet, sondern aus der
bereits vorliegenden Datei runs/kreuztabelle_bc_2026-08-20.json (nur
gelesen, TABU laut Auftrag) uebernommen.

Schreibt runs/roh_bf_cf_2026-08-20.json (Rohmaterial), die eigentliche
Beurteilung (vier Klassen + Begruendungssatz) traegt der Agent von Hand in
runs/beurteilung_bf_cf_2026-08-20.json ein.
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

FAELLE = json.loads((_w / "runs/kreuztabelle_bc_2026-08-20.json").read_text())[
    "schritt2_dritte_gruppe_bf_cf"]
TARGET_IDS = set(FAELLE["faelle"])
KOSINUS_JE_TARGET = {k["target_id"]: k["bester_kosinus"] for k in FAELLE["kennzahlen"]}

CORPUS = {c["target_id"]: c for c in ml.load_cases()}
OUT = _w / "runs/roh_bf_cf_2026-08-20.json"


def main() -> None:
    rows = []
    with ml._gegen_schnappschuss():
        with ml._with_state(ml.STATES["B_2Kanal_an_Pflicht_aus"]):
            for tid in FAELLE["faelle"]:
                c = CORPUS[tid]
                nodes, lessons = ml.run_case(c)
                nodes_out = [{"path": n["path"], "title": n.get("title"),
                               "summary": n.get("summary")} for n in nodes[:3]]
                lessons_out = [{"id": l["id"], "description": l.get("description"),
                                 "prevention": l.get("prevention")} for l in lessons[:3]]
                rows.append({
                    "target_id": tid,
                    "target_kind": c["target_kind"],
                    "task": c["task"],
                    "target_label": c["target_label"],
                    "bester_kosinus": KOSINUS_JE_TARGET.get(tid),
                    "ausgeliefert_nodes": nodes_out,
                    "ausgeliefert_lessons": lessons_out,
                })
    OUT.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"geschrieben: {OUT} ({len(rows)} Faelle)")


def demo() -> None:
    """Ponytail-Selbsttest: alle 20 Ziel-IDs aus der Vorgabedatei sind im
    Korpus auffindbar, sonst waere jeder run_case()-Aufruf sinnlos."""
    assert len(TARGET_IDS) == 20, len(TARGET_IDS)
    missing = TARGET_IDS - set(CORPUS)
    assert not missing, missing
    assert len(KOSINUS_JE_TARGET) == 20
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main()
