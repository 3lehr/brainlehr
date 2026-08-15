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

import hashlib
import json
import os
import random
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

SHARED_KNOWLEDGE = _w
HUB = SHARED_KNOWLEDGE.parent
sys.path.insert(0, str(HUB / "scripts"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
import knowledge_recall_hook as hook  # noqa: E402

CORPUS = SHARED_KNOWLEDGE / "runs/pruefkorpus.jsonl"
RESULT = SHARED_KNOWLEDGE / "runs/messlauf_abrufguete.json"

# KNOWLEDGE_SUCHPFAD_ABRUF: "0" in jedem Zustand seit 2026-08-15 (Befund
# Aufgabe 71/Messung messung_aufgabe71_45_gegen_33). Seit Commit b52856b
# (2026-08-09, "Suchpfad EIN") ist SUCHPFAD_ABRUF modulweit Vorgabe True --
# knowledge_recall_hook.query() nimmt dann den Suchpfad-Zweig und kehrt VOR
# der ENSEMBLE_PFLICHT-Abfrage zurueck (haken/knowledge_recall_hook.py, Zeile
# ~1106-1142). Ohne diese Zeile hier vergleichen B und C denselben Zweig --
# ENSEMBLE_PFLICHT wirkt nie, B und C werden bit-identisch. Erzwingt hier den
# alten, von ENSEMBLE_PFLICHT tatsaechlich gesteuerten Zweig, damit die drei
# Zustaende wieder das messen, was ihr Name verspricht.
STATES = {
    "A_beide_aus":              {"KNOWLEDGE_ZWEITER_KANAL": "0", "KNOWLEDGE_ENSEMBLE_PFLICHT": "0", "KNOWLEDGE_SUCHPFAD_ABRUF": "0"},
    "B_2Kanal_an_Pflicht_aus":  {"KNOWLEDGE_ZWEITER_KANAL": "1", "KNOWLEDGE_ENSEMBLE_PFLICHT": "0", "KNOWLEDGE_SUCHPFAD_ABRUF": "0"},
    "C_beide_an":               {"KNOWLEDGE_ZWEITER_KANAL": "1", "KNOWLEDGE_ENSEMBLE_PFLICHT": "1", "KNOWLEDGE_SUCHPFAD_ABRUF": "0"},
}


def load_cases() -> list[dict]:
    cases = [json.loads(l) for l in open(CORPUS, encoding="utf-8")]
    assert len(cases) == 45, f"Korpus hat {len(cases)} Faelle, erwartet 45 -- Datei geaendert?"
    return cases


def _seeded_rand(task: str):
    """Determinismus-Fix Aufgabe 68: hook.query() reicht `rand` an
    hook._maybe_explore() durch, das ohne dieses Argument auf das
    ungeseedete random.random() zurueckfaellt (EXPLORE_RATE=0.15 ersetzt
    dann bei ~15% der Aufrufe den schwaechsten Treffer durch einen anderen
    -- zwei Laeufe desselben Standes koennen seither auseinandergehen,
    siehe tests/test_messlauf_deterministisch.py::test_maybe_explore_ohne_seed_kann_abweichen
    fuer den Rot-Beleg). Seed haengt NUR am Fall-Text, nicht an Uhrzeit/
    Prozess -- zwei Laeufe desselben Korpus wuerfeln deshalb identisch,
    verschiedene Faelle weiterhin unabhaengig voneinander."""
    seed = int(hashlib.sha256(task.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(seed).random


def run_case(c: dict) -> tuple[list, list]:
    """main()-Gatter nachgebildet (len(kws) < MIN_HITS -> sofortige Stille,
    genau wie main() vor dem ersten query()-Aufruf), sonst reiner query()."""
    kws = hook.keywords(c["task"])
    if len(kws) < hook.MIN_HITS:
        return [], []
    return hook.query(kws, rand=_seeded_rand(c["task"]), cwd=None, prompt=c["task"])


def laufmetadaten(cases: list, corpus_path: Path) -> dict:
    """Rueckverfolgbarkeit fuer den Vergleich zweier Laeufe (Aufgabe 68,
    Vorschlag aus messung_aufgabe71_45_gegen_33 Frage 5): Commit-Kennung zur
    Laufzeit + Korpusteilung + Korpus-Hash. Ohne diese drei ist eine spaeter
    gefundene Zahl nicht auf Codestand und Korpusversion zurueckfuehrbar --
    genau das musste bei Aufgabe 71 ueber Dateizeiten/git-diff rekonstruiert
    werden, weil es fehlte. Bestandsgroesse und gesetzte Schalter liefert
    bereits messparameter.schnappschuss() (nur importiert, nicht veraendert)."""
    solvable = sum(1 for c in cases if c["category"] != "negative")
    negative = sum(1 for c in cases if c["category"] == "negative")
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=SHARED_KNOWLEDGE, text=True,
            stderr=subprocess.DEVNULL).strip()
        schmutzig = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=SHARED_KNOWLEDGE, text=True,
            stderr=subprocess.DEVNULL).strip())
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        commit = None
        schmutzig = None
    return {
        "commit": commit,
        "arbeitsbaum_schmutzig": schmutzig,
        "korpus_datei": str(corpus_path.relative_to(SHARED_KNOWLEDGE)),
        "korpus_hash_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "korpus_gesamt": len(cases),
        "korpus_solvable": solvable,
        "korpus_negative": negative,
    }


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
    meta = laufmetadaten(cases, CORPUS)
    assert meta["korpus_gesamt"] == 45 and meta["korpus_solvable"] == 35 and meta["korpus_negative"] == 10
    assert len(meta["korpus_hash_sha256"]) == 64
    print("demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
        sys.exit(0)
    cases = load_cases()
    ergebnis = {"messlauf": messlauf(cases)}
    if "--eichung-only" not in sys.argv:
        ergebnis["eichung"] = eichung(cases)
    ergebnis["laufmetadaten"] = laufmetadaten(cases, CORPUS)
    try:
        import messparameter  # noqa: E402 -- nur gelesen (bestand/schalter), kern/ liegt schon im Suchpfad
        ergebnis["konfiguration"] = messparameter.schnappschuss()
    except ImportError:
        pass
    RESULT.parent.mkdir(exist_ok=True)
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\ngeschrieben: {RESULT}")
