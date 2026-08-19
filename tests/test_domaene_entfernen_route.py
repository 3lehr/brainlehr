"""Eine Domaene laesst sich wieder entfernen -- ueber denselben Weg, der sie
hereingebracht hat.

ANLASS (Betreiberfrage 2026-08-19): „wie bekommen wir es wieder entfernt?"
Gemessen an diesem Tag: `kern.domaene.nimm_import_zurueck()` existiert seit
Langem und ist sorgfaeltig gebaut -- aber kein Endpunkt und kein Menuepunkt
fuehrte dorthin. Man konnte einbinden und nicht loesen.

WARUM DAS SCHLIMMER IST ALS EINE FEHLENDE FUNKTION: Wer nicht entfernen kann,
probiert nichts aus. Ein Einbindeweg ohne Rueckweg macht jede Domaene zu einer
Entscheidung auf Dauer.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
if str(WURZEL) not in sys.path:
    sys.path.insert(0, str(WURZEL))

from berichte import entscheidungen_server as server  # noqa: E402


@pytest.fixture()
def frische_db(tmp_path) -> str:
    """Echtes Schema, leerer Bestand -- Erstanlage, nicht gewachsen
    (Hausregel: zwei Ausgangszustaende, geprueft wird meist der falsche).
    Uebernommen aus tests/test_domaene.py, nicht neu erfunden."""
    db = tmp_path / "entfernen.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    return str(db)


@pytest.fixture()
def paket() -> dict:
    return {
        "contract_version": 1,
        "domaene": "probefall",
        "bezeichnung": "Probefall",
        "herkunft": "Test",
        "stand": "2026-08-19",
        "quellen": {},
        "regeln": [],
        "dienst": {},
        "oberflaeche": {"fassung": 1, "bildschirme": []},
    }


def test_entfernen_gibt_es_ueberhaupt():
    """Der Weg muss existieren -- vorher fuehrte keiner dorthin."""
    assert hasattr(server, "_domaene_entfernen"), "kein Weg zum Entfernen"


def test_unbekannte_kennung_wird_benannt_statt_still_zu_scheitern(frische_db):
    """Eine leise Null waere von einer erfolgreichen Ruecknahme ohne Zeilen
    nicht zu unterscheiden -- dieselbe Begruendung wie in
    kern.domaene.nimm_import_zurueck."""
    ergebnis = server._domaene_entfernen({"kennung": "gibtsnicht"}, db=frische_db)
    assert ergebnis.get("entfernt") is not True
    assert ergebnis.get("meldung"), "kein Satz fuer den Menschen"
    assert "traceback" not in json.dumps(ergebnis).lower()


def test_fehlende_kennung_wird_abgelehnt(frische_db):
    ergebnis = server._domaene_entfernen({}, db=frische_db)
    assert ergebnis.get("entfernt") is not True
    assert ergebnis.get("meldung")


def test_import_und_ruecknahme_in_beide_richtungen(frische_db, paket):
    """Der eigentliche Beleg: erst hereinbringen, dann wieder loesen -- und
    dazwischen messen, dass ueberhaupt etwas da war. Ohne die Zwischenprobe
    haelt 'nachher ist nichts da' auch dann, wenn nie etwas ankam."""
    db = frische_db
    from kern import domaene

    rein = domaene.speichere(paket, db=db)
    assert rein.get("angenommen") is True, rein
    kennung = rein.get("importkennung")
    assert kennung, "ohne Importkennung gibt es nichts zurueckzunehmen"
    assert rein.get("gespeichert", 0) > 0, "nichts geschrieben -- die Ruecknahme waere ohne Gegenstand"

    raus = server._domaene_entfernen({"kennung": kennung}, db=db)
    assert raus.get("entfernt") is True, raus
    assert raus.get("anzahl", 0) > 0
    assert raus.get("meldung")
