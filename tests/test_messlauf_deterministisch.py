"""Aufgabe 68 (Linie D): Pruefkorpus-Lauf deterministisch machen.

Befund (gemessen 2026-08-15): hook.query() reicht `rand` an
hook._maybe_explore() durch, faellt ohne Argument auf ungeseedetes
random.random() zurueck. EXPLORE_RATE=0.15 ersetzt dann bei ~15% der
Aufrufe den schwaechsten Treffer durch einen anderen Kandidaten -- zwei
Laeufe desselben Standes koennen seither auseinandergehen. Direkt am realen
Signal geprueft: 200 Wuerfe mit rand=None ergaben 33x explore=True (~16.5%,
passt zu EXPLORE_RATE). Reihenfolge/Korpusgroesse/DB-Wachstum waren NICHT
die Ursache -- messlauf_abrufguete.py::load_cases() liest die Datei ohne
Shuffle, messe() zaehlt ohne Zufall.

Fix: kern/messlauf_abrufguete.py::_seeded_rand() seedet random.Random() aus
sha256(fall_text) und wird als `rand` an hook.query() durchgereicht -- der
Wuerfel haengt nur noch am Fall-Text, nicht mehr an Uhrzeit/Prozess.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import messlauf_abrufguete as m  # noqa: E402
import knowledge_recall_hook as hook  # noqa: E402


def _signal(n_gesamt=15, n_regular=10):
    signal = [{"path": f"/x/{i}", "score": i} for i in range(n_gesamt)]
    return signal[:n_regular], signal


def test_seeded_rand_liefert_gleiche_zahl_bei_gleichem_fall():
    task = "irgendein testfall-text, egal welcher"
    r1 = m._seeded_rand(task)
    r2 = m._seeded_rand(task)
    assert r1() == r2()


def test_seeded_rand_unterscheidet_faelle():
    r_a = m._seeded_rand("fall A")()
    r_b = m._seeded_rand("fall B")()
    # nicht zwingend verschieden (Kollision moeglich), hier aber der Fall --
    # haelt fest, dass der Seed wirklich am Text haengt, nicht an einer Konstante.
    assert r_a != r_b


def test_maybe_explore_mit_seed_reproduzierbar():
    """GRUEN: mit _seeded_rand() liefern zwei Aufrufe desselben Falls
    dasselbe Ergebnis -- Fix wirkt."""
    nodes, signal = _signal()
    task = "wiederholbarer testfall"
    out1 = hook._maybe_explore(list(nodes), signal, rand=m._seeded_rand(task), log_path=None)
    out2 = hook._maybe_explore(list(nodes), signal, rand=m._seeded_rand(task), log_path=None)
    assert [n.get("path") for n in out1] == [n.get("path") for n in out2]
    assert [n.get("explore") for n in out1] == [n.get("explore") for n in out2]


def test_maybe_explore_ohne_seed_kann_abweichen():
    """ROT-Probe: der Vorzustand (rand=None, wie vor dem Fix) liefert ueber
    viele Wuerfe beide moeglichen Ergebnisse -- Beleg, dass das Problem vor
    dem Fix real war und keine Annahme ist."""
    nodes, signal = _signal()
    ergebnisse = set()
    for _ in range(80):
        out = hook._maybe_explore(list(nodes), signal, rand=None, log_path=None)
        ergebnisse.add(tuple(n.get("path") for n in out))
    assert len(ergebnisse) > 1, (
        "unseeded random sollte ueber 80 Wuerfe abweichen (EXPLORE_RATE=0.15) -- "
        "wenn nicht, ist entweder die Rate 0 oder der Testaufbau falsch, nicht der Fund widerlegt"
    )


def test_run_case_nutzt_seeded_rand_nicht_none():
    """run_case() muss rand explizit setzen -- sonst greift der Fix nicht,
    weil hook.query() intern wieder auf random.random() zurueckfaellt."""
    import inspect
    quelle = inspect.getsource(m.run_case)
    assert "rand=" in quelle and "_seeded_rand" in quelle


def test_laufmetadaten_traegt_korpusteilung_und_hash():
    cases = m.load_cases()
    meta = m.laufmetadaten(cases, m.CORPUS)
    assert meta["korpus_gesamt"] == 45
    assert meta["korpus_solvable"] == 35
    assert meta["korpus_negative"] == 10
    assert meta["korpus_solvable"] + meta["korpus_negative"] == meta["korpus_gesamt"]
    assert len(meta["korpus_hash_sha256"]) == 64  # sha256 hexdigest


def demo() -> None:
    test_seeded_rand_liefert_gleiche_zahl_bei_gleichem_fall()
    test_seeded_rand_unterscheidet_faelle()
    test_maybe_explore_mit_seed_reproduzierbar()
    test_maybe_explore_ohne_seed_kann_abweichen()
    test_run_case_nutzt_seeded_rand_nicht_none()
    test_laufmetadaten_traegt_korpusteilung_und_hash()
    print("demo ok")


if __name__ == "__main__":
    demo()
