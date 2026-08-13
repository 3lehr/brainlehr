"""Deckt messungen/metaphern_regelpaare.py ab -- Schritt 1 aus
docs/PLAN_METAPHERN_2026-08-13.md (Regelpaare und Fallmengen, KEINE Messung).

Rot-Probe zu Abnahme 2 (von Hand gefahren, nicht Teil dieses Laufs): die
Schwelle-1-Pruefung in pruefe_paar() (der Block 'if len(fm["nicht_gemeint"])
< 1') wurde einmalig auskommentiert -- test_negativfall_unvollstaendiges_paar_wird_abgewiesen
schlug daraufhin fehl (AssertionError bei 'assert not ok'), weil das
unvollstaendige Paar dann als gueltig durchging. Nach dem Zurueckstellen des
Blocks lief die volle Datei wieder gruen. Damit ist belegt, dass der Test
tatsaechlich die Schwelle-1-Pruefung prueft und nicht zufaellig gruen ist.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "messungen")]

import metaphern_regelpaare as mr  # noqa: E402


def _paar(nicht_gemeint: list[str], gleiche_mengen: bool = True) -> dict:
    fallmengen = mr._fallmengen(genannt=["g"], gemeint=["m"], nicht_gemeint=nicht_gemeint)
    return {
        "id": "test",
        "fassungen": {"woertlich": "A", "passend": "B", "unpassend": "C"},
        "fallmengen": fallmengen,
    }


# --------------------------------------------------------- Abnahme 1, 3, 6
def test_alle_regelpaare_haben_drei_fallmengen_und_menge3_nicht_leer():
    assert len(mr.REGELPAARE) >= 4
    for paar in mr.REGELPAARE:
        for fassung in mr.FASSUNGEN:
            fm = paar["fallmengen"][fassung]
            assert set(mr.MENGEN) <= set(fm.keys())
            assert len(fm["nicht_gemeint"]) >= 1


def test_gegenprobe_vollstaendiges_paar_wird_angenommen():
    """Abnahme 3: Gegenprobe in die andere Richtung -- ein vollstaendiges
    Paar wird angenommen. Ohne diese Richtung wuerde auch eine Pruefung
    bestehen, die schlicht alles abweist."""
    for paar in mr.REGELPAARE:
        ok, grund = mr.pruefe_paar(paar)
        assert ok, f"{paar['id']}: {grund}"
        assert grund is None


def test_alle_vier_regelpaare_stammen_aus_dem_echten_bestand():
    for paar in mr.REGELPAARE:
        assert paar.get("quelle", "").startswith("CLAUDE.md")


# ------------------------------------------------------------------ Abnahme 2
def test_negativfall_unvollstaendiges_paar_wird_abgewiesen():
    """Ein Paar ohne nicht-gemeinte Faelle (Menge 3 leer) wird abgewiesen."""
    ok, grund = mr.pruefe_paar(_paar(nicht_gemeint=[]))
    assert not ok
    assert "nicht_gemeint" in grund


# ------------------------------------------------------------------ Abnahme 4
def test_grenzwert_genau_ein_fall_reicht():
    ok, _ = mr.pruefe_paar(_paar(nicht_gemeint=["genau einer"]))
    assert ok


def test_grenzwert_null_faelle_reicht_nicht():
    ok, _ = mr.pruefe_paar(_paar(nicht_gemeint=[]))
    assert not ok


# ------------------------------------------------------------------ Abnahme 5
def test_abweichende_fallmengen_je_fassung_machen_paar_ungueltig():
    paar = _paar(nicht_gemeint=["z"])
    # Eine Fassung erhaelt eine eigene, abweichende Fallmengen-Zuordnung --
    # das Paar ist damit ungueltig, unabhaengig davon wie gut die Metapher ist.
    paar["fallmengen"]["passend"] = {
        "genannt": ["g"], "gemeint": ["m"], "nicht_gemeint": ["ANDERER FALL"]}
    ok, grund = mr.pruefe_paar(paar)
    assert not ok
    assert "weichen" in grund


def test_gleiche_fallmengen_je_fassung_bleiben_gueltig():
    # Gegenprobe zur vorigen: unveraendert (alle drei Fassungen identisch) bleibt gueltig.
    ok, _ = mr.pruefe_paar(_paar(nicht_gemeint=["z"]))
    assert ok


# ---------------------------------------------------------------------- Rest
def test_pruefe_alle_liefert_ergebnis_je_paar():
    ergebnisse = mr.pruefe_alle(mr.REGELPAARE)
    assert len(ergebnisse) == len(mr.REGELPAARE)
    assert all(ok for _, ok, _ in ergebnisse)


def test_selftest_laeuft_ohne_fehler():
    mr._selftest()
