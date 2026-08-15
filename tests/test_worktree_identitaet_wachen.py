#!/usr/bin/env python3
"""Rot-vor-gruen fuer den Nachtrag 2026-08-15 an haken/worktree_identitaet.py.

DER BEFUND (runs/haken_bei_agenten_2026-08-15T142000+0200.json): Ein
Arbeitsbaum bekam beim Anlegen eine settings.json-Kopie. Eine Wache, die
der Hauptbaum SPAETER dazubekam (`stash_guard_hook.py`, PreToolUse), hat
diesen Arbeitsbaum nie erreicht -- die alte Regel kopierte nur, wenn im
Ziel noch KEINE settings.json lag. `git stash` lief in genau diesem Baum
mit EXIT=0 durch, waehrend der Hauptbaum ihn schon ablehnte.

ROT-PROBE: Mit dem Stand vor diesem Nachtrag (`_identitaet_nachziehen` kopiert
settings.json nur bei `not ziel.exists()`) bleibt `test_stale_wache_wird_nachgezogen`
unten rot -- die zweite Wache fehlt im Ziel, weil das Ziel schon eine
settings.json hatte. Nachgestellt, nicht behauptet: `git stash` (log)
bestaetigt e1eb1... siehe Bericht im Auftrag.
"""

import importlib.util
import json
import pathlib
import tempfile

WURZEL = pathlib.Path(__file__).resolve().parent.parent
HOOK_PATH = WURZEL / "haken" / "worktree_identitaet.py"

_spec = importlib.util.spec_from_file_location("worktree_identitaet_wachen_ev", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def _basis_mit_zwei_wachen(td: str) -> pathlib.Path:
    """Hauptbaum, wie er NACH dem Hinzufuegen der stash-Wache aussieht."""
    basis = pathlib.Path(td) / "hauptbaum"
    (basis / ".claude").mkdir(parents=True)
    (basis / "CLAUDE.md").write_text("# Hausregeln\n", encoding="utf-8")
    (basis / ".claude" / "settings.json").write_text(json.dumps({
        "hooks": {
            "PreToolUse": [{
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "python3 haken/stash_guard_hook.py"}],
            }],
            "Stop": [{
                "hooks": [{"type": "command", "command": "python3 haken/existenzpruefung.py"}],
            }],
        }
    }), encoding="utf-8")
    return basis


def test_stale_wache_wird_nachgezogen():
    """POSITIV, die eigentliche Reparatur: ein Arbeitsbaum, der ANFANGS nur
    die Stop-Wache kannte (aeltere Kopie), bekommt bei einem weiteren Lauf
    von _identitaet_nachziehen die inzwischen im Hauptbaum dazugekommene
    PreToolUse-Wache nachgezogen -- ohne dass die eigene Stop-Wache verloren
    geht oder ersetzt wird."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis_mit_zwei_wachen(td)
        ziel = basis / ".claude" / "worktrees" / "alter-baum"
        (ziel / ".claude").mkdir(parents=True)
        # Stand des Arbeitsbaums: nur die Stop-Wache, wie sie vor der
        # stash-Wache im Hauptbaum aussah -- exakt der gemessene Befund.
        alte_fassung = {
            "hooks": {
                "Stop": [{
                    "hooks": [{"type": "command", "command": "python3 haken/existenzpruefung.py"}],
                }],
            }
        }
        (ziel / ".claude" / "settings.json").write_text(json.dumps(alte_fassung), encoding="utf-8")

        hook._identitaet_nachziehen(str(basis), ziel)

        neu = json.loads((ziel / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert "PreToolUse" in neu["hooks"], "stash-Wache wurde nicht nachgezogen -- der urspruengliche Fehler"
        assert neu["hooks"]["PreToolUse"] == [{
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "python3 haken/stash_guard_hook.py"}],
        }]
        assert neu["hooks"]["Stop"] == alte_fassung["hooks"]["Stop"], "eigene Stop-Wache darf nicht verschwinden"


def test_lokale_wache_im_arbeitsbaum_bleibt_erhalten():
    """GRENZWERT: hat der Arbeitsbaum eine Wache, die der Hauptbaum gar nicht
    kennt (z.B. lokal per Hand ergaenzt), darf der Merge sie nicht loeschen."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis_mit_zwei_wachen(td)
        ziel = basis / ".claude" / "worktrees" / "baum-mit-eigener-wache"
        (ziel / ".claude").mkdir(parents=True)
        eigene = {
            "hooks": {
                "Stop": [{
                    "hooks": [{"type": "command", "command": "python3 haken/existenzpruefung.py"}],
                }],
                "PostToolUse": [{
                    "hooks": [{"type": "command", "command": "python3 lokal_nur_hier.py"}],
                }],
            }
        }
        (ziel / ".claude" / "settings.json").write_text(json.dumps(eigene), encoding="utf-8")

        hook._identitaet_nachziehen(str(basis), ziel)

        neu = json.loads((ziel / ".claude" / "settings.json").read_text(encoding="utf-8"))
        assert neu["hooks"]["PostToolUse"] == eigene["hooks"]["PostToolUse"], "lokale Wache wurde entfernt"
        assert "PreToolUse" in neu["hooks"], "gleichzeitig haette die neue Hauptbaum-Wache dazukommen muessen"


def test_zweiter_lauf_ohne_neue_wachen_ist_ein_no_op():
    """GRENZWERT: ist der Arbeitsbaum schon auf dem Stand des Hauptbaums,
    aendert ein weiterer Merge-Lauf die Datei nicht (keine unnoetigen
    Schreibvorgaenge/Zeitstempel)."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis_mit_zwei_wachen(td)
        ziel = basis / ".claude" / "worktrees" / "aktueller-baum"
        (ziel / ".claude").mkdir(parents=True)
        (ziel / ".claude" / "settings.json").write_text(
            (basis / ".claude" / "settings.json").read_text(encoding="utf-8"), encoding="utf-8")
        vorher = (ziel / ".claude" / "settings.json").stat().st_mtime_ns

        hook._identitaet_nachziehen(str(basis), ziel)

        nachher = (ziel / ".claude" / "settings.json").stat().st_mtime_ns
        assert vorher == nachher, "Datei wurde ohne inhaltliche Aenderung neu geschrieben"


def test_kaputtes_json_im_ziel_wird_nicht_angefasst():
    """NEGATIV: Ist die settings.json im Arbeitsbaum kein gueltiges JSON,
    darf der Merge nicht versuchen, sie zu ueberschreiben oder abzustuerzen."""
    with tempfile.TemporaryDirectory() as td:
        basis = _basis_mit_zwei_wachen(td)
        ziel = basis / ".claude" / "worktrees" / "kaputter-baum"
        (ziel / ".claude").mkdir(parents=True)
        (ziel / ".claude" / "settings.json").write_text("{kein json", encoding="utf-8")

        hook._identitaet_nachziehen(str(basis), ziel)  # darf nicht werfen

        assert (ziel / ".claude" / "settings.json").read_text(encoding="utf-8") == "{kein json"


if __name__ == "__main__":
    test_stale_wache_wird_nachgezogen()
    print("[POSITIV] stale Wache wird nachgezogen")
    test_lokale_wache_im_arbeitsbaum_bleibt_erhalten()
    print("[GRENZWERT] lokale Wache bleibt erhalten, neue kommt dazu")
    test_zweiter_lauf_ohne_neue_wachen_ist_ein_no_op()
    print("[GRENZWERT] zweiter Lauf ohne Aenderung ist ein No-Op")
    test_kaputtes_json_im_ziel_wird_nicht_angefasst()
    print("[NEGATIV] kaputtes JSON im Ziel bleibt unangetastet")
    print("test_worktree_identitaet_wachen: alle Zusicherungen halten")
