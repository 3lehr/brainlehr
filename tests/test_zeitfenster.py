"""Tests fuer kern/zeitfenster.py (Aufgabe 88, Schritt 1): eine Anfrage
optional auf einen Zeitraum einschraenken ("das wurde letzte Woche gemacht").

Auf tmp-DB, nicht auf dem echten Bestand -- Zugriff ausschliesslich ueber
kern/speicher (ueber kern/anfrage_erweiterung.treffer(), das denselben Weg
nutzt)."""
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
import uuid
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import zeitfenster as zf  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    return db_path


def _insert_node(conn: sqlite3.Connection, title: str, created_at: str) -> str:
    """Minimaler, den schema.sql-Triggern genuegender Knoten. `title` traegt
    das gemeinsame Suchwort 'zielwort', damit anfrage_erweiterung.treffer()
    ihn ueberhaupt findet -- der Zeitfilter soll NUR den Zeitraum pruefen,
    nicht den Inhaltstreffer."""
    node_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO knowledge_nodes
        (id, path, parent_path, project_id, title, summary, source, anlass,
         norm_entscheidung, norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund,
         created_at, updated_at)
        VALUES (?, ?, NULL, 'shared', ?, 'Testknoten', 'test', 'skript',
                'keine_norm', 'test', ?, 'Testvorrichtung, keine echte Norm-Pruefung',
                ?, ?)
        """,
        (node_id, f"/zeitfenster-test/{node_id}", title, created_at, created_at, created_at),
    )
    return node_id


def _bestand(conn: sqlite3.Connection) -> None:
    """Ein Knoten VOR, einer GENAU AM und einer NACH dem Testzeitraum
    (2026-08-03 .. 2026-08-09) -- der Grenzwert-Fall aus der Abnahme."""
    _insert_node(conn, "zielwort davor", "2026-08-02T23:59:59+01:00")
    _insert_node(conn, "zielwort am unteren Rand", "2026-08-03T00:00:00+01:00")
    _insert_node(conn, "zielwort am oberen Rand", "2026-08-09T23:59:59+01:00")
    _insert_node(conn, "zielwort danach", "2026-08-10T00:00:01+01:00")


def test_zeitraum_liefert_echte_teilmenge_der_inhaltssuche(temp_db):
    """Hauptabnahme: Inhalt+Zeitraum liefert eine ECHTE Teilmenge dessen,
    was Inhalt ALLEIN liefert -- an einem Fall, bei dem die Zeit den
    Ausschlag gibt (der 'davor'- und der 'danach'-Knoten fallen raus).
    Rot-Probe: ohne Zeitraum sind beide Mengen gleich gross (siehe
    test_negativfall_leeres_zeitfenster_kein_effekt fuer den Beleg,
    dass der Filter selbst wirkt und nicht nur ausschliesst)."""
    conn = sqlite3.connect(str(temp_db))
    _bestand(conn)
    conn.commit()
    conn.close()

    ohne_zeitraum = zf.treffer("zielwort", db=temp_db)
    mit_zeitraum = zf.treffer("zielwort", von="2026-08-03", bis="2026-08-09", db=temp_db)

    assert len(ohne_zeitraum) == 4, ohne_zeitraum
    assert mit_zeitraum < ohne_zeitraum, (mit_zeitraum, ohne_zeitraum)
    assert len(mit_zeitraum) == 2, mit_zeitraum


def test_negativfall_zeitraum_ueber_alles_aendert_nichts(temp_db):
    """Negativfall: ein Zeitraum, der den gesamten Bestand umfasst, aendert
    NICHTS an der Treffermenge -- ohne diesen Test bestuende der erste Test
    auch bei einem Filter, der immer alles ausschliesst (leer waere dann
    ebenfalls < ohne_zeitraum)."""
    conn = sqlite3.connect(str(temp_db))
    _bestand(conn)
    conn.commit()
    conn.close()

    ohne_zeitraum = zf.treffer("zielwort", db=temp_db)
    alles_umfassend = zf.treffer("zielwort", von="2000-01-01", bis="2100-01-01", db=temp_db)
    assert alles_umfassend == ohne_zeitraum, (alles_umfassend, ohne_zeitraum)


def test_ohne_zeitangabe_unveraendert_wie_heute(temp_db):
    """Wichtigste Eigenschaft: der Filter ist OPTIONAL. Ohne von/bis
    verhaelt sich treffer() exakt wie anfrage_erweiterung.treffer()."""
    import anfrage_erweiterung as ae

    conn = sqlite3.connect(str(temp_db))
    _bestand(conn)
    conn.commit()
    conn.close()

    assert zf.treffer("zielwort", db=temp_db) == ae.treffer("zielwort", db=temp_db)


def test_grenzwert_rand_gehoert_dazu_ein_tag_davor_und_danach_nicht(temp_db):
    """Grenzwert: der Knoten GENAU am unteren bzw. oberen Rand des
    Zeitraums (2026-08-03T00:00:00 / 2026-08-09T23:59:59) gehoert dazu --
    beide Grenzen sind inklusiv (Tagesgranularitaet, siehe Moduldoc). Der
    Knoten einen Tag davor bzw. danach gehoert NICHT dazu."""
    conn = sqlite3.connect(str(temp_db))
    _bestand(conn)
    conn.commit()
    conn.close()

    treffer = zf.treffer("zielwort", von="2026-08-03", bis="2026-08-09", db=temp_db)
    titel = {
        row[0]
        for row in sqlite3.connect(str(temp_db)).execute(
            "SELECT title FROM knowledge_nodes WHERE id IN ({})".format(
                ",".join("?" * len(treffer))
            ),
            tuple(id_ for _, id_ in treffer),
        )
    } if treffer else set()

    assert "zielwort am unteren Rand" in titel
    assert "zielwort am oberen Rand" in titel
    assert "zielwort davor" not in titel
    assert "zielwort danach" not in titel


def test_im_zeitraum_pure_grenzwerte():
    """Grenzwert direkt auf der reinen Vergleichsfunktion, Schwelle-1/
    Schwelle/Schwelle+1 auf beiden Seiten."""
    assert zf.im_zeitraum("2026-08-03T00:00:00+01:00", "2026-08-03", "2026-08-09")
    assert zf.im_zeitraum("2026-08-09T23:59:59+01:00", "2026-08-03", "2026-08-09")
    assert not zf.im_zeitraum("2026-08-02T23:59:59+01:00", "2026-08-03", "2026-08-09")
    assert not zf.im_zeitraum("2026-08-10T00:00:00+01:00", "2026-08-03", "2026-08-09")
