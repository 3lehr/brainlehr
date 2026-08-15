"""Tests fuer kern/designtokens_latex.py (ADR-015, LaTeX-Erzeuger).

Rot-vor-gruen-Beleg: das Modul existierte bis zu diesem Auftrag nicht
(0 Treffer fuer generate_latex im ganzen Verbund, siehe
runs/messung_i2_designvorrat_2026-08-15T111743.md Abschnitt 5) -- vor der
Erzeugung dieser Datei war jeder Test hier ein ImportError.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT)]

from kern import designtokens_latex as dtl  # noqa: E402


def test_selftest_bestanden():
    assert dtl._selftest() == 0


def test_datei_fehlt():
    with pytest.raises(FileNotFoundError):
        dtl.lade_guide("/pfad/der/garantiert/nicht/existiert.json")


def test_datei_leer(tmp_path):
    p = tmp_path / "leer.json"
    p.write_text("")
    with pytest.raises(ValueError):
        dtl.lade_guide(str(p))


def test_unbekannter_farbraum():
    _, warnungen = dtl.generate_latex(
        {"farben": {"x": {"hex": "rgb(1,2,3)"}}, "meta": {}}
    )
    assert any("UNBEKANNTER FARBRAUM" in w for w in warnungen)


def test_sonderzeichen_im_namen_wird_nicht_still_verschluckt():
    latex, warnungen = dtl.generate_latex(
        {"farben": {"!!!": {"hex": "#123456"}}, "meta": {}}
    )
    assert "123456" not in latex  # nicht uebersetzt
    assert any("Sonderzeichen" in w for w in warnungen)  # aber gemeldet


def test_wert_ohne_entsprechung_wird_gemeldet_nicht_verschluckt():
    """Auflage 4: Schatten/Elevation (komponenten.*.elevation) hat keine
    LaTeX-Entsprechung -- muss als UEBERSPRUNGEN in den Warnungen auftauchen,
    nicht klanglos fehlen."""
    guide = {
        "meta": {},
        "farben": {},
        "komponenten": {"kurs_card": {"elevation": 1}},
    }
    latex, warnungen = dtl.generate_latex(guide)
    assert any("komponenten" in w and "UEBERSPRUNGEN" in w for w in warnungen)
    assert "% komponenten: keine Entsprechung, nicht uebersetzt" in latex


def test_gegen_kanonische_datei_wenn_vorhanden():
    """Laeuft nur, wenn der kanonische Designvorrat lokal vorhanden ist
    (design-lab ist ein fremdes Repo, wird hier nur GELESEN)."""
    if not os.path.exists(dtl.KANONISCHER_PFAD):
        pytest.skip("kanonischer Designvorrat lokal nicht vorhanden")
    guide = dtl.lade_guide(dtl.KANONISCHER_PFAD)
    latex, warnungen = dtl.generate_latex(guide)
    assert "\\definecolor{akaPrimary}{HTML}{00993E}" in latex
    assert len(warnungen) > 0  # der Guide traegt garantiert Bloecke ohne Entsprechung


def test_erzeugtes_latex_ist_wirklich_setzbar(tmp_path):
    """Rot-vor-gruen fuer die Satzprobe: eine erfundene, garantiert
    fehlerfreie Guide-Struktur wird durch tectonic gejagt. Bricht der Satz,
    ist der Erzeuger kaputt -- unabhaengig vom Kanon-Bestand."""
    tectonic = None
    for kandidat in ("tectonic", "lualatex"):
        from shutil import which

        if which(kandidat):
            tectonic = kandidat
            break
    if tectonic is None:
        pytest.skip("kein LaTeX-Satzprogramm (tectonic/lualatex) installiert")

    guide = {
        "meta": {"version": "0.0.1-test"},
        "farben": {"primary": {"hex": "#00AA33"}},
        "typografie": {"font_family_primary": "Latin Modern Roman"},
        "pdf_masszahlen": {
            "border_radius_system": {"xl": {"pt": 12}},
            "print_typo_skala": [{"pt": 10.0, "rolle": "body"}],
        },
    }
    latex, _ = dtl.generate_latex(guide)
    (tmp_path / "tokens.tex").write_text(latex)
    probe = tmp_path / "probe.tex"
    probe.write_text(
        "\\documentclass{article}\n"
        "\\input{tokens.tex}\n"
        "\\begin{document}\n"
        "\\textcolor{akaPrimary}{Testfarbe}\\par\n"
        "\\rule{\\akaRadiusXl}{1pt}\\par\n"
        "{\\fontsize{\\akaFontSizeBody}{12pt}\\selectfont Testtext}\n"
        "\\end{document}\n"
    )
    cmd = [tectonic, "probe.tex"] if tectonic == "tectonic" else ["lualatex", "-interaction=nonstopmode", "probe.tex"]
    result = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "probe.pdf").exists()
    assert (tmp_path / "probe.pdf").stat().st_size > 0
