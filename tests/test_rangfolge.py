"""Tests fuer rangfolge.py (Auftrag 2026-08-08, Knoten
/brainlehr/zu-tun-rangfolge-verschraenken-vier).

Rot-vor-gruen: vor dieser Datei/rangfolge.py gab es dieses Modul nicht --
jeder Import schlug fehl (rot). Deckt: norm_score-Skala inkl. Grenzwerte,
hebb_score-Normierung, Abschaltbarkeit je Signal (Gegenprobe in beide
Richtungen -- an UND aus veraendern/veraendern nicht die Reihenfolge) und den
zentralen Negativfall (Knoten ohne Kante/Normrang faellt nicht zurueck).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import os
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import pytest

from rangfolge import anwenden, hebb_gewichte, hebb_score, norm_score


def test_norm_score_skala_und_grenzwerte():
    assert norm_score(1) == 1.0
    assert norm_score(2) == pytest.approx(2 / 3)
    assert norm_score(3) == pytest.approx(1 / 3)
    assert norm_score(None) == 0.0
    assert norm_score(0) == 0.0
    assert norm_score(4) == 0.0  # kein heutiger Traeger (Rang 4 unbesetzt, siehe normrang.py)


def test_hebb_score_normierung():
    assert hebb_score(0.0, 0.0) == 0.0
    assert hebb_score(2.0, 4.0) == 0.5
    assert hebb_score(4.0, 4.0) == 1.0


@pytest.fixture
def db(tmp_path) -> sqlite3.Connection:
    db_path = tmp_path / "knowledge.db"
    schema_sql = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema_sql)
    now = "2026-08-08T00:00:00+02:00"

    def insert_node(path: str, rang: int | None) -> None:
        entscheidung = "keine_norm" if rang is None else "norm_unbefristet"
        gilt_ab = None if rang is None else now
        conn.execute(
            "INSERT INTO knowledge_nodes (id,path,title,summary,source,created_at,updated_at,"
            "norm_rang,gilt_ab,norm_entscheidung,norm_entschieden_von,norm_entschieden_am,norm_entschieden_grund) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (path, path, path, "Test", "selftest", now, now, rang, gilt_ab, entscheidung,
             "skript:rangfolge.py", now, "Testvorrichtung, keine echte Norm-Pruefung"),
        )

    # 8 Kandidaten, Rangabstand 1/8=0.125 < Gewicht 0.15 -- nur so kann ein
    # Signal einen NACHBARN ueberholen, ohne die Relevanzfuehrung (/a bleibt
    # immer vorn) zu brechen.
    for p, r in (("/a", None), ("/p1", None), ("/p2", None), ("/p3", None),
                 ("/nB", None), ("/b", 1), ("/nG", None), ("/g", None), ("/aussen", None)):
        insert_node(p, r)
    conn.execute(
        "INSERT INTO knowledge_relations (id,source_path,target_path,relation_type,weight,source) "
        "VALUES ('R-1','/g','/aussen','analogous_to',5.0,'hebb_kanten.py')"
    )
    conn.commit()
    yield conn
    conn.close()


NAMEN = ["/a", "/p1", "/p2", "/p3", "/nB", "/b", "/nG", "/g"]


def _order(db, norm: str, hebb: str) -> list[str]:
    os.environ["KNOWLEDGE_NORMRANG_AKTIV"] = norm
    os.environ["KNOWLEDGE_HEBB_AKTIV"] = hebb
    try:
        candidates = [{"path": p} for p in NAMEN]
        return [c["path"] for c in anwenden(candidates, db)]
    finally:
        os.environ.pop("KNOWLEDGE_NORMRANG_AKTIV", None)
        os.environ.pop("KNOWLEDGE_HEBB_AKTIV", None)


def test_beide_schalter_aus_ist_wirkungslos(db):
    assert _order(db, "0", "0") == NAMEN


def test_normrang_an_ueberholt_nachbarn_hebb_bleibt_wirkungslos(db):
    reihenfolge = _order(db, "1", "0")
    assert reihenfolge.index("/b") < reihenfolge.index("/nB")
    # Gegenprobe Richtung 2: der ANDERE Schalter ist aus -> /g bleibt hinter /nG.
    assert reihenfolge.index("/nG") < reihenfolge.index("/g")
    assert reihenfolge[0] == "/a"


def test_hebb_an_ueberholt_nachbarn_normrang_bleibt_wirkungslos(db):
    reihenfolge = _order(db, "0", "1")
    assert reihenfolge.index("/g") < reihenfolge.index("/nG")
    # Gegenprobe Richtung 2: der ANDERE Schalter ist aus -> /b bleibt hinter /nB.
    assert reihenfolge.index("/nB") < reihenfolge.index("/b")
    assert reihenfolge[0] == "/a"


def test_beide_an_negativfall_kein_rueckfall(db):
    """Zentraler Negativfall: /a hat WEDER Kante NOCH Normrang. Gegenueber
    dem heutigen Zustand (Schalter aus, Zeile oben) darf es nicht schlechter
    dastehen -- hier: bleibt es ganz vorn, weil sein rank_score additiv
    unveraendert bleibt und kein anderer Kandidat den Abstand zu Rang 0
    ueberbruecken kann."""
    reihenfolge = _order(db, "1", "1")
    assert reihenfolge.index("/b") < reihenfolge.index("/nB")
    assert reihenfolge.index("/g") < reihenfolge.index("/nG")
    assert reihenfolge[0] == "/a"


def test_env_override_hat_vorrang_vor_modulkonstante(db, monkeypatch):
    """Wie ZWEITER_KANAL/ENSEMBLE_PFLICHT im Hook: KNOWLEDGE_<NAME>-Var
    uebersteuert die Modulkonstante, unabhaengig von deren Wert."""
    import rangfolge

    monkeypatch.setattr(rangfolge, "NORMRANG_AKTIV", True)
    monkeypatch.setattr(rangfolge, "HEBB_AKTIV", True)
    reihenfolge = _order(db, "0", "0")
    assert reihenfolge == NAMEN, "Env-Override '0' muss die Modulkonstante True uebersteuern"


def test_hebb_gewichte_summiert_beide_richtungen(db):
    gewichte = hebb_gewichte(db, ["/g", "/nG", "/aussen"])
    assert gewichte["/g"] == 5.0
    assert gewichte["/nG"] == 0.0
    assert gewichte["/aussen"] == 5.0
