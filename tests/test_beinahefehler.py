"""Beinahefehler-Kennzeichnung (Plan docs/PLAN_BEINAHEFEHLER_2026-08-16.md).

ROT VOR GRUEN, am 2026-08-16 vor der Aenderung gefahren, vier Proben:
  1. Bestand brainlehr.db: Spalte 'beinahefehler' nicht vorhanden (False)
  2. frische DB aus schema.sql: INSERT ... beinahefehler bricht mit
     'table lessons_learned has no column named beinahefehler'
  3. Trigger lessons_learned_beinahe_check_bi/_bu existierten nicht
  4. kms.lesson_record(..., beinahefehler=True) -> TypeError:
     unexpected keyword argument 'beinahefehler'

Die Pruefung sitzt doppelt: sprechend im Werkzeug (_validate_beinahefehler)
UND als Trigger in der Datenbank. Der Trigger ist der wirksame Teil -- MCP
laeuft ueber stdio, jeder Klient haelt seinen eigenen Prozess mit eigenem
Codestand, es gibt keinen zentralen Neustart. Deshalb pruefen die Tests
beide Wege getrennt.
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
    db_path = tmp_path / "beinahe_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


# --- Datenbankschranke ------------------------------------------------

def test_spalten_und_trigger_in_der_erstanlage(temp_db):
    conn = sqlite3.connect(str(temp_db))
    spalten = {r[1] for r in conn.execute("PRAGMA table_info(lessons_learned)")}
    trigger = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='lessons_learned'")}
    conn.close()
    assert {"beinahefehler", "bemerkt_woran"} <= spalten
    assert {"lessons_learned_beinahe_check_bi",
            "lessons_learned_beinahe_check_bu"} <= trigger


@pytest.mark.parametrize("woran", sorted(kms.ALLOWED_BEMERKT_WORAN))
def test_trigger_laesst_jeden_erlaubten_wert_durch(temp_db, woran):
    conn = sqlite3.connect(str(temp_db))
    conn.execute("INSERT INTO lessons_learned (id, type, description, beinahefehler, bemerkt_woran) "
                 "VALUES (?, 'error', 'x', 1, ?)", (f"L-ok-{woran}", woran))
    conn.commit()
    conn.close()


@pytest.mark.parametrize("woran", [None, "", "   ", "\t\n", "irgendwas", "Zahl "])
def test_trigger_weist_kennzeichnung_ohne_gueltiges_woran_ab(temp_db, woran):
    """Grenzwerte: fehlend (NULL), leer, nur Leerzeichen, unbekannter Wert --
    alle vier muessen DASSELBE tun. 'Zahl ' prueft zusaetzlich, dass die
    Schranke nicht ueber Gross-/Kleinschreibung aufweicht."""
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError) as fehler:
        conn.execute("INSERT INTO lessons_learned (id, type, description, beinahefehler, bemerkt_woran) "
                     "VALUES ('L-nein', 'error', 'x', 1, ?)", (woran,))
    assert "bemerkt_woran" in str(fehler.value)
    conn.close()


def test_trigger_weist_fehlende_spalte_im_insert_ab(temp_db):
    """bemerkt_woran im INSERT gar nicht genannt -- derselbe Fall wie NULL."""
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO lessons_learned (id, type, description, beinahefehler) "
                     "VALUES ('L-nein2', 'error', 'x', 1)")
    conn.close()


def test_trigger_greift_auch_beim_nachtraeglichen_kennzeichnen(temp_db):
    """UPDATE-Weg: eine bestehende Lehre nachtraeglich zum Beinahefehler
    machen, ohne zu sagen woran -- muss genauso scheitern wie INSERT."""
    conn = sqlite3.connect(str(temp_db))
    conn.execute("INSERT INTO lessons_learned (id, type, description) VALUES ('L-alt','error','x')")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE lessons_learned SET beinahefehler = 1 WHERE id = 'L-alt'")
    conn.execute("UPDATE lessons_learned SET beinahefehler = 1, bemerkt_woran = 'zufall' WHERE id = 'L-alt'")
    conn.commit()
    conn.close()


def test_beinahefehler_nimmt_nur_null_oder_eins(temp_db):
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO lessons_learned (id, type, description, beinahefehler, bemerkt_woran) "
                     "VALUES ('L-zwei', 'error', 'x', 2, 'zahl')")
    conn.close()


def test_nachzug_bringt_spalten_und_trigger_in_gewachsene_datenbank(tmp_path):
    """Der Fall, der hier schon zweimal schiefging (L-55075a, L-7e0823): eine
    gewachsene Datenbank ohne die neuen Spalten. ensure_schema muss beides
    nachziehen -- Spalten UND Trigger, in dieser Reihenfolge."""
    db = tmp_path / "gewachsen.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.execute("DROP TRIGGER lessons_learned_beinahe_check_bi")
    conn.execute("DROP TRIGGER lessons_learned_beinahe_check_bu")
    conn.commit()

    kms.ensure_schema(conn)

    trigger = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name='lessons_learned'")}
    assert {"lessons_learned_beinahe_check_bi",
            "lessons_learned_beinahe_check_bu"} <= trigger
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO lessons_learned (id, type, description, beinahefehler) "
                     "VALUES ('L-nach', 'error', 'x', 1)")
    conn.close()


# --- Werkzeugweg ------------------------------------------------------

def test_lesson_record_schreibt_kennzeichnung(temp_db):
    res = kms.lesson_record("error", "Leeres Log fast als Beleg verbucht",
                            beinahefehler=True, bemerkt_woran="zahl")
    assert res.get("status") == "recorded", res
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT beinahefehler, bemerkt_woran, type FROM lessons_learned WHERE id = ?",
                       (res["id"],)).fetchone()
    conn.close()
    assert row == (1, "zahl", "error")


@pytest.mark.parametrize("woran", ["", "   ", "unbekannter_wert"])
def test_lesson_record_weist_kennzeichnung_ohne_woran_ab(temp_db, woran):
    """Negativfall: gekennzeichnet, aber nicht gesagt woran -- nichts wird
    geschrieben, und die Meldung nennt die erlaubte Liste."""
    res = kms.lesson_record("error", f"Ohne woran {woran!r}", beinahefehler=True,
                            bemerkt_woran=woran)
    assert res.get("status") == "rejected", res
    assert "bemerkt_woran" in res.get("error", "")
    conn = sqlite3.connect(str(temp_db))
    anzahl = conn.execute("SELECT count(*) FROM lessons_learned").fetchone()[0]
    conn.close()
    assert anzahl == 0, "abgewiesener Aufruf hat trotzdem geschrieben"


def test_lesson_record_ohne_kennzeichnung_bleibt_wie_bisher(temp_db):
    """Die Vorgabe darf sich nicht aendern: wer nichts angibt, schreibt eine
    ganz normale Lehre -- ohne bemerkt_woran, ohne Ablehnung."""
    res = kms.lesson_record("insight", "Ganz normale Lehre")
    assert res.get("status") == "recorded", res
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT beinahefehler, bemerkt_woran FROM lessons_learned WHERE id = ?",
                       (res["id"],)).fetchone()
    conn.close()
    assert row == (0, None)


def test_werkzeugschema_kennt_beide_felder():
    """Ohne Eintrag im inputSchema ist der Weg fuer ein Modell unsichtbar --
    genau der Mangel, den lesson_record bei actor/model/session hatte."""
    eigenschaften = kms.TOOLS["lesson_record"]["inputSchema"]["properties"]
    assert "beinahefehler" in eigenschaften
    assert eigenschaften["bemerkt_woran"]["enum"] == sorted(kms.ALLOWED_BEMERKT_WORAN)
