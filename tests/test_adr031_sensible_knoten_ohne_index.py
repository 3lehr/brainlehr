"""ADR-031, Schritt 1 und 2: sensible Knoten stehen NICHT im Volltextindex.

Der Index ist der stille Weg um jede Spaltenverschluesselung herum -- solange
er den Klartext haelt, gibt er ihn heraus, egal was in der Spalte steht
(belegt in tests/test_e07_bestand_im_klartext.py). Deshalb kommt der
Ausschluss VOR der Verschluesselung.

Alle vier Uebergaenge werden geprueft, nicht nur der bequeme:
  anlegen sensibel      -> nie im Index
  anlegen normal        -> im Index (sonst waere die Sperre eine Attrappe)
  normal -> sensibel    -> Eintrag verschwindet
  sensibel -> normal    -> Eintrag entsteht
Die letzten beiden sind der Grund, warum knowledge_au in zwei Trigger
zerfaellt; mit einem einzigen waere genau hier ein beschaedigter Index
entstanden.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))

WORT = "meiershofstrasse"


@pytest.fixture()
def db(tmp_path):
    pfad = tmp_path / "t.db"
    conn = sqlite3.connect(str(pfad))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    return conn


def _anlegen(conn, node_id: str, sensibel: int) -> None:
    conn.execute(
        "insert into knowledge_nodes (id, path, title, summary, content, "
        "project_id, anlass, norm_entscheidung, norm_entschieden_grund, "
        "norm_entschieden_von, source, sensibel) values (?,?,?,?,?,?,?,?,?,?,?,?)",
        (node_id, "/" + node_id, "Fall", f"WEG-Beschluss {WORT} 12b",
         f"WEG-Beschluss {WORT} 12b", "shared", "skript", "keine_norm",
         "Testfall ADR-031", "test", "erzeugt aus tests/test_adr031_...py",
         sensibel),
    )
    conn.commit()


def _treffer(conn) -> int:
    return conn.execute(
        "select count(*) from knowledge_fts where knowledge_fts match ?", (WORT,)
    ).fetchone()[0]


def test_sensibler_knoten_kommt_nicht_in_den_index(db):
    _anlegen(db, "s1", sensibel=1)
    assert _treffer(db) == 0


def test_normaler_knoten_kommt_sehr_wohl_in_den_index(db):
    """Die Gegenprobe. Ohne sie belegt der Test oben nur, dass die Suche
    nichts findet -- was auch ein kaputter Index waere."""
    _anlegen(db, "n1", sensibel=0)
    assert _treffer(db) == 1


def test_nachtraeglich_sensibel_entfernt_den_eintrag(db):
    _anlegen(db, "n2", sensibel=0)
    assert _treffer(db) == 1
    db.execute("update knowledge_nodes set sensibel = 1 where id = 'n2'")
    db.commit()
    assert _treffer(db) == 0


def test_nachtraeglich_entstuft_legt_den_eintrag_an(db):
    _anlegen(db, "s2", sensibel=1)
    assert _treffer(db) == 0
    db.execute("update knowledge_nodes set sensibel = 0 where id = 's2'")
    db.commit()
    assert _treffer(db) == 1


def test_der_index_bleibt_dabei_heil(db):
    """FTS5 mit externer Inhaltstabelle laesst sich still beschaedigen, wenn
    'delete' mit anderen Werten gerufen wird als beim Indizieren. Ein
    beschaedigter Index faellt sonst erst irgendwann bei einer fremden Suche
    auf -- deshalb hier die eingebaute Pruefung nach allen Uebergaengen."""
    _anlegen(db, "a", sensibel=0)
    _anlegen(db, "b", sensibel=1)
    db.execute("update knowledge_nodes set sensibel = 1 where id = 'a'")
    db.execute("update knowledge_nodes set sensibel = 0 where id = 'b'")
    db.execute("update knowledge_nodes set summary = 'geaendert' where id = 'b'")
    db.execute("delete from knowledge_nodes where id = 'a'")
    db.commit()
    db.execute("insert into knowledge_fts(knowledge_fts) values ('integrity-check')")


def test_vorgabe_ist_nicht_sensibel(db):
    """Wer die Spalte nicht kennt, schreibt weiter wie bisher -- und landet
    im Index. Das ist die richtige Vorgabe: unauffindbar wird nur, was
    ausdruecklich so gemeint ist."""
    db.execute(
        "insert into knowledge_nodes (id, path, title, summary, project_id, "
        "anlass, norm_entscheidung, norm_entschieden_grund, "
        "norm_entschieden_von, source) "
        "values ('v','/v','T',?,'shared','skript','keine_norm','x','test','y')",
        (WORT,))
    db.commit()
    assert db.execute("select sensibel from knowledge_nodes where id='v'").fetchone()[0] == 0
    assert _treffer(db) == 1
