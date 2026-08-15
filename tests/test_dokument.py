"""Rot-vor-Gruen fuer die fuenf ADR-019-Merkmale auf Dokumentebene:
Verschachtelung, Alternativtext, Sprache, Veroeffentlicht, Fassungen.

Der Selbsttest in `kern/dokument.py --selftest` deckt dasselbe ab; diese
Datei haelt es zusaetzlich in der Suite fest.
"""
from __future__ import annotations

import base64

import pytest

pycrdt = pytest.importorskip("pycrdt")

from baustein import Baustein, VertragsFehler  # noqa: E402
from dokument import (  # noqa: E402
    BAUSTEINE,
    Anker,
    _liste,
    anmerkung_setzen,
    baustein_anhaengen,
    bausteine,
    bausteine_baum,
    fassungen,
    ist_veroeffentlicht,
    leeres_dokument,
    neue_kennung,
    sprache,
    sprache_setzen,
    verwaiste,
    veroeffentlichen,
    veroeffentlichungsstand,
)


# --------------------------------------------------------------- Verschachtelung

def test_flache_ablage_bleibt_einfuegereihenfolge():
    doc = leeres_dokument()
    wurzel = baustein_anhaengen(doc, "ueberschrift", "Abschnitt 1")
    kind = baustein_anhaengen(doc, "absatz", "Unterpunkt", eltern=wurzel)
    weitere_wurzel = baustein_anhaengen(doc, "absatz", "Abschnitt 2")
    assert [b.kennung for b in bausteine(doc)] == [wurzel, kind, weitere_wurzel]


def test_baumreihenfolge_stellt_kind_hinter_seinen_elternteil():
    doc = leeres_dokument()
    wurzel = baustein_anhaengen(doc, "ueberschrift", "Abschnitt 1")
    kind = baustein_anhaengen(doc, "absatz", "Unterpunkt", eltern=wurzel)
    weitere_wurzel = baustein_anhaengen(doc, "absatz", "Abschnitt 2")
    assert [b.kennung for b in bausteine_baum(doc)] == [wurzel, kind, weitere_wurzel]


def test_zwei_ebenen_tief():
    doc = leeres_dokument()
    wurzel = baustein_anhaengen(doc, "ueberschrift", "A")
    kind = baustein_anhaengen(doc, "absatz", "B", eltern=wurzel)
    enkel = baustein_anhaengen(doc, "absatz", "C", eltern=kind)
    assert [b.kennung for b in bausteine_baum(doc)] == [wurzel, kind, enkel]


def test_leeres_dokument_leere_baumreihenfolge():
    assert bausteine_baum(leeres_dokument()) == []


def test_eltern_ohne_bestand_wird_wurzel_und_geht_nicht_verloren():
    doc = leeres_dokument()
    verwaister_elter = baustein_anhaengen(doc, "absatz", "steht allein", eltern="9" * 12)
    assert [b.kennung for b in bausteine_baum(doc)] == [verwaister_elter]


def test_zyklus_baustein_geht_nicht_verloren_und_haengt_das_dokument_nicht():
    doc = leeres_dokument()
    ring_kennung = neue_kennung()
    ring = Baustein(kennung=ring_kennung, typ="absatz", text="Ring", eltern=ring_kennung)
    _liste(doc, BAUSTEINE).append(pycrdt.Map(ring.als_dict()))
    ergebnis = bausteine_baum(doc)
    assert [b.kennung for b in ergebnis] == [ring_kennung]


def test_anmerkung_auf_ein_vorhandenes_kind_ist_nicht_verwaist():
    doc = leeres_dokument()
    wurzel = baustein_anhaengen(doc, "ueberschrift", "A")
    kind = baustein_anhaengen(doc, "absatz", "B", eltern=wurzel)
    anmerkung_setzen(doc, Anker(baustein=kind), "auf das Kind", "darstellung", "mensch")
    assert verwaiste(doc) == []


# --------------------------------------------------------------- Alternativtext

def test_alt_ist_an_jedem_typ_erlaubt_nicht_nur_grafik():
    for typ in ("absatz", "ueberschrift", "tabelle", "grafik"):
        b = Baustein(kennung="a" * 12, typ=typ, text="x", alt="Beschreibung fuer Screenreader")
        assert b.alt == "Beschreibung fuer Screenreader"


def test_alt_vorgabe_ist_leerer_text():
    b = Baustein(kennung="a" * 12, typ="tabelle", text="x")
    assert b.alt == ""


# --------------------------------------------------------------- Sprache

def test_sprache_vorgabe_deckungsgleich_mit_altem_vorspann():
    assert sprache(leeres_dokument()) == "de-DE"


def test_sprache_setzen_gibt_den_gesetzten_wert_zurueck():
    doc = leeres_dokument()
    assert sprache_setzen(doc, "en-US") == "en-US"
    assert sprache(doc) == "en-US"


def test_leere_sprache_faellt():
    doc = leeres_dokument()
    with pytest.raises(VertragsFehler):
        sprache_setzen(doc, "")


# --------------------------------------------------------------- Veroeffentlicht

def test_veroeffentlicht_vorgabe_ist_nein():
    doc = leeres_dokument()
    assert ist_veroeffentlicht(doc) is False
    assert veroeffentlichungsstand(doc) == {
        "veroeffentlicht": False, "urheber": None, "zeitpunkt": None,
    }


def test_veroeffentlichen_ohne_urheber_faellt():
    doc = leeres_dokument()
    with pytest.raises(VertragsFehler):
        veroeffentlichen(doc, "")


def test_veroeffentlichen_setzt_urheber_und_zeitpunkt():
    doc = leeres_dokument()
    erreicht = veroeffentlichen(doc, "gamlehr", jetzt="2026-08-15T10:00:00Z")
    assert erreicht == {
        "veroeffentlicht": True, "urheber": "gamlehr", "zeitpunkt": "2026-08-15T10:00:00Z",
    }
    assert ist_veroeffentlicht(doc) is True


# --------------------------------------------------------------- Fassungen

def test_veroeffentlichen_haelt_eine_fassung_fest():
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Stand zum Zeitpunkt der Veroeffentlichung.")
    veroeffentlichen(doc, "gamlehr", jetzt="2026-08-15T10:00:00Z")
    fs = fassungen(doc)
    assert len(fs) == 1
    assert fs[0]["urheber"] == "gamlehr"
    assert fs[0]["zeitpunkt"] == "2026-08-15T10:00:00Z"


def test_fassung_ist_rekonstruierbar_auch_nach_spaeterer_aenderung():
    """Der eigentliche Beleg fuer Entscheidung 4: die Fassung zeigt den STAND
    zum Veroeffentlichungszeitpunkt, nicht den heutigen -- rot vor der
    Aenderung waere: es gaebe ueberhaupt keine Fassung, die Ablage
    ueberschreibt bei jedem Update den vollen Stand."""
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Alter Stand.")
    fassung = veroeffentlichen(doc, "gamlehr", jetzt="2026-08-15T10:00:00Z")

    # Nach der Veroeffentlichung aendert sich das Dokument weiter.
    baustein_anhaengen(doc, "absatz", "Neuer Stand, nach der Fassung.")

    rekonstruiert = leeres_dokument()
    rekonstruiert.apply_update(base64.b64decode(fassungen(doc)[0]["stand"]))
    assert [b.text for b in bausteine(rekonstruiert)] == ["Alter Stand."]


def test_zweite_veroeffentlichung_haengt_an_ueberschreibt_nicht():
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "x")
    veroeffentlichen(doc, "gamlehr", jetzt="2026-08-15T10:00:00Z")
    veroeffentlichen(doc, "gamlehr", jetzt="2026-08-15T11:00:00Z")
    assert len(fassungen(doc)) == 2
