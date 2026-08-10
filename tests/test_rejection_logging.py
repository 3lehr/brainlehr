"""Tests fuer Ablehnungs-Protokollierung (Auftrag 2026-08-06).

Befund vor diesem Fix: access_log stand bei completed=1349/started=212/
rejected=0, obwohl knowledge_mcp_server.py taeglich Ablehnungen aussprach
(fehlende source, ungueltiger anlass, Elternpfad-Fehler, ...). Jeder fruehe
return mit einem error-Feld gibt den Fehler an den Aufrufer zurueck, ohne
ihn je in access_log zu schreiben -- das Werkzeug MELDET, PROTOKOLLIERT aber
nicht.

Fix: jeder dieser Rueckgabepfade ruft vorher log_access(..., status="rejected",
query=<feste Grund-Kategorie>) -- query wird hier zweckentfremdet (bedeutet
bei anderen Actions Suchtext/Relation-ID), das stoert nicht, weil jede
Auswertung auf status='rejected' einschraenkt. Kein Schema-Wechsel: status
und query existierten bereits, nur "rejected" kam zu EVENT_STATUSES dazu.
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

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import knowledge_lint as lint  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische Test-DB mit dem echten Schema, DB_PATH umgebogen. NIE gegen knowledge.db."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _rejected_rows(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT action, query FROM access_log WHERE status = 'rejected'"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def test_rot_vor_gruen_ablehnung_wird_protokolliert(temp_db):
    """Vorher keine Zeile, nachher eine mit status='rejected' + Grund."""
    assert _rejected_rows(temp_db) == []  # ROT: noch nichts

    result = kms.knowledge_add(parent_path="/", title="t", summary="s", source="")

    assert result == {
        "error": "source fehlt: Herkunft des Knotens angeben (aus welcher Datei/welchem Lauf er stammt). "
                 "Beispiel: 'erzeugt aus /pfad/zur/datei.md (Stand 2026-08-05T23:40:00+02:00)'.",
    }
    rows = _rejected_rows(temp_db)
    assert rows == [{"action": "add", "query": "source_fehlt"}]  # GRUEN


def test_gueltiger_aufruf_bleibt_unveraendert_und_erzeugt_keine_ablehnung(temp_db):
    result = kms.knowledge_add(parent_path="/", title="t", summary="s", source="quelle.md")
    assert result["status"] == "created"
    assert _rejected_rows(temp_db) == []


def test_alle_bekannten_ablehnungspfade_protokollieren(temp_db):
    """Ein Pfad je bekannter Kategorie -- Vollstaendigkeits-Stichprobe."""
    r_ok = kms.knowledge_add(parent_path="/", title="Dup", summary="s", source="quelle.md")
    nid = r_ok["id"]

    faelle = [
        ("add", "anlass_ungueltig",
         lambda: kms.knowledge_add(parent_path="/", title="a1", summary="s", source="x", anlass="quatsch")),
        ("add", "source_fehlt",
         lambda: kms.knowledge_add(parent_path="/", title="a2", summary="s", source="")),
        ("add", "elternpfad_fehlt",
         lambda: kms.knowledge_add(parent_path="/nope", title="a3", summary="s", source="x")),
        ("add", "pfad_existiert_bereits",
         lambda: kms.knowledge_add(parent_path="/", title="Dup", summary="s", source="x")),
        ("update", "knoten_nicht_gefunden",
         lambda: kms.knowledge_update(node_id="doesnotexist")),
        ("zurueckziehen", "grund_fehlt",
         lambda: kms.knowledge_zurueckziehen(node_id=nid, grund="")),
        ("read", "knoten_nicht_gefunden",
         lambda: kms.knowledge_read(node_id="doesnotexist")),
        ("relation_update", "relation_nicht_gefunden",
         lambda: kms.knowledge_relation_update(relation_id="doesnotexist")),
        ("lesson", "beschreibung_leer",
         lambda: kms.lesson_record(type_="insight", description="")),
        ("lesson_update", "lesson_nicht_gefunden",
         lambda: kms.lesson_update(lesson_id="doesnotexist")),
    ]
    for action, grund, aufruf in faelle:
        vorher = len(_rejected_rows(temp_db))
        res = aufruf()
        assert "error" in res
        rows = _rejected_rows(temp_db)
        assert len(rows) == vorher + 1, f"{action}/{grund}: keine neue Zeile"
        assert rows[-1] == {"action": action, "query": grund}


def test_lint_zeigt_ablehnungen_je_grund_und_lehren_im_zeitraum(temp_db):
    kms.knowledge_add(parent_path="/", title="a1", summary="s", source="")
    kms.knowledge_add(parent_path="/", title="a2", summary="s", source="")
    kms.knowledge_add(parent_path="/", title="a3", summary="s", source="x", anlass="quatsch")
    kms.lesson_record(type_="insight", description="Lehre aus den drei Ablehnungen")

    result = lint.run(db_path=temp_db)
    rj = result["rejections"]
    assert rj["gesamt"] == 3
    by_grund = {i["grund"]: i["anzahl"] for i in rj["je_grund"]}
    assert by_grund == {"source_fehlt": 2, "anlass_ungueltig": 1}
    assert rj["lessons_im_zeitraum"] == 1


def test_lint_keine_ablehnungen_ist_leer(temp_db):
    result = lint.run(db_path=temp_db)
    assert result["rejections"]["gesamt"] == 0
    assert result["rejections"]["je_grund"] == []
