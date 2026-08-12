"""Der Zahlenmelder haengt wirklich am Stop-Haltepunkt -- und bleibt dort.

Gleicher Grund wie tests/test_normbezug_verdrahtung.py: der Aufruf in
antwort_abruf.py::modus_stop faengt jede Ausnahme und schweigt (ein Absturz
darf den Abruf, die eigentliche Aufgabe des Hooks, nicht mitreissen). Genau
deshalb kann die Verdrahtung lautlos ausfallen -- ein Umbenennen in
zahlenbezug.py, ein Importfehler -- und nichts wuerde auffallen.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import subprocess
import sys
from pathlib import Path

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


def test_unbelegte_zahl_wird_am_stop_gemeldet(tmp_path):
    text = ("Ich habe die Temperaturkurve modelliert, nicht gemessen. "
            "Jahresmittel und Amplitude stammen aus meinem Modellwissen, "
            "gekennzeichnet als Annahme.")
    aus = _stop(tmp_path, text)
    assert "ZAHL AUS ANNAHME/MODELLWISSEN" in aus, f"Melder schwieg: {aus!r}"


def test_zahl_aus_quelle_erzeugt_keine_meldung(tmp_path):
    text = ("Ausgangslage 2026-08-12T12:00, selbst gemessen: 863 passed, "
            "1 skipped, 7 xfailed, 0 failed.")
    aus = _stop(tmp_path, text)
    assert "ZAHL AUS ANNAHME/MODELLWISSEN" not in aus, aus


def test_ohne_annahme_keine_meldung(tmp_path):
    aus = _stop(tmp_path, "Der Melder aendert nichts an gewoehnlichem Text.")
    assert "ZAHL AUS ANNAHME/MODELLWISSEN" not in aus


def test_melder_bricht_den_hook_nicht(tmp_path):
    """Der Hook muss auch dann sauber enden, wenn zahlenbezug.py nicht
    importierbar ist -- das ist der Grund fuer das stille except."""
    text = ("Ich habe die Temperaturkurve modelliert, nicht gemessen, "
            "gekennzeichnet als Annahme.")
    payload = json.dumps({"transcript_path": str(_transcript(tmp_path, text)),
                          "session_id": "s"})
    r = subprocess.run([sys.executable, str(HAKEN), "--stop"],
                       input=payload, capture_output=True, text=True,
                       cwd=str(tmp_path))  # anderes cwd -> Import kann scheitern
    assert r.returncode == 0
