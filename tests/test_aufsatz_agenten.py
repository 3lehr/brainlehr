"""Der erste Aufsatz — und die Zusicherung, die ihn zum Aufsatz macht.

Ein Aufsatz darf ausfallen, ohne dass etwas anderes mitfaellt. Das ist hier
kein Vorsatz, sondern gepruefte Eigenschaft: ohne Register meldet er das und
endet mit einem Fehlercode, statt zu raten oder etwas zu schreiben.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL / "aufsaetze"))

import agenten  # type: ignore  # noqa: E402


def _register(tmp_path: Path, zeilen: list[dict]) -> Path:
    p = tmp_path / "register.jsonl"
    p.write_text("\n".join(json.dumps(z) for z in zeilen), encoding="utf-8")
    return p


def test_zaehlt_starts_nicht_stopps(tmp_path):
    """Der Vorbehalt aus dem Bericht als Zusicherung: im echten Register
    standen 169 Starts gegen 411 Stopps. Wer Stopps mitzaehlt, meldet
    doppelt so viele Laeufe wie es gab."""
    p = _register(tmp_path, [
        {"ev": "start", "agent_type": "a", "ts": 1_780_000_000, "model": "sonnet"},
        {"ev": "stop", "agent_type": "a", "ts": 1_780_000_100},
        {"ev": "stop", "agent_type": "a", "ts": 1_780_000_200},
        {"ev": "file", "agent_type": "a", "ts": 1_780_000_150, "file": "x.py"},
    ])
    erg = agenten.auswerten(agenten.lies_register(p), None)
    assert erg["laeufe"]["a"] == 1
    assert erg["dateien"]["a"] == 1
    assert (erg["starts"], erg["stops"]) == (1, 2)


def test_nie_ausgeloeste_werden_benannt(tmp_path):
    """Die eigentliche Frage des Betreibers braucht einen Nenner: nicht
    'wie oft lief einer', sondern 'wie viele liefen ueberhaupt nie'."""
    ordner = tmp_path / "agents"
    ordner.mkdir()
    for name in ("laeuft", "liegt_brach"):
        (ordner / f"{name}.md").write_text("x", encoding="utf-8")
    gefunden = agenten.definierte([ordner])
    assert set(gefunden) == {"laeuft", "liegt_brach"}

    p = _register(tmp_path, [{"ev": "start", "agent_type": "laeuft", "ts": 1_780_000_000}])
    erg = agenten.auswerten(agenten.lies_register(p), None)
    nie = set(gefunden) - set(erg["laeufe"])
    assert nie == {"liegt_brach"}


def test_kaputte_zeile_kippt_die_auswertung_nicht(tmp_path):
    p = tmp_path / "register.jsonl"
    p.write_text('{"ev":"start","agent_type":"a","ts":1780000000}\nkein json\n{}\n',
                 encoding="utf-8")
    erg = agenten.auswerten(agenten.lies_register(p), None)
    assert erg["laeufe"]["a"] == 1


def test_ohne_register_faellt_nur_der_aufsatz_aus(tmp_path, capsys):
    """Die Zusicherung, die ihn zum Aufsatz macht."""
    rc = agenten.main(["--register", str(tmp_path / "gibtsnicht.jsonl")])
    assert rc == 1
    assert "nichts anderes faellt mit" in capsys.readouterr().out
