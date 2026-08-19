#!/usr/bin/env python3
"""Tests fuer kern/risikoeinstufung.py -- E18 (Vier-Augen selektiv) + U06 (Routing ohne Inhaltsleck)."""
import pytest

from kern.risikoeinstufung import (
    Stufe,
    VierAugenErforderlich,
    melde,
    pruefe_vier_augen,
    senke_lesen,
    stufe_ereignis,
    stufe_vorgang,
)

# `hold` stand hier bis 2026-08-19 als EINE Art auf NIEDRIG -- und traf damit
# ausgerechnet die gefaehrliche Richtung nicht. `rechtssperre_aufheben`
# (kern/kundenschluessel.py) gibt Daten zur Vernichtung frei; `widerrufen()`
# wirft nur, solange die Sperre steht. Setzen ist folgenlos, Aufheben ist der
# unumkehrbare Weg.
VORGANGSARTEN_HOCH = ["regelrang", "export", "connector", "providerwechsel",
                      "ausnahme", "hold_aufheben"]
VORGANGSARTEN_NIEDRIG = ["hold_setzen"]


@pytest.mark.parametrize("art", VORGANGSARTEN_HOCH + VORGANGSARTEN_NIEDRIG)
def test_e18_jede_vorgangsart_ist_eingestuft(art):
    assert stufe_vorgang(art) in (Stufe.HOCH, Stufe.NIEDRIG)


@pytest.mark.parametrize("art", VORGANGSARTEN_HOCH)
def test_e18_hoch_ohne_zweites_augenpaar_wird_abgewiesen(art):
    with pytest.raises(VierAugenErforderlich):
        pruefe_vier_augen(art, zweites_augenpaar=None)


@pytest.mark.parametrize("art", VORGANGSARTEN_HOCH)
def test_e18_hoch_mit_zweitem_augenpaar_geht_durch(art):
    assert pruefe_vier_augen(art, zweites_augenpaar="pruefer-x") is Stufe.HOCH


def test_e18_gegenprobe_niedrig_laeuft_ohne_zweites_augenpaar_durch():
    # Die Zeile, die Selektivitaet beweist: eine Matrix, die ALLES gatet,
    # wuerde hier ebenfalls werfen. Das darf nicht passieren.
    assert pruefe_vier_augen("hold_setzen", zweites_augenpaar=None) is Stufe.NIEDRIG


def test_e18_die_riskante_haelfte_von_hold_ist_gegatet():
    """Rot vor gruen: Gegen den Stand vor 2026-08-19 kannte die Matrix nur
    `hold` auf NIEDRIG -- dieser Test schlug dort mit KeyError bzw. NIEDRIG
    fehl. Er ist der einzige, der die Trennung erzwingt; alle anderen waeren
    auch mit der groben Einstufung gruen geblieben."""
    assert stufe_vorgang("hold_aufheben") is Stufe.HOCH
    with pytest.raises(VierAugenErforderlich):
        pruefe_vier_augen("hold_aufheben", zweites_augenpaar=None)
    # Und die harmlose Richtung darf dadurch NICHT mitgefangen werden --
    # sonst waere aus einer zu groben eine zu strenge Matrix geworden.
    assert pruefe_vier_augen("hold_setzen", zweites_augenpaar=None) is Stufe.NIEDRIG


def test_u06_ohne_inhaltsleck():
    geheimer_titel = "STRENG-GEHEIM-XK9-Kuendigung-Mandant-Berger"
    m = melde("konflikt", "eintrag-42")
    assert geheimer_titel not in m.text
    assert geheimer_titel not in m.objekt_kennung
    for kanal, eintraege in {"eskalation": senke_lesen("eskalation"), "protokoll": senke_lesen("protokoll")}.items():
        for e in eintraege:
            assert geheimer_titel not in e.text


def test_u06_routing_unterschiedliche_kanaele_nach_stufe():
    assert stufe_ereignis("konflikt") is Stufe.HOCH
    assert stufe_ereignis("policy_denial") is Stufe.HOCH
    assert stufe_ereignis("ablauf") is Stufe.NIEDRIG
    assert stufe_ereignis("quellenluecke") is Stufe.NIEDRIG

    m_hoch = melde("konflikt", "eintrag-hoch")
    m_niedrig = melde("ablauf", "eintrag-niedrig")
    assert m_hoch.kanal != m_niedrig.kanal


@pytest.mark.parametrize("art", ["konflikt", "ablauf", "quellenluecke", "policy_denial"])
def test_u06_jede_ereignisart_ist_eingestuft(art):
    assert stufe_ereignis(art) in (Stufe.HOCH, Stufe.NIEDRIG)
