"""Liefermenge des Abrufs (Auftrag 2026-08-09, Aufgabe 1) -- abrufguete.py
misst nur TREFFER/NICHT-GETROFFEN. Dieses Skript misst den PREIS: wieviel
liefert der Abruf pro Fall aus, je Einstellung von ZWEITER_KANAL/
ENSEMBLE_PFLICHT/NORMRANG. Ruft denselben echten Abrufweg wie abrufguete.py
auf (abrufguete.abrufen -> rh.keywords()+rh.query(), Exploration deterministisch
AUS ueber rand=lambda:1.0, s. abrufguete.py-Modul-Docstring). Bestehende
Trefferzaehlung in abrufguete.py bleibt unangetastet -- reiner Lesezugriff
per Import.

Ueber ALLE 45 Faelle (nicht nur die 35 mit target_kind): Liefermenge faellt
fuer jeden Prompt an, unabhaengig davon, ob ein Ziel definiert ist."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import os
import sys
from pathlib import Path

WURZEL = _w
sys.path.insert(0, str(WURZEL / "haken"))
import abrufguete as ag  # noqa: E402 -- liefert lade_korpus()/abrufen(), unveraendert
import knowledge_recall_hook as rh  # noqa: E402


def knoten_text(n: dict) -> str:
    return f"{n['path']} {n['title']} {n['summary']}"


def lehre_text(l: dict) -> str:
    return f"{l['id']} {l['description']} {l['root_cause']} {l['prevention']}"


def liefermenge_fall(nodes: list, lessons: list) -> dict:
    zeichen = sum(len(knoten_text(n)) for n in nodes) + sum(len(lehre_text(l)) for l in lessons)
    return {"n_nodes": len(nodes), "n_lessons": len(lessons), "zeichen": zeichen}


def messe_liefermenge(faelle: list) -> dict:
    """Liefert pro Fall n_nodes/n_lessons/zeichen sowie nodes/lessons roh
    (fuer die Stichprobe)."""
    einzel = []
    for fall in faelle:
        nodes, lessons = ag.abrufen(fall["task"])
        m = liefermenge_fall(nodes, lessons)
        m["task"] = fall["task"]
        m["nodes"] = nodes
        m["lessons"] = lessons
        einzel.append(m)
    return {
        "einzel": einzel,
        "avg_nodes": sum(e["n_nodes"] for e in einzel) / len(einzel),
        "max_nodes": max(e["n_nodes"] for e in einzel),
        "avg_lessons": sum(e["n_lessons"] for e in einzel) / len(einzel),
        "max_lessons": max(e["n_lessons"] for e in einzel),
        "anteil_leer": sum(1 for e in einzel if e["n_nodes"] == 0 and e["n_lessons"] == 0) / len(einzel),
        "avg_zeichen": sum(e["zeichen"] for e in einzel) / len(einzel),
        "max_zeichen": max(e["zeichen"] for e in einzel),
    }


def einstellung(env: dict, faelle: list) -> dict:
    alt = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        return messe_liefermenge(faelle)
    finally:
        for k, v in alt.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


EINSTELLUNGEN = [
    ("VORGABE (ZK=0,EP=1)", {}),
    ("ZK=1 (EP=1 Vorgabe)", {"KNOWLEDGE_ZWEITER_KANAL": "1"}),
    ("ZK=1,EP=0", {"KNOWLEDGE_ZWEITER_KANAL": "1", "KNOWLEDGE_ENSEMBLE_PFLICHT": "0"}),
    ("ZK=1,EP=0,NORMRANG=1", {"KNOWLEDGE_ZWEITER_KANAL": "1", "KNOWLEDGE_ENSEMBLE_PFLICHT": "0",
                               "KNOWLEDGE_NORMRANG_AKTIV": "1"}),
]


def main() -> None:
    faelle = ag.lade_korpus()
    print(f"Bestand: {rh.DB}")
    print(f"Faelle gesamt: {len(faelle)} (Liefermenge ueber ALLE, nicht nur die mit target_kind)\n")

    ergebnisse = {}
    for label, env in EINSTELLUNGEN:
        r = einstellung(env, faelle)
        ergebnisse[label] = r

    kopf = f"{'Einstellung':24s}{'avg_nodes':>10s}{'max_nodes':>10s}{'avg_lehren':>11s}{'max_lehren':>11s}{'leer%':>8s}{'avg_zeichen':>12s}{'max_zeichen':>12s}"
    print(kopf)
    for label, r in ergebnisse.items():
        print(f"{label:24s}{r['avg_nodes']:10.2f}{r['max_nodes']:10d}{r['avg_lessons']:11.2f}"
              f"{r['max_lessons']:11d}{r['anteil_leer']*100:7.1f}%{r['avg_zeichen']:12.0f}{r['max_zeichen']:12d}")

    # Determinismus-Abnahme: gleiche Einstellung zweimal -> gleiche Zahl.
    r1 = einstellung(dict(EINSTELLUNGEN[0][1]), faelle)
    r2 = einstellung(dict(EINSTELLUNGEN[0][1]), faelle)
    gleich = (r1["avg_nodes"], r1["avg_lessons"], r1["avg_zeichen"]) == \
             (r2["avg_nodes"], r2["avg_lessons"], r2["avg_zeichen"])
    print(f"\nDeterminismus (VORGABE zweimal gemessen): {'JA -- identisch' if gleich else 'NEIN -- Abweichung!'}")

    # Stichprobe: ZK=1,EP=0 liefert mehr als ZK=1,EP=1 -- was genau zusaetzlich?
    ep1 = ergebnisse["ZK=1 (EP=1 Vorgabe)"]["einzel"]
    ep0 = ergebnisse["ZK=1,EP=0"]["einzel"]
    kandidaten = []
    for e1, e0, fall in zip(ep1, ep0, faelle):
        n1 = {n["path"] for n in e1["nodes"]}
        l1 = {l["id"] for l in e1["lessons"]}
        n0 = {n["path"] for n in e0["nodes"]}
        l0 = {l["id"] for l in e0["lessons"]}
        zusatz_n = n0 - n1
        zusatz_l = l0 - l1
        if zusatz_n or zusatz_l:
            kandidaten.append((fall, e0, zusatz_n, zusatz_l))

    print(f"\nFaelle mit EP=0 > EP=1 (mehr Liefermenge): {len(kandidaten)} von {len(faelle)}")
    print("Stichprobe (bis zu 3), zusaetzlich gelieferte Eintraege im Klartext:")
    for fall, e0, zusatz_n, zusatz_l in kandidaten[:3]:
        print(f"\n  Fall: {fall.get('target_id', '(kein Ziel)')} -- \"{fall['task'][:70]}...\"")
        for n in e0["nodes"]:
            if n["path"] in zusatz_n:
                print(f"    + Knoten {n['path']}: {n['title']}")
        for l in e0["lessons"]:
            if l["id"] in zusatz_l:
                print(f"    + Lehre {l['id']}: {l['description'][:80]}")


def demo() -> None:
    """Mutationsprobe: liefermenge_fall() durch eine Funktion ersetzt, die
    immer 0 liefert -> alle gemeldeten Durchschnitte (avg_nodes/avg_lessons/
    avg_zeichen) muessen auf 0 einbrechen."""
    # ZWEI Faelle, nicht fuenf (2026-08-19). Gemessen: mit 5 lief dieser
    # Selbsttest 94 s gegen die 120-s-Grenze in tests/test_alle_selftests.py
    # -- unter Last kippte er darueber und war in der vollen Suite rot, allein
    # aber gruen. Ein Ergebnis, das von der Auslastung abhaengt, ist keines.
    # Die Datei mit der Grenze sagt selbst, was dann zu tun ist: "Wer hier
    # weiter hochsetzen muss, hat einen langsamen Selbsttest und kein
    # Zeitproblem: dann gehoert der Selbsttest verkuerzt, nicht die Grenze."
    # Die Mutationsprobe braucht die Menge nicht -- sie braucht nur einen
    # echten Lauf ueber 0 und einen mutierten auf 0.
    faelle = ag.lade_korpus()[0][:2]  # lade_korpus() gibt (faelle, dubletten) zurueck
    echt = messe_liefermenge(faelle)
    assert echt["avg_nodes"] > 0 or echt["avg_lessons"] > 0, (
        "echte Messung liefert nirgends etwas -- Mutationsprobe waere nicht aussagekraeftig")

    global liefermenge_fall
    orig = liefermenge_fall
    liefermenge_fall = lambda nodes, lessons: {"n_nodes": 0, "n_lessons": 0, "zeichen": 0}
    try:
        mutiert = messe_liefermenge(faelle)
    finally:
        liefermenge_fall = orig

    assert mutiert["avg_nodes"] == 0.0 and mutiert["avg_lessons"] == 0.0 and mutiert["avg_zeichen"] == 0.0, (
        f"Mutation haette auf 0 zwingen muessen, war {mutiert}")
    print(f"Mutationsprobe: echt avg_zeichen={echt['avg_zeichen']:.0f} -> mutiert avg_zeichen=0.0 -- "
          f"Messwerkzeug misst tatsaechlich.")
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main()
