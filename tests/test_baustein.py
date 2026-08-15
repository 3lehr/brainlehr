"""Rot-vor-Gruen fuer die Verschachtelung in kern/baustein.py (ADR-019).

Der Selbsttest in `kern/baustein.py --selftest` deckt dasselbe ab; diese
Datei haelt es zusaetzlich in der Suite fest, damit `pytest` es ohne
Sonderaufruf faengt.
"""
from __future__ import annotations

from baustein import Baustein, baumreihenfolge


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
