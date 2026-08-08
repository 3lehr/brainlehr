"""Abrufguete auf dem Pruefkorpus (runs/pruefkorpus.jsonl, 45 Faelle) --
misst, ob der ECHTE Abrufweg (haken/knowledge_recall_hook.py: keywords()
+ query()) den Zielknoten bzw. die Ziel-Lehre unter den gelieferten
Treffern liefert. Kein zweiter Abrufweg: ruft rh.keywords()/rh.query()
exakt so auf wie wissensnutzen_blind.py (blind_retrieve()) -- ein Auftrag
im Klartext rein, keine Handauswahl.

Exploration deterministisch AUS (rand=lambda: 1.0 injiziert; EXPLORE_RATE
in knowledge_recall_hook.py ist 0.15 < 1.0 -> _maybe_explore() zieht nie).
Gleicher Aufruf, gleiche Zahl -- keine weitere Zufallsquelle im Abrufweg.

Gruppen (nie ein Gesamtmittel):
  LESSON      target_kind == "lesson"                       (15 Faelle)
  NODE        target_kind == "node"                         (20 Faelle)
  MIT_KANTE   Ziel hat >=1 Kante in knowledge_relations (Quelle ODER Ziel-Spalte)
  OHNE_KANTE  Ziel hat 0 Kanten
  UEBERGANGEN target_kind fehlt -- kein Ziel definiert, nur gezaehlt        (10 Faelle)

Vier Messreihen ueber KNOWLEDGE_NORMRANG_AKTIV/KNOWLEDGE_HEBB_AKTIV, exakt
das Umschaltmuster aus rangfolge.py._selftest() (os.environ vor jedem
query()-Aufruf gesetzt, danach zurueckgesetzt -- rangfolge.py selbst bleibt
unangetastet, es liest die Variable nur bei jedem Aufruf neu).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL / "haken"))
import knowledge_recall_hook as rh  # noqa: E402 -- echter Abrufweg, nicht nachgebaut

KORPUS = WURZEL / "runs" / "pruefkorpus.jsonl"


def _kein_explore() -> float:
    """EXPLORE_RATE=0.15 < 1.0 -> _maybe_explore() zieht mit diesem Wert nie."""
    return 1.0


def lade_korpus(pfad: Path = KORPUS) -> list[dict]:
    faelle = []
    with pfad.open(encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if zeile:
                faelle.append(json.loads(zeile))
    return faelle


def hat_kante(conn: sqlite3.Connection, target_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM knowledge_relations WHERE source_path = ? OR target_path = ? LIMIT 1",
        (target_id, target_id),
    ).fetchone()
    return row is not None


def treffer(nodes: list, lessons: list, target_kind: str, target_id: str) -> bool:
    """Der Trefferabgleich -- die Mutationsprobe (siehe demo()) ersetzt GENAU
    diese Funktion durch eine, die immer False liefert."""
    if target_kind == "node":
        return target_id in [n["path"] for n in nodes]
    if target_kind == "lesson":
        return target_id in [l["id"] for l in lessons]
    return False


def abrufen(task_text: str) -> tuple[list, list]:
    """Identisch zu wissensnutzen_blind.blind_retrieve(), cwd=None (Korpus
    traegt keine cwd-Angabe je Fall -- fuer alle 45 Faelle und alle vier
    Messreihen gleich, also vergleichbar)."""
    kws = rh.keywords(task_text)
    if len(kws) < rh.MIN_HITS:
        return [], []
    return rh.query(kws, rand=_kein_explore, cwd=None)


def messe(faelle: list, conn: sqlite3.Connection, treffer_fn=treffer) -> dict:
    gruppen: dict[str, list[bool]] = {"LESSON": [], "NODE": [], "MIT_KANTE": [], "OHNE_KANTE": []}
    uebergangen = 0
    einzel: dict[str, bool] = {}
    for fall in faelle:
        kind = fall.get("target_kind")
        if not kind:
            uebergangen += 1
            continue
        nodes, lessons = abrufen(fall["task"])
        ok = treffer_fn(nodes, lessons, kind, fall["target_id"])
        einzel[fall["target_id"]] = ok
        gruppen["LESSON" if kind == "lesson" else "NODE"].append(ok)
        gruppen["MIT_KANTE" if hat_kante(conn, fall["target_id"]) else "OHNE_KANTE"].append(ok)
    ergebnis = {g: (sum(v), len(v)) for g, v in gruppen.items()}
    ergebnis["UEBERGANGEN"] = (None, uebergangen)
    ergebnis["_einzel"] = einzel
    return ergebnis


def messreihe(env_norm: str, env_hebb: str, faelle: list, conn: sqlite3.Connection, treffer_fn=treffer) -> dict:
    os.environ["KNOWLEDGE_NORMRANG_AKTIV"] = env_norm
    os.environ["KNOWLEDGE_HEBB_AKTIV"] = env_hebb
    try:
        return messe(faelle, conn, treffer_fn)
    finally:
        for k in ("KNOWLEDGE_NORMRANG_AKTIV", "KNOWLEDGE_HEBB_AKTIV"):
            os.environ.pop(k, None)


REIHEN = [
    ("AUS/AUS", "0", "0"),
    ("NUR_NORMRANG", "1", "0"),
    ("NUR_HEBB", "0", "1"),
    ("BEIDE_AN", "1", "1"),
]
GRUPPEN = ("LESSON", "NODE", "MIT_KANTE", "OHNE_KANTE")


def _zelle(paar: tuple) -> str:
    treffer_n, gesamt_n = paar
    return f"{treffer_n}/{gesamt_n}"


def main() -> None:
    faelle = lade_korpus()
    conn = sqlite3.connect(f"file:{rh.DB}?mode=ro", uri=True)
    print(f"Bestand: {rh.DB}")
    print(f"Faelle gesamt im Korpus: {len(faelle)}")

    zeilen = [(label, messreihe(en, eh, faelle, conn)) for label, en, eh in REIHEN]

    kopf = f"{'Reihe':14s}" + "".join(f"{g:>14s}" for g in GRUPPEN)
    print("\n" + kopf)
    for label, q in zeilen:
        zelle = "".join(f"{_zelle(q[g]):>14s}" for g in GRUPPEN)
        print(f"{label:14s}{zelle}")

    uebergangen = zeilen[0][1]["UEBERGANGEN"][1]
    print(f"\nUebergangen (kein target_kind, nicht in obiger Tabelle): {uebergangen}/{len(faelle)}")

    aus_aus = zeilen[0][1]
    beide_an = zeilen[-1][1]
    unterschied = any(aus_aus[g] != beide_an[g] for g in GRUPPEN)
    vergleich = ", ".join(f"{g}: {_zelle(aus_aus[g])} -> {_zelle(beide_an[g])}" for g in GRUPPEN)
    print(f"Unterschied AUS/AUS vs BEIDE_AN: {'JA' if unterschied else 'NEIN'} ({vergleich})")
    conn.close()


def demo() -> None:
    """Netzloser Selbsttest gegen die echte DB (kein Ollama noetig -- der
    Keyword-Kanal braucht keins). Belegt zwei Dinge getrennt:

    1) Mutationsprobe: der Trefferabgleich (treffer()) wird durch eine
       Funktion ersetzt, die immer False liefert -> die gemeldete Guete
       faellt in JEDER Gruppe auf 0. Dafuer braucht es einen Fall, der OHNE
       Mutation nachweislich True liefert -- den liefert der reale
       Pruefkorpus NICHT (siehe Befund unten), darum hier ein synthetischer
       Fall: Titel+Summary eines echten Knotens (/testing/pytest) wortwoertlich
       als Aufgabentext -- derselbe Abrufweg (rh.keywords/rh.query), keine
       Handauswahl der Treffer, nur der Aufgabentext ist konstruiert statt aus
       dem Korpus.
    2) Namentlicher Fehlgriff aus dem ECHTEN Korpus: der erste Fall
       (L-a9ccd0) -- nachgewiesen nicht gefunden, echter Lauf."""
    conn = sqlite3.connect(f"file:{rh.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    zeile = conn.execute(
        "SELECT path, title, summary FROM knowledge_nodes WHERE path = ?", ("/testing/pytest",)
    ).fetchone()
    assert zeile is not None, "Testfixtur /testing/pytest fehlt in der DB -- Fixtur pruefen"
    synth_task = f"{zeile['title']} {zeile['summary']}"
    synth_fall = {"target_kind": "node", "target_id": zeile["path"], "task": synth_task}

    echt = messe([synth_fall], conn, treffer_fn=treffer)
    immer_falsch = lambda nodes, lessons, kind, tid: False
    mutiert = messe([synth_fall], conn, treffer_fn=immer_falsch)

    assert echt["_einzel"][zeile["path"]] is True, (
        f"synthetischer Selbsttreffer auf {zeile['path']} schlug fehl -- "
        f"Messwerkzeug fehlerhaft oder Fixtur veraltet")
    assert mutiert["_einzel"][zeile["path"]] is False, "Mutation haette auf False zwingen muessen"
    for g in GRUPPEN:
        assert mutiert[g][0] == 0, f"Mutation haette {g} auf 0 zwingen muessen, war {mutiert[g]}"
    print(f"Mutationsprobe (synthetischer Fall {zeile['path']}): "
          f"echt=True, mutiert=False -- Messwerkzeug misst tatsaechlich.")

    faelle = lade_korpus()
    erster_lesson_fall = next(f for f in faelle if f.get("target_kind") == "lesson")
    kws = rh.keywords(erster_lesson_fall["task"])
    _, lessons = abrufen(erster_lesson_fall["task"])
    gefunden = erster_lesson_fall["target_id"] in [l["id"] for l in lessons]
    assert gefunden is False, (
        f"{erster_lesson_fall['target_id']} sollte laut Befund ein Fehlgriff sein, "
        f"war aber ein Treffer -- Bestand oder Befund hat sich geaendert, neu pruefen")
    print(f"Benannter Fehlgriff aus dem echten Korpus: {erster_lesson_fall['target_id']} "
          f"(Abruf lieferte {[l['id'] for l in lessons]} statt dem Ziel)")

    conn.close()
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main()
