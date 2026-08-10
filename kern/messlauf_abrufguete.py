"""Misst knowledge_recall_hook.query() gegen den Pruefkorpus (45 Faelle,
shared-knowledge/runs/pruefkorpus.jsonl) in drei Zustaenden A/B/C
(KNOWLEDGE_ZWEITER_KANAL / KNOWLEDGE_ENSEMBLE_PFLICHT). Nur lesen/aufrufen --
knowledge_recall_hook.py wird NICHT veraendert, Schalter nur per os.environ
(ein anderer Agent arbeitet an der Datei). pruefkorpus.py/bedeckung.py/
wissensnutzen*.py/wirkung.py: nur gelesen, nicht importiert/veraendert.

Vier Zahlen je Zustand, Nenner getrennt:
  trefferguete        Ziel unter den Treffern? -- nur die 35 loesbaren Faelle
  falsches_schweigen  loesbare Aufgabe, nichts eingespielt          (Fehler)
  richtiges_schweigen negative Aufgabe, nichts eingespielt          (richtig)
  falsches_sprechen   negative Aufgabe, trotzdem etwas eingespielt  (Rauschen)

Ausfuehren: python3 messlauf_abrufguete.py [--eichung-only]
Ergebnis: shared-knowledge/runs/messlauf_abrufguete.json
"""
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

import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = _w
HUB = SHARED_KNOWLEDGE.parent
sys.path.insert(0, str(HUB / "scripts"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
import knowledge_recall_hook as hook  # noqa: E402

CORPUS = SHARED_KNOWLEDGE / "runs/pruefkorpus.jsonl"
RESULT = SHARED_KNOWLEDGE / "runs/messlauf_abrufguete.json"

STATES = {
    "A_beide_aus":              {"KNOWLEDGE_ZWEITER_KANAL": "0", "KNOWLEDGE_ENSEMBLE_PFLICHT": "0"},
    "B_2Kanal_an_Pflicht_aus":  {"KNOWLEDGE_ZWEITER_KANAL": "1", "KNOWLEDGE_ENSEMBLE_PFLICHT": "0"},
    "C_beide_an":               {"KNOWLEDGE_ZWEITER_KANAL": "1", "KNOWLEDGE_ENSEMBLE_PFLICHT": "1"},
}


def load_cases() -> list[dict]:
    cases = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    assert len(cases) == 45, f"Korpus hat {len(cases)} Faelle, erwartet 45 -- Datei geaendert?"
    return cases


def run_case(c: dict) -> tuple[list, list]:
    """main()-Gatter nachgebildet (len(kws) < MIN_HITS -> sofortige Stille,
    genau wie main() vor dem ersten query()-Aufruf), sonst reiner query()."""
    kws = hook.keywords(c["task"])
    if len(kws) < hook.MIN_HITS:
        return [], []
    return hook.query(kws, cwd=None, prompt=c["task"])


def target_hit(c: dict, nodes: list, lessons: list) -> bool:
    if c["target_kind"] == "node":
        return any(n["path"] == c["target_id"] for n in nodes)
    if c["target_kind"] == "lesson":
        return any(l["id"] == c["target_id"] for l in lessons)
    return False


def messe(cases: list) -> dict:
    solvable = [c for c in cases if c["category"] != "negative"]
    negative = [c for c in cases if c["category"] == "negative"]
    assert len(solvable) == 35 and len(negative) == 10

    treffer = falsches_schweigen = 0
    for c in solvable:
        nodes, lessons = run_case(c)
        if target_hit(c, nodes, lessons):
            treffer += 1
        if not nodes and not lessons:
            falsches_schweigen += 1

    richtiges_schweigen = 0
    for c in negative:
        nodes, lessons = run_case(c)
        if not nodes and not lessons:
            richtiges_schweigen += 1
    falsches_sprechen = len(negative) - richtiges_schweigen

    return {
        "trefferguete": [treffer, len(solvable)],
        "falsches_schweigen": [falsches_schweigen, len(solvable)],
        "richtiges_schweigen": [richtiges_schweigen, len(negative)],
        "falsches_sprechen": [falsches_sprechen, len(negative)],
    }


def _with_state(env: dict):
    class _Ctx:
        def __enter__(self):
            self.old = {k: os.environ.get(k) for k in env}
            os.environ.update(env)
        def __exit__(self, *a):
            for k, v in self.old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    return _Ctx()


def messlauf(cases: list) -> dict:
    ergebnis = {}
    for name, env in STATES.items():
        with _with_state(env):
            ergebnis[name] = messe(cases)
        r = ergebnis[name]
        print(f"{name}:")
        for k, (n, d) in r.items():
            print(f"  {k}: {n}/{d} = {n/d:.2%}")
    return ergebnis


def eichung(cases: list) -> dict:
    """Gegenprobe (verbindlich laut Auftrag): ein loesbarer Fall, der VOR
    Entfernung tatsaechlich ein Treffer ist -- reines bm25 (Zustand A) liefert
    wegen der Anti-Zirkularitaet des Korpus 0/35 Treffer, darum ueber alle
    drei Zustaende gesucht. Ziel aus einer KOPIE der DB entfernt (NIE am
    Original), danach muss derselbe Fall im selben Zustand kein Treffer mehr
    sein. Ohne diese Gegenprobe misst der Aufbau nichts (Auftrag)."""
    solvable = [c for c in cases if c["category"] != "negative"]
    case = zustand = None
    for name, env in STATES.items():
        with _with_state(env):
            for c in solvable:
                nodes, lessons = run_case(c)
                if target_hit(c, nodes, lessons):
                    case, zustand = c, name
                    break
        if case:
            break
    assert case is not None, "kein Fall in irgendeinem Zustand ein Treffer -- Eichung nicht durchfuehrbar"

    with _with_state(STATES[zustand]):
        nodes, lessons = run_case(case)
        vor = target_hit(case, nodes, lessons)
        assert vor

        copy_path = "/tmp/knowledge_eichung_copy.db"
        shutil.copyfile(hook.DB, copy_path)
        conn = sqlite3.connect(copy_path)
        if case["target_kind"] == "lesson":
            conn.execute("DELETE FROM lessons_learned WHERE id = ?", (case["target_id"],))
            conn.execute("DELETE FROM lessons_fts WHERE rowid NOT IN (SELECT rowid FROM lessons_learned)")
            conn.execute("DELETE FROM knowledge_embeddings WHERE kind='lesson' AND ref_id=?", (case["target_id"],))
        else:
            # target_id ist die path-Spalte (Materialized Path), nicht id --
            # knowledge_embeddings.ref_id verweist dagegen auf id.
            row = conn.execute("SELECT id FROM knowledge_nodes WHERE path=?", (case["target_id"],)).fetchone()
            assert row, f"Ziel {case['target_id']!r} nicht in der Kopie gefunden"
            conn.execute("DELETE FROM knowledge_nodes WHERE path=?", (case["target_id"],))
            conn.execute("DELETE FROM knowledge_fts WHERE rowid NOT IN (SELECT rowid FROM knowledge_nodes)")
            conn.execute("DELETE FROM knowledge_embeddings WHERE kind='node' AND ref_id=?", (row[0],))
        conn.commit()
        conn.close()

        orig_db = hook.DB
        hook.DB = copy_path
        try:
            nodes, lessons = run_case(case)
        finally:
            hook.DB = orig_db
        os.remove(copy_path)

    nach = target_hit(case, nodes, lessons)
    assert not nach, "Ziel darf nach Entfernung aus der Kopie nicht mehr gefunden werden -- Aufbau misst nichts"
    print(f"\nEICHUNG ok: Fall {case['target_kind']} {case['target_id']!r}, Zustand {zustand} -- "
          f"Treffer {vor} -> {nach} nach Entfernung aus der Kopie (Original unangetastet).")
    return {"case": case["target_id"], "zustand": zustand, "vor": vor, "nach": nach}


def demo() -> None:
    """Ponytail-Selbsttest: run_case()/target_hit() gegen die echte DB, keine
    Netzwerk-/Ollama-Abhaengigkeit (Zustand A, reiner Stichwort-Kanal)."""
    cases = load_cases()
    with _with_state(STATES["A_beide_aus"]):
        r = messe(cases)
    assert set(r) == {"trefferguete", "falsches_schweigen", "richtiges_schweigen", "falsches_sprechen"}
    for n, d in r.values():
        assert 0 <= n <= d
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    cases = load_cases()
    ergebnis = {"messlauf": messlauf(cases)}
    if "--eichung-only" not in sys.argv:
        ergebnis["eichung"] = eichung(cases)
    RESULT.parent.mkdir(exist_ok=True)
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\ngeschrieben: {RESULT}")
