"""Rot-vor-Gruen fuer die Ableitungswache -- pro Eigenschaft ein Sabotagefall."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SPIKE_PDF = Path(__file__).resolve().parent.parent / "spikes/pdf_a3_erechnung/rechnung.pdf"

from dokument import baustein_anhaengen, leeres_dokument
from satz import satz_quelle
from satzwache import (
    pdf_text,
    pruefe,
    pruefe_konformitaet,
    pruefe_treue,
    pruefe_vollstaendigkeit,
    satz_lauf,
)


# ---------------------------------------------------------------- Vollstaendigkeit

def test_vollstaendigkeit_positivfall_nichts_fehlt():
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster.")
    baustein_anhaengen(doc, "absatz", "Zweiter.")
    quelle = satz_quelle(doc, "Pruefblatt")
    assert pruefe_vollstaendigkeit(doc, quelle) == []


def test_vollstaendigkeit_sabotierte_quelle_meldet_die_kennung():
    """Sabotage NUR an der lokal gebauten Quelle -- kern/satz.py bleibt unberuehrt."""
    doc = leeres_dokument()
    a = baustein_anhaengen(doc, "absatz", "Erster.")
    b = baustein_anhaengen(doc, "absatz", "Zweiter.")
    quelle = satz_quelle(doc, "Pruefblatt")
    sabotiert = quelle.replace(f"\\label{{bau:{b}}}\n", "")  # Baustein b faellt still heraus
    fehlt = pruefe_vollstaendigkeit(doc, sabotiert)
    assert fehlt == [b], f"erwartet: genau {b!r} fehlt, gemeldet: {fehlt!r}"
    assert a not in fehlt


# ------------------------------------------------------------------------- Treue

def test_treue_positivfall_text_wiedergefunden():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "feld", "2026-0001", feldname="rechnungsnummer")
    pdf_text_richtig = "rechnungsnummer: 2026-0001"
    assert pruefe_treue(doc, pdf_text_richtig) == []
    assert b  # Kennung existiert, nur zur Lesbarkeit referenziert


def test_treue_veraenderter_text_im_blatt_meldet_die_kennung():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "feld", "2026-0001", feldname="rechnungsnummer")
    pdf_text_falsch = "rechnungsnummer: 2026-0002"  # Ziffer im Blatt anders als im Baustein
    abweichend = pruefe_treue(doc, pdf_text_falsch)
    assert abweichend == [b], f"erwartet: {b!r} weicht ab, gemeldet: {abweichend!r}"


def test_treue_grenzwert_umbruch_und_leerraum_stoert_nicht():
    """Belegt die im Modulkopf genannte Grenze: Normalisierung toleriert
    Umbruch/Leerraum, aber keinen echten Inhaltsunterschied."""
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Ein langer Satz mit mehreren Woertern.")
    pdf_text_umgebrochen = "Ein  langer\nSatz mit   mehreren\nWoertern."
    assert pruefe_treue(doc, pdf_text_umgebrochen) == []


@pytest.mark.skipif(not shutil.which("lualatex") or not shutil.which("pdftotext"),
                     reason="lualatex oder pdftotext fehlt")
def test_treue_echter_satzlauf_positivfall(tmp_path):
    """Kein Vertrauen auf den Rueckgabewert -- echtes PDF gerendert und gelesen."""
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster Satz.")
    baustein_anhaengen(doc, "feld", "2026-0001", feldname="rechnungsnummer")
    quelle = satz_quelle(doc, "Pruefblatt")
    pdf, grund = satz_lauf(tmp_path, quelle)
    assert pdf is not None, f"lualatex scheiterte: {grund}"
    text, textgrund = pdf_text(pdf)
    assert textgrund == ""
    assert pruefe_treue(doc, text) == []
    assert pruefe_vollstaendigkeit(doc, quelle) == []


# ------------------------------------------------------------------ Konformitaet

@pytest.mark.skipif(not shutil.which("lualatex") or not shutil.which("verapdf"),
                     reason="lualatex oder verapdf fehlt")
def test_konformitaet_blatt_ohne_kennzeichnung_faellt(tmp_path):
    """Ein Blatt ohne \\DocumentMetadata (PDF/A-3U, PDF/UA-1) faellt bei verapdf durch."""
    tex = tmp_path / "unmarkiert.tex"
    tex.write_text(
        "\\documentclass{article}\n\\begin{document}\nText ohne PDF/A- und PDF/UA-Kennzeichnung.\n\\end{document}\n",
        encoding="utf-8",
    )
    lauf = subprocess.run(
        ["lualatex", "-interaction=nonstopmode", "-output-directory", str(tmp_path), str(tex)],
        capture_output=True, text=True, timeout=60,
    )
    assert lauf.returncode == 0, f"Vorbereitung scheiterte: {lauf.stdout[-500:]}"
    pdf = tmp_path / "unmarkiert.pdf"
    assert pdf.exists()

    ergebnis = pruefe_konformitaet(pdf)
    assert ergebnis["ua1"] == "FAIL", f"erwartet FAIL, bekam {ergebnis!r}"
    assert ergebnis["3u"] == "FAIL", f"erwartet FAIL, bekam {ergebnis!r}"


@pytest.mark.skipif(not shutil.which("verapdf") or not SPIKE_PDF.exists(),
                     reason="verapdf oder spikes/pdf_a3_erechnung/rechnung.pdf fehlt")
def test_konformitaet_positivfall_echter_vorspann_besteht():
    """Gegenprobe zur vorigen: die schon verapdf-belegte Spike-Datei -- PASS.

    NICHT `satz.satz_quelle()` selbst: diese Wache deckte auf, dass die dort
    kopierte VORSPANN-Fassung kein `\\title`/`pdftitle` mehr setzt (das Original
    in `spikes/pdf_a3_erechnung/rechnung.tex` hat beides) und darum PDF/UA-1
    wegen fehlendem `dc:title` FAIL liefert -- siehe
    `test_treffer_gegen_satz_py_fehlende_titel_metadata` unten. Fund gemeldet,
    `kern/satz.py` bleibt nach Auftrag unangetastet."""
    ergebnis = pruefe_konformitaet(SPIKE_PDF)
    assert ergebnis["ua1"] == "PASS", f"erwartet PASS, bekam {ergebnis!r}"
    assert ergebnis["3u"] == "PASS", f"erwartet PASS, bekam {ergebnis!r}"


# ----------------------------------------------------------------------- pruefe()

@pytest.mark.skipif(not shutil.which("lualatex") or not shutil.which("pdftotext") or not shutil.which("verapdf"),
                     reason="lualatex, pdftotext oder verapdf fehlt")
def test_pruefe_end_zu_ende_findet_vollstaendigkeit_und_treue_in_ordnung(tmp_path):
    """Vollstaendigkeit und Treue bestehen fuer echten satz_quelle()-Output.

    Konformitaet NICHT mitgeprueft auf 'bestanden()': FUND waehrend dieses
    Auftrags -- `satz.satz_quelle()` liefert derzeit `ua1: FAIL`, weil dem
    kopierten Vorspann `\\title`/`pdftitle` fehlt (dc:title, ISO 14289-1:2014
    Klausel 7.1). Siehe `test_treffer_gegen_satz_py_fehlende_titel_metadata`."""
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster Satz.")
    baustein_anhaengen(doc, "feld", "2026-0001", feldname="rechnungsnummer")
    bericht = pruefe(doc, arbeitsverzeichnis=tmp_path)
    assert bericht.vollstaendigkeit_fehlt == [], bericht
    assert bericht.treue_abweichungen == [], bericht
    assert bericht.konformitaet["3u"] == "PASS", bericht


def test_satz_quelle_setzt_den_dokumenttitel(tmp_path):
    """Rueckfallschutz fuer den ersten Fund dieser Wache.

    Die Wache fand beim ERSTEN Lauf, dass `satz_quelle()` Blaetter ohne
    `dc:title` erzeugte: `verapdf -f ua1` fiel mit ISO 14289-1:2014 Klausel 7.1.
    Der Vorspann stammte aus dem Spike, dort stand der Titel im Rumpf statt im
    Vorspann. Behoben durch einen Pflichtparameter `titel` -- kein Vorgabewert,
    weil ein nichtssagender Titel formal besteht und genau er vorgelesen wird.

    Dieser Test haelt beides fest: dass das Blatt besteht UND dass der
    uebergebene Titel wirklich im Blatt ankommt. Ohne die zweite Zusicherung
    wuerde ein fest verdrahteter Titel den Test ebenso bestehen."""
    if not shutil.which("lualatex") or not shutil.which("verapdf"):
        pytest.skip("lualatex oder verapdf fehlt")
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster Satz.")
    quelle = satz_quelle(doc, "Rechnung 2026-0001")
    assert "Rechnung 2026-0001" in quelle, "Titel kommt nicht in der Quelle an"
    pdf, grund = satz_lauf(tmp_path, quelle)
    assert pdf is not None, f"lualatex scheiterte: {grund}"
    ergebnis = pruefe_konformitaet(pdf)
    assert ergebnis["ua1"] == "PASS", (
        f"dc:title fehlt wieder -- Rueckfall auf den Fund vom 2026-08-14: {ergebnis!r}"
    )


def test_pruefe_meldet_fehlendes_werkzeug_statt_stillschweigend_zu_bestehen(monkeypatch, tmp_path):
    """Grenzwert: fehlt lualatex, ist das Ergebnis 'nicht geprueft', nie True."""
    monkeypatch.setattr(shutil, "which", lambda name: None)
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Erster Satz.")
    bericht = pruefe(doc, arbeitsverzeichnis=tmp_path)
    assert bericht.treue_grund.startswith("nicht geprueft:")
    assert all(v.startswith("nicht geprueft:") for v in bericht.konformitaet.values())
    assert bericht.bestanden() is False


# ---------------------------------------------------------------- Verschachtelung
#
# ADR-019, Auflage der Entwurfsprobe zu kern/satzwache.py:90,99: ein Kind-
# Baustein darf weder aus der Vollstaendigkeits- noch aus der Treue-Pruefung
# herausfallen. Bei der gewaehlten Speicherform (Elternfeld statt Kind-Array)
# liegt jeder Baustein ohnehin flach im selben Array -- diese beiden Tests
# sind trotzdem hier festgehalten, weil sie die Mengenaussage ("kein Kind
# fehlt") direkt gegen ein Dokument mit Verschachtelung pruefen, statt sie nur
# aus der Bauform zu behaupten.

def test_vollstaendigkeit_findet_ein_kind_baustein():
    doc = leeres_dokument()
    wurzel = baustein_anhaengen(doc, "ueberschrift", "Abschnitt")
    baustein_anhaengen(doc, "absatz", "Unterpunkt", eltern=wurzel)
    quelle = satz_quelle(doc, "Pruefblatt")
    assert pruefe_vollstaendigkeit(doc, quelle) == []


def test_vollstaendigkeit_sabotiertes_kind_wird_gemeldet():
    doc = leeres_dokument()
    wurzel = baustein_anhaengen(doc, "ueberschrift", "Abschnitt")
    kind = baustein_anhaengen(doc, "absatz", "Unterpunkt", eltern=wurzel)
    quelle = satz_quelle(doc, "Pruefblatt")
    sabotiert = quelle.replace(f"\\label{{bau:{kind}}}\n", "")
    assert pruefe_vollstaendigkeit(doc, sabotiert) == [kind]
