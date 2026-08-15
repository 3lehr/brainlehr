"""Test fuer haken/agentenanker_abruf.py + haken/agentenanker_einspielung.py.

Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung.

Rot-vor-gruen-Beleg fuer die Bruecke ueber die Pending-Datei: das Ziel ist
NICHT, dass eine SubagentStart-Antwort irgendetwas ausgibt, sondern dass sie
GENAU DANN etwas ausgibt, wenn der vorangehende PreToolUse:Agent-Aufruf
(gleiche session_id) einen echten Bau-Auftrag mit Ankertreffer sah -- und
sonst still bleibt.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "haken"))

import agentenanker_abruf as abruf  # noqa: E402
import agentenanker_einspielung as einspielung  # noqa: E402


def test_selftests_bestehen():
    assert abruf._selftest() == 0
    assert einspielung._selftest() == 0


def test_kein_bausignal_bleibt_still(monkeypatch, tmp_path):
    pending = tmp_path / "pending.jsonl"
    monkeypatch.setattr(abruf, "PENDING", pending)
    eingabe = {"tool_input": {"prompt": "Erklaere mir, wie kern/ausweis.py funktioniert."},
               "session_id": "s-lesen", "cwd": str(_w)}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(eingabe)))
    abruf.main()
    assert not pending.exists()


def test_bau_auftrag_mit_treffer_erreicht_subagenten(monkeypatch, tmp_path):
    """Rot vor gruen: OHNE den PreToolUse-Aufruf (unten auskommentiert
    gedacht) gaebe es keine Pending-Zeile und SubagentStart bliebe still --
    ERST der PreToolUse-Aufruf erzeugt die Zeile, die SubagentStart danach
    findet. Das ist die eigentliche Behauptung dieses Tests, nicht nur
    'main() liefert irgendwas'."""
    pending = tmp_path / "pending.jsonl"
    monkeypatch.setattr(abruf, "PENDING", pending)
    monkeypatch.setattr(einspielung, "PENDING", pending)

    # Vorher: SubagentStart ohne vorangegangenen PreToolUse-Lauf -> still.
    buf_vorher = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"session_id": "s-bau", "hook_event_name": "SubagentStart"})))
    with redirect_stdout(buf_vorher):
        einspielung.main()
    assert buf_vorher.getvalue() == ""

    # PreToolUse:Agent mit echtem Anker (die Datei existiert im Repo).
    prompt = ("Baue eine Existenzprobe fuer Agentenauftraege. Lege die Datei "
              "unter haken/existenzpruefung.py an.")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_input": {"prompt": prompt}, "session_id": "s-bau", "cwd": str(_w)})))
    abruf.main()
    assert pending.exists()

    # Danach: SubagentStart derselben Sitzung liefert additionalContext.
    buf_danach = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"session_id": "s-bau", "hook_event_name": "SubagentStart"})))
    with redirect_stdout(buf_danach):
        einspielung.main()
    ausgabe = json.loads(buf_danach.getvalue())
    ctx = ausgabe["hookSpecificOutput"]["additionalContext"]
    assert "haken/existenzpruefung.py" in ctx
    assert ausgabe["hookSpecificOutput"]["hookEventName"] == "SubagentStart"


def test_fremde_sitzung_bekommt_nichts(monkeypatch, tmp_path):
    pending = tmp_path / "pending.jsonl"
    monkeypatch.setattr(abruf, "PENDING", pending)
    monkeypatch.setattr(einspielung, "PENDING", pending)
    prompt = "Baue etwas in haken/existenzpruefung.py."
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"tool_input": {"prompt": prompt}, "session_id": "eigene", "cwd": str(_w)})))
    abruf.main()

    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"session_id": "andere-sitzung", "hook_event_name": "SubagentStart"})))
    with redirect_stdout(buf):
        einspielung.main()
    assert buf.getvalue() == ""
