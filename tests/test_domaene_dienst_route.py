"""INT-REG-001: Port und Lebenszeichen einer Domaene kommen ueber eine eigene
JSON-Quelle, nicht aus einer Anzeige-HTML.

Rot vor gruen: Vor dieser Aenderung gab es weder domaene.lies_dienst() noch
/api/domaene-dienst -- der erste Anlauf im atelier las die Angaben aus der
Seite /eintrag/<kennung> zurueck und haette damit am Format einer
Darstellungsfunktion gehangen (gemeldet vom ausfuehrenden Agenten am
2026-08-18, deshalb hier nachgezogen).

Drei Lagen, drei Antworten -- dieselbe Unterscheidung wie bei der
Oberflaeche: nicht importiert / importiert ohne Dienst / importiert mit
Dienst. Ein leeres Ergebnis und "gar nicht da" sind fuer den Aufrufer zwei
verschiedene Saetze."""

import sqlite3
from pathlib import Path

import pytest

from kern.domaene import lies_dienst, speichere

WURZEL = Path(__file__).resolve().parents[1]
_QUELLEN = {"z1": {"bezeichnung": "Betriebsausgaben"}}


@pytest.fixture
def frische_db(tmp_path):
    db = tmp_path / "dienst.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    return db


def _paket(dienst, domaene="probe"):
    return {
        "contract_version": 1,
        "domaene": domaene,
        "bezeichnung": "Probe",
        "herkunft": "test",
        "stand": "2026-08-18T06:00:00+0200",
        "quellen": _QUELLEN,
        "regeln": [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}],
        "dienst": dienst,
        "oberflaeche": {"fassung": 1, "bildschirme": []},
    }


def test_nicht_importierte_domaene_ist_none(frische_db):
    assert lies_dienst("gibtsnicht", db=frische_db) is None


def test_importiert_ohne_dienst_ist_leeres_dict_nicht_none(frische_db):
    """ADR-013: eine Domaene darf reines Wissen sein. Das ist etwas anderes
    als 'nicht importiert' -- und der Unterschied ist der ganze Zweck."""
    speichere(_paket({}), db=frische_db)

    assert lies_dienst("probe", db=frische_db) == {}


def test_dienst_kommt_mit_port_und_lebenszeichen_zurueck(frische_db):
    dienst = {"start": ["__REPO_PFAD__/.venv/bin/python", "-m", "dienst"],
              "horcht_auf": 8812, "lebenszeichen": "/gesundheit"}
    speichere(_paket(dienst), db=frische_db)

    assert lies_dienst("probe", db=frische_db) == dienst


def test_zwei_domaenen_stoeren_einander_nicht(frische_db):
    speichere(_paket({"horcht_auf": 8812, "lebenszeichen": "/gesundheit"}, "eins"), db=frische_db)
    speichere(_paket({"horcht_auf": 8899, "lebenszeichen": "/leben"}, "zwei"), db=frische_db)

    assert lies_dienst("eins", db=frische_db)["horcht_auf"] == 8812
    assert lies_dienst("zwei", db=frische_db)["horcht_auf"] == 8899
