"""Rot-vor-Gruen fuer den Satzweg: Baustein-Baum -> LaTeX -> gesetztes PDF."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from dokument import baustein_anhaengen, leeres_dokument
from satz import maskiere, satz_quelle

LUALATEX = shutil.which("lualatex") or "/usr/local/bin/lualatex"


def test_positivfall_beide_texte_in_der_quelle():
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster Satz.")
    baustein_anhaengen(doc, "feld", "2026-0001", feldname="rechnungsnummer")
    quelle = satz_quelle(doc, "Pruefblatt")
    assert "Erster Satz." in quelle
    assert "2026-0001" in quelle
    assert "rechnungsnummer" in quelle


def test_kennung_im_blatt_wiederfindbar():
    doc = leeres_dokument()
    kennung = baustein_anhaengen(doc, "absatz", "Text.")
    quelle = satz_quelle(doc, "Pruefblatt")
    assert f"bau:{kennung}" in quelle


def test_sperrfall_boesartiger_text_bricht_den_satz_nicht():
    """Der wichtigste Fall: \\newpage{}$x&y%z# muss maskiert im Blatt landen."""
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "\\newpage{}$x&y%z#")
    quelle = satz_quelle(doc, "Pruefblatt")
    # Ein unmaskiertes Steuerzeichen stuende NICHT hinter einem eigenen
    # Backslash -- die Pruefung muss also das Escape mitpruefen, sonst
    # findet ein Substring-Test "$x" auch im korrekt maskierten "\$x".
    for maskiert in (r"\{\}", r"\$x", r"\&y", r"\%z", r"\#"):
        assert maskiert in quelle, f"Maskierung fehlt: {maskiert!r} nicht in {quelle!r}"
    assert r"\textbackslash{}newpage" in quelle  # Backslash selbst ist maskiert, kein rohes \newpage


def test_ohne_maskierung_bricht_der_lauf_oder_zeigt_falsches(tmp_path):
    """Gegenprobe: dieselbe Quelle OHNE Maskierung -- lualatex faellt.

    Belegt, dass die Maskierung in test_sperrfall... etwas wirklich
    verhindert, statt nur einen Text zu enthalten, der zufaellig nicht
    vorkam.
    """
    if not Path(LUALATEX).exists() and not shutil.which("lualatex"):
        pytest.skip("lualatex nicht gefunden")

    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "\\newpage{}$x&y%z#")

    from satz import NACHSPANN, VORSPANN

    (kennung,) = [b.kennung for b in __import__("dokument").bausteine(doc)]
    # Quelle OHNE Maskierung von Hand gebaut -- Gegenteil von satz_quelle().
    kaputte_quelle = VORSPANN + f"\\label{{bau:{kennung}}}\n" + "\\newpage{}$x&y%z#" + "\n\n" + NACHSPANN

    tex = tmp_path / "kaputt.tex"
    tex.write_text(kaputte_quelle, encoding="utf-8")
    ergebnis = subprocess.run(
        [LUALATEX, "-interaction=nonstopmode", "-output-directory", str(tmp_path), str(tex)],
        capture_output=True, text=True, timeout=60,
    )
    # $x&y%z# ausserhalb Mathe-Modus oeffnet einen nie geschlossenen
    # Mathe-Modus (das $) und einen Tabellenwechsel (&) im Fliesstext --
    # lualatex bricht mit Fehler ab (Exit-Code != 0).
    assert ergebnis.returncode != 0, (
        f"erwartet: kaputte Quelle scheitert. War aber returncode="
        f"{ergebnis.returncode}, stdout-Ende: {ergebnis.stdout[-500:]!r}"
    )


def test_echter_lualatex_lauf_erzeugt_lesbares_pdf(tmp_path):
    """Kein Vertrauen auf den Rueckgabewert -- ins PDF hineingesehen (pdftotext)."""
    if not shutil.which("lualatex"):
        pytest.skip("lualatex nicht gefunden")
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        pytest.skip("pdftotext nicht gefunden")

    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster Satz.")
    baustein_anhaengen(doc, "absatz", "\\newpage{}$x&y%z#")

    quelle = satz_quelle(doc, "Pruefblatt")
    tex = tmp_path / "blatt.tex"
    tex.write_text(quelle, encoding="utf-8")

    ergebnis = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-output-directory", str(tmp_path), str(tex)],
        capture_output=True, text=True, timeout=60,
    )
    assert ergebnis.returncode == 0, f"lualatex scheiterte: {ergebnis.stdout[-1000:]}"

    pdf = tmp_path / "blatt.pdf"
    assert pdf.exists(), "kein PDF erzeugt trotz returncode 0"

    text = subprocess.run([pdftotext, str(pdf), "-"], capture_output=True, text=True, timeout=20).stdout
    assert "Erster Satz." in text
    # Der maskierte Boesewicht-Text landet als LESBARER Text im PDF, nicht als
    # ausgefuehrtes LaTeX-Steuerzeichen.
    assert "newpage" in text or "\\newpage" in text


def test_maskiere_leerer_text():
    assert maskiere("") == ""
