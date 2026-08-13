"""Rot-vor-gruen-Test fuer haken/stand_format_waechter_hook.py (Aufgabe 103).

Deckt: Ueberschreitung meldet mit Ist/Soll, Grenzwert (genau 10 erlaubt, 11
nicht mehr), Negativfall (Format eingehalten -> keine Meldung), und dass der
Haken nur bei STAND.md reagiert (andere Datei -> keine Meldung).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "haken" / "stand_format_waechter_hook.py"


def _lauf(pfad: str) -> dict:
    eingabe = json.dumps({"tool_input": {"file_path": pfad}})
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=eingabe,
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0, f"Haken muss immer exit 0 liefern, war {p.returncode}"
    return {"stdout": p.stdout.strip(), "proc": p}


def _schreibe(tmp_path: Path, name: str, zeilen: int) -> Path:
    datei = tmp_path / name
    datei.write_text("\n".join(f"Zeile {i}" for i in range(1, zeilen + 1)) + "\n")
    return datei


def test_ueberschreitung_meldet_ist_und_soll(tmp_path):
    datei = _schreibe(tmp_path, "STAND.md", 11)  # eine Zeile zu viel
    out = _lauf(str(datei))["stdout"]
    assert out, "Bei 11 Zeilen (Pflichtformat 10) MUSS eine Meldung kommen"
    daten = json.loads(out)
    text = daten["hookSpecificOutput"]["additionalContext"]
    assert "11" in text and "10" in text, text


def test_negativfall_im_format_meldet_nicht(tmp_path):
    datei = _schreibe(tmp_path, "STAND.md", 8)
    out = _lauf(str(datei))["stdout"]
    assert out == "", f"Datei im Format darf keine Meldung ausloesen, war: {out!r}"


def test_grenzwert_genau_erlaubt(tmp_path):
    datei = _schreibe(tmp_path, "STAND.md", 10)
    out = _lauf(str(datei))["stdout"]
    assert out == "", f"Genau 10 Zeilen sind erlaubt, war: {out!r}"


def test_grenzwert_eine_mehr_meldet(tmp_path):
    datei = _schreibe(tmp_path, "STAND.md", 11)
    out = _lauf(str(datei))["stdout"]
    assert out != "", "11 Zeilen (eine mehr als erlaubt) MUSS melden"


def test_andere_datei_wird_ignoriert(tmp_path):
    datei = _schreibe(tmp_path, "ANDERE.md", 999)
    out = _lauf(str(datei))["stdout"]
    assert out == "", f"Nur STAND.md darf melden, war: {out!r}"


def test_rot_probe_ohne_pruefung_waere_immer_still(tmp_path):
    """Gegenprobe zur Rot-vor-gruen-Pflicht: ein Haken, der nie prueft
    (LIMIT auf unendlich gesetzt), wuerde test_ueberschreitung nicht
    bestehen -- das belegt, dass der Test die echte Pruefung trifft,
    nicht nur den JSON-Rahmen."""
    quelltext = HOOK.read_text(encoding="utf-8")
    kaputt = quelltext.replace("LIMIT = 10", "LIMIT = 10**9")
    kaputter_haken = tmp_path / "kaputter_hook.py"
    kaputter_haken.write_text(quelltext.replace(quelltext, kaputt), encoding="utf-8")

    datei = _schreibe(tmp_path, "STAND.md", 11)
    eingabe = json.dumps({"tool_input": {"file_path": str(datei)}})
    p = subprocess.run(
        [sys.executable, str(kaputter_haken)],
        input=eingabe,
        capture_output=True,
        text=True,
    )
    assert p.stdout.strip() == "", "Rot-Probe: ohne Pruefung darf nichts melden"
