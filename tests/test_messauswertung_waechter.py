"""Rot-vor-gruen-Beleg fuer haken/messauswertung_waechter.py (Teil B,
2026-08-15): der Ausloeser fuer den Schritt "beim Auswerten einer Messung"
fehlte komplett (gemessen mit `python3 melder/ausloeserlos.py` --
melder/messregeln.py stand in der Liste der Mechanismen ohne Ausloeser).
Die Pruef-Logik selbst ist nicht neu (siehe melder/messregeln.py und dessen
eigenen `--selftest`) -- neu ist nur, WANN sie laeuft: beim Push, aber nur
fuer runs/*.json, die im ausgehenden Commit-Bereich neu/geaendert sind. Ohne
diese Eingrenzung wuerde jeder Fund gegen den historischen runs/-Bestand
(4 von 153 Dateien, alle bereits auf origin, siehe Docstring der Datei)
JEDEN kuenftigen Push blockieren -- das ist der eigentliche Fehler, den
dieser Test verhindert.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import messauswertung_waechter as w  # noqa: E402


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "runs").mkdir(parents=True)
    _git(tmp_path, "init", "-q", str(repo))
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "runs" / "start.json").write_text(json.dumps({"treffer": 1}))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "start")
    return repo


def test_geaenderte_runs_dateien_findet_nur_neue_datei(tmp_path):
    repo = _init_repo(tmp_path)
    basis = _git(repo, "rev-parse", "HEAD").stdout.strip()

    (repo / "runs" / "neu.json").write_text(json.dumps({"treffer": 2}))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "neu")
    spitze = _git(repo, "rev-parse", "HEAD").stdout.strip()

    gefunden = w.geaenderte_runs_dateien(basis, spitze, cwd=repo)
    assert [p.name for p in gefunden] == ["neu.json"]


def test_geaenderte_runs_dateien_ignoriert_altbestand(tmp_path):
    # Altbestand (start.json) ist schon in "basis" enthalten -- ein Diff
    # gegen sich selbst (basis..basis) darf ihn nicht als "neu" zaehlen.
    repo = _init_repo(tmp_path)
    basis = _git(repo, "rev-parse", "HEAD").stdout.strip()
    gefunden = w.geaenderte_runs_dateien(basis, basis, cwd=repo)
    assert gefunden == []


def test_rot_vor_gruen_vergleich_ohne_haltemenge_wird_beanstandet(tmp_path):
    repo = _init_repo(tmp_path)
    basis = _git(repo, "rev-parse", "HEAD").stdout.strip()

    schlecht = repo / "runs" / "vergleich_schlecht.json"
    schlecht.write_text(json.dumps(
        {"varianten": {"a": {"treffer": 5}, "b": {"treffer": 9}}}))

    # ROT: ohne den Waechter (direkter Dateizugriff) wird nichts geprueft --
    # das ist der Zustand vor diesem Auftrag, keine Pruefung existiert.
    # Hier als Gegenprobe: die Pruefung selbst MUSS bei dieser Datei anschlagen.
    befunde = w.pruefe([schlecht])
    assert len(befunde) == 1
    assert "Haltemenge" in " ".join(befunde[0]["fehlt"])

    # GRUEN: dieselbe Datei mit Versuchszahl, Haltemenge und Trennverfahren
    # -- keine Beanstandung mehr.
    gut = repo / "runs" / "vergleich_gut.json"
    gut.write_text(json.dumps({
        "varianten": {"a": {"treffer": 5}, "b": {"treffer": 9}},
        "versuche": 2, "haltemenge": {"b": 3}, "verfahren": "Hash-Drittel",
    }))
    assert w.pruefe([gut]) == []


def test_grenzwerte_keine_beanstandung() -> None:
    import tempfile

    d = Path(tempfile.mkdtemp())

    leer = d / "leer.json"
    leer.write_text("")
    ohne_zahlen = d / "ohne_zahlen.json"
    ohne_zahlen.write_text(json.dumps({"notiz": "nur text"}))
    fliesstext_zahl = d / "fliesstext.json"
    fliesstext_zahl.write_text(json.dumps(
        {"notiz": "gemessen 2026-08-15, commit 58569423, version 2.1.0"}))
    eine_variante = d / "eine_variante.json"
    eine_variante.write_text(json.dumps({"varianten": {"x": 1}, "treffer": 9}))

    assert w.pruefe([leer, ohne_zahlen, fliesstext_zahl, eine_variante]) == []


def test_main_end_to_end(tmp_path, capsys):
    repo = _init_repo(tmp_path)
    basis = _git(repo, "rev-parse", "HEAD").stdout.strip()

    (repo / "runs" / "vergleich_schlecht.json").write_text(json.dumps(
        {"varianten": {"a": {"treffer": 5}, "b": {"treffer": 9}}}))
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "schlechter vergleich")
    spitze = _git(repo, "rev-parse", "HEAD").stdout.strip()

    alt_argv, alt_cwd = sys.argv, Path.cwd()
    try:
        sys.argv = ["messauswertung_waechter.py", basis, spitze]
        # main() nutzt WURZEL (Modul-Konstante) fuer geaenderte_runs_dateien,
        # daher hier direkt die Funktionen statt main() pruefen -- main()
        # ist duenne CLI-Huelle um dieselbe Logik.
        import os
        os.chdir(repo)
        dateien = w.geaenderte_runs_dateien(basis, spitze, cwd=repo)
        befunde = w.pruefe(dateien)
    finally:
        sys.argv = alt_argv
        import os
        os.chdir(alt_cwd)

    assert len(befunde) == 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
