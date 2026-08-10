"""Tests fuer knowledge_zurueckziehen/knowledge_freigeben (Auftrag 2026-08-06,
Luecke "kein Loeschweg fuer die KI"). Entwurfsvorgabe: ein Loeschwerkzeug, das
eine KI autonom aufrufen kann, ist gefaehrlicher als der fehlende Loeschweg
(Auditkette Z5). Zwei Vorgaenge: Zurueckziehen (KI, reversibel, Zeile bleibt)
und endgueltiges Entfernen (nur Mensch, eigenes Skript, siehe
test_endgueltig_entfernen.py)."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _sql(temp_db, query, params=()):
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute(query, params).fetchone()
    conn.close()
    return row


def _make_node(**overrides):
    payload = dict(
        parent_path="/", title="Zuruecknahme-Testknoten",
        summary="Zusammenfassung mit Klartext, den zurueckziehen leeren soll",
        content="Inhalt, der nach dem Zurueckziehen weg sein muss",
        source="erzeugt aus Test (Stand 2026-08-06T00:00:00+0200)",
        norm_entscheidung="keine_norm",
    )
    payload.update(overrides)
    return kms.knowledge_add(**payload)


# ─── a) ROT VOR GRUEN: knowledge_search vor/nach Zurueckziehen ─────────────

def test_a_rot_vor_gruen_suche(temp_db):
    node = _make_node()
    assert node.get("status") == "created", node

    vorher = kms.knowledge_search("Zuruecknahme-Testknoten")
    vorher_ids = [r["id"] for r in vorher["results"]]
    assert node["id"] in vorher_ids, ("VORHER: Knoten muss auffindbar sein", vorher)

    res = kms.knowledge_zurueckziehen(node["id"], "Testbeleg fuer rot-vor-gruen")
    assert res["status"] == "zurueckgezogen", res

    nachher = kms.knowledge_search("Zuruecknahme-Testknoten")
    nachher_ids = [r["id"] for r in nachher["results"]]
    assert node["id"] not in nachher_ids, ("NACHHER: Knoten darf nicht mehr auftauchen", nachher)


# ─── b) Negativfall: Zurueckziehen ohne Begruendung ────────────────────────

def test_b_ohne_grund_abgelehnt(temp_db):
    node = _make_node(title="Ohne-Grund-Testknoten")
    assert node.get("status") == "created", node

    res = kms.knowledge_zurueckziehen(node["id"], "")
    assert "error" in res, res

    row = _sql(temp_db, "SELECT zurueckgezogen, content, summary FROM knowledge_nodes WHERE id = ?", (node["id"],))
    assert row["zurueckgezogen"] == 0, "trotz Ablehnung wurde etwas geaendert"
    assert row["content"], "content waere trotz Ablehnung geleert worden"
    assert row["summary"], "summary waere trotz Ablehnung geleert worden"


# ─── c) Die Zeile bleibt, mit Grund und Zeitpunkt ──────────────────────────

def test_c_zeile_bleibt_mit_grund_und_zeitpunkt(temp_db):
    node = _make_node(title="Zeile-bleibt-Testknoten")
    kms.knowledge_zurueckziehen(node["id"], "Nachweis: Zeile bleibt stehen")

    row = _sql(
        temp_db,
        "SELECT path, title, content, summary, zurueckgezogen, zurueckgezogen_grund, "
        "zurueckgezogen_am, zurueckgezogen_von FROM knowledge_nodes WHERE id = ?",
        (node["id"],),
    )
    assert row is not None, "Zeile ist komplett verschwunden -- das darf Zurueckziehen nicht tun"
    assert row["title"] == "Zeile-bleibt-Testknoten"
    assert row["path"] == node["path"]
    assert row["zurueckgezogen"] == 1
    assert row["zurueckgezogen_grund"] == "Nachweis: Zeile bleibt stehen"
    assert row["zurueckgezogen_am"], "zurueckgezogen_am fehlt"
    assert row["content"] == "", row["content"]
    assert row["summary"] == "", row["summary"]


# ─── d) Umkehrung: freigeben -> taucht wieder auf, content bleibt leer ─────

def test_d_freigeben_macht_sichtbar_nicht_inhalt(temp_db):
    node = _make_node(title="Freigeben-Testknoten")
    kms.knowledge_zurueckziehen(node["id"], "Testbeleg fuer Umkehrung")

    vor_freigabe = kms.knowledge_search("Freigeben-Testknoten")
    assert node["id"] not in [r["id"] for r in vor_freigabe["results"]], vor_freigabe

    res = kms.knowledge_freigeben(node["id"])
    assert res["status"] == "freigegeben", res

    nach_freigabe = kms.knowledge_search("Freigeben-Testknoten")
    # Suche laeuft ueber title -- title blieb die ganze Zeit stehen, deshalb
    # findbar, sobald zurueckgezogen wieder 0 ist.
    assert node["id"] in [r["id"] for r in nach_freigabe["results"]], nach_freigabe

    row = _sql(temp_db, "SELECT content, summary, zurueckgezogen FROM knowledge_nodes WHERE id = ?", (node["id"],))
    assert row["zurueckgezogen"] == 0
    assert row["content"] == "", "Inhalt haette NICHT wiederhergestellt werden duerfen"
    assert row["summary"] == "", "Zusammenfassung haette NICHT wiederhergestellt werden duerfen"


def test_freigeben_unbekannter_knoten(temp_db):
    res = kms.knowledge_freigeben("existiert-nicht")
    assert "error" in res, res


def test_freigeben_ohne_vorheriges_zurueckziehen_ist_no_op(temp_db):
    node = _make_node(title="Nie-zurueckgezogen")
    res = kms.knowledge_freigeben(node["id"])
    assert res["status"] == "unchanged", res


# ─── access_log: beide Vorgaenge erscheinen darin ──────────────────────────

def test_access_log_traegt_beide_vorgaenge(temp_db):
    node = _make_node(title="Log-Testknoten")
    kms.knowledge_zurueckziehen(node["id"], "Log-Beleg")
    kms.knowledge_freigeben(node["id"])

    conn = sqlite3.connect(str(temp_db))
    actions = {r[0] for r in conn.execute(
        "SELECT DISTINCT action FROM access_log WHERE node_path = ?", (node["path"],)
    )}
    conn.close()
    assert "zurueckziehen" in actions, actions
    assert "freigeben" in actions, actions


# ─── e) Dispatch-Ebene: node_id ODER path (Auftrag 2026-08-07) ─────────────
# Befund: `knowledge_zurueckziehen(path="/probe", grund="...")` ueber den
# MCP-Dispatch (TOOLS[...]["handler"](args)) ergab {"error": "'node_id'"} --
# roher KeyError, kein sprechender Fehler. Diese Tests laufen bewusst durch
# die TOOLS-Handler, nicht durch die Python-Funktion direkt: der Fehler lebte
# in der Dispatch-Schicht (args["node_id"]), eine Pruefung nur auf
# kms.knowledge_zurueckziehen() waere blind dafuer gewesen.

def test_e_rot_dispatch_mit_path_kein_roher_keyerror(temp_db):
    node = _make_node(title="Dispatch-Path-Testknoten")
    args = {"path": node["path"], "grund": "Testbeleg Dispatch mit path"}
    res = kms.TOOLS["knowledge_zurueckziehen"]["handler"](args)
    assert res.get("status") == "zurueckgezogen", res
    assert res["error"] if "error" in res else True  # nur zur Doku: kein KeyError-Text
    assert res != {"error": "'node_id'"}, ("roher KeyError kam durch", res)


def test_e_dispatch_weder_node_id_noch_path(temp_db):
    with pytest.raises(ValueError) as exc:
        kms.TOOLS["knowledge_zurueckziehen"]["handler"]({"grund": "egal"})
    msg = str(exc.value)
    assert "node_id" in msg and "path" in msg, msg
    assert msg != "'node_id'", "roher KeyError statt sprechender Meldung"


def test_e_dispatch_node_id_und_path_widersprechen_sich(temp_db):
    node = _make_node(title="Widerspruch-Testknoten")
    with pytest.raises(ValueError) as exc:
        kms.TOOLS["knowledge_zurueckziehen"]["handler"](
            {"node_id": node["id"], "path": "/anderer/pfad", "grund": "egal"}
        )
    assert "widersprechen" in str(exc.value)


def test_e_dispatch_node_id_und_path_gleich_ist_erlaubt(temp_db):
    node = _make_node(title="Gleicher-Wert-Testknoten")
    args = {"node_id": node["path"], "path": node["path"], "grund": "beide gleich"}
    res = kms.TOOLS["knowledge_zurueckziehen"]["handler"](args)
    assert res.get("status") == "zurueckgezogen", res


def test_e_dispatch_pfad_nicht_gefunden_nennt_pfad(temp_db):
    res = kms.TOOLS["knowledge_zurueckziehen"]["handler"](
        {"path": "/nicht/vorhanden", "grund": "egal"}
    )
    assert "error" in res, res
    assert "/nicht/vorhanden" in res["error"], res


def test_e_freigeben_dispatch_mit_path(temp_db):
    node = _make_node(title="Freigeben-Dispatch-Testknoten")
    kms.knowledge_zurueckziehen(node["id"], "vorher zurueckziehen")
    res = kms.TOOLS["knowledge_freigeben"]["handler"]({"path": node["path"]})
    assert res.get("status") == "freigegeben", res


def test_e_freigeben_dispatch_ohne_angabe(temp_db):
    with pytest.raises(ValueError) as exc:
        kms.TOOLS["knowledge_freigeben"]["handler"]({})
    msg = str(exc.value)
    assert "node_id" in msg and "path" in msg, msg
