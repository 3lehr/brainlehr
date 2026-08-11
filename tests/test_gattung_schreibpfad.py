"""Die Gattung muss ueber den MCP-Weg setzbar sein, nicht nur in der Datenbank.

BEFUND, der diesen Test veranlasst hat (2026-08-10, docs/PLAN_KLIENTENDOKU §5):
`knowledge_nodes.gattung` traegt den Unterschied zwischen ARBEITSBESTAND und
NACHSCHLAGEWERK. Nachschlagewerke sind ausdruecklich Heuhaufen -- sie duerfen im
Bestand liegen und als Ablenkung dienen, aber nie Ziel eines Prueffalls sein
(Wissensknoten 096669de), und `kern/pruefkorpus.py` filtert sie genau danach.

Die Spalte existiert seit einer Migration, hat einen Wertebereichs-Trigger und
die Vorgabe 'arbeitsbestand'. Der MCP-Server kannte sie bis heute NICHT: weder
`knowledge_add` noch `knowledge_update` nahmen sie entgegen, und im
Werkzeugschema fehlte sie. Damit landete jeder ueber den einzigen zugelassenen
Schreibweg angelegte Fremdquellen-Knoten als Arbeitsbestand -- und verduennte
den Abruf, gegen den er als Ablenkung haette liegen sollen.

Was ausdruecklich NICHT der Ausweg war: ein rohes SQLite-UPDATE. Es umgeht
Herkunftspflicht, Zugriffsprotokoll und Auditkette; der Plan nennt es
"Audit-Bypass" und hat es aus genau diesem Grund unterlassen.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3
import sys
import uuid

import pytest

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def frische_db(tmp_path, monkeypatch):
    """Leere Datenbank aus schema.sql -- kein Bestand, keine Fremdwirkung."""
    pfad = tmp_path / "knowledge.db"
    conn = sqlite3.connect(str(pfad))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", pfad)
    return pfad


def _gattung(pfad, node_id: str) -> str:
    conn = sqlite3.connect(str(pfad))
    try:
        zeile = conn.execute(
            "SELECT gattung FROM knowledge_nodes WHERE id=?", (node_id,)).fetchone()
    finally:
        conn.close()
    assert zeile, f"Knoten {node_id} nicht angelegt"
    return zeile[0]


def _anlegen(**mehr):
    """Ein Knoten mit den Pflichtfeldern, damit die Trigger ihn durchlassen."""
    return kms.knowledge_add(
        parent_path="/",
        title=f"Probe {uuid.uuid4().hex[:8]}",
        summary="Probeknoten fuer den Gattungs-Schreibweg.",
        source="Test test_gattung_schreibpfad.py",
        norm_entscheidung="keine_norm",
        norm_entschieden_grund="Testknoten ohne normative Wirkung.",
        **mehr,
    )


def test_das_werkzeugschema_kennt_gattung():
    """ROT VOR GRUEN: bis 2026-08-11 fehlte das Feld in beiden Schemata.

    Ein Feld, das die Funktion annimmt, aber das Schema nicht nennt, ist fuer
    ein Sprachmodell nicht vorhanden -- es sieht nur das Schema."""
    for werkzeug in ("knowledge_add", "knowledge_update"):
        felder = kms.TOOLS[werkzeug]["inputSchema"]["properties"]
        assert "gattung" in felder, f"{werkzeug} nennt gattung nicht"
        assert felder["gattung"].get("enum") == ["arbeitsbestand", "nachschlagewerk"], \
            f"{werkzeug}: Wertebereich fehlt oder weicht vom Trigger ab"


def test_ohne_angabe_bleibt_es_arbeitsbestand(frische_db):
    """Die Vorgabe darf sich durch den neuen Weg NICHT aendern."""
    erg = _anlegen()
    assert "error" not in erg, erg
    assert _gattung(frische_db, erg["id"]) == "arbeitsbestand"


def test_nachschlagewerk_laesst_sich_setzen(frische_db):
    """Der eigentliche Zweck: ein Fremdquellen-Knoten als Heuhaufen."""
    erg = _anlegen(gattung="nachschlagewerk")
    assert "error" not in erg, erg
    assert _gattung(frische_db, erg["id"]) == "nachschlagewerk"


def test_unzulaessiger_wert_wird_abgewiesen(frische_db):
    """NEGATIVFALL: der Trigger muss greifen, nicht der Aufrufer.

    Wichtig ist hier nicht, DASS abgewiesen wird, sondern WO -- die Schranke
    sitzt in der Datenbank und wirkt damit auch fuer Wege, die an dieser
    Funktion vorbeischreiben."""
    erg = _anlegen(gattung="heuhaufen")
    assert "error" in erg, f"unzulaessige Gattung wurde angenommen: {erg}"
    assert "gattung" in erg["error"].lower()


def test_umklassifizieren_geht_ueber_update(frische_db):
    """Bestehende Knoten muessen umgestellt werden koennen -- sonst bleibt der
    Weg fuer die drei bereits angelegten Destillate versperrt."""
    erg = _anlegen()
    assert _gattung(frische_db, erg["id"]) == "arbeitsbestand"
    kms.knowledge_update(node_id=erg["id"], gattung="nachschlagewerk")
    assert _gattung(frische_db, erg["id"]) == "nachschlagewerk"


def test_update_ohne_gattung_laesst_sie_stehen(frische_db):
    """Gegenprobe: eine Aktualisierung anderer Felder darf die Gattung nicht
    stillschweigend auf die Vorgabe zuruecksetzen."""
    erg = _anlegen(gattung="nachschlagewerk")
    kms.knowledge_update(node_id=erg["id"], summary="Neue Zusammenfassung.")
    assert _gattung(frische_db, erg["id"]) == "nachschlagewerk"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
