"""Duenner pytest-Wrapper um pflege/wissenskorpus_einlesweg.py::_selftest().
Der Selbsttest selbst traegt die Assertions (rot vor gruen, Pflichten 1-3,
Gegenprobe, Bruecke, Fachbestand-Blocker, Doppellauf) -- dieser Test macht ihn
nur ueber `pytest` auffindbar, wie tests/test_pruefkorpus.py es fuer
kern/pruefkorpus.py._selftest() bereits tut."""
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "pflege"))

import wissenskorpus_einlesweg as w  # noqa: E402


def test_selftest():
    w._selftest()
