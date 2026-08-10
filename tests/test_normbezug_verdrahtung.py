"""Der Normmelder haengt wirklich am Stop-Haltepunkt -- und bleibt dort.

WARUM DIESER TEST PFLICHT IST, nicht Kuer: _normbezug_melden() faengt JEDE
Ausnahme und schweigt (bewusst -- ein Absturz wuerde den Abruf mitreissen, der
die eigentliche Aufgabe des Hooks ist). Genau deshalb kann die Verdrahtung
lautlos ausfallen: ein Umbenennen in normbezug.py, ein Importfehler, ein
geaenderter Rueckgabewert -- nichts davon wuerde auffallen. Ein stiller Melder
ist schlimmer als keiner, weil man sich auf ihn verlaesst.

Fehlklasse: gebautes Werkzeug ohne Verdrahtung (Knoten 92e31dfe, "nicht
fehlendes Tooling, sondern fehlende Verdrahtung").
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parent.parent
HAKEN = SHARED_KNOWLEDGE / "haken" / "antwort_abruf.py"


def _transcript(tmp_path: Path, text: str) -> Path:
    t = tmp_path / "transcript.jsonl"
    zeilen = [
        {"type": "user", "message": {"role": "user", "content": "frage"}},
        {"type": "assistant", "message": {"role": "assistant",
         "content": [{"type": "text", "text": text + " Fuelltext. " * 40}]}},
    ]
    t.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return t


def _stop(tmp_path: Path, text: str) -> str:
    payload = json.dumps({"transcript_path": str(_transcript(tmp_path, text)),
                          "session_id": "testsess"})
    r = subprocess.run([sys.executable, str(HAKEN), "--stop"],
                       input=payload, capture_output=True, text=True,
                       cwd=str(SHARED_KNOWLEDGE))
    return r.stdout


@pytest.mark.parametrize("zitat,erwartet", [
    ("Geprueft nach ISO 99999-1.", "ISO 99999-1"),
    ("Laut ADR-999 ist das beschlossen.", "ADR-999"),
    ("Siehe L-ffffff dazu.", "L-ffffff"),
])
def test_unbelegtes_zitat_wird_am_stop_gemeldet(tmp_path, zitat, erwartet):
    """Drei Bauformen, alle erfunden: technische Norm, ADR, Lehre."""
    aus = _stop(tmp_path, zitat)
    assert "NORMBEZUG OHNE BELEG" in aus, f"Melder schwieg bei {zitat!r}"
    assert erwartet in aus


def test_belegtes_zitat_erzeugt_keine_meldung(tmp_path):
    """Gegenprobe: ein Melder, der auch bei Ordnung spricht, wird
    abgeschaltet. Ohne diese Probe waere ein 'melde immer' genauso gruen."""
    aus = _stop(tmp_path, "Nach Art. 6 Abs. 1 lit. f DSGVO zulaessig.")
    assert "NORMBEZUG OHNE BELEG" not in aus, aus


def test_ohne_zitat_keine_meldung(tmp_path):
    aus = _stop(tmp_path, "Der Melder aendert nichts an gewoehnlichem Text.")
    assert "NORMBEZUG" not in aus


def test_melder_bricht_den_hook_nicht(tmp_path, monkeypatch):
    """Der Hook muss auch dann sauber enden, wenn normbezug.py kaputt ist --
    das ist der Grund fuer das stille except, und zugleich der Grund, warum es
    diesen Test braucht."""
    payload = json.dumps({"transcript_path": str(
        _transcript(tmp_path, "Laut ADR-999 beschlossen.")), "session_id": "s"})
    r = subprocess.run([sys.executable, str(HAKEN), "--stop"],
                       input=payload, capture_output=True, text=True,
                       cwd=str(tmp_path))  # anderes cwd -> Import kann scheitern
    assert r.returncode == 0
