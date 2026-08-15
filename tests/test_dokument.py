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
    anmerkungen,
    baustein_anhaengen,
    baustein_loeschen,
    baustein_text_setzen,
    baustein_verschieben,
    bausteine,
    bausteine_baum,
    bereichsfehler,
    fassungen,
    ist_veroeffentlicht,
    leeres_dokument,
    mitwirkende,
    neue_kennung,
    praeferenzpaare,
    sprache,
    sprache_setzen,
    verwaiste,
    veroeffentlichen,
    veroeffentlichungsstand,
    zustand_setzen,
)
from teilnehmer import KennungsFehler
from teilnehmer import neue_kennung as neue_teilnehmerkennung


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


# --------------------------------------------------------------- Mensch UND Modell
#
# Gesamtplan F5, woertlich: "'modell' kommt in kern/dokument.py nur als Wert
# in einem Selbsttest vor... das Modell hat dort noch nie gesessen." Der
# gruene `test_zwei_teilnehmer_tippen_gleichzeitig` (test_walkthrough_
# dokumentfenster.py) belegt "mehrere Teilnehmer gleichzeitig" -- NICHT
# "Mensch und Modell am selben Dokument, distinguishable". Die drei Tests
# unten pruefen genau das und waren ROT, bevor `mitwirkende()` existierte:
# `ImportError: cannot import name 'mitwirkende'` -- es gab schlicht keine
# Stelle im Code, die diese Frage beantwortete.

def test_mensch_und_modell_gleichzeitig_am_dokument_unterscheidbar():
    """Der Kern der Sache: zwei Teilnehmer -- einer 'mensch', einer 'modell' --
    setzen GLEICHZEITIG eine Anmerkung auf denselben Baustein, jeder ohne den
    Stand des anderen zu kennen. Nach dem Zusammenfuehren sind beide Beitraege
    da UND ihrem Urheber eindeutig zuzuordnen -- nicht nur "zwei Anmerkungen
    liegen im Array", sondern "WER hat WAS beigetragen"."""
    von_mensch = leeres_dokument()
    stelle = baustein_anhaengen(von_mensch, "absatz", "Ein Satz mit einem Fehler drin.")
    von_modell = leeres_dokument(neue_teilnehmerkennung())
    von_modell.apply_update(von_mensch.get_update())   # beide sehen denselben Baustein

    a_mensch = anmerkung_setzen(von_mensch, Anker(baustein=stelle, suchtext="Fehler"),
                                "das muss anders klingen", "inhalt", "mensch")
    a_modell = anmerkung_setzen(von_modell, Anker(baustein=stelle, suchtext="Fehler"),
                                "Tippfehler: 'drin' -> 'darin'.", "tippfehler", "modell")

    zusammen = leeres_dokument()
    zusammen.apply_update(von_mensch.get_update())
    zusammen.apply_update(von_modell.get_update())

    wer = mitwirkende(zusammen)
    assert wer["mensch"] == [a_mensch], wer
    assert wer["modell"] == [a_modell], wer

    # Und die Klasse zeigt, was das Modell selbstaendig duerfte -- der Mensch
    # hat hier keinen Schalter, weil "inhalt" eine schwere Klasse ist.
    nach_kennung = {a.kennung: a for a in anmerkungen(zusammen)}
    assert nach_kennung[a_modell].darf_automatisch is True    # tippfehler
    assert nach_kennung[a_mensch].darf_automatisch is False   # inhalt


def test_verworfene_anmerkung_des_modells_bleibt_im_verlauf():
    """Gegenprobe: eine Anmerkung des Modells, die der Mensch VERWIRFT,
    verschwindet nicht spurlos -- sie bleibt sichtbar, im Zustand 'abgelehnt',
    mit dem Uebergang im Verlauf."""
    doc = leeres_dokument()
    stelle = baustein_anhaengen(doc, "absatz", "Text.")
    a = anmerkung_setzen(doc, Anker(baustein=stelle), "Vorschlag des Modells.",
                         "inhalt", "modell")
    assert zustand_setzen(doc, a, "abgelehnt") == "abgelehnt"

    eintrag = {x.kennung: x for x in anmerkungen(doc)}[a]
    assert eintrag.zustand == "abgelehnt"
    assert eintrag.verlauf == ["offen->abgelehnt"]
    assert a in mitwirkende(doc)["modell"], "verworfen ist nicht verschwunden"


# --------------------------------------------------------------- F7: Anker ueberlebt den Neusatz

def test_geloeschter_baustein_macht_seine_anmerkung_verwaist():
    """ROT waere: die Anmerkung springt auf den zweiten Baustein mit gleichem
    Text. GRUEN: sie verwaist sichtbar, springt nirgends hin."""
    doc = leeres_dokument()
    ziel = baustein_anhaengen(doc, "absatz", "Erster Satz.")
    zwilling = baustein_anhaengen(doc, "absatz", "Erster Satz.")
    a = anmerkung_setzen(doc, Anker(baustein=ziel, suchtext="Erster Satz."),
                         "hier korrigieren", "inhalt", "mensch")
    assert verwaiste(doc) == []
    assert baustein_loeschen(doc, ziel) == ziel
    assert [x.kennung for x in verwaiste(doc)] == [a]
    assert zwilling in {b.kennung for b in bausteine(doc)}


def test_baustein_loeschen_unbekannte_kennung_faellt():
    doc = leeres_dokument()
    with pytest.raises(Exception):
        baustein_loeschen(doc, "999999999999")


def test_verschobener_baustein_behaelt_seinen_anker():
    """ROT waere: nach dem Umhaengen zeigt der Anker ins Leere oder auf den
    falschen Baustein. GRUEN: die Kennung, nicht die Baumposition, traegt den
    Anker -- das ist der ganze Sinn von F7."""
    doc = leeres_dokument()
    alt = baustein_anhaengen(doc, "ueberschrift", "Alt")
    neu = baustein_anhaengen(doc, "ueberschrift", "Neu")
    ziel = baustein_anhaengen(doc, "absatz", "Zieltext.", eltern=alt)
    a = anmerkung_setzen(doc, Anker(baustein=ziel), "haengt am Ziel", "inhalt", "mensch")
    assert baustein_verschieben(doc, ziel, neu) == neu
    assert verwaiste(doc) == []
    nach_kennung = {x.kennung: x for x in anmerkungen(doc)}
    assert nach_kennung[a].anker.baustein == ziel


def test_baustein_kann_nicht_sein_eigener_elternteil_werden():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "X")
    with pytest.raises(Exception):
        baustein_verschieben(doc, b, b)


def test_unveraenderter_baustein_laesst_seine_anmerkung_unveraendert():
    """Gegenprobe: ohne Aenderung am Baustein bleibt die Anmerkung exakt gleich."""
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "Ein Satz.")
    anmerkung_setzen(doc, Anker(baustein=b), "pruefen", "darstellung", "mensch")
    vorher = anmerkungen(doc)
    assert anmerkungen(doc) == vorher


def test_gekuerzter_text_meldet_bereichsfehler_statt_zu_verwaisen():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "Ein langer Satz mit vielen Worten.")
    a = anmerkung_setzen(doc, Anker(baustein=b, suchtext="langer", von=4, bis=10),
                         "Wort falsch", "inhalt", "mensch")
    assert bereichsfehler(doc) == []
    baustein_text_setzen(doc, b, "Kurz.")
    assert verwaiste(doc) == [], "der Baustein existiert weiterhin"
    assert [x.kennung for x in bereichsfehler(doc)] == [a]


def test_anker_ohne_bereich_kann_nicht_in_bereichsfehler_laufen():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "Ein langer Satz.")
    anmerkung_setzen(doc, Anker(baustein=b), "generell", "darstellung", "mensch")
    baustein_text_setzen(doc, b, "x")
    assert bereichsfehler(doc) == []


def test_leeres_dokument_ohne_anmerkungen_meldet_nichts():
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Text.")
    assert verwaiste(doc) == []
    assert bereichsfehler(doc) == []


def test_baustein_text_setzen_unbekannte_kennung_faellt():
    doc = leeres_dokument()
    with pytest.raises(Exception):
        baustein_text_setzen(doc, "999999999999", "x")


def test_teilnehmerkennung_ueber_der_schranke_ist_ausgeschlossen():
    """Grenzwert (ADR-010, L-44dc9f): 2**32-1 traegt (Swift schneidet erst
    DAHINTER ab), 2**32 nicht. Statt das Verdoppeln nur zu MELDEN, laesst
    unsere Vergabe es gar nicht erst zu -- das ist der bessere Beleg."""
    assert leeres_dokument(2**32 - 1).client_id == 2**32 - 1
    with pytest.raises(KennungsFehler):
        leeres_dokument(2**32)


# ------------------------------------------------------------ Herkunftsverlauf
# Rot-vor-Gruen fuer den Betreiberauftrag 2026-08-15: ein einzelner
# Herkunftswert konnte weder eine BESSERE Handeingabe von einer schlechteren
# unterscheiden noch eine Ruecknahme ueberleben. ROT vor dieser Aenderung:
# `baustein_text_setzen` loeschte die Quellenkennung still, `praeferenzpaare`
# gab es nicht.


def test_dreischritt_vorschlag_widerspruch_ruecknahme_auf_dokumentebene():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "der richtige Satz",
                           herkunft="vorschlag_angenommen",
                           herkunftsquelle="anmerkung:aa11bb22cc33")

    baustein_text_setzen(doc, b, "mein Satz", jetzt="t1")
    nach_widerspruch = [x for x in bausteine(doc) if x.kennung == b][0]
    assert nach_widerspruch.herkunft == "eingegeben"
    assert len(nach_widerspruch.herkunftsverlauf) == 1
    assert nach_widerspruch.herkunftsverlauf[0]["zurueckgenommen_am"] is None

    baustein_text_setzen(doc, b, "der richtige Satz", jetzt="t2")
    nach_ruecknahme = [x for x in bausteine(doc) if x.kennung == b][0]
    assert nach_ruecknahme.herkunft == "vorschlag_angenommen", \
        "die Ruecknahme muss die vorherige Herkunft wiederherstellen"
    assert nach_ruecknahme.herkunftsquelle == "anmerkung:aa11bb22cc33"
    assert len(nach_ruecknahme.herkunftsverlauf) == 1, "ergaenzt, kein zweiter Eintrag"

    assert praeferenzpaare(doc) == [{
        "baustein": b,
        "herkunft_bewertet": "vorschlag_angenommen", "herkunftsquelle": "anmerkung:aa11bb22cc33",
        "text_abgeleitet": "der richtige Satz", "bevorzugt": "abgeleitet",
        "zeitpunkt_widerspruch": "t1", "zeitpunkt_ruecknahme": "t2",
    }]


def test_praeferenzpaar_offener_widerspruch_ohne_ruecknahme_zaehlt_zugunsten_mensch():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "abgeleiteter Text",
                           herkunft="abgeleitet", herkunftsquelle="knoten:x")
    baustein_text_setzen(doc, b, "menschlicher Text", jetzt="t1")
    paare = praeferenzpaare(doc)
    assert len(paare) == 1
    assert paare[0]["bevorzugt"] == "mensch"
    assert paare[0]["zeitpunkt_ruecknahme"] is None


def test_negativfall_nie_geaendert_erzeugt_kein_praeferenzpaar():
    doc = leeres_dokument()
    baustein_anhaengen(doc, "absatz", "Nie angefasst.")
    assert praeferenzpaare(doc) == []


def test_negativfall_zwei_handaenderungen_ohne_vorschlag_erzeugt_kein_paar():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "A")
    baustein_text_setzen(doc, b, "B", jetzt="t1")
    baustein_text_setzen(doc, b, "C", jetzt="t2")
    assert praeferenzpaare(doc) == []


def test_zweiter_teilnehmer_sieht_denselben_herkunftsverlauf():
    doc = leeres_dokument()
    b = baustein_anhaengen(doc, "absatz", "der richtige Satz",
                           herkunft="vorschlag_angenommen",
                           herkunftsquelle="anmerkung:aa")
    baustein_text_setzen(doc, b, "mein Satz", jetzt="t1")
    baustein_text_setzen(doc, b, "der richtige Satz", jetzt="t2")

    zweiter = leeres_dokument(neue_teilnehmerkennung())
    zweiter.apply_update(doc.get_update())
    assert praeferenzpaare(zweiter) == praeferenzpaare(doc)
