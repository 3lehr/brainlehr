"""Vektorstand haengt seit 2026-08-15 nicht an ~/.claude/settings.json, sondern
an melder/pruefer.py::alle() -- pruefer.py selbst ist schon per SessionStart
verdrahtet (siehe SOLLEN_LAUFEN in test_melder_verdrahtung.py), also erbt jeder
in alle() aufgerufene Melder dieselbe Verdrahtung, ohne eine zweite,
verlierbare settings.json-Zeile zu brauchen (L-083b95: dort verschwand ein
Haken 36 Minuten nach dem Commit wieder).

DIESE PROBE FRAGT DIE WIRKLICHKEIT AB, NICHT DIE ABSICHT: sie ruft
pruefer.alle() wirklich auf (gegen die echte, lesend geoeffnete Datenbank) und
prueft, ob vektorstand.melden() TATSAECHLICH mitgelaufen ist -- durch
Monkeypatch auf einen erkennbaren Rueckgabewert, nicht durch Textsuche im
Quellcode. Eine Zeile 'import vektorstand' beweist nichts; der Aufruf muss
im Ergebnis auftauchen.
"""
from __future__ import annotations

import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "melder"), str(_w / "kern"), str(_w / "haken")]

import pruefer  # noqa: E402
import vektorstand  # noqa: E402


def test_pruefer_ruft_vektorstand_melden_wirklich_auf(monkeypatch):
    sentinel = {
        "pruefung": "vektorstand:testkanarie",
        "befund": "kanarie",
        "fehlklasse": "test",
        "fehlalarm_kostet": "test",
    }
    monkeypatch.setattr(vektorstand, "melden", lambda conn=None: sentinel)

    conn = pruefer._verbindung()
    try:
        funde = pruefer.alle(conn)
    finally:
        conn.close()

    assert sentinel in funde, (
        "pruefer.alle() hat vektorstand.melden() nicht aufgerufen -- die Verdrahtung "
        "ist eine Textzeile geblieben, kein wirksamer Aufruf")


def test_negativfall_sauberer_bestand_meldet_nichts_ueber_vektorstand(monkeypatch):
    """Gegenprobe: liefert vektorstand.melden() None (sauberer Bestand), taucht
    kein vektorstand-Fund in pruefer.alle() auf."""
    monkeypatch.setattr(vektorstand, "melden", lambda conn=None: None)

    conn = pruefer._verbindung()
    try:
        funde = pruefer.alle(conn)
    finally:
        conn.close()

    assert not any(f.get("pruefung", "").startswith("vektorstand") for f in funde)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
