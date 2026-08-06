"""Regressionsnetz fuer paretolauf.py (Pareto-Front Recall@5 vs. Fehlalarm).
Ruft nur dessen eigenen selftest() -- der deckt Pareto-Mechanik, Determinismus
(gleicher/verschiedener sampler_seed) und Kein-Modell/Netz-Zusicherung ab."""
from __future__ import annotations

import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent.parent
PRUEFSTAND = SHARED_KNOWLEDGE / "pruefstand"
sys.path.insert(0, str(PRUEFSTAND))

import paretolauf  # type: ignore  # noqa: E402


def test_paretolauf_selftest():
    paretolauf.selftest()


def test_pareto_front_indices_dominance():
    # eigenstaendig, ohne Optuna: klare geometrische Faelle.
    assert paretolauf.pareto_front_indices([(0.9, 0.1), (0.5, 0.5)]) == [0]
    assert set(paretolauf.pareto_front_indices([(0.9, 0.9), (0.1, 0.1)])) == {0, 1}


def test_assert_valid_front_catches_bad_front():
    try:
        paretolauf.assert_valid_front([(0.5, 0.5), (0.9, 0.1)])
    except AssertionError:
        return
    raise AssertionError("assert_valid_front haette den dominierten Punkt (0.5,0.5) melden muessen")
