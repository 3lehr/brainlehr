"""Rot-vor-gruen fuer kern/belegvertrag.py (PLAN_OPENLEHR_2026-08-14.md H1).
Vorbild: openlehr/apps/openlehr/daemon/steuer/euer_zuordnung.py::_belegt/
_selbsttest_regeln."""

import pytest

from kern.belegvertrag import herkunftsart, pruefe_regeln, tatsache


def test_regel_mit_belegter_fundstelle_laedt():
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    quellen = {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}}
    pruefe_regeln(regeln, quellen)  # wirft nicht


def test_regel_ohne_fundstelle_wirft_mit_regelkennung_und_grund():
    regeln = [{"id": "r2", "ziel_id": "z1", "fundstelle": "Erfundener Text"}]
    quellen = {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}}
    with pytest.raises(ValueError) as exc:
        pruefe_regeln(regeln, quellen)
    text = str(exc.value)
    assert "r2" in text
    assert "Erfundener Text" in text


def test_fundstelle_als_teilstring_eines_anderen_wortes_zaehlt_als_beleg():
    # Entscheidung (wie Vorbild _belegt: `fundstelle in zeile[...]`, reiner
    # Substring-Test, gross-/kleinschreibungssensitiv): "ausgaben" ist
    # Teilstring von "Betriebsausgaben" und zaehlt als Beleg -- ein
    # woertliches Substring-Zitat ist immer noch woertlich, keine
    # Wortgrenzenpruefung im Vorbild.
    regeln = [{"id": "r3", "ziel_id": "z1", "fundstelle": "ausgaben"}]
    quellen = {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}}
    pruefe_regeln(regeln, quellen)  # wirft nicht


def test_widerspruechliche_tatsache_ergibt_none_nicht_false():
    def widerspruechlich():
        raise ValueError("zwei sich ausschliessende Angaben gespeichert")

    assert tatsache(widerspruechlich) is None
    assert tatsache(widerspruechlich) is not False


def test_leere_fundstelle_gilt_nicht_als_beleg():
    """Fund einer unabhaengigen Pruefung am 2026-08-14, Stunden nach dem Bau.

    `"" in text` ist in Python immer wahr. Ohne die Leerpruefung gilt damit
    ausgerechnet die Regel als belegt, die KEINE Fundstelle angibt -- der
    Vertrag haette genau seinen Zweck verfehlt. Der urspruengliche Selbsttest
    fand es nicht, weil er nur echte Fundstellen probierte: er hat den
    Positivfall und den Falschfall geprueft, nie den LEEREN Fall."""
    from kern.belegvertrag import belegt, pruefe_regeln

    assert belegt("", {"t": "beliebiger Text"}) is False
    assert belegt("   ", {"t": "beliebiger Text"}) is False

    for leer in ("", "   "):
        with pytest.raises(ValueError) as fehler:
            pruefe_regeln(
                [{"id": "ohne_beleg", "ziel_id": "z1", "fundstelle": leer}],
                {"z1": {"text": "beliebig"}},
            )
        assert "ohne_beleg" in str(fehler.value)


# ---------------------------------------------------------------------------
# FUND O3 (docs/SICHERHEITSFUNDE_2026-08-14.md): Herkunftsart der Quelle.

def test_herkunftsart_ohne_feld_ist_mitgeliefert():
    assert herkunftsart({"bezeichnung": "x"}) == ("mitgeliefert", None)


def test_herkunftsart_erkennt_bestandsverweis():
    assert herkunftsart({"bezeichnung": "x", "_herkunft": "bestand:abc123"}) == ("bestand", "abc123")


def test_herkunftsart_leerer_bestandsverweis_hat_keine_id():
    assert herkunftsart({"_herkunft": "bestand:   "}) == ("bestand", None)


def test_herkunft_schluessel_selbst_zaehlt_nicht_als_belegtext():
    """Rot-Probe des naiven Entwurfs: OHNE den Ausschluss in belegt() koennte
    eine Fundstelle wie 'bestand' durch das eigene Steuerfeld '_herkunft'
    belegt werden -- ein Beleg ueber Verwaltungsdaten statt Inhalt. Von Hand
    geprueft: `"bestand" in "bestand:abc"` ist True, ohne den Feldausschluss
    haette diese Regel geladen."""
    from kern.belegvertrag import belegt

    quelle = {"bezeichnung": "voellig anderer Text", "_herkunft": "bestand:abc123"}
    assert belegt("bestand", quelle) is False
