"""Tests fuer migrate_lehre_geltung.py -- Aufgabe 79487bf9 (ADR-030).

gilt_ab/gilt_bis/bezug/gilt_bis_version an lessons_learned, additiv. Details
und Begruendung stehen im Modul-Docstring von migrate_lehre_geltung.py, hier
nur die Abnahme:

1. ROT VOR GRUEN gegen einen FESTEN Commit (nie HEAD, L-82415c): der Stand
   vor dieser Aufgabe (`dee26e17:schema.sql`) kennt keine der vier Spalten --
   gegen den Stand waeren diese Tests rot gewesen.
2. Gegenprobe beide Richtungen: eine Lehre MIT Produktnennung bekommt bezug,
   eine OHNE bleibt '[]'.
3. Negativfall: gilt_bis_version bleibt nach der Migration bei ALLEN Zeilen
   leer.
4. Idempotenz: zweiter Lauf faengt nichts Neues ein, keine Verdopplung.
5. Falle "zwei Ausgangszustaende" (CLAUDE.md): eine Datenbank, deren Spalten
   und Trigger schon vollstaendig da sind, aber deren bezug nie befuellt
   wurde, wird trotzdem befuellt -- das Backfuellen haengt an
   `bezug IS NULL`, nicht an "Spalte fehlt".
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import migrate_lehre_geltung as m

WURZEL = _w
FESTER_COMMIT = "dee26e17"  # Stand unmittelbar vor dieser Aufgabe (ADR-030 angenommen)


def _alter_tabellenblock() -> str:
    """CREATE-TABLE-Block von lessons_learned zum FESTEN Fixpunkt-Commit --
    nie HEAD, sonst vergleicht der Test einen Stand gegen sich selbst."""
    alt_schema = subprocess.run(
        ["git", "show", f"{FESTER_COMMIT}:schema.sql"],
        cwd=WURZEL, capture_output=True, text=True, check=True,
    ).stdout
    start = alt_schema.index("CREATE TABLE IF NOT EXISTS lessons_learned")
    ende = alt_schema.index(");", start) + 2
    return alt_schema[start:ende]


def _leere_alte_db(pfad) -> sqlite3.Connection:
    block = _alter_tabellenblock()
    for spalte in m.SPALTEN:
        assert spalte not in block, (
            f"{spalte} bereits im Fixpunkt-Schema ({FESTER_COMMIT}) -- Test waere gegen "
            "diesen Stand nicht rot gewesen"
        )
    conn = sqlite3.connect(str(pfad))
    conn.executescript(block)
    return conn


def test_rot_vor_gruen_fixpunkt_kennt_spalten_nicht():
    """Punkt 1 der Abnahme: der Fixpunkt-Commit hat keine der vier Spalten."""
    block = _alter_tabellenblock()
    for spalte in m.SPALTEN:
        assert spalte not in block


def test_bezug_positiv_und_negativ(tmp_path):
    """Punkt 2: Gegenprobe beide Richtungen."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_alte_db(db_path)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
        "VALUES ('L-ios', 'insight', 'Auf iOS bricht die Kopplung nach SIGSTOP.', 'skript', 'test')"
    )
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
        "VALUES ('L-neutral', 'insight', 'Ein Commit umfasst eine Sache.', 'skript', 'test')"
    )
    conn.commit()
    conn.close()

    res = m.migrate(db_path, apply=True)
    assert res["bezug_gefuellt"] == 1

    conn = sqlite3.connect(str(db_path))
    bezug = dict(conn.execute("SELECT id, bezug FROM lessons_learned").fetchall())
    conn.close()
    assert json.loads(bezug["L-ios"]) == ["iOS"], bezug["L-ios"]      # Positivkontrolle
    assert json.loads(bezug["L-neutral"]) == [], bezug["L-neutral"]   # Gegenprobe: kein Raten


def test_gilt_bis_version_bleibt_leer(tmp_path):
    """Punkt 3, der wichtigste Negativfall: gilt_bis_version wird von der
    Migration NIE gesetzt, bei keiner der Zeilen."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_alte_db(db_path)
    for i in range(5):
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
            "VALUES (?, 'insight', 'Flutter-Widget verliert Fokus.', 'skript', 'test')",
            (f"L-{i}",),
        )
    conn.commit()
    conn.close()

    res = m.migrate(db_path, apply=True)
    assert res["gilt_bis_version_nicht_leer"] == 0

    conn = sqlite3.connect(str(db_path))
    n = conn.execute(
        "SELECT COUNT(*) FROM lessons_learned WHERE gilt_bis_version IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    assert n == 0, f"{n} von 5 Zeilen tragen gilt_bis_version nach der Migration -- sollte 0 sein"


def test_migration_zweimal_ohne_verdopplung(tmp_path):
    """Punkt 4: zweiter Lauf idempotent."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_alte_db(db_path)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
        "VALUES ('L-android', 'insight', 'Android-Emulator startet GATT-Server nicht.', 'skript', 'test')"
    )
    conn.commit()
    conn.close()

    res1 = m.migrate(db_path, apply=True)
    assert res1["backup"] is not None

    conn = sqlite3.connect(str(db_path))
    bezug_nach_lauf1 = conn.execute("SELECT bezug FROM lessons_learned WHERE id = 'L-android'").fetchone()[0]
    conn.close()

    res2 = m.migrate(db_path, apply=True)
    assert res2["backup"] is None
    assert res2["etwas_fehlt"] is False
    assert res2["bezug_gefuellt"] == 0

    conn = sqlite3.connect(str(db_path))
    bezug_nach_lauf2 = conn.execute("SELECT bezug FROM lessons_learned WHERE id = 'L-android'").fetchone()[0]
    conn.close()
    assert bezug_nach_lauf2 == bezug_nach_lauf1 == '["Android"]'


def test_zwei_ausgangszustaende_spalte_da_aber_unbefuellt(tmp_path):
    """Punkt 5: eine Datenbank mit Spalten UND Triggern, aber ungeprueftem
    bezug (z.B. frisch aus schema.sql erzeugt, nie migriert) wird trotzdem
    befuellt -- sonst haengt das Backfuellen faelschlich an 'Spalte fehlt'."""
    db_path = tmp_path / "brainlehr.db"
    block = _alter_tabellenblock()
    voller_block = block.replace(
        ");", ", gilt_ab TEXT, gilt_bis TEXT, bezug TEXT, gilt_bis_version TEXT);"
    )
    conn = sqlite3.connect(str(db_path))
    conn.executescript(voller_block)
    conn.executescript(m.TRIGGER_SQL)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
        "VALUES ('L-fastapi', 'insight', 'FastAPI-Endpoint gibt 500 statt 409.', 'skript', 'test')"
    )
    conn.commit()

    assert m.missing_columns(conn) == []
    assert m.missing_triggers(conn) == []
    conn.close()

    res = m.migrate(db_path, apply=True)
    assert res["spalten_fehlen"] == [] and res["trigger_fehlen"] == [] and res["etwas_fehlt"] is False
    assert res["backup"] is not None, "unbefuelltes bezug haette trotz vollstaendigem Schema erkannt werden muessen"
    assert res["bezug_gefuellt"] == 1

    conn = sqlite3.connect(str(db_path))
    bezug = conn.execute("SELECT bezug FROM lessons_learned WHERE id = 'L-fastapi'").fetchone()[0]
    conn.close()
    assert json.loads(bezug) == ["FastAPI"]


def test_gilt_bis_vor_gilt_ab_wird_abgelehnt(tmp_path):
    """Gegenprobe zum Trigger, beide Richtungen: ein Enddatum vor dem
    Anfangsdatum wird abgelehnt, danach oder gleichzeitig angenommen."""
    db_path = tmp_path / "brainlehr.db"
    conn = _leere_alte_db(db_path)
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, anlass, bemerkt_woran) "
        "VALUES ('L-x', 'insight', 'neutral', 'skript', 'test')"
    )
    conn.commit()
    conn.close()

    m.migrate(db_path, apply=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE lessons_learned SET gilt_ab='2026-08-19', gilt_bis='2026-08-01' WHERE id='L-x'"
        )
        abgelehnt = False
    except sqlite3.IntegrityError:
        abgelehnt = True
    assert abgelehnt

    conn.execute(
        "UPDATE lessons_learned SET gilt_ab='2026-08-01', gilt_bis='2026-08-19' WHERE id='L-x'"
    )
    conn.commit()
    conn.close()
