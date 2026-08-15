"""Rot-vor-Gruen fuer die Verschachtelung in kern/baustein.py (ADR-019).

Der Selbsttest in `kern/baustein.py --selftest` deckt dasselbe ab; diese
Datei haelt es zusaetzlich in der Suite fest, damit `pytest` es ohne
Sonderaufruf faengt.
"""
from __future__ import annotations

from baustein import Baustein, baumreihenfolge, herkunft_nach_textaenderung, praeferenzpaare


def _b(kennung: str, eltern: str | None = None, rang: float = 0.0) -> Baustein:
    return Baustein(kennung=kennung, typ="absatz", text=kennung, eltern=eltern, rang=rang)


def test_leeres_dokument_leere_reihenfolge():
    assert baumreihenfolge([]) == []


def test_baustein_ohne_eltern_ist_wurzel():
    a = _b("a" * 12)
    assert [b.kennung for b in baumreihenfolge([a])] == [a.kennung]


def test_zwei_ebenen_tief_kind_direkt_hinter_eltern():
    wurzel = _b("w" * 12, rang=0.0)
    andere_wurzel = _b("x" * 12, rang=1.0)
    kind = _b("k" * 12, eltern=wurzel.kennung)
    enkel = _b("e" * 12, eltern=kind.kennung)
    geordnet = baumreihenfolge([andere_wurzel, enkel, wurzel, kind])
    assert [b.kennung for b in geordnet] == [
        wurzel.kennung, kind.kennung, enkel.kennung, andere_wurzel.kennung,
    ]


def test_geschwister_nach_rang_sortiert_nicht_nach_einfuegereihenfolge():
    erst_eingefuegt = _b("1" * 12, rang=5.0)
    zuletzt_eingefuegt = _b("2" * 12, rang=0.0)
    geordnet = baumreihenfolge([erst_eingefuegt, zuletzt_eingefuegt])
    assert [b.kennung for b in geordnet] == [zuletzt_eingefuegt.kennung, erst_eingefuegt.kennung]


def test_eltern_zeigt_auf_nicht_existierende_kennung_wird_wurzel():
    """Grenzwert aus ADR-019: ein Baustein darf nicht verschwinden, nur weil
    sein Elternteil (noch) nicht existiert -- er wird als Wurzel gelesen."""
    verwaist = _b("v" * 12, eltern="9" * 12)
    assert [b.kennung for b in baumreihenfolge([verwaist])] == [verwaist.kennung]


def test_zyklus_baustein_ist_sein_eigener_elternteil():
    """Preis der Elternfeld-Bauform: ein Zyklus ist moeglich, ein Kind-Array
    haette ihn strukturell verhindert. Muss abgefangen werden, nicht crashen."""
    selbst = _b("z" * 12, eltern="z" * 12)
    assert [b.kennung for b in baumreihenfolge([selbst])] == [selbst.kennung]


def test_zyklus_ueber_zwei_bausteine_kein_verlust_keine_endlosschleife():
    a = _b("a" * 12, eltern="b" * 12)
    b = _b("b" * 12, eltern="a" * 12)
    ergebnis = baumreihenfolge([a, b])
    assert {x.kennung for x in ergebnis} == {a.kennung, b.kennung}
    assert len(ergebnis) == 2, "kein Baustein aus dem Ring darf doppelt oder gar nicht auftauchen"


# ---------------------------------------------------------- Herkunftsverlauf
# Rot-vor-Gruen fuer den Dreischritt aus dem Betreiberauftrag 2026-08-15:
# Vorschlag angenommen -> Mensch aendert von Hand -> Mensch nimmt zurueck.


def test_dreischritt_widerspruch_dann_ruecknahme_ist_ablesbar():
    h1, q1, v1 = herkunft_nach_textaenderung(
        herkunft="vorschlag_angenommen", herkunftsquelle="anmerkung:aa",
        text_alt="Vorschlag", text_neu="Mensch", verlauf=[], jetzt="t1",
    )
    assert (h1, q1) == ("eingegeben", None), "Handaenderung gewinnt, wie vor dieser Aenderung"
    assert v1 == [{
        "zeitpunkt": "t1", "herkunft_vorher": "vorschlag_angenommen",
        "herkunftsquelle_vorher": "anmerkung:aa", "text_vorher": "Vorschlag",
        "zurueckgenommen_am": None,
    }]

    h2, q2, v2 = herkunft_nach_textaenderung(
        herkunft=h1, herkunftsquelle=q1, text_alt="Mensch", text_neu="Vorschlag",
        verlauf=v1, jetzt="t2",
    )
    assert (h2, q2) == ("vorschlag_angenommen", "anmerkung:aa"), \
        "Ruecknahme stellt die vorherige Herkunft wieder her"
    assert len(v2) == 1, "derselbe Eintrag wird ergaenzt, kein zweiter"
    assert v2[0]["zurueckgenommen_am"] == "t2"

    baustein = Baustein(kennung="q" * 12, typ="absatz", text="Vorschlag",
                        herkunft=h2, herkunftsquelle=q2, herkunftsverlauf=v2)
    assert praeferenzpaare(baustein) == [{
        "herkunft_bewertet": "vorschlag_angenommen", "herkunftsquelle": "anmerkung:aa",
        "text_abgeleitet": "Vorschlag", "bevorzugt": "abgeleitet",
        "zeitpunkt_widerspruch": "t1", "zeitpunkt_ruecknahme": "t2",
    }]


def test_negativfall_nie_geaendert_erzeugt_kein_paar():
    nie = Baustein(kennung="r" * 12, typ="absatz", text="Nie angefasst.")
    assert praeferenzpaare(nie) == []


def test_negativfall_zwei_handaenderungen_ohne_vorschlag_erzeugt_kein_paar():
    h1, q1, v1 = herkunft_nach_textaenderung(
        herkunft="eingegeben", herkunftsquelle=None, text_alt="A", text_neu="B",
        verlauf=[], jetzt="t1",
    )
    h2, q2, v2 = herkunft_nach_textaenderung(
        herkunft=h1, herkunftsquelle=q1, text_alt="B", text_neu="C", verlauf=v1, jetzt="t2",
    )
    assert v2 == []
    baustein = Baustein(kennung="s" * 12, typ="absatz", text="C",
                        herkunft=h2, herkunftsquelle=q2, herkunftsverlauf=v2)
    assert praeferenzpaare(baustein) == []


def test_grenzwert_aehnlicher_text_ist_keine_ruecknahme():
    """Nur EXAKTE Gleichheit zaehlt -- eine Aehnlichkeitsschwelle ist nicht
    gemessen (CLAUDE.md: Schwellen sind gemessen, nicht gesetzt)."""
    _, _, v1 = herkunft_nach_textaenderung(
        herkunft="abgeleitet", herkunftsquelle="knoten:x",
        text_alt="A", text_neu="B", verlauf=[], jetzt="t1",
    )
    h2, q2, v2 = herkunft_nach_textaenderung(
        herkunft="eingegeben", herkunftsquelle=None,
        text_alt="B", text_neu="A, fast", verlauf=v1, jetzt="t2",
    )
    assert (h2, q2) == ("eingegeben", None), "aehnlich loest keine Ruecknahme aus"
    assert v2[-1]["zurueckgenommen_am"] is None, "der Eintrag bleibt offen"


def test_grenzwert_leerer_text_als_ruecknahmeziel():
    _, _, v1 = herkunft_nach_textaenderung(
        herkunft="abgeleitet", herkunftsquelle="knoten:x",
        text_alt="", text_neu="von Hand", verlauf=[], jetzt="t1",
    )
    h2, q2, v2 = herkunft_nach_textaenderung(
        herkunft="eingegeben", herkunftsquelle=None,
        text_alt="von Hand", text_neu="", verlauf=v1, jetzt="t2",
    )
    assert (h2, q2) == ("abgeleitet", "knoten:x")
    assert v2[-1]["zurueckgenommen_am"] == "t2"


def test_grenzwert_offener_eintrag_ohne_treffer_bleibt_offen():
    """Verlauf mit genau einem Eintrag: ein dritter, unbeteiligter Text
    loest weder eine Ruecknahme noch einen zweiten Eintrag aus (Herkunft ist
    schon 'eingegeben')."""
    _, _, v1 = herkunft_nach_textaenderung(
        herkunft="vorschlag_angenommen", herkunftsquelle="anmerkung:aa",
        text_alt="Vorschlag", text_neu="Mensch", verlauf=[], jetzt="t1",
    )
    h2, q2, v2 = herkunft_nach_textaenderung(
        herkunft="eingegeben", herkunftsquelle=None,
        text_alt="Mensch", text_neu="noch ein anderer Text", verlauf=v1, jetzt="t2",
    )
    assert (h2, q2) == ("eingegeben", None)
    assert len(v2) == 1
    assert v2[0]["zurueckgenommen_am"] is None
