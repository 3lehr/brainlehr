"""Tests fuer den WAL-Checkpoint-Fix in den _backup()-Fassungen.

Befund 2026-08-05: shutil.copy2 der Hauptdatei einer WAL-DB kann committete,
aber noch nicht ins Hauptfile zurueckgeschriebene Aenderungen verlieren --
beobachtet an drei echten .bak-Dateien, denen die neu angelegte Spalte
norm_rang fehlte (eine davon entstand sogar NACH der Migration).

Testet vier Fassungen (normrang.py::_backup ist bereits korrekt, ist Vorlage,
wird hier nicht erneut getestet -- eigene Tests in test_normrang.py):
build_embeddings._backup, fix_namensraum_knoten._backup, hebb_kanten._backup,
migrate_normfelder._backup. migrate_relations.py hat keine eigene
_backup()-Fassung -- migrate() nutzt sqlite3 Connection.backup(), die
Online-Backup-API, die WAL-konsistent liest (kein Checkpoint noetig, separat
belegt in test_rot_vor_gruen_alter_copy2_verliert_wal_daten als Kontrast).
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

import shutil
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "kern"))

import build_embeddings
import fix_namensraum_knoten
import hebb_kanten
import migrate_normfelder

# (Modul, _backup-Aufruf, DB_PATH-Attribut-Patch noetig?)
NO_ARG = [build_embeddings, fix_namensraum_knoten]  # _backup() liest Modul-DB_PATH
WITH_ARG = [hebb_kanten, migrate_normfelder]  # _backup(db_path)


def _make_wal_db(db_path: Path, keep_open: sqlite3.Connection | None = None) -> None:
    conn = keep_open or sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    if keep_open is None:
        conn.close()


def _add_column_leave_in_wal(db_path: Path, keep_open: sqlite3.Connection | None = None) -> None:
    """Simuliert die Migration: Spalte committen, aber WAL klein genug lassen,
    dass wal_autocheckpoint (Vorgabe 1000 Seiten) NICHT von selbst abgleicht.

    Wichtig fuer den Testaufbau (siehe L-cc6d37 in der Knowledge-DB): SQLite
    checkpointet automatisch, wenn die LETZTE offene Verbindung zur Datei
    schliesst -- schliessen alle Verbindungen zwischen Schreiben und Kopieren,
    verschwindet die WAL-Datei von selbst und der Fehler laesst sich nicht
    mehr reproduzieren. `keep_open` haelt deshalb waehrend des ganzen Tests
    eine Verbindung offen, genau wie im echten Betrieb der Recall-Hook."""
    conn = keep_open or sqlite3.connect(str(db_path))
    conn.execute("ALTER TABLE t ADD COLUMN norm_rang INTEGER")
    conn.execute("INSERT INTO t VALUES (2, 5)")
    conn.commit()
    if keep_open is None:
        conn.close()


def _has_column(db_path: Path, col: str) -> bool:
    conn = sqlite3.connect(str(db_path))
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(t)")}
        return col in cols
    finally:
        conn.close()


# --- rot: der alte, kaputte Weg -------------------------------------------

def test_rot_vor_gruen_alter_copy2_verliert_wal_daten(tmp_path):
    """Beleg fuer den Fehler selbst: reiner shutil.copy2 (der alte Stand
    aller vier Fassungen vor diesem Fix) verliert die WAL-Aenderung."""
    db_path = tmp_path / "brainlehr.db"
    holder = sqlite3.connect(str(db_path))  # bleibt offen, siehe Docstring oben
    try:
        _make_wal_db(db_path, keep_open=holder)
        _add_column_leave_in_wal(db_path, keep_open=holder)
        assert (db_path.parent / "brainlehr.db-wal").exists()
        assert _has_column(db_path, "norm_rang")  # Live-DB hat die Spalte

        dest = tmp_path / "alt.bak"
        shutil.copy2(db_path, dest)  # der alte Weg, ohne Checkpoint
        assert not _has_column(dest, "norm_rang"), (
            "Beweis fuer den Fehler: die Kopie haette die Spalte nicht sehen "
            "duerfen, wenn der Bug real ist -- WAL-Daten wurden nicht mitkopiert."
        )
    finally:
        holder.close()


# --- gruen: die reparierten Fassungen --------------------------------------

@pytest.mark.parametrize("mod", NO_ARG)
def test_backup_no_arg_enthaelt_wal_daten(tmp_path, monkeypatch, mod):
    db_path = tmp_path / "brainlehr.db"
    holder = sqlite3.connect(str(db_path))
    try:
        _make_wal_db(db_path, keep_open=holder)
        _add_column_leave_in_wal(db_path, keep_open=holder)
        monkeypatch.setattr(mod, "DB_PATH", db_path)

        dest = mod._backup()
        assert _has_column(dest, "norm_rang")
    finally:
        holder.close()


@pytest.mark.parametrize("mod", WITH_ARG)
def test_backup_with_arg_enthaelt_wal_daten(tmp_path, mod):
    db_path = tmp_path / "brainlehr.db"
    holder = sqlite3.connect(str(db_path))
    try:
        _make_wal_db(db_path, keep_open=holder)
        _add_column_leave_in_wal(db_path, keep_open=holder)

        dest = mod._backup(db_path)
        assert _has_column(dest, "norm_rang")
    finally:
        holder.close()


# --- Gegenprobe: DB ohne WAL-Sidecar bleibt unbeeintraechtigt --------------

@pytest.mark.parametrize("mod", NO_ARG)
def test_backup_ohne_wal_sidecar_no_arg(tmp_path, monkeypatch, mod):
    db_path = tmp_path / "brainlehr.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()
    assert not (db_path.parent / "brainlehr.db-wal").exists()
    monkeypatch.setattr(mod, "DB_PATH", db_path)

    dest = mod._backup()
    assert dest.exists()
    c = sqlite3.connect(str(dest))
    assert c.execute("SELECT x FROM t").fetchone() == (1,)
    c.close()


@pytest.mark.parametrize("mod", WITH_ARG)
def test_backup_ohne_wal_sidecar_with_arg(tmp_path, mod):
    db_path = tmp_path / "brainlehr.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE t (x INTEGER)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()

    dest = mod._backup(db_path)
    assert dest.exists()
    c = sqlite3.connect(str(dest))
    assert c.execute("SELECT x FROM t").fetchone() == (1,)
    c.close()


# --- Fehlerfall: Checkpoint blockiert -> keine unvollstaendige Datei -------

@pytest.mark.parametrize("mod", WITH_ARG)
def test_backup_bricht_ab_wenn_checkpoint_busy(tmp_path, mod):
    db_path = tmp_path / "brainlehr.db"
    _make_wal_db(db_path)

    # Zweite Verbindung haelt eine offene Schreibtransaktion -> TRUNCATE-
    # Checkpoint kann die WAL nicht leeren und meldet busy=1 (empirisch
    # geprueft, siehe Modul-Docstring-Befund).
    blocker = sqlite3.connect(str(db_path))
    blocker.execute("BEGIN IMMEDIATE")
    blocker.execute("INSERT INTO t VALUES (2)")
    try:
        before = set(db_path.parent.glob("brainlehr.db.bak-*"))
        with pytest.raises(RuntimeError, match="WAL-Checkpoint blockiert"):
            mod._backup(db_path)
        after = set(db_path.parent.glob("brainlehr.db.bak-*"))
        assert before == after, "kein neues Sicherungsfile bei blockiertem Checkpoint"
    finally:
        blocker.rollback()
        blocker.close()
