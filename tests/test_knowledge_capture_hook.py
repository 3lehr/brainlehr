#!/usr/bin/env python3
"""Selbsttest fuer knowledge_capture_hook.py, `python3 hub/scripts/test_knowledge_capture_hook.py`.

Auftrag 2026-08-07: Hook fragte bisher nur nach Fehlschlaegen (Bestand 243
antipattern/97 error gegen 79 pattern). Zweite Frage nach nicht-offensicht-
lichem Erfolg ergaenzt, OHNE Frage 1 zu verdraengen. Dieser Test belegt:
beide Fragen stehen woertlich im Text, Frage 1 bleibt vor Frage 2 und
unverkuerzt, der Block bleibt 1x/Session und schleifenfest, und eine Session
ohne genug Edits blockt gar nicht (kein erfundenes Pattern aus Nichts).

Rot-Probe (im Auftrag verlangt): _INSTRUCTION auf die alte Ein-Fragen-Fassung
zuruecksetzen -> ERFOLGS-FRAGE wird rot. MIN_EDITS-Check aus main() entfernen
-> NEGATIVFALL wird rot.

Nachtrag 2026-08-07: Erfolgsfrage forderte Reihenfolge/Voraussetzung nicht
ausdruecklich ein ('mehrschrittige Aufgabe' war nur eines von drei Beispielen).
Jetzt verlangt der Text woertlich REIHENFOLGE der Schritte UND VORAUSSETZUNG,
sonst gilt es als Beobachtung, keine Anleitung. Rot-Probe: REIHENFOLGE/
VORAUSSETZUNG streichen -> REIHENFOLGE-VORAUSSETZUNG wird rot.
"""
import io
import importlib.util
import json
import pathlib
import sys
import tempfile

HUB = pathlib.Path(__file__).resolve().parent.parent
# Die Automatik liegt seit dem 2026-08-08 in brainlehr/haken, nicht in
# hub/scripts — der Test folgt ihr.
HOOK_PATH = HUB / "haken" / "knowledge_capture_hook.py"

_spec = importlib.util.spec_from_file_location("knowledge_capture_hook", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _run(td: str, payload: dict) -> str:
    hook.TMP = td
    stdin_bak, stdout_bak = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(json.dumps(payload))
    sys.stdout = out = io.StringIO()
    try:
        hook.main()
    finally:
        sys.stdin, sys.stdout = stdin_bak, stdout_bak
    return out.getvalue()


def _dirty(td: str, sid: str, n: int) -> None:
    (pathlib.Path(td) / f"claude_know_{sid}.dirty").write_text(str(n))


def beide_fragen_woertlich_vorhanden() -> str:
    assert "FEHLSCHLAG" in hook._INSTRUCTION, "Frage 1 fehlt"
    assert "ERFOLG" in hook._INSTRUCTION, "Frage 2 fehlt"
    pos1, pos2 = hook._INSTRUCTION.find("FEHLSCHLAG"), hook._INSTRUCTION.find("ERFOLG")
    assert pos1 < pos2, "Erfolgsfrage steht vor der Fehlschlagsfrage -- verdraengt sie"
    assert "zusätzlich" in hook._INSTRUCTION, "Frage 2 nicht ausdruecklich als Zusatz markiert"
    assert "kein Pattern erfinden" in hook._INSTRUCTION, "Sperrklausel gegen erfundene Pattern fehlt"
    return f"Frage 1 vor Frage 2, als Zusatz markiert, Sperrklausel vorhanden ({len(hook._INSTRUCTION)} Zeichen)"


def erfolgsfrage_erzwingt_reihenfolge_und_voraussetzung() -> str:
    """Auftrag 2026-08-07 Teil 2: 'mehrschrittige Aufgabe' als eines von drei
    Beispielen reichte nicht -- ein Verfahren ohne Reihenfolge ist eine
    Beobachtung, keine Anleitung. Rot-Probe: REIHENFOLGE/VORAUSSETZUNG aus
    _INSTRUCTION streichen -> dieser Test wird rot, waehrend
    beide_fragen_woertlich_vorhanden weiter gruen bliebe (die alte Fassung
    haette diese Luecke nicht gefunden)."""
    assert "REIHENFOLGE" in hook._INSTRUCTION, "Reihenfolge wird nicht eingefordert"
    assert "VORAUSSETZUNG" in hook._INSTRUCTION, "Voraussetzung wird nicht eingefordert"
    assert hook._INSTRUCTION.find("REIHENFOLGE") < hook._INSTRUCTION.find("Nur eintragen"), \
        "Reihenfolge-Forderung steht nicht in der Erfolgsfrage selbst"
    assert len(hook._INSTRUCTION) <= 1190, f"_INSTRUCTION ueber Obergrenze: {len(hook._INSTRUCTION)}"
    return f"Erfolgsfrage erzwingt Reihenfolge+Voraussetzung, {len(hook._INSTRUCTION)} Zeichen (Obergrenze 1190)"


def block_bei_genug_edits() -> str:
    with tempfile.TemporaryDirectory() as td:
        sid = "sessA"
        _dirty(td, sid, hook.MIN_EDITS)
        out = _run(td, {"session_id": sid})
        data = json.loads(out)
        assert data["decision"] == "block", data
        assert "FEHLSCHLAG" in data["reason"] and "ERFOLG" in data["reason"], data
        return "genug Edits -> block mit beiden Fragen im reason-Text"


def negativfall_zu_wenig_edits_kein_block() -> str:
    """Session ohne nennenswerte Arbeit darf keine erfundene Faehigkeit erzwingen."""
    with tempfile.TemporaryDirectory() as td:
        sid = "sessB"
        _dirty(td, sid, hook.MIN_EDITS - 1)
        out = _run(td, {"session_id": sid})
        assert out == "", f"blockte trotz zu weniger Edits: {out!r}"
        return "zu wenig Edits -> kein Block, keine erzwungene Faehigkeit"


def einmal_je_session_dann_still() -> str:
    with tempfile.TemporaryDirectory() as td:
        sid = "sessC"
        _dirty(td, sid, hook.MIN_EDITS)
        erster = _run(td, {"session_id": sid})
        assert json.loads(erster)["decision"] == "block"
        zweiter = _run(td, {"session_id": sid})
        assert zweiter == "", f"blockte ein zweites Mal: {zweiter!r}"
        return "1. Stop blockt, 2. Stop derselben Session bleibt still (Marker haelt)"


def stop_hook_active_verhindert_schleife() -> str:
    with tempfile.TemporaryDirectory() as td:
        sid = "sessD"
        _dirty(td, sid, hook.MIN_EDITS)
        out = _run(td, {"session_id": sid, "stop_hook_active": True})
        assert out == "", f"stop_hook_active ignoriert: {out!r}"
        return "stop_hook_active=True -> sofort still, keine Schleife"


def main() -> None:
    checks = [
        ("TEXT", beide_fragen_woertlich_vorhanden),
        ("REIHENFOLGE-VORAUSSETZUNG", erfolgsfrage_erzwingt_reihenfolge_und_voraussetzung),
        ("BLOCK", block_bei_genug_edits),
        ("NEGATIVFALL", negativfall_zu_wenig_edits_kein_block),
        ("EINMAL-JE-SESSION", einmal_je_session_dann_still),
        ("ENDLOSSCHUTZ", stop_hook_active_verhindert_schleife),
    ]
    for label, fn in checks:
        beleg = fn()
        print(f"[{label}] {beleg}")
    print("test_knowledge_capture_hook: alle Zusicherungen halten")


if __name__ == "__main__":
    main()


def test_selbsttest_laeuft_durch():
    """Diese Datei war ein Selbsttest zum Aufrufen von Hand und lag in
    hub/scripts. In tests/ sammelt pytest sie nur ein, wenn eine Funktion
    test_* heisst — sonst zaehlt sie als gruen, ohne je gelaufen zu sein.
    Der Aufruf hier macht aus der Ablage wieder eine Pruefung."""
    main()
