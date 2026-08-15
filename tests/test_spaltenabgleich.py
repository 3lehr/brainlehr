"""melder/spaltenabgleich.py: J3 -- Tabellen und Spalten aus sqlite_master
(IST) gegen schema.sql (SOLL), NAMENTLICH je Spalte statt als Gesamttext.

ANLASS: melder/schemastand.py haelt schema.sql gegen die installierte
Datenbank, aber als GANZEN CREATE-TABLE-Text -- weicht eine Tabelle ab, sagt
es nur "Text weicht ab", nie welche Spalte. Rot-vor-gruen-Beleg fuer genau
diese Luecke steht in test_bestehender_melder_nennt_spalte_nicht_neuer_schon
unten: derselbe Fall (eine untergeschobene Spalte) wird von schemastand.py
nur auf Tabellenebene gemeldet, von spaltenabgleich.py mit Namen.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import schemastand  # noqa: E402 -- via conftest.py im sys.path (melder/)
import spaltenabgleich  # noqa: E402 -- via conftest.py im sys.path (melder/)
import speicher  # noqa: E402 -- via conftest.py im sys.path (kern/)

WURZEL = Path(__file__).resolve().parents[1]


def _exakter_nachbau(ziel: Path) -> None:
    with speicher.schreiben(ziel) as conn:
        conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))


def test_negativfall_exakter_nachbau_meldet_nichts(tmp_path):
    """Gegenprobe: ein Melder, der immer meldet, wird nach drei Sitzungen
    weggeklickt (L-528f0c). Ohne diesen Test bestuende das nicht."""
    db = tmp_path / "exakt.db"
    _exakter_nachbau(db)
    ergebnis = spaltenabgleich.vergleich(db=db)
    assert ergebnis["tabellen"] == {"nur_soll": [], "nur_ist": []}
    assert ergebnis["spalten"] == {}


def test_grenzwert_leere_datenbank_meldet_alle_tabellen_als_fehlend(tmp_path):
    """Grenzwert aus dem Auftrag: eine Datenbank ganz ohne Tabellen. Muss
    jede schema.sql-Tabelle als fehlend nennen, ohne abzustuerzen -- und darf
    keine Spalten vergleichen, weil keine Tabelle beidseitig existiert."""
    db = tmp_path / "leer.db"
    with speicher.schreiben(db):
        pass
    ergebnis = spaltenabgleich.vergleich(db=db)
    assert "schema_migrations" in ergebnis["tabellen"]["nur_soll"]
    assert ergebnis["spalten"] == {}


def test_tabelle_fehlt_installiert_wird_gemeldet(tmp_path):
    db = tmp_path / "tab_fehlt.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("DROP TABLE schema_migrations")
    ergebnis = spaltenabgleich.vergleich(db=db)
    assert "schema_migrations" in ergebnis["tabellen"]["nur_soll"]


def test_zusaetzliche_tabelle_wird_gemeldet(tmp_path):
    """Der Fund-Fall aus Linie J: ein Objekt installiert, das schema.sql
    nicht kennt."""
    db = tmp_path / "tab_extra.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("CREATE TABLE gewachsen (id INTEGER PRIMARY KEY)")
    ergebnis = spaltenabgleich.vergleich(db=db)
    assert "gewachsen" in ergebnis["tabellen"]["nur_ist"]


def test_spalte_fehlt_in_gemeinsamer_tabelle_wird_namentlich_gemeldet(tmp_path):
    db = tmp_path / "sp_fehlt.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("ALTER TABLE schema_migrations DROP COLUMN beschreibung")
    ergebnis = spaltenabgleich.vergleich(db=db)
    assert "beschreibung" in ergebnis["spalten"]["schema_migrations"]["fehlt"]


def test_zusaetzliche_spalte_wird_namentlich_gemeldet(tmp_path):
    db = tmp_path / "sp_extra.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN untergeschoben TEXT")
    ergebnis = spaltenabgleich.vergleich(db=db)
    assert "untergeschoben" in ergebnis["spalten"]["schema_migrations"]["zusaetzlich"]


def test_grenzwert_gleicher_spaltenname_anderer_typ_ist_abweichend_nicht_fehlend(tmp_path):
    """L-55075a auf Spaltenebene: gleicher Name, anderer Rumpf (hier: Typ).
    Muss als 'abweichend' erscheinen, nicht als fehlend+zusaetzlich."""
    db = tmp_path / "sp_abweichend.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("ALTER TABLE schema_migrations DROP COLUMN beschreibung")
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN beschreibung INTEGER")
    ergebnis = spaltenabgleich.vergleich(db=db)
    d = ergebnis["spalten"]["schema_migrations"]
    assert "beschreibung" in d["abweichend"]
    assert "beschreibung" not in d["fehlt"]
    assert "beschreibung" not in d["zusaetzlich"]


def test_bestehender_melder_nennt_spalte_nicht_neuer_schon(tmp_path):
    """Rot-vor-gruen-Beleg fuer diesen Melder selbst: derselbe Fall
    (untergeschobene Spalte) wird vom bestehenden schemastand.py NUR auf
    Tabellenebene gemeldet ('abweichendes_sql': table X) -- ohne diesen
    neuen Melder gibt es KEINE Stelle, die die Spalte NAMENTLICH nennt."""
    db = tmp_path / "sp_extra2.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("ALTER TABLE schema_migrations ADD COLUMN untergeschoben TEXT")

    alt = schemastand.vergleich(db=db)
    assert ("table", "schema_migrations") in alt["abweichendes_sql"]
    assert not any("untergeschoben" in str(e) for e in alt["abweichendes_sql"]), (
        "schemastand.py nennt die Spalte bereits -- der neue Melder waere ueberfluessig"
    )

    neu = spaltenabgleich.vergleich(db=db)
    assert "untergeschoben" in neu["spalten"]["schema_migrations"]["zusaetzlich"]


def test_gegen_echte_datenbank_laeuft_nur_lesend():
    """Kein rot/gruen-Anspruch -- der echte Bestand darf Abweichungen haben.
    Die Probe ist: der Aufruf laeuft durch und liefert die erwartete Form."""
    ergebnis = spaltenabgleich.vergleich()
    assert set(ergebnis) == {"tabellen", "spalten"}
    assert set(ergebnis["tabellen"]) == {"nur_soll", "nur_ist"}
