"""Die Kaskaden-Wache muss wissen, WER vor ihr sitzt.

GEPRUEFTE DATEI, und sie liegt NICHT in diesem Repo:
`hub/scripts/cascade_guard_hook.py`, versioniert im hub (zuletzt 14d4f3763).
Dass sie dort unter Versionskontrolle steht, ist der Unterschied zum Fall
`caveman_policy.json` -- die war untracked, und deshalb wurde dort NICHT
geaendert, sondern nur markiert (L-54b09d). Hier ist beides moeglich.

BEFUND, der diesen Test veranlasst (2026-08-11, Betreiberweisung):
Die Wache blockt Code-Edits im Hauptfaden und verweist auf die Kaskaden-Regel
-- ihr eigener Kopfkommentar begruendet sie mit "Der SONNET-Hauptfaden
delegiert Code-Aenderungen an Sonnet-Subagenten (Kontext-Isolation, nicht
Modell-Ersparnis)". Die Voraussetzung ist das schwaechere Orchestratormodell.

Laeuft der Hauptfaden auf Opus 5, faellt diese Voraussetzung weg. Genau
dieselbe Ausnahme hat der Betreiber am 2026-08-04T05:44:04+0200 schon einmal
getroffen, fuer die Fuenf-Fragen-Liste in der globalen CLAUDE.md ("Gilt nicht
fuer Opus 5 ... eine zusaetzliche Aufforderung erzeugt Ueber-Verifikation").
Dieser Test zieht die Wache auf denselben Stand.

Der Hook-Eingabe fehlt ein Modellfeld -- gemessen am Protokoll
/tmp/cascade-guard-debug.jsonl, das session_id, transcript_path, cwd,
permission_mode und effort traegt, aber kein model. Die Wache muss es sich
also aus dem Transkript holen, auf das transcript_path zeigt.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "tests"))

from conftest import HUB  # noqa: E402

GUARD = (HUB / "scripts" / "cascade_guard_hook.py") if HUB else None

if GUARD is None or not GUARD.exists():
    pytest.skip("cascade_guard_hook.py liegt im hub, der hier nicht vorhanden ist",
                allow_module_level=True)


def _transkript(tmp_path: Path, modell: str | None) -> Path:
    """Ein Transkript, wie der Klient es schreibt -- Modell in der assistant-Zeile."""
    p = tmp_path / "transkript.jsonl"
    zeilen = [{"type": "user", "message": {"role": "user", "content": "bau das"}}]
    if modell is not None:
        zeilen.append({"type": "assistant",
                       "message": {"role": "assistant", "model": modell,
                                   "content": [{"type": "text", "text": "ja"}]}})
    p.write_text("\n".join(json.dumps(z) for z in zeilen) + "\n", encoding="utf-8")
    return p


def _frage(tmp_path: Path, modell: str | None, datei: str = "/Volumes/daten/Begod2026/beispiel/kern.py") -> dict:
    """Ruft die Wache ueber ihre echte Schnittstelle auf: JSON auf stdin."""
    eingabe = {
        "session_id": "test", "hook_event_name": "PreToolUse",
        "transcript_path": str(_transkript(tmp_path, modell)),
        "cwd": "/Volumes/daten/Begod2026/beispiel", "tool_name": "Edit",
        "tool_input": {"file_path": datei},
    }
    lauf = subprocess.run(
        [sys.executable, str(GUARD)], input=json.dumps(eingabe),
        capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin",
             "CLAUDE_CASCADE_GUARD_LOG": str(tmp_path / "log.jsonl"),
             # Eigener Marker-Pfad: sonst verbraucht dieser Testlauf die
             # Einmal-Ausnahme des echten Fadens -- und faerbt sich selbst gruen.
             "CLAUDE_CASCADE_GUARD_MARKER": str(tmp_path / "marker")},
    )
    if not lauf.stdout.strip():
        return {}
    return json.loads(lauf.stdout)


def _blockt(antwort: dict) -> bool:
    hso = antwort.get("hookSpecificOutput") or {}
    return hso.get("permissionDecision") == "deny"


def test_sonnet_wird_weiter_gebremst(tmp_path):
    """Die Regel bleibt in Kraft, wo ihre Voraussetzung zutrifft.

    Ohne diese Zusicherung waere die Aenderung ein ersatzloses Abschalten --
    und die Kontext-Isolation, fuer die die Wache gebaut wurde, faellt weg."""
    assert _blockt(_frage(tmp_path, "claude-sonnet-5")), \
        "Sonnet-Hauptfaden muss weiterhin an Subagenten delegieren"


def test_opus5_darf_selbst_editieren(tmp_path):
    """Der eigentliche Zweck dieser Aenderung."""
    assert not _blockt(_frage(tmp_path, "claude-opus-5")), \
        "Opus 5 traegt die Voraussetzung der Kaskaden-Regel nicht"


def test_unbekanntes_modell_bremst(tmp_path):
    """NEGATIVFALL, und die Richtung ist Absicht: Wer das Modell nicht kennt,
    darf nicht das Schutzlose annehmen. Die Wache ist sonst fail-open --
    hier NICHT, denn ein unlesbares Transkript waere sonst der bequemste Weg,
    sie loszuwerden."""
    assert _blockt(_frage(tmp_path, None)), \
        "ohne erkennbares Modell bleibt es beim Delegieren"
    assert _blockt(_frage(tmp_path, "irgendein-fremdes-modell")), \
        "ein unbekannter Modellname ist kein Freibrief"


def test_grenzfall_opus4_bleibt_gebremst(tmp_path):
    """GRENZWERT: Die Ausnahme gilt Opus FUENF, nicht jedem Opus.

    Ein Praefix-Vergleich auf 'opus' waere der naheliegende Fehlgriff und
    wuerde aeltere Opus-Staende mitnehmen, fuer die der Betreiberbeschluss
    vom 2026-08-04 nicht gilt."""
    assert _blockt(_frage(tmp_path, "claude-opus-4-20250514")), \
        "der Beschluss nennt Opus 5, nicht Opus 4"


def test_modellwechsel_mitten_in_der_sitzung_zaehlt_der_letzte(tmp_path):
    """Ein Faden kann das Modell per /model wechseln. Gilt der letzte Stand?

    Ohne diese Zusicherung waere die Erkennung von der Reihenfolge im
    Transkript abhaengig, und ein einziger Opus-Zug am Sitzungsanfang wuerde
    einen danach auf Sonnet umgestellten Faden dauerhaft freistellen."""
    p = tmp_path / "transkript.jsonl"
    p.write_text("\n".join(json.dumps(z) for z in [
        {"type": "assistant", "message": {"role": "assistant", "model": "claude-opus-5",
                                          "content": [{"type": "text", "text": "a"}]}},
        {"type": "assistant", "message": {"role": "assistant", "model": "claude-sonnet-5",
                                          "content": [{"type": "text", "text": "b"}]}},
    ]) + "\n", encoding="utf-8")
    eingabe = {
        "session_id": "test", "hook_event_name": "PreToolUse",
        "transcript_path": str(p), "cwd": "/Volumes/daten/Begod2026/beispiel",
        "tool_name": "Edit",
        "tool_input": {"file_path": "/Volumes/daten/Begod2026/beispiel/kern.py"},
    }
    lauf = subprocess.run(
        [sys.executable, str(GUARD)], input=json.dumps(eingabe),
        capture_output=True, text=True, timeout=30,
        env={"PATH": "/usr/bin:/bin",
             "CLAUDE_CASCADE_GUARD_LOG": str(tmp_path / "log.jsonl"),
             "CLAUDE_CASCADE_GUARD_MARKER": str(tmp_path / "marker")},
    )
    antwort = json.loads(lauf.stdout) if lauf.stdout.strip() else {}
    assert _blockt(antwort), "nach dem Wechsel auf Sonnet muss wieder gebremst werden"


def test_nichtcode_bleibt_frei(tmp_path):
    """GEGENPROBE: Das bisherige Verhalten fuer Nicht-Code darf sich nicht
    aendern -- sonst misst der Test die falsche Sache."""
    assert not _blockt(_frage(tmp_path, "claude-sonnet-5", datei="/Volumes/daten/Begod2026/beispiel/notiz.md"))
