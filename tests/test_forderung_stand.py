"""Tests fuer knowledge_nodes.forderung_stand (Auftrag F, 2026-08-21,
docs/PLAN_BETRIEBSPROFILE_2026-08-20.md Abschnitt F).

Belegt gegen den Stand vor diesem Auftrag (Commit f64e7a12, B1): dort trug
schema.sql die Spalte forderung_stand bereits, aber "kein Trigger, keine
Logik, kein Wertebereich" -- ein Ablehnen ohne Grund, ein unbekannter
Zustandswert und ein Ruecksetzen auf NULL gingen alle klaglos durch. Diese
Datei zeigt zuerst, dass genau das an f64e7a12 zutraf (ROT), dann dass der
aktuelle Stand es verhindert (GRUEN).

Reine DB-Trigger-Pruefung, keine knowledge_add()/knowledge_update()-Pfade:
beide Funktionen (knowledge_mcp_server.py) kennen forderung_stand nicht --
diese Datei ist im Auftrag ausdruecklich nicht anzufassen. Die Haerte liegt
komplett in schema.sql; melder/forderung_vorgang.py ist nur ein duenner
Aufrufer davon (siehe dessen eigener Selbsttest fuer den Weg ueber diese
Datei)."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent


def _insert_sql(node_id: str, path: str, erstellt: str = "2026-08-08T09:00:00Z") -> str:
    # norm_entscheidung ist an f64e7a12 bereits Pflicht (Auftrag 2026-08-08)
    # -- unabhaengig von diesem Auftrag, aber jede rohe INSERT-Zeile muss sie
    # mitliefern, sonst scheitert die Zeile an der FALSCHEN Schranke.
    return (
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, "
        "level, source, created_at, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund) VALUES "
        f"('{node_id}','{path}','shared','t','x','x',0,'test','{erstellt}','keine_norm','test',"
        "'Testvorrichtung, keine echte Norm-Pruefung')"
    )


@pytest.fixture()
def schema_f64e7a12() -> str:
    """Der Schemastand VOR diesem Auftrag, unveraendert aus git geholt --
    kein Nachbau von Hand, der beim naechsten Umbau von f64e7a12 abweichen
    koennte."""
    return subprocess.run(
        ["git", "show", "f64e7a12:schema.sql"],
        cwd=WURZEL, capture_output=True, text=True, check=True,
    ).stdout


@pytest.fixture()
def schema_aktuell() -> str:
    return (WURZEL / "schema.sql").read_text(encoding="utf-8")


def _frische_db(tmp_path: Path, schema: str, name: str = "test.db") -> Path:
    db = tmp_path / name
    conn = sqlite3.connect(str(db))
    conn.executescript(schema)
    conn.execute(_insert_sql("a", "/brainlehr/alt"))
    conn.commit()
    conn.close()
    return db


# --- ROT: Stand f64e7a12 hat keine Haerte -----------------------------------

def test_rot_f64e7a12_erlaubt_ablehnung_ohne_grund(tmp_path, schema_f64e7a12):
    db = _frische_db(tmp_path, schema_f64e7a12)
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='abgelehnt' WHERE path='/brainlehr/alt'")
    conn.commit()  # darf NICHT werfen -- das ist der Befund, kein Erfolg
    stand = conn.execute("SELECT forderung_stand FROM knowledge_nodes WHERE path='/brainlehr/alt'").fetchone()[0]
    assert stand == "abgelehnt", "Beleg fuer den Vorher-Zustand ist selbst kaputt"
    conn.close()


def test_rot_f64e7a12_erlaubt_unbekannten_zustand(tmp_path, schema_f64e7a12):
    db = _frische_db(tmp_path, schema_f64e7a12)
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='quatsch' WHERE path='/brainlehr/alt'")
    conn.commit()
    stand = conn.execute("SELECT forderung_stand FROM knowledge_nodes WHERE path='/brainlehr/alt'").fetchone()[0]
    assert stand == "quatsch"
    conn.close()


def test_rot_f64e7a12_erlaubt_ruecksetzen_auf_null(tmp_path, schema_f64e7a12):
    db = _frische_db(tmp_path, schema_f64e7a12)
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='offen' WHERE path='/brainlehr/alt'")
    conn.execute("UPDATE knowledge_nodes SET forderung_stand=NULL WHERE path='/brainlehr/alt'")
    conn.commit()
    stand = conn.execute("SELECT forderung_stand FROM knowledge_nodes WHERE path='/brainlehr/alt'").fetchone()[0]
    assert stand is None
    conn.close()


# --- GRUEN: aktueller Stand haelt die drei Faelle ---------------------------

def test_gruen_ablehnung_ohne_grund_scheitert(tmp_path, schema_aktuell):
    db = _frische_db(tmp_path, schema_aktuell)
    conn = sqlite3.connect(str(db))
    with pytest.raises(sqlite3.IntegrityError, match="forderung_grund"):
        conn.execute("UPDATE knowledge_nodes SET forderung_stand='abgelehnt' WHERE path='/brainlehr/alt'")
    conn.close()


def test_gruen_ablehnung_mit_grund_gelingt(tmp_path, schema_aktuell):
    """Gegenprobe zum vorigen Test: derselbe Uebergang, diesmal mit Grund."""
    db = _frische_db(tmp_path, schema_aktuell)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "UPDATE knowledge_nodes SET forderung_stand='abgelehnt', forderung_grund='Testvorrichtung' "
        "WHERE path='/brainlehr/alt'"
    )
    conn.commit()
    stand = conn.execute("SELECT forderung_stand FROM knowledge_nodes WHERE path='/brainlehr/alt'").fetchone()[0]
    assert stand == "abgelehnt"
    conn.close()


def test_gruen_unbekannter_zustand_scheitert(tmp_path, schema_aktuell):
    db = _frische_db(tmp_path, schema_aktuell)
    conn = sqlite3.connect(str(db))
    with pytest.raises(sqlite3.IntegrityError, match="forderung_stand unzulaessig"):
        conn.execute("UPDATE knowledge_nodes SET forderung_stand='quatsch' WHERE path='/brainlehr/alt'")
    conn.close()


def test_gruen_ruecksetzen_auf_null_scheitert(tmp_path, schema_aktuell):
    db = _frische_db(tmp_path, schema_aktuell)
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='offen' WHERE path='/brainlehr/alt'")
    conn.commit()
    with pytest.raises(sqlite3.IntegrityError, match="forderung_stand kann nicht auf NULL"):
        conn.execute("UPDATE knowledge_nodes SET forderung_stand=NULL WHERE path='/brainlehr/alt'")
    conn.close()


def test_gruen_neuer_knoten_ohne_angabe_bleibt_null(tmp_path, schema_aktuell):
    """Kein stiller Vorgabewert: ein Knoten, der forderung_stand nicht
    mitgibt, bleibt NULL -- das Feld existiert, wird aber nie automatisch
    befuellt (Auftrag F1)."""
    db = _frische_db(tmp_path, schema_aktuell, name="andere.db")
    conn = sqlite3.connect(str(db))
    stand = conn.execute("SELECT forderung_stand FROM knowledge_nodes WHERE path='/brainlehr/alt'").fetchone()[0]
    assert stand is None
    conn.close()


def test_gruen_wechsel_zwischen_zwei_entschiedenen_zustaenden_erlaubt(tmp_path, schema_aktuell):
    """Kein Ruecksfall nur auf NULL -- der Wechsel zwischen zwei echten
    Zustaenden bleibt frei (z.B. offen -> ueberholt)."""
    db = _frische_db(tmp_path, schema_aktuell)
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='offen' WHERE path='/brainlehr/alt'")
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='ueberholt' WHERE path='/brainlehr/alt'")
    conn.commit()
    stand = conn.execute("SELECT forderung_stand FROM knowledge_nodes WHERE path='/brainlehr/alt'").fetchone()[0]
    assert stand == "ueberholt"
    conn.close()


# --- Die FALLE aus dem Auftrag: gewachsene DB ohne die Spalten -------------

def test_gewachsene_db_ohne_spalten_bricht_ensure_schema_nicht_ab(tmp_path, monkeypatch):
    """Kopie einer Datenbank OHNE forderung_stand/forderung_grund (Stand vor
    B1), ensure_schema() darueber gefahren, Tabellen UND Trigger gezaehlt --
    exakt die im Auftrag verlangte Gegenprobe zur FALLE (Trigger am
    Dateiende, nicht mittendrin -- ein CREATE INDEX an dieser Stelle haette
    executescript mitten in der Datei abbrechen lassen, siehe Kommentar in
    schema.sql)."""
    sys.path.insert(0, str(WURZEL))
    import knowledge_mcp_server as kms

    schema = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    vor = schema.index("    -- forderung_stand (Strang F")
    nach_marker = "    forderung_grund TEXT\n);"
    nach = schema.index(nach_marker) + len(nach_marker)
    kopf = schema[:vor].rstrip()
    assert kopf.endswith(","), kopf[-20:]
    schema_ohne = kopf[:-1] + "\n);" + schema[nach:]
    assert "forderung_stand" not in schema_ohne.split("CREATE TABLE IF NOT EXISTS knowledge_nodes")[1].split(");")[0]

    db = tmp_path / "alt_ohne_forderung.db"
    conn = sqlite3.connect(str(db))
    conn.executescript(schema_ohne)
    vor_tab = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    conn.close()

    monkeypatch.setattr(kms, "DB_PATH", db)
    kms.get_db().close()

    conn = sqlite3.connect(str(db))
    nach_tab = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    cols = {r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    trg = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE '%forderung%'")}
    conn.close()

    assert nach_tab == vor_tab, "ensure_schema() darf keine Tabelle verlieren"
    assert "forderung_stand" in cols and "forderung_grund" in cols
    assert trg == {
        "knowledge_nodes_forderung_stand_check_bi",
        "knowledge_nodes_forderung_stand_check_bu",
        "knowledge_nodes_forderung_abgelehnt_grund_bi",
        "knowledge_nodes_forderung_abgelehnt_grund_bu",
        "knowledge_nodes_forderung_stand_kein_rueckfall_bu",
    }, trg
