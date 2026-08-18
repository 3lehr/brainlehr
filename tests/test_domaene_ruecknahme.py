"""Rot-vor-gruen fuer INT-UPD-002 (docs/REQUIREMENTS_INTERFACE_KOMPAT.md):
speichere() traegt eine Importkennung, nimm_import_zurueck() nimmt genau
diesen Importvorgang zurueck. Abnahmekriterium des Auftrags ist
tests/test_interface_kompat_katalog.py::test_int_upd_002_import_ist_ruecknehmbar
(TABU, nicht angefasst) -- dieser Datei geht es um die Details drumherum:
Negativfall (in Kraft gesetzte Zeilen ueberleben), Grenzwert (zwei Importe
derselben Domaene, der zweite darf den ersten nicht mitnehmen) und
Grenzfall (unbekannte Kennung)."""

import sqlite3
from pathlib import Path

import pytest

from kern.domaene import nimm_import_zurueck, setze_in_kraft, speichere

_WURZEL = Path(__file__).resolve().parent.parent


@pytest.fixture
def frische_db(tmp_path):
    """Erstanlage aus dem echten Schema, leer -- wie tests/test_domaene.py."""
    db = tmp_path / "ruecknahme.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((_WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    return db


def _paket(regeln, quellen, **zusatz):
    basis = {
        "domaene": "steuer",
        "bezeichnung": "Steuer und Belege",
        "herkunft": "test",
        "stand": "2026-08-14T00:00:00+0200",
        "quellen": quellen,
        "regeln": regeln,
        "contract_version": 1,
        "dienst": {},
        "oberflaeche": {"fassung": 1, "bildschirme": []},
    }
    basis.update(zusatz)
    return basis


def _anzahl_zeilen(db) -> int:
    with sqlite3.connect(str(db)) as conn:
        (n,) = conn.execute("select count(*) from knowledge_nodes").fetchone()
    return n


def test_grundfall_ruecknahme_entfernt_alle_beruehrten_zeilen(frische_db):
    paket = _paket(
        [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}],
        {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}},
    )
    ergebnis = speichere(paket, db=frische_db)
    assert ergebnis["importkennung"]
    angelegt = ergebnis["gespeichert"]
    assert angelegt > 0

    bericht = nimm_import_zurueck(ergebnis["importkennung"], db=frische_db)
    assert bericht == {"entfernt": angelegt, "stehen_geblieben": 0}
    assert _anzahl_zeilen(frische_db) == 0


def test_negativfall_in_kraft_gesetzte_regel_ueberlebt_ruecknahme(frische_db):
    paket = _paket(
        [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}],
        {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}},
    )
    ergebnis = speichere(paket, db=frische_db)
    setze_in_kraft("steuer", wer="Testmensch", grund="Testfall", norm_rang=3, db=frische_db)

    bericht = nimm_import_zurueck(ergebnis["importkennung"], db=frische_db)

    assert bericht["stehen_geblieben"] == 1
    assert bericht["entfernt"] == ergebnis["gespeichert"] - 1
    with sqlite3.connect(str(frische_db)) as conn:
        conn.row_factory = sqlite3.Row
        zeile = conn.execute(
            "SELECT norm_entscheidung FROM knowledge_nodes WHERE id='domaenenregel-steuer-r1'"
        ).fetchone()
    assert zeile is not None
    assert zeile["norm_entscheidung"] == "norm_unbefristet"


def test_grenzwert_zweiter_import_nimmt_ersten_nicht_mit(frische_db):
    paket1 = _paket(
        [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}],
        {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}},
    )
    ergebnis1 = speichere(paket1, db=frische_db)

    # Zweiter Import derselben Domaene: r1/z1/wurzel/oberflaeche unveraendert
    # (uebersprungen), nur r2/z2 sind neu -- nur die duerfen in kennung2s
    # Buchfuehrung landen.
    paket2 = _paket(
        [
            {"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"},
            {"id": "r2", "ziel_id": "z2", "fundstelle": "Werbungskosten"},
        ],
        {
            "z1": {"bezeichnung": "Betriebsausgaben (netto)"},
            "z2": {"bezeichnung": "Werbungskosten"},
        },
    )
    ergebnis2 = speichere(paket2, db=frische_db)
    assert ergebnis2["gespeichert"] == 2  # nur r2 + z2
    assert ergebnis2["uebersprungen"] >= 2  # wurzel + oberflaeche mindestens

    bericht = nimm_import_zurueck(ergebnis2["importkennung"], db=frische_db)
    assert bericht == {"entfernt": 2, "stehen_geblieben": 0}

    with sqlite3.connect(str(frische_db)) as conn:
        ids = {row[0] for row in conn.execute("select id from knowledge_nodes")}
    assert "domaenenregel-steuer-r1" in ids
    assert "domaenenquelle-steuer-z1" in ids
    assert "domaenenregel-steuer-r2" not in ids
    assert "domaenenquelle-steuer-z2" not in ids

    # kennung1 nimmt danach noch immer alles ab, was der erste Import anlegte.
    bericht1 = nimm_import_zurueck(ergebnis1["importkennung"], db=frische_db)
    assert bericht1 == {"entfernt": ergebnis1["gespeichert"], "stehen_geblieben": 0}
    assert _anzahl_zeilen(frische_db) == 0


def test_grenzfall_unbekannte_kennung_wirft_sprechenden_fehler(frische_db):
    with pytest.raises(ValueError):
        nimm_import_zurueck("nie-gab-es-das", db=frische_db)
