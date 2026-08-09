"""Messreihe ueber den Trichter (Auftrag 2026-08-09): MIN_HITS x MAX_LESSONS x
MAX_NODES, bei der im Betrieb geltenden Schalterstellung (ZWEITER_KANAL=0,
ENSEMBLE_PFLICHT=1 -- beide unangetastet, kein os.environ-Eingriff noetig,
das ist bereits die Vorgabe ohne Overrides).

Setzt die drei Regler als Modul-Attribute auf haken/knowledge_recall_hook
(rh.MIN_HITS/rh.MAX_NODES/rh.MAX_LESSONS) -- query() und abrufguete.abrufen()
lesen diese Namen jedes Mal frisch aus dem Modul (siehe deren Quelltext:
`rh.MIN_HITS`, `MIN_HITS`/`MAX_NODES`/`MAX_LESSONS` als freie Namen in
query()), ein Ueberschreiben vor dem Lauf wirkt also tatsaechlich. Datei
haken/knowledge_recall_hook.py bleibt unangetastet (Monolith-Stopp).

Nutzt abrufguete.messe() (Treffer, LESSON/NODE getrennt) und
liefermenge.messe_liefermenge() (Preis: Zeichen/Fall, Anteil leer) --
beide unveraendert per Import, keine Nachbauten."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL / "haken"))
import abrufguete as ag  # noqa: E402
import liefermenge as lm  # noqa: E402
import knowledge_recall_hook as rh  # noqa: E402

MIN_HITS_GITTER = (1, 2, 3, 4)
MAX_LESSONS_GITTER = (2, 3, 5)
MAX_NODES_GITTER = (3, 5, 8)


def _punkt(min_hits: int, max_lessons: int, max_nodes: int, faelle: list, conn: sqlite3.Connection) -> dict:
    alt = (rh.MIN_HITS, rh.MAX_LESSONS, rh.MAX_NODES)
    rh.MIN_HITS, rh.MAX_LESSONS, rh.MAX_NODES = min_hits, max_lessons, max_nodes
    try:
        treffer = ag.messe(faelle, conn)
        preis = lm.messe_liefermenge(faelle)
    finally:
        rh.MIN_HITS, rh.MAX_LESSONS, rh.MAX_NODES = alt
    return {
        "lesson": treffer["LESSON"], "node": treffer["NODE"],
        "avg_zeichen": preis["avg_zeichen"], "anteil_leer": preis["anteil_leer"],
    }


def main() -> None:
    faelle = ag.lade_korpus()
    conn = sqlite3.connect(f"file:{rh.DB}?mode=ro", uri=True)
    print(f"Bestand: {rh.DB}")
    print(f"Faelle: {len(faelle)} -- Schalter: unveraendert (Betrieb: ZWEITER_KANAL=0, ENSEMBLE_PFLICHT=1)\n")

    zeilen = []
    for mh in MIN_HITS_GITTER:
        for ml in MAX_LESSONS_GITTER:
            for mn in MAX_NODES_GITTER:
                p = _punkt(mh, ml, mn, faelle, conn)
                zeilen.append((mh, ml, mn, p))

    kopf = f"{'MIN_HITS':>9s}{'MAX_LESSONS':>12s}{'MAX_NODES':>10s}{'Lehren':>10s}{'Knoten':>10s}{'Zeichen/Fall':>13s}{'leer%':>8s}"
    print(kopf)
    for mh, ml, mn, p in zeilen:
        l = f"{p['lesson'][0]}/{p['lesson'][1]}"
        n = f"{p['node'][0]}/{p['node'][1]}"
        print(f"{mh:>9d}{ml:>12d}{mn:>10d}{l:>10s}{n:>10s}{p['avg_zeichen']:>13.0f}{p['anteil_leer']*100:>7.1f}%")

    # --- Determinismus: derselbe Punkt zweimal ---
    p1 = _punkt(3, 2, 3, faelle, conn)
    p2 = _punkt(3, 2, 3, faelle, conn)
    gleich = (p1["lesson"], p1["node"], p1["avg_zeichen"]) == (p2["lesson"], p2["node"], p2["avg_zeichen"])
    print(f"\nDeterminismus (MIN_HITS=3,MAX_LESSONS=2,MAX_NODES=3 zweimal): "
          f"{'JA -- identisch' if gleich else 'NEIN -- Abweichung'} "
          f"(Exploration in abrufguete.abrufen() deterministisch AUS)")

    # --- Gegenprobe: absurd hoher MIN_HITS muss auf 0 druecken ---
    p_absurd = _punkt(50, 2, 3, faelle, conn)
    print(f"\nGegenprobe (MIN_HITS=50, Rest wie Vorgabe): "
          f"Lehren {p_absurd['lesson'][0]}/{p_absurd['lesson'][1]}, Knoten {p_absurd['node'][0]}/{p_absurd['node'][1]} "
          f"-- {'0 wie erwartet, Setzen wirkt' if p_absurd['lesson'][0] == 0 and p_absurd['node'][0] == 0 else 'FEHLER: kein Effekt, Ueberschreiben wirkt nicht'}")

    # --- Regler ohne Wirkung: MAX_LESSONS/MAX_NODES pruefen, ob sie je die
    #     Trefferzahl bei festem MIN_HITS bewegen ---
    print("\nRegler-Wirkung bei festem MIN_HITS (bewegt MAX_LESSONS/MAX_NODES die Trefferzahl?):")
    for mh in MIN_HITS_GITTER:
        werte = {(ml, mn): _punkt(mh, ml, mn, faelle, conn) for ml in MAX_LESSONS_GITTER for mn in MAX_NODES_GITTER}
        lesson_werte = {v["lesson"] for v in werte.values()}
        node_werte = {v["node"] for v in werte.values()}
        print(f"  MIN_HITS={mh}: Lehren-Trefferzahlen ueber alle MAX_LESSONS/MAX_NODES: {sorted(lesson_werte)} "
              f"-- Knoten-Trefferzahlen: {sorted(node_werte)}")

    conn.close()


def demo() -> None:
    """Selbsttest: Gegenprobe MIN_HITS=50 muss beide Trefferzahlen auf 0
    zwingen (unabhaengig vom main()-Lauf, klein gehalten)."""
    faelle = ag.lade_korpus()
    conn = sqlite3.connect(f"file:{rh.DB}?mode=ro", uri=True)
    # MIN_HITS=3 (Betriebswert) liefert laut Befund 0/35 -- als "normal" fuer
    # die Nichttrivialitaets-Probe taugt daher MIN_HITS=1 (lockerste Schwelle).
    normal = _punkt(1, 2, 3, faelle, conn)
    assert normal["lesson"][0] > 0 or normal["node"][0] > 0, "Normalpunkt (MIN_HITS=1) liefert nirgends Treffer -- Probe nicht aussagekraeftig"
    absurd = _punkt(50, 2, 3, faelle, conn)
    assert absurd["lesson"][0] == 0 and absurd["node"][0] == 0, f"MIN_HITS=50 haette 0 erzwingen muessen, war {absurd}"
    assert rh.MIN_HITS == 3, "Ruecksetzen nach _punkt() fehlgeschlagen -- globaler Zustand haengt"
    conn.close()
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main()
