"""Wache: jeder Knoten der behandelten S12-Haelfte braucht eine Urfassung.

ANLASS, gemessen am 2026-08-13: behandelte Haelfte 1096 Knoten,
s12_urfassungen 1070 -- 26 Nachzuegler ohne Sicherung. Die Luecke entsteht bei
jedem neuen Knoten neu (Sicherungslauf ist ein Schnappschuss, kein Trigger),
darum ist das hier eine WACHE, kein einmaliger Nachtrag. Faellt sie um, ist
der Ausweg woertlich Teil des Fehlertexts: der Sicherungslauf selbst.

Die eigentliche Pruefung (`fehlende_urfassungen`) ist eine REINE FUNKTION ueber
zwei Mengen -- deshalb laesst sie sich testen, ohne die echte Datenbank
anzufassen (test_fehlende_urfassungen_schweigt_bei_vollstaendiger_sicherung).
Der DB-Test bindet nur die Mengenbeschaffung an; die Logik selbst ist an
keiner Stelle dupliziert.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

import speicher
import teilung_s12

AUSWEG = "python3 kern/sicherung_s12.py --sichern"


def fehlende_urfassungen(behandelt_ids: set[str], gesicherte_ids: set[str]) -> list[str]:
    """Behandelte Knoten ohne Zeile in s12_urfassungen, sortiert (stabile
    Meldung). Reine Mengenfunktion -- kennt weder DB noch Schema."""
    return sorted(behandelt_ids - gesicherte_ids)


def _behandelte_ids_aus_db(conn) -> set[str]:
    ids = teilung_s12.bestand(conn)["knoten"]
    return {i for i in ids if teilung_s12.haelfte("knoten", i) == teilung_s12.BEHANDELT}


def _gesicherte_ids_aus_db(conn) -> set[str]:
    try:
        return {r[0] for r in conn.execute("SELECT node_id FROM s12_urfassungen")}
    except Exception:
        return set()


def test_alle_behandelten_knoten_haben_eine_urfassung():
    """ROT, solange auch nur ein behandelter Knoten keine Urfassung hat.
    Nennt die Kennungen namentlich -- sonst weiss niemand, welcher Fall
    die Regel bricht."""
    db = teilung_s12.haken_ort.DB
    if not (db.exists() and db.stat().st_size > 0):
        import pytest
        pytest.skip("keine reale Datenbank vorhanden")

    with speicher.lesen(db) as conn:
        behandelt = _behandelte_ids_aus_db(conn)
        gesichert = _gesicherte_ids_aus_db(conn)

    fehlend = fehlende_urfassungen(behandelt, gesichert)
    assert not fehlend, (
        f"{len(fehlend)} behandelte Knoten ohne Urfassung: {fehlend}. "
        f"Ausweg: {AUSWEG}"
    )


def test_fehlende_urfassungen_grenzwert_ein_fehlender_schlaegt_an():
    behandelt = {"n-1", "n-2", "n-3"}
    vollstaendig = {"n-1", "n-2", "n-3"}
    assert fehlende_urfassungen(behandelt, vollstaendig) == []

    fehlt_einer = {"n-1", "n-2"}
    assert fehlende_urfassungen(behandelt, fehlt_einer) == ["n-3"]


def test_fehlende_urfassungen_schweigt_bei_vollstaendiger_sicherung():
    """Negativfall ohne echte Datenbank: eine vollstaendige Menge meldet
    nichts, eine unvollstaendige nennt genau die fehlenden Kennungen."""
    behandelt = {f"k-{i}" for i in range(50)}

    vollstaendig = set(behandelt)
    assert fehlende_urfassungen(behandelt, vollstaendig) == []

    unvollstaendig = vollstaendig - {"k-7", "k-23"}
    assert fehlende_urfassungen(behandelt, unvollstaendig) == ["k-23", "k-7"]
