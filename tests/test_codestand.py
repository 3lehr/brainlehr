"""Tests fuer kern/codestand.py (AUFGABE 70).

Befund: messungen/stichwortkanal_alleinreichweite.py trug den Codestand fest
verdrahtet als Zeichenkette ("51927d1 (Zweig brainlehr/b4-ausweis)") im
Quelltext -- ab dem naechsten Commit falsch, trotzdem geglaubt. Dieser Test
war VOR der Umstellung rot: das Modul hatte kein Attribut `codestand`, und
selbst mit importiertem Modul haette die Zeichenkette dem echten HEAD nur
zufaellig entsprochen.

Isoliert: keine Datenbank, kein Schreiben in knowledge.db. Der Test gegen
einen schmutzigen Arbeitsbaum benutzt ein eigenes temporaeres Git-Repo, nie
das echte Repo (dessen Sauberkeit haengt vom Lauf anderer Agenten ab).
"""
from __future__ import annotations

import subprocess
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]
_sys.path.insert(0, str(_w / "messungen"))

import codestand
import stichwortkanal_alleinreichweite as skript  # das umgestellte Messskript


def test_ermitteln_matches_real_head():
    """codestand.ermitteln() liefert exakt den echten HEAD -- unabhaengig
    vom Commit, gegen den zuletzt gemessen wurde."""
    echter_head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=_w,
        capture_output=True, text=True, check=True).stdout.strip()
    ergebnis = codestand.ermitteln(_w)
    assert ergebnis["commit"] == echter_head, ergebnis
    assert isinstance(ergebnis["schmutzig"], bool), ergebnis
    assert ergebnis["zweig"], ergebnis
    assert ergebnis["ermittelt"], ergebnis


def test_messskript_ruft_geteilte_stelle_auf():
    """Das umgestellte Messskript verwendet dasselbe kern/codestand.py --
    keine eigene, zweite Ermittlung. Vorher (rot): das Skript kannte kein
    Attribut `codestand`, die Ausgabe war die feste Zeichenkette."""
    assert skript.codestand is codestand
    quelltext = (_w / "messungen" / "stichwortkanal_alleinreichweite.py").read_text(
        encoding="utf-8")
    assert "51927d1" not in quelltext, (
        "alte fest verdrahtete Codestand-Zeichenkette noch im Quelltext")
    assert "codestand.ermitteln(WURZEL)" in quelltext


def _mk_git_repo(tmp_path: _Path) -> _Path:
    """Eigenes, isoliertes Repo -- keine Beruehrung des echten Arbeitsbaums."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    datei = repo / "datei.txt"
    datei.write_text("erste Fassung\n")
    subprocess.run(["git", "add", "datei.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "erste Fassung"], cwd=repo, check=True)
    return repo


def test_schmutzig_wird_ausgewiesen(tmp_path):
    """Negativfall: uncommittete Aenderung im Arbeitsbaum muss `schmutzig`
    True setzen -- eine Zahl, die dagegen gemessen wurde, ist nicht
    reproduzierbar."""
    repo = _mk_git_repo(tmp_path)

    sauber = codestand.ermitteln(repo)
    assert sauber["schmutzig"] is False, sauber

    (repo / "datei.txt").write_text("zweite Fassung, nicht committet\n")
    schmutzig = codestand.ermitteln(repo)
    assert schmutzig["schmutzig"] is True, schmutzig
    # Commit unveraendert -- nur der Zusatzstatus aendert sich.
    assert schmutzig["commit"] == sauber["commit"]


def test_unbekannte_datei_zaehlt_ebenfalls_als_schmutzig(tmp_path):
    """Grenzwert: auch eine unversionierte (untracked) neue Datei ist
    `git status --porcelain` nicht leer -- muss ebenfalls als schmutzig
    gelten, nicht nur eine Aenderung an einer bereits versionierten Datei."""
    repo = _mk_git_repo(tmp_path)
    (repo / "neu.txt").write_text("unversioniert\n")
    ergebnis = codestand.ermitteln(repo)
    assert ergebnis["schmutzig"] is True, ergebnis


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
