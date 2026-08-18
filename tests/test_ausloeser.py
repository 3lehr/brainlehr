"""tests/test_ausloeser.py -- INT-ACT-001, Negativfaelle und Grenzwerte fuer
kern/ausloeser.py. Sieht der Code anders aus als hier beschrieben, halte dich
an den Code.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json

import pytest

import ausloeser
import ausweis


@pytest.fixture
def pfade(tmp_path):
    return {
        "plaene_pfad": tmp_path / "plaene.json",
        "protokoll_pfad": tmp_path / "protokoll.jsonl",
        "ausschalter_pfad": tmp_path / "aus",
    }


BEGLAUBIGT = ausweis.Ausweis(name="probe", rollen=("leser",), beglaubigt=True)
UNBEGLAUBIGT = ausweis.Ausweis(name="wer", rollen=(), beglaubigt=False)


def _zeilen(pfad):
    if not pfad.exists():
        return []
    return pfad.read_text(encoding="utf-8").splitlines()


def test_plane_erklaert_ohne_auszufuehren(pfade):
    plan = ausloeser.plane("t1", "taeglich 06:30", "bericht",
                           plaene_pfad=pfade["plaene_pfad"])
    assert plan["ausweis"] and plan["protokoll"] and plan["ausschalter"]
    # Grenzwert: erklaert, nie ausgefuehrt -> KEIN Protokolleintrag.
    assert not pfade["protokoll_pfad"].exists()


def test_aktion_mit_aussenwirkung_wird_abgewiesen(pfade):
    for aktion in ("versand", "netzaufruf", "push", "veroeffentlichung",
                   "geld_ueberweisen", "kennwort_lesen"):
        with pytest.raises(ValueError):
            ausloeser.plane("boese", "taeglich", aktion,
                            plaene_pfad=pfade["plaene_pfad"])


def test_fehlender_ausweis_verhindert_ausfuehrung(pfade):
    ausloeser.plane("t1", "taeglich", "bericht", plaene_pfad=pfade["plaene_pfad"])
    with pytest.raises(PermissionError):
        ausloeser.fuehre_aus("t1", ausw=UNBEGLAUBIGT, **pfade)
    # Grenzwert: eine abgewiesene Ausfuehrung hinterlaesst SEHR WOHL einen Eintrag.
    zeilen = _zeilen(pfade["protokoll_pfad"])
    assert len(zeilen) == 1
    assert "abgewiesen:kein_ausweis" in zeilen[0]


def test_ausschalter_verhindert_ausfuehrung(pfade):
    ausloeser.plane("t1", "taeglich", "bericht", plaene_pfad=pfade["plaene_pfad"])
    pfade["ausschalter_pfad"].touch()
    with pytest.raises(PermissionError):
        ausloeser.fuehre_aus("t1", ausw=BEGLAUBIGT, **pfade)
    zeilen = _zeilen(pfade["protokoll_pfad"])
    assert len(zeilen) == 1
    assert "abgewiesen:ausschalter_gesetzt" in zeilen[0]


def test_unerklaerter_ausloeser_wird_abgewiesen(pfade):
    with pytest.raises(ValueError):
        ausloeser.fuehre_aus("nie-geplant", ausw=BEGLAUBIGT, **pfade)
    zeilen = _zeilen(pfade["protokoll_pfad"])
    assert len(zeilen) == 1
    assert "abgewiesen:nicht_erklaert" in zeilen[0]


def test_gueltiger_lauf_wird_ausgefuehrt_und_protokolliert(pfade):
    ausloeser.plane("t1", "taeglich", "bericht", plaene_pfad=pfade["plaene_pfad"])
    ergebnis = ausloeser.fuehre_aus("t1", ausw=BEGLAUBIGT, **pfade)
    assert ergebnis["ausgefuehrt"] is True
    zeilen = _zeilen(pfade["protokoll_pfad"])
    assert len(zeilen) == 1
    assert "ausgefuehrt" in zeilen[0]


# --- Aktionstyp 'bericht': kein Platzhalter mehr, siehe kern/ausloeser.py
# ::_aktion_bericht(). Rot-vor-gruen gegen den fruehreren Platzhalter belegt
# (2026-08-18): der alte Rueckgabewert trug nur einen "hinweis"-Text und
# schrieb NIE nach kennzahlendatei() -- diese Tests scheiterten dagegen mit
# "assert not True" (kennzahlen_pfad.exists() war False) bzw. KeyError auf
# "kennzahlen".

@pytest.fixture
def kennzahlen_pfad(tmp_path, monkeypatch):
    ziel = tmp_path / "kennzahlen.jsonl"
    monkeypatch.setenv(ausloeser.ENV_KENNZAHLEN, str(ziel))
    return ziel


def test_bericht_erzeugt_echte_kennzahlenzeile(pfade, kennzahlen_pfad):
    ausloeser.plane("t1", "taeglich", "bericht", plaene_pfad=pfade["plaene_pfad"])
    ergebnis = ausloeser.fuehre_aus("t1", ausw=BEGLAUBIGT, **pfade)
    assert ergebnis["ergebnis"]["kennzahlen"]  # kein Platzhalter-"hinweis" mehr
    assert kennzahlen_pfad.exists()
    zeilen = _zeilen(kennzahlen_pfad)
    assert len(zeilen) == 1
    eintrag = json.loads(zeilen[0])
    assert eintrag["name"] == "t1"
    assert "zeit" in eintrag
    for feld in ("knoten_gesamt", "knoten_arbeitsbestand", "lehren_aktiv",
                 "access_log_zeilen", "access_log_mit_tokens"):
        assert isinstance(eintrag[feld], int)


def test_bericht_zweimal_haengt_an_ueberschreibt_nicht(pfade, kennzahlen_pfad):
    ausloeser.plane("t1", "taeglich", "bericht", plaene_pfad=pfade["plaene_pfad"])
    ausloeser.fuehre_aus("t1", ausw=BEGLAUBIGT, **pfade)
    ausloeser.fuehre_aus("t1", ausw=BEGLAUBIGT, **pfade)
    # Grenzwert: zwei Ausfuehrungen -> ZWEI Zeilen, keine ueberschriebene eine.
    assert len(_zeilen(kennzahlen_pfad)) == 2


def test_ausschalter_verhindert_auch_die_kennzahlenzeile(pfade, kennzahlen_pfad):
    ausloeser.plane("t1", "taeglich", "bericht", plaene_pfad=pfade["plaene_pfad"])
    pfade["ausschalter_pfad"].touch()
    with pytest.raises(PermissionError):
        ausloeser.fuehre_aus("t1", ausw=BEGLAUBIGT, **pfade)
    # Negativfall: abgewiesen -> KEINE Kennzahlenzeile, nur der Protokolleintrag.
    assert not kennzahlen_pfad.exists()
