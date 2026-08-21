"""Tests fuer forderung_faellig_am/forderung_zustaendig (P17, Auftrag
2026-08-21, docs/PLAN_NAECHSTE_STUFE_2026-08-21.md Abschnitt 3.2/9).

NICHT zu verwechseln mit tests/test_faelligkeit.py -- das prueft
melder/faelligkeit.py, den Startmelder-ROTATIONSKANAL fuer nie gelesene
Normen/Lehren (Auftrag 2026-08-20). Diese Datei hier prueft die KALENDER-
Achse einer Forderung (Strang F, melder/forderung_vorgang.py): Faelligkeits-
datum und Zustaendiger je Vorgang. Zwei verschiedene Dinge, die beide
zufaellig "Faelligkeit" heissen -- daher der laengere Dateiname.

Belegt gegen den festen Bezugspunkt Commit 5403a71b: dort kannte
knowledge_nodes weder forderung_faellig_am noch forderung_zustaendig, und die
Startliste (melder/forderung_vorgang.offene()) sortierte ausschliesslich nach
created_at. Diese Datei zeigt zuerst, dass genau das an 5403a71b zutraf (ROT),
dann dass der aktuelle Stand die Kalender-Achse traegt (GRUEN).

BEIDE Ausgangszustaende: frisch (ueber schema.sql direkt) UND gewachsen (eine
Datenbank auf Stand 5403a71b, per schema_nachzug ergaenzt -- der Weg, den ein
echter Betrieb tatsaechlich nimmt, siehe knowledge_mcp_server._ensure_core_
schema -> schema_nachzug.nachziehen())."""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "melder"))
sys.path.insert(0, str(WURZEL / "kern"))
sys.path.insert(0, str(WURZEL / "haken"))

import forderung_vorgang  # noqa: E402
import schema_nachzug  # noqa: E402

BEZUGSPUNKT = "5403a71b"


def _insert_sql(node_id: str, path: str, erstellt: str) -> str:
    return (
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, "
        "level, source, created_at, norm_entscheidung, norm_entschieden_von, "
        "norm_entschieden_grund) VALUES "
        f"('{node_id}','{path}','shared','t','x','x',0,'test','{erstellt}','keine_norm','test',"
        "'Testvorrichtung, keine echte Norm-Pruefung')"
    )


@pytest.fixture()
def schema_bezugspunkt() -> str:
    return subprocess.run(
        ["git", "show", f"{BEZUGSPUNKT}:schema.sql"],
        cwd=WURZEL, capture_output=True, text=True, check=True,
    ).stdout


@pytest.fixture()
def schema_aktuell() -> str:
    return (WURZEL / "schema.sql").read_text(encoding="utf-8")


def _frische_db(tmp_path: Path, schema: str, name: str = "test.db") -> Path:
    db = tmp_path / name
    conn = sqlite3.connect(str(db))
    conn.executescript(schema)
    conn.execute(_insert_sql("a", "/brainlehr/frist_bald", "2026-08-01T09:00:00Z"))
    conn.execute(_insert_sql("b", "/brainlehr/frist_spaet", "2026-08-02T09:00:00Z"))
    conn.execute(_insert_sql("c", "/brainlehr/ohne_frist", "2026-07-01T09:00:00Z"))
    conn.commit()
    conn.close()
    return db


# --- ROT: Bezugspunkt kennt die Kalender-Achse nicht ------------------------

def test_rot_bezugspunkt_hat_keine_faelligkeitsspalte(tmp_path, schema_bezugspunkt):
    db = _frische_db(tmp_path, schema_bezugspunkt)
    conn = sqlite3.connect(str(db))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    conn.close()
    assert "forderung_faellig_am" not in cols, "Befund ungueltig -- Spalte existierte schon"
    assert "forderung_zustaendig" not in cols, "Befund ungueltig -- Spalte existierte schon"


def test_rot_bezugspunkt_startliste_sortiert_nur_nach_alter(tmp_path, schema_bezugspunkt):
    """Am Bezugspunkt sortiert offene() nach created_at -- ein juenger
    angelegter Vorgang kann nicht vor einen aelteren ohne Frist rutschen,
    weil es die Frist als Sortierkriterium schlicht nicht gibt."""
    db = _frische_db(tmp_path, schema_bezugspunkt)
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE knowledge_nodes SET forderung_stand='offen'")
    conn.commit()
    rows = conn.execute(
        "SELECT path FROM knowledge_nodes WHERE forderung_stand='offen' ORDER BY created_at ASC"
    ).fetchall()
    conn.close()
    # aeltester zuerst -- /brainlehr/ohne_frist (2026-07-01) vor den beiden
    # anderen, obwohl es im GRUENEN Stand die spaetere Frist der beiden
    # datierten Vorgaenge unterbieten wuerde.
    assert [r[0] for r in rows][0] == "/brainlehr/ohne_frist"


# --- GRUEN: aktueller Stand traegt Datum, Zustaendigen, Formpruefung -------

def test_gruen_terminieren_setzt_datum_und_zustaendigen(tmp_path, schema_aktuell):
    db = _frische_db(tmp_path, schema_aktuell)
    forderung_vorgang.markiere("/brainlehr/frist_bald", "offen", db=db)
    forderung_vorgang.terminieren(
        "/brainlehr/frist_bald", faellig_am="2026-08-15", zustaendig="mira", db=db)
    conn = sqlite3.connect(str(db))
    r = conn.execute(
        "SELECT forderung_faellig_am, forderung_zustaendig FROM knowledge_nodes "
        "WHERE path='/brainlehr/frist_bald'").fetchone()
    conn.close()
    assert r == ("2026-08-15", "mira"), r


def test_gruen_negativtest1_vorgang_ohne_datum_bekommt_keines(tmp_path, schema_aktuell):
    """Negativtest 1 (Auftrag): kein Datum ist ein zulaessiger, gewollter
    Zustand -- nicht jede Forderung hat eine Frist."""
    db = _frische_db(tmp_path, schema_aktuell)
    forderung_vorgang.markiere("/brainlehr/ohne_frist", "offen", db=db)
    conn = sqlite3.connect(str(db))
    f = conn.execute(
        "SELECT forderung_faellig_am FROM knowledge_nodes WHERE path='/brainlehr/ohne_frist'"
    ).fetchone()[0]
    conn.close()
    assert f is None, ("stiller Vorgabewert entstanden", f)


def test_gruen_negativtest2_vergangenheit_ok_ungueltiges_format_scheitert(tmp_path, schema_aktuell):
    """Negativtest 2 (Auftrag): ein Datum in der Vergangenheit ist zulaessig
    (Fristen laufen ab), ein UNGUELTIGES Datum scheitert."""
    db = _frische_db(tmp_path, schema_aktuell)
    forderung_vorgang.markiere("/brainlehr/frist_bald", "offen", db=db)

    # Vergangenheit: darf gelingen.
    forderung_vorgang.terminieren("/brainlehr/frist_bald", faellig_am="2020-01-01", db=db)

    # Ungueltiges Format: muss scheitern.
    with pytest.raises(sqlite3.IntegrityError, match="forderung_faellig_am"):
        forderung_vorgang.terminieren("/brainlehr/frist_bald", faellig_am="nicht-datum", db=db)


def test_gruen_gegenprobe_beide_richtungen_und_sortierung(tmp_path, schema_aktuell):
    """Gegenprobe in beide Richtungen: ein abgeschlossener Vorgang
    verschwindet aus der Startliste, ein offener mit Frist steht darin -- und
    die Sortierung stimmt, wenn beide Sorten (mit/ohne Frist) gemischt sind."""
    db = _frische_db(tmp_path, schema_aktuell)
    for pfad in ("/brainlehr/frist_bald", "/brainlehr/frist_spaet", "/brainlehr/ohne_frist"):
        forderung_vorgang.markiere(pfad, "offen", db=db)
    forderung_vorgang.terminieren("/brainlehr/frist_bald", faellig_am="2026-08-15", db=db)
    forderung_vorgang.terminieren("/brainlehr/frist_spaet", faellig_am="2026-09-01", db=db)
    # /brainlehr/ohne_frist bleibt ohne Datum, ist aber AELTER (2026-07-01)
    # als beide datierten -- die alte Sortierung haette es zuerst gezeigt.

    off = forderung_vorgang.offene(db)
    assert [o["path"] for o in off] == [
        "/brainlehr/frist_bald", "/brainlehr/frist_spaet", "/brainlehr/ohne_frist",
    ], off

    # Abschluss wirkt: /brainlehr/frist_spaet verschwindet, die anderen bleiben.
    forderung_vorgang.markiere("/brainlehr/frist_spaet", "erledigt", db=db)
    off = forderung_vorgang.offene(db)
    assert [o["path"] for o in off] == [
        "/brainlehr/frist_bald", "/brainlehr/ohne_frist",
    ], off


# --- Ausgangszustand 2: gewachsen (Bezugspunkt + Nachzug) ------------------

def test_gewachsene_db_bekommt_die_kalenderachse_per_nachzug(tmp_path, schema_bezugspunkt, schema_aktuell):
    """Der Weg, den ein echter Betrieb nimmt: eine Datenbank auf dem Stand
    von 5403a71b (ohne die neuen Spalten), darueber schema_nachzug.nachziehen()
    mit dem AKTUELLEN schema.sql -- wie knowledge_mcp_server._ensure_core_
    schema es tut. Bestandszeile ueberlebt, die neuen Spalten sind NULL."""
    db = _frische_db(tmp_path, schema_bezugspunkt, name="gewachsen.db")
    conn = sqlite3.connect(str(db))
    ergaenzt = schema_nachzug.nachziehen(conn, schema_aktuell)
    conn.commit()

    cols = {r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    assert {"forderung_faellig_am", "forderung_zustaendig"} <= cols, cols
    assert "forderung_faellig_am" in ergaenzt.get("knowledge_nodes", []), ergaenzt

    # Bestandszeile ueberlebt, neue Spalten sind NULL (kein stiller Vorgabewert).
    r = conn.execute(
        "SELECT forderung_faellig_am, forderung_zustaendig FROM knowledge_nodes "
        "WHERE path='/brainlehr/frist_bald'").fetchone()
    assert r == (None, None), r
    conn.close()

    # Und ueber diese nachgezogene DB funktioniert terminieren()/offene() wie
    # auf einer frischen -- der Aufrufer merkt den Unterschied nicht.
    forderung_vorgang.markiere("/brainlehr/frist_bald", "offen", db=db)
    forderung_vorgang.terminieren("/brainlehr/frist_bald", faellig_am="2026-08-15", db=db)
    off = forderung_vorgang.offene(db)
    assert [o["path"] for o in off] == ["/brainlehr/frist_bald"], off
