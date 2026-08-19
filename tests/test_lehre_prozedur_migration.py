"""Tests fuer migrate_lehre_prozedur.py -- Aufgabe 79487bf9, BDW-F03-AC1.

Begruendung und Heuristik stehen im Modul-Docstring von
migrate_lehre_prozedur.py, hier nur die Abnahme:

1. ROT VOR GRUEN gegen einen FESTEN Commit (nie HEAD, L-82415c): der
   Fixpunkt `06391b58:schema.sql` traegt gedaechtnisart/gilt_ab/gilt_bis/
   gilt_bis_version bereits (diese Aufgabe schafft keine Spalte) -- vor dem
   Migrationslauf steht bei jeder frisch eingefuegten Zeile die Vorgabe
   'episodisch', das ist der rote Zustand.
2. Gegenprobe beide Richtungen: eine 'pattern'-Lehre MIT Schrittfolge wird
   zugeordnet, eine 'antipattern'-Lehre MIT Schrittfolge NICHT -- sonst
   ordnet die Migration nach Schritten statt nach Art zu.
3. Widerruf: eine Prozedur bleibt nach dem Widerruf lesbar (Wortlaut
   unveraendert, nur gilt_bis/gilt_bis_version gesetzt) -- im selben Test
   gegen einen Fakten-Widerruf gestellt, der content/summary leert.
4. Negativfall: widerrufe_prozedur() lehnt eine nicht-prozedurale Lehre ab.
5. Migration zweimal hintereinander fahrbar, ohne zu verdoppeln.
"""
from __future__ import annotations

import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import pytest

import migrate_lehre_prozedur as m

WURZEL = _w


def _leere_db(pfad) -> sqlite3.Connection:
    block = m._alter_tabellenblock()
    for spalte in ("gedaechtnisart", "gilt_ab", "gilt_bis", "gilt_bis_version"):
        assert spalte in block, f"{spalte} fehlt im Fixpunkt {m.FESTER_COMMIT} -- falscher Fixpunkt"
    conn = sqlite3.connect(str(pfad))
    conn.executescript(block)
    return conn


def test_rot_vor_gruen_vorgabe_ist_episodisch(tmp_path):
    """Punkt 1: vor dem Migrationslauf traegt eine frische Zeile die
    Vorgabe 'episodisch' -- das ist der rote Zustand, den migrate() beheben
    muss."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_db(db_path)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, resolution, anlass, bemerkt_woran) "
        "VALUES ('L-x', 'pattern', 'V', '1. A. 2. B.', 'skript', 'test')"
    )
    conn.commit()
    vorher = conn.execute("SELECT gedaechtnisart FROM lessons_learned WHERE id='L-x'").fetchone()[0]
    conn.close()
    assert vorher == "episodisch"


def test_zuordnung_positiv_und_negativ_nach_art(tmp_path):
    """Punkt 2: pattern+Schrittfolge -> prozedural, antipattern+Schrittfolge
    -> bleibt episodisch (die wichtigere Gegenprobe: Art entscheidet, nicht
    nur die Schrittfolge)."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_db(db_path)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, resolution, anlass, bemerkt_woran) "
        "VALUES ('L-pat', 'pattern', 'Verfahren', '1. Erst A. 2. Dann B. 3. Dann C.', 'skript', 'test')"
    )
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, prevention, anlass, bemerkt_woran) "
        "VALUES ('L-anti', 'antipattern', 'Fehler', '1. Nie X. 2. Nie Y.', 'skript', 'test')"
    )
    conn.commit()
    conn.close()

    res = m.migrate(db_path, apply=True)
    assert res["kandidaten"] == 1
    assert res["neu_prozedural"] == 1

    conn = sqlite3.connect(str(db_path))
    arten = dict(conn.execute("SELECT id, gedaechtnisart FROM lessons_learned").fetchall())
    conn.close()
    assert arten["L-pat"] == "prozedural", arten
    assert arten["L-anti"] == "episodisch", arten


def test_widerruf_prozedur_bleibt_lesbar_fakt_wird_geleert(tmp_path):
    """Punkt 3, der Kern der Zeile: Prozedur-Widerruf und Fakten-Widerruf
    nebeneinander, in einem Testfall."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_db(db_path)
    conn.executescript(m._tabellenblock("knowledge_nodes"))
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, resolution, anlass, bemerkt_woran, gedaechtnisart) "
        "VALUES ('L-proz', 'pattern', 'Verfahren', '1. A. 2. B.', 'skript', 'test', 'prozedural')"
    )
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, title, summary, content) "
        "VALUES ('n1', '/test/fakt', 'Titel', 'stimmte nicht', 'Wortlaut')"
    )
    conn.commit()

    m.widerrufe_prozedur(conn, "L-proz", "2026-08-19", gilt_bis_version="9.9.9")
    # Fakten-Widerruf wie knowledge_mcp_server.py::knowledge_zurueckziehen
    # (dort nicht importiert, hier nur zum Vergleich nachgebaut -- diese
    # Datei aendert an knowledge_nodes nichts).
    conn.execute(
        "UPDATE knowledge_nodes SET zurueckgezogen = 1, zurueckgezogen_grund = 'falsch', "
        "content = '', summary = '' WHERE id = 'n1'"
    )
    conn.commit()

    prozedur = conn.execute(
        "SELECT resolution, gilt_bis, gilt_bis_version FROM lessons_learned WHERE id='L-proz'"
    ).fetchone()
    fakt = conn.execute(
        "SELECT title, summary, content, zurueckgezogen FROM knowledge_nodes WHERE id='n1'"
    ).fetchone()
    conn.close()

    assert prozedur[0] == "1. A. 2. B.", "Prozedur-Widerruf haette den Wortlaut nicht veraendern duerfen"
    assert prozedur[1] == "2026-08-19" and prozedur[2] == "9.9.9"
    assert fakt[0] == "Titel"          # title bleibt (wie beim echten Fakten-Widerruf)
    assert fakt[1] == "" and fakt[2] == "", "Fakten-Widerruf haette Inhalt leeren muessen"
    assert fakt[3] == 1


def test_widerruf_lehnt_nicht_prozedurale_lehre_ab(tmp_path):
    """Punkt 4: Negativfall."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_db(db_path)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
        "VALUES ('L-ep', 'insight', 'x', 'skript', 'test')"
    )
    conn.commit()
    with pytest.raises(ValueError):
        m.widerrufe_prozedur(conn, "L-ep", "2026-08-19")
    conn.close()


def test_migration_zweimal_ohne_verdopplung(tmp_path):
    """Punkt 5: idempotent."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_db(db_path)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, resolution, anlass, bemerkt_woran) "
        "VALUES ('L-a', 'pattern', 'V', '1. A. 2. B.', 'skript', 'test')"
    )
    conn.commit()
    conn.close()

    res1 = m.migrate(db_path, apply=True)
    assert res1["neu_prozedural"] == 1 and res1["backup"] is not None

    res2 = m.migrate(db_path, apply=True)
    assert res2["neu_prozedural"] == 0 and res2["kandidaten"] == 0 and res2["backup"] is None
