"""Auftrag 36 (2026-08-13): Sperre gegen NORMRANG_AKTIV=True ohne Skala.

Lehre L-0392e4: norm_rang ist eine Zahl ohne Einheit. Die Spalte
knowledge_nodes.norm_rang trug bisher ausschliesslich Werte aus EINER Quelle
(der Direktiven-Hierarchie: 1=globale CLAUDE.md, 2=hub-CLAUDE.md, 3=ADR).
Zweites Vorkommen 2026-08-12: dieselbe Spalte traegt inzwischen auch Werte
aus mindestens einer weiteren, unvereinbaren Skala (buckeberg,
/ops/verwalterwahl-weg-im-buckeberg-zum-2027, 1=Gesetz..6=muendlich), und
zwei der geteilten Werte (Rang 1, Rang 3) sitzen auf denselben Zahlen wie
Direktiven-Eintraege. kern/rangfolge.py::norm_score() bewertet Rang 1/2/3
heute einheitlich als Direktiven-Rang, ohne die Skala zu kennen. Solange
NORMRANG_AKTIV (kern/rangfolge.py) False ist, bleibt das folgenlos --
norm_score wird nirgends auf den Abruf angewandt. Sobald der Schalter auf
True geht, rangiert der Abruf zwei unvereinbare Ordnungen gegeneinander --
still, ohne Fehlermeldung.

DIESE DATEI IST DIE SPERRE, nicht nur eine Notiz:
test_normrang_aktiv_verlangt_skala laeuft bei JEDEM Testlauf unbedingt (kein
Skip, kein Monkeypatch) und schlaegt fehl, sobald NORMRANG_AKTIV wirksam auf
True steht (Modul-Konstante ODER Umgebungsvariable
KNOWLEDGE_NORMRANG_AKTIV=1 -- kern/rangfolge.py::_normrang_aktiv() deckt
beides ab), ohne dass kern/rangfolge.py eine Skala hinterlegt hat. Eine Skala
gilt als hinterlegt, wenn das Modul ein befuelltes Attribut RANG_SKALEN
traegt (Name bewusst nicht an eine bereits existierende Konstante gebunden --
die Sperre prueft auf ein benanntes Artefakt, das noch zu bauen ist, nicht
auf Zufall). Es gibt heute kein solches Attribut, darum ist die Sperre JEDES
Mal scharf, sobald jemand NORMRANG_AKTIV umlegt.

Rot-vor-gruen (siehe Bericht/Commit): mit KNOWLEDGE_NORMRANG_AKTIV=1 gesetzt
und ohne RANG_SKALEN fiel test_normrang_aktiv_verlangt_skala durch. Danach
zurueckgenommen (Umgebungsvariable wieder aus) -- gruen. Die Gegenprobe
(test_sperre_laesst_echte_skala_passieren) belegt, dass dieselbe Pruefung
keine pauschale Absage an den Schalter ist, sondern nur an die fehlende
Voraussetzung: sobald RANG_SKALEN existiert, laesst sie den aktiven Schalter
durch.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]

import rangfolge  # noqa: E402


def _skala_hinterlegt() -> bool:
    return bool(getattr(rangfolge, "RANG_SKALEN", None))


def test_normrang_aktiv_verlangt_skala():
    """DIE SPERRE. Prueft den tatsaechlichen, unveraenderten Zustand (kein
    Monkeypatch) -- greift also auch, wenn der Schalter kuenftig per Umgebung
    oder per Modul-Konstante umgelegt wird, ohne dass diese Datei angefasst
    werden muss."""
    aktiv = rangfolge._normrang_aktiv()
    assert (not aktiv) or _skala_hinterlegt(), (
        "NORMRANG_AKTIV steht auf True, aber kern.rangfolge traegt keine "
        "Skala (RANG_SKALEN) -- norm_rang bleibt eine Zahl ohne Einheit "
        "(L-0392e4). Zuerst die Skala hinterlegen, dann den Schalter umlegen.")


def test_ausgangslage_schalter_aus():
    """Haelt die heute gueltige Vorgabe fest (Modul-Kommentar 'VORGABE AUS,
    und das ist eine Entscheidung'). Kein Widerspruch zur Sperre oben, nur
    eine zweite, unabhaengige Aussage ueber denselben Bestand."""
    assert rangfolge.NORMRANG_AKTIV is False
    assert os.environ.get("KNOWLEDGE_NORMRANG_AKTIV") in (None, "0"), (
        "Testumgebung darf den Schalter nicht schon global gesetzt haben")
    assert not _skala_hinterlegt(), (
        "Sobald eine Skala hinterlegt wird, ist dieser Test bewusst "
        "anzupassen -- er haelt fest, dass sie heute noch fehlt")


def test_sperre_schlaegt_fehl_wenn_schalter_ohne_skala_umgelegt_wird(monkeypatch):
    """Rot-Probe, reproduzierbar: dieselbe Bedingung wie in der Sperre, hier
    unter kontrolliertem Override erzwungen und ausdruecklich als Fehlschlag
    gezeigt (statt nur behauptet)."""
    monkeypatch.setenv("KNOWLEDGE_NORMRANG_AKTIV", "1")
    monkeypatch.delattr(rangfolge, "RANG_SKALEN", raising=False)
    assert rangfolge._normrang_aktiv() is True, "Testvoraussetzung: Override muss wirken"
    try:
        assert (not rangfolge._normrang_aktiv()) or _skala_hinterlegt()
    except AssertionError:
        pass
    else:
        raise AssertionError(
            "die Sperre haette hier fehlschlagen muessen: Schalter an, keine Skala")


def test_sperre_laesst_echte_skala_passieren(monkeypatch):
    """Gegenprobe: sobald eine Skala hinterlegt ist, blockiert dieselbe
    Pruefung nicht mehr -- kein pauschales Verbot des Schalters, nur der
    fehlenden Voraussetzung."""
    monkeypatch.setenv("KNOWLEDGE_NORMRANG_AKTIV", "1")
    monkeypatch.setattr(rangfolge, "RANG_SKALEN", {"direktiven": (1, 2, 3)}, raising=False)
    aktiv = rangfolge._normrang_aktiv()
    assert (not aktiv) or _skala_hinterlegt()
