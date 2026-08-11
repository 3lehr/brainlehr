"""knowledge_update kann bisher summary/content/tags aendern, aber nicht
title -- die Signatur nennt title nicht, und der updates/params-Block hat
keinen title-Zweig. Blockiert den Umschriftlauf ueber 384 Knoten (Titel ist
der wirksamste Teil der Umschrift, Trefferquote 3/20 auf 10/20 gemessen).

ROT VOR GRUEN: gegen den Stand vor der Aenderung bricht
test_title_aendert_sich_pfad_bleibt mit TypeError ab (title ist kein
Parameter von knowledge_update).

Die Fassungshistorie (Trigger knowledge_fassung_au, schema.sql,
2026-08-09) existiert in DIESEM Repo-Wurzel-schema.sql noch nicht -- nur
in der Worktree hallo-3b3c8d, wo der Trigger geschrieben wurde. In der
LIVE-DB (brainlehr.db am Repo-Stamm) steht er trotzdem schon (per Hand
angewendet). Diese Testdatei spielt ihn deshalb direkt als DDL ein, wie
test_update_fremder_actor.py es fuer herkunft_unveraenderlich.sql tut --
sonst wuerde der Test die Archivierung gar nicht pruefen."""
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

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

_FASSUNGEN_DDL = """
CREATE TABLE IF NOT EXISTS knowledge_fassungen (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    path TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    content TEXT,
    tags TEXT,
    actor TEXT,
    model TEXT,
    session TEXT,
    galt_bis TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_fassungen_node ON knowledge_fassungen(node_id, id DESC);
CREATE TRIGGER IF NOT EXISTS knowledge_fassung_au AFTER UPDATE ON knowledge_nodes
WHEN COALESCE(OLD.title,'')   <> COALESCE(NEW.title,'')
  OR COALESCE(OLD.summary,'') <> COALESCE(NEW.summary,'')
  OR COALESCE(OLD.content,'') <> COALESCE(NEW.content,'')
  OR COALESCE(OLD.tags,'')    <> COALESCE(NEW.tags,'')
BEGIN
    INSERT INTO knowledge_fassungen (node_id, path, title, summary, content, tags, actor, model, session)
    VALUES (OLD.id, OLD.path, OLD.title, OLD.summary, OLD.content, OLD.tags, OLD.actor, OLD.model, OLD.session);
END;
"""


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.executescript(_FASSUNGEN_DDL)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _anlegen(**kw):
    res = kms.knowledge_add(
        parent_path="/",
        title=kw.pop("title", "Alter Titel"),
        summary="Ausgangs-Summary",
        content=kw.pop("content", "Ausgangs-Content"),
        source="erzeugt fuer test_knowledge_update_title.py",
        neuer_ast=True,
        norm_entscheidung="keine_norm",
        norm_entschieden_grund="Testknoten, keine Regel",
        actor="actor-A",
        session="sitzung-A",
        model="modell-A",
        **kw,
    )
    assert "error" not in res, res
    return res["id"]


def _row(db_path, node_id):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,)).fetchone()
    conn.close()
    return row


def test_title_aendert_sich_pfad_bleibt(temp_db):
    node_id = _anlegen()
    vorher = _row(temp_db, node_id)
    alter_pfad = vorher["path"]

    res = kms.knowledge_update(node_id, title="Neuer Titel", actor="actor-B")
    assert "error" not in res, res

    nachher = _row(temp_db, node_id)
    assert nachher["title"] == "Neuer Titel"
    # Der Pfad bleibt stehen -- title wird nur bei knowledge_add zu einem
    # Pfad geslugt, nie nachtraeglich (Rueckverweise/Kanten haengen am Pfad).
    assert nachher["path"] == alter_pfad

    # Gegenprobe: die alte Fassung steht genau einmal im Archiv, mit dem
    # ALTEN Titel -- das ist zugleich der Beleg, dass der Rueckweg existiert.
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    fassungen = conn.execute(
        "SELECT * FROM knowledge_fassungen WHERE node_id = ?", (node_id,)
    ).fetchall()
    conn.close()
    assert len(fassungen) == 1
    assert fassungen[0]["title"] == "Alter Titel"


def test_ohne_title_bleibt_titel_stehen(temp_db):
    """Gegenrichtung: ein Aufruf ohne title darf den Titel nicht still leeren."""
    node_id = _anlegen()

    res = kms.knowledge_update(node_id, summary="nur Summary geaendert", actor="actor-B")
    assert "error" not in res, res

    row = _row(temp_db, node_id)
    assert row["title"] == "Alter Titel"
    assert row["summary"] == "nur Summary geaendert"


def test_nur_title_laesst_summary_und_content_unberuehrt(temp_db):
    """Negativfall: ein Aufruf, der NUR title setzt, aendert weder summary
    noch content."""
    node_id = _anlegen()

    res = kms.knowledge_update(node_id, title="Nur der Titel", actor="actor-B")
    assert "error" not in res, res

    row = _row(temp_db, node_id)
    assert row["title"] == "Nur der Titel"
    assert row["summary"] == "Ausgangs-Summary"
    assert row["content"] == "Ausgangs-Content"
