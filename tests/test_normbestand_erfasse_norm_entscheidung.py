"""Rot-vor-gruen-Beleg zum Fund in kern/normbestand.py::erfasse(): der
'created'-Zweig rief kms.knowledge_add() frueher OHNE norm_entscheidung auf
(PFLICHTfeld seit 2026-08-08) -- fuer Regelartefakte (globale CLAUDE.md,
hub-CLAUDE.md, docs/adr/*.md) waere 'keine_norm' geraten gewesen, keine
Einordnung. Jetzt zwingt der Server den Aufrufer, die Einordnung zu liefern,
statt sie zu erfinden.

Sieht der Code anders aus als hier beschrieben, halte dich an den Code und
melde die Abweichung."""
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

ROOT = _w
sys.path.insert(0, str(ROOT))

import knowledge_mcp_server as kms  # noqa: E402
import normbestand  # noqa: E402

# Gesichert VOR jedem Fixture-Lauf (gleiches Muster wie test_norm_entscheidung.py):
# conftest.py patcht kms.knowledge_add fuer Testbequemlichkeit mit Vorgabewerten
# (u.a. norm_entscheidung) -- diese Referenz ruft die ECHTE, ungeschminkte
# Durchsetzung auf, sonst wuerde der erste Test hier still gruen, obwohl die
# Schranke geprueft werden soll.
_REAL_ADD = kms.knowledge_add


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    now = kms.now_iso()
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source,
            created_at, updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
           VALUES ('root0001', '/', NULL, 'shared', 'root', 'root', '', 0, '[]',
                   'testfixtur:test_normbestand_erfasse_norm_entscheidung.py',
                   ?, ?, 'keine_norm', 'skript:test', 'Testvorrichtung: Wurzelknoten')""",
        (now, now),
    )
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source,
            created_at, updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
           VALUES ('meth0001', '/methodik', '/', 'shared', 'methodik', 'methodik', '', 1, '[]',
                   'testfixtur:test_normbestand_erfasse_norm_entscheidung.py',
                   ?, ?, 'keine_norm', 'skript:test', 'Testvorrichtung: Sammelknoten')""",
        (now, now),
    )
    conn.execute(
        """INSERT INTO knowledge_nodes
           (id, path, parent_path, project_id, title, summary, content, level, tags, source,
            created_at, updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund)
           VALUES ('dir00001', '/methodik/direktiven', '/methodik', 'shared', 'direktiven', 'x', '', 2, '[]',
                   'testfixtur:test_normbestand_erfasse_norm_entscheidung.py',
                   ?, ?, 'keine_norm', 'skript:test', 'Testvorrichtung: Sammelknoten')""",
        (now, now),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def test_uebernahme_ohne_einordnung_wird_abgewiesen(temp_db):
    """Die eigentliche Schranke, gegen die erfasse() heute anrennen wuerde,
    liesse man norm_entscheidung wieder weg: derselbe Aufruf, den der
    'created'-Zweig fuer ein Regelartefakt absetzt, MINUS norm_entscheidung.
    Gegen den heutigen Server-Code (seit 2026-08-08) ist das ein 'error',
    kein stiller Erfolg mit geratener Einordnung -- das war NICHT immer so:
    vor diesem Feld haette derselbe Aufruf klaglos angenommen."""
    res = _REAL_ADD(
        parent_path="/", title="Testabschnitt ohne Einordnung",
        summary="x", content="Text", project_id="shared", tags=["methodik"],
        source="erzeugt aus /irgendeine/CLAUDE.md (Stand 2026-08-12T00:00:00+02:00)",
        actor="normbestand.py",
        # norm_entscheidung bewusst weggelassen -- das war die Luecke.
    )
    assert "error" in res, res
    assert "norm_entscheidung" in res["error"]


def test_erfasse_liefert_die_einordnung_mit(temp_db):
    """Gegenprobe: der reparierte 'created'-Zweig liefert norm_entscheidung
    mit und legt die drei Regelartefakt-Quellen tatsaechlich an."""
    tmp = temp_db.parent
    global_md = tmp / "global.md"
    global_md.write_text("# G\n\n## Ein Abschnitt\n\nText.\n", encoding="utf-8")
    hub_md = tmp / "hub.md"
    hub_md.write_text("# H\n\nkein Abschnitt\n", encoding="utf-8")
    adr_dir = tmp / "adr"
    adr_dir.mkdir()

    out = normbestand.erfasse(temp_db, apply=True, global_md=global_md,
                               hub_md=hub_md, adr_dir=adr_dir)
    assert out["angelegt"]["global"], out

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT norm_entscheidung, norm_rang, gilt_bis FROM knowledge_nodes WHERE path = ?",
        (out["angelegt"]["global"][0],),
    ).fetchone()
    conn.close()
    assert row["norm_entscheidung"] == "norm_unbefristet", dict(row)
    assert row["norm_rang"] == 1, dict(row)
    assert row["gilt_bis"] is None, dict(row)


if __name__ == "__main__":
    import subprocess
    raise SystemExit(subprocess.run(
        [sys.executable, "-m", "pytest", str(Path(__file__)), "-q"]).returncode)
