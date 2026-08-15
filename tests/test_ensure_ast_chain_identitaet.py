"""Befund 2026-08-15, Knoten 3e6fdd55 (Pfad /woanders): ein Astknoten, den
_ensure_ast_chain() beim Anlegen (neuer_ast=True) automatisch erzeugt, trug
actor/session/model/client/bedient_von allesamt NULL -- der Pfad legte den
Knoten an, bevor irgendeine Identitaet aufgeloest wurde. knowledge_add() hatte
sie fuer den ausloesenden Kindknoten laengst ermittelt (_identity() lief schon
vorher), nur die Weitergabe fehlte. Ein Eintrag ohne Herkunft ist von einem
untergeschobenen nicht zu unterscheiden.

Gegenprobe (Aufgabe 2, L-34e5f8): der ausloesende Kindknoten selbst trug
Identitaet schon vorher -- dieser Test darf daran nichts aendern.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

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
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _row(temp_db, path):
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT actor, session, model, client, bedient_von FROM knowledge_nodes WHERE path = ?",
        (path,),
    ).fetchone()
    conn.close()
    return row


def test_astknoten_traegt_identitaet_wie_der_ausloesende_kindknoten(temp_db, monkeypatch):
    # Feste Identitaet statt der Ausweis-Umgebungsaufloesung, damit der Test
    # nicht von der laufenden Sitzung abhaengt (wie in test_update_fremder_actor.py).
    monkeypatch.setenv("BEGOD_KNOWLEDGE_SESSION", "sitzung-test-73")
    res = kms.knowledge_add("/woanders/tief", "Tiefer Fund", "Zusammenfassung",
                            neuer_ast=True, source="test", model="claude-opus-5")
    assert res.get("status") == "created", res

    astknoten = _row(temp_db, "/woanders")
    assert astknoten is not None, "Astknoten /woanders wurde nicht angelegt"
    assert astknoten["actor"] is not None, "actor blieb NULL -- der urspruengliche Fund"
    assert astknoten["session"] is not None, "session blieb NULL"
    assert astknoten["model"] is not None, "model blieb NULL"
    assert astknoten["client"] is not None, "client blieb NULL"
    # bedient_von ist in DREI Faellen legitim NULL (siehe _bedient_von():
    # unbeglaubigt, Mensch selbst, kein Einladungsweg) -- dieser Testlauf hat
    # keinen beglaubigten Ausweis, also ist NULL hier korrekt. Geprueft wird
    # daher nicht "gesetzt", sondern "gleich dem Kindknoten" (unten).

    kind = _row(temp_db, "/woanders/tief")
    # Gegenprobe: der ausloesende Kindknoten (bestehender Schreibweg,
    # unveraendert von diesem Fix) traegt dieselbe Identitaet wie der
    # automatisch mit angelegte Astknoten.
    assert kind["actor"] == astknoten["actor"]
    assert kind["session"] == astknoten["session"]
    assert kind["model"] == astknoten["model"]
    assert kind["client"] == astknoten["client"]
    assert kind["bedient_von"] == astknoten["bedient_von"]


def test_mehrstufige_kette_jede_stufe_traegt_identitaet(temp_db):
    res = kms.knowledge_add("/a/b/c", "Tiefer Fund", "Zusammenfassung",
                            neuer_ast=True, source="test")
    assert res.get("status") == "created", res
    for path in ("/a", "/a/b", "/a/b/c"):
        row = _row(temp_db, path)
        assert row is not None, path
        assert row["actor"] is not None, f"{path}: actor blieb NULL"
        assert row["session"] is not None, f"{path}: session blieb NULL"


def test_unbeglaubigter_aufrufer_bekommt_trotzdem_eine_zuschreibung(temp_db):
    # Grenzwert: kein Ausweis, kein actor-Argument -- _identity() darf hier
    # nicht stumm NULL liefern, sondern muss wie ueberall sonst
    # 'unbeglaubigt:...'/UNBEKANNTER_SCHREIBER eintragen.
    res = kms.knowledge_add("/fremd/pfad", "Fund ohne Ausweis", "Zusammenfassung",
                            neuer_ast=True, source="test")
    assert res.get("status") == "created", res
    row = _row(temp_db, "/fremd")
    assert row["actor"] not in (None, ""), "unbeglaubigter Aufrufer verschwindet spurlos"
