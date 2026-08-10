"""Tests fuer Geltungspruefung (gilt_ab/gilt_bis) in knowledge_search().

Luecke, die diesen Auftrag ausloeste: knowledge_add/knowledge_update setzen
gilt_ab/gilt_bis seit kurzem, aber knowledge_search wertete sie nie aus --
eine abgelaufene Norm kam ununterscheidbar neben der geltenden zurueck.

Grenzwerte fuer gilt_bis INKLUSIV (Stichtag == gilt_bis: gilt noch, letzter
Tag) -- kanonisch festgehalten in normkraft.py::in_kraft, seit 2026-08-06
auch dort so geprueft (vorher wich es ab, siehe test_geltung_konsistenz.py
fuer die Kreuzprobe). Siehe Docstring von _geltung_status().
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.executemany(
        """INSERT INTO knowledge_nodes
           (id, path, project_id, title, summary, content, level, source, norm_rang, gilt_ab, gilt_bis, norm_entscheidung,
            norm_entschieden_von, norm_entschieden_grund)
           VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', ?, ?, ?, ?, 'skript:test', 'Testvorrichtung')""",
        [
            # Fakt -- norm_rang NULL, von der Geltungspruefung unberuehrt.
            ("f1", "/steuer/fakt-abschreibung", "AfA Fakt", "Abschreibung Fakttext",
             None, None, None, "keine_norm"),
            # Norm, aktuell gueltig.
            ("n-aktuell", "/steuer/regel-aktuell", "Abschreibung aktuell", "Abschreibung geltende Regel",
             3, "2026-01-01T00:00:00+01:00", "2026-12-31T23:59:59+01:00", "norm_befristet"),
            # Norm, abgelaufen.
            ("n-abgelaufen", "/steuer/regel-2024", "Abschreibung 2024", "Abschreibung alte Regel",
             3, "2024-01-01T00:00:00+01:00", "2024-12-31T23:59:59+01:00", "norm_befristet"),
            # Norm, noch nicht in Kraft.
            ("n-kuenftig", "/steuer/regel-2027", "Abschreibung 2027", "Abschreibung kuenftige Regel",
             3, "2027-01-01T00:00:00+01:00", None, "norm_unbefristet"),
            # Norm, unbefristet (gilt_bis NULL).
            ("n-unbefristet", "/steuer/regel-dauer", "Abschreibung dauerhaft", "Abschreibung unbefristete Regel",
             3, "2020-01-01T00:00:00+01:00", None, "norm_unbefristet"),
        ],
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _ids(result):
    return [r["id"] for r in result["results"]]


# --- a) rot vor gruen ist im Commit-Diff belegt (siehe Auftragsantwort), nicht hier ---


def test_abgelaufene_norm_rutscht_ans_ende_und_wird_markiert(temp_db):
    result = kms.knowledge_search("Abschreibung", stichtag="2026-08-06T00:00:00+01:00")
    ids = _ids(result)
    assert ids.index("n-abgelaufen") > ids.index("n-aktuell")
    abgelaufen = next(r for r in result["results"] if r["id"] == "n-abgelaufen")
    assert abgelaufen["geltung"] == "abgelaufen"
    assert abgelaufen["gilt_bis"] == "2024-12-31T23:59:59+01:00"
    # nachrangig, nicht verborgen:
    assert "n-abgelaufen" in ids


def test_kuenftige_norm_rutscht_ans_ende_und_wird_markiert(temp_db):
    result = kms.knowledge_search("Abschreibung", stichtag="2026-08-06T00:00:00+01:00")
    ids = _ids(result)
    assert ids.index("n-kuenftig") > ids.index("n-aktuell")
    kuenftig = next(r for r in result["results"] if r["id"] == "n-kuenftig")
    assert kuenftig["geltung"] == "noch_nicht_in_kraft"
    assert kuenftig["gilt_ab"] == "2027-01-01T00:00:00+01:00"


def test_nur_geltende_blendet_statt_nachzureihen(temp_db):
    result = kms.knowledge_search("Abschreibung", stichtag="2026-08-06T00:00:00+01:00", nur_geltende=True)
    ids = _ids(result)
    assert "n-abgelaufen" not in ids
    assert "n-kuenftig" not in ids
    assert "n-aktuell" in ids


def test_gilt_bis_null_nie_abgelaufen(temp_db):
    result = kms.knowledge_search("Abschreibung", stichtag="2099-01-01T00:00:00+01:00")
    unbefristet = next(r for r in result["results"] if r["id"] == "n-unbefristet")
    # gilt_bis NULL heisst unbefristet -- kein "abgelaufen", darum keine
    # Nachrangig-Markierung noetig (bleibt wie ein regulaerer Treffer).
    assert "geltung" not in unbefristet


@pytest.mark.parametrize("stichtag,erwartet", [
    ("2026-01-01T00:00:00+01:00", "in_kraft"),          # Stichtag == gilt_ab: gilt
    ("2026-12-31T23:59:59+01:00", "in_kraft"),           # Stichtag == gilt_bis: gilt, letzter Tag
    ("2027-01-01T00:00:00+01:00", "abgelaufen"),         # Stichtag == gilt_bis + 1 Tag
    ("2025-12-31T23:59:59+01:00", "noch_nicht_in_kraft"),  # Stichtag == gilt_ab - 1 Sekunde
])
def test_grenzwerte_gilt_ab_gilt_bis(temp_db, stichtag, erwartet):
    result = kms.knowledge_search("Abschreibung", stichtag=stichtag)
    aktuell = next(r for r in result["results"] if r["id"] == "n-aktuell")
    if erwartet == "in_kraft":
        assert aktuell.get("geltung") in (None, "in_kraft")
    else:
        assert aktuell["geltung"] == erwartet


def test_fakten_unveraendert_vor_und_nach_geltungspruefung(temp_db):
    """Nichtaenderung: reine Fakten (norm_rang NULL) liefern exakt dieselbe
    Reihenfolge/Form, ob mit oder ohne stichtag/nur_geltende aufgerufen."""
    ohne = kms.knowledge_search("Fakttext")
    mit_stichtag = kms.knowledge_search("Fakttext", stichtag="2020-01-01T00:00:00+01:00")
    assert _ids(ohne) == _ids(mit_stichtag) == ["f1"]
    assert ohne["results"][0] == mit_stichtag["results"][0]
    assert "geltung" not in ohne["results"][0]
