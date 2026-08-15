"""B4/I4 (ADR-017, Linie I in docs/PLAN_GESAMT_2026-08-13.md): Widerruf fuer
Ausweise. Vorher gab es 'gilt_bis' als Ablaufdatum, aber KEIN Widerrufsfeld,
KEINE Sperrliste, KEINEN Versionszaehler -- ein gewoehnlicher Ausweis ohne
gesetztes gilt_bis war ueber kein Feld zuruecknehmbar (Messung 2026-08-15,
runs/messung_i4_g6_2026-08-15T055326+0200.json, Knoten 5124a160).

ROT VOR GRUEN, woertlich gezeigt (nicht behauptet): Ein Lauf gegen den Stand
VOR dieser Aenderung (git show HEAD:kern/ausweis.py, Commit vor diesem) ergab

    hat ausweis_vorher ueberhaupt widerrufen()? -> False
    ROT: AttributeError beim Versuch zu widerrufen:
        module 'ausweis_vorher' has no attribute 'widerrufen'
    danach WEITERHIN beglaubigt (kein Widerrufsweg vorhanden): True

Ein bereits ausgestellter Ausweis ohne gilt_bis blieb also fuer immer
beglaubigt -- es gab schlicht keine Funktion, die das haette aendern koennen.

BAUFORM (siehe ausweis.py, Abschnitt '--- Widerruf ---' fuer die volle
Begruendung): ein Feld `widerrufen_am` AM EINTRAG, kein zweiter Ort (Sperrliste)
und kein Versionszaehler -- damit lebt und stirbt der Widerruf mit dem
Eintrag, keine zweite Quelle, die auseinanderlaufen koennte.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

from datetime import datetime, timedelta, timezone

import pytest

import ausweis  # noqa: E402

T0 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def bestand(tmp_path):
    """Gruendungsakt + Meldeamt-Ausstattung, wie im Betrieb."""
    pfad = tmp_path / "ausweise.json"
    gruender = ausweis.anlegen("gruender", ["betreiber"], art="mensch", pfad=pfad)
    return pfad, gruender


def _anlegen(pfad, gruender, *a, **kw):
    return ausweis.anlegen(*a, aussteller=gruender, pfad=pfad, **kw)


# --- Gegenprobe beide Richtungen -------------------------------------------

def test_unwiderrufener_ausweis_geht_durch(bestand):
    pfad, gruender = bestand
    g = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    assert ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt


def test_widerrufener_ausweis_wird_abgewiesen(bestand):
    pfad, gruender = bestand
    g = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    assert ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt  # vorher

    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad, jetzt=T0)

    a = ausweis.loese_auf("hausmeister", geheimnis=g, pfad=pfad, jetzt=T0)
    assert not a.beglaubigt, "widerrufener Ausweis beglaubigt weiter"
    assert a.rollen == (), "widerrufener Ausweis behielt Rollen"
    assert a.protokollname == "unbeglaubigt:hausmeister"


# --- Frage 1: Pruefstellen --------------------------------------------------

def test_widerruf_wirkt_ohne_neustart_und_ohne_cache_leiche(bestand):
    """loese_auf() cacht die scrypt-Pruefung (lru_cache) -- der Widerruf darf
    trotzdem sofort greifen, weil der Dateistand Teil des Cache-Schluessels
    ist. Kein Neustart, kein Aufraeumen noetig."""
    pfad, gruender = bestand
    g = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    a1 = ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0)
    assert a1.beglaubigt

    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad, jetzt=T0)
    a2 = ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0)
    assert not a2.beglaubigt


# --- Frage 2: bereits erteilte Mandate eines Widerrufenen -------------------

def test_mandat_eines_widerrufenen_mandanten_wirkt_nicht_mehr(bestand):
    pfad, gruender = bestand
    g_chef = _anlegen(pfad, gruender, "chefin", ["schreiber"], art="mensch")
    g_bote = _anlegen(pfad, gruender, "bote", ["leser"],
                      mandat={"von": "chefin", "rollen": ["schreiber"],
                              "gegenstand": ["abfallwirtschaft"]})

    # vorher: das Mandat greift
    vor = ausweis.loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                            gegenstand="abfallwirtschaft")
    assert set(vor.rollen) == {"leser", "schreiber"}

    ausweis.widerrufen("chefin", aussteller=gruender, pfad=pfad, jetzt=T0)

    nach = ausweis.loese_auf(geheimnis=g_bote, pfad=pfad, jetzt=T0,
                             gegenstand="abfallwirtschaft")
    assert nach.beglaubigt, "der Bote selbst ist nicht widerrufen"
    assert nach.rollen == ("leser",), \
        f"Mandat einer widerrufenen Chefin wirkte weiter: {nach.rollen}"


def test_neues_mandat_auf_widerrufenen_mandanten_wird_abgelehnt(bestand):
    pfad, gruender = bestand
    _anlegen(pfad, gruender, "chefin", ["schreiber"], art="mensch")
    ausweis.widerrufen("chefin", aussteller=gruender, pfad=pfad, jetzt=T0)

    with pytest.raises(ValueError, match="widerrufen"):
        _anlegen(pfad, gruender, "bote", ["leser"],
                mandat={"von": "chefin", "rollen": ["schreiber"],
                        "gegenstand": ["abfallwirtschaft"]})


# --- Frage 3: Umkehrbarkeit --------------------------------------------------

def test_entwiderrufen_stellt_beglaubigung_wieder_her(bestand):
    pfad, gruender = bestand
    g = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad, jetzt=T0)
    assert not ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt

    ausweis.entwiderrufen("hausmeister", aussteller=gruender, pfad=pfad)
    assert ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt


def test_entwiderrufen_eines_nicht_widerrufenen_ist_wirkungslos(bestand):
    pfad, gruender = bestand
    g = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    ausweis.entwiderrufen("hausmeister", aussteller=gruender, pfad=pfad)  # kein Fehler
    assert ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt


def test_entwiderrufen_verlangt_dasselbe_recht(bestand):
    pfad, gruender = bestand
    g_h = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    g_l = _anlegen(pfad, gruender, "leser2", ["leser"])
    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad, jetzt=T0)

    with pytest.raises(PermissionError):
        ausweis.entwiderrufen("hausmeister", aussteller=g_l, pfad=pfad)
    assert not ausweis.loese_auf(geheimnis=g_h, pfad=pfad, jetzt=T0).beglaubigt


# --- Grenzwerte --------------------------------------------------------------

def test_widerruf_eines_nicht_existierenden_ausweises(bestand):
    pfad, gruender = bestand
    with pytest.raises(ValueError, match="kein Ausweis"):
        ausweis.widerrufen("gibtsnicht", aussteller=gruender, pfad=pfad, jetzt=T0)


def test_doppelter_widerruf_ist_kein_fehler(bestand):
    pfad, gruender = bestand
    g = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad, jetzt=T0)
    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad, jetzt=T0)  # kein Fehler
    assert not ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt


def test_widerruf_ohne_ausstellungsrecht_scheitert(bestand):
    pfad, gruender = bestand
    g_h = _anlegen(pfad, gruender, "hausmeister", ["leser"])
    g_l = _anlegen(pfad, gruender, "leser2", ["leser"])
    with pytest.raises(PermissionError):
        ausweis.widerrufen("hausmeister", aussteller=g_l, pfad=pfad, jetzt=T0)
    # Gegenprobe: der Ausweis lebt noch, der abgewiesene Versuch aenderte nichts
    assert ausweis.loese_auf(geheimnis=g_h, pfad=pfad, jetzt=T0).beglaubigt


def test_selbstwiderruf_ist_erlaubt_und_wirkt(bestand):
    """Frage aus dem Auftrag: darf sich jemand selbst aussperren? Ja -- wie
    ein Verwalter, der sein eigenes Konto sperrt. Keine Sonderpruefung dagegen
    (siehe Begruendung in ausweis.widerrufen())."""
    pfad, gruender = bestand
    g_amt = _anlegen(pfad, gruender, "amtsleiter", ["betreiber"], art="mensch")
    ausweis.widerrufen("amtsleiter", aussteller=g_amt, pfad=pfad, jetzt=T0)
    assert not ausweis.loese_auf(geheimnis=g_amt, pfad=pfad, jetzt=T0).beglaubigt


def test_widerruf_mit_gleichzeitig_gesetztem_gilt_bis(bestand):
    """Widerruf zieht auch VOR dem eingetragenen Ablauf -- er ist keine
    zweite, schwaechere Frist, sondern wirkt sofort."""
    pfad, gruender = bestand
    ende = T0 + timedelta(hours=1)
    g = _anlegen(pfad, gruender, "befristet", ["leser"], gilt_bis=ende.isoformat())
    assert ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt

    ausweis.widerrufen("befristet", aussteller=gruender, pfad=pfad, jetzt=T0)
    assert not ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=T0).beglaubigt, \
        "Widerruf vor gilt_bis wirkte nicht sofort"
    # und auch am/nach dem eigentlichen Ablauf bleibt es unbeglaubigt
    assert not ausweis.loese_auf(geheimnis=g, pfad=pfad, jetzt=ende).beglaubigt


# --- Herkunft am Eintrag (wie bei ausgestellt_von) ---------------------------

def test_widerruf_traegt_herkunft(bestand):
    pfad, gruender = bestand
    _anlegen(pfad, gruender, "hausmeister", ["leser"])
    ausweis.widerrufen("hausmeister", aussteller=gruender, pfad=pfad, jetzt=T0)

    eintrag = ausweis._finde(ausweis._lies_datei(pfad), "hausmeister")
    assert eintrag["widerrufen_am"] == T0.isoformat()
    assert eintrag["widerrufen_von"] == "gruender"
