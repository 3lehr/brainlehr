"""B4.3: tools/call prueft Rechte -- nicht nur tools/list kuendigt an.

ROT VOR GRUEN: Gegen den Stand vor dieser Aenderung bediente tools/call jedes
Werkzeug, egal wer fragte. Der Quelltext sagte es ueber sich selbst: die
Profilbeschraenkung "beschraenkt nur die ANKUENDIGUNG (tools/list), nicht den
Aufruf: tools/call bedient jedes Werkzeug in TOOLS weiter, egal ob es hier
gelistet wurde. Kein Autorisierungsmechanismus."

Geprueft wird am ECHTEN JSON-RPC-Pfad (handle_request), nicht an der
Hilfsfunktion -- sonst prueft der Test die Rechtelogik und nicht ihre
Verdrahtung. Das ist der Unterschied, an dem Werkzeuge ohne Wirkung entstehen
(Knoten 92e31dfe).
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

import json
import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import ausweis  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture()
def umgebung(tmp_path, monkeypatch):
    db = tmp_path / "k.db"
    conn = sqlite3.connect(str(db))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(tmp_path / "a.json"))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    monkeypatch.delenv("BRAINLEHR_DURCHSETZUNG", raising=False)
    ausweis._pruefe.cache_clear()
    return tmp_path


def _call(werkzeug: str, args: dict | None = None) -> dict:
    antwort = kms.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": werkzeug, "arguments": args or {}},
    })
    return antwort["result"]


def _abgewiesen(res: dict) -> str | None:
    """Gibt den Grund zurueck, wenn abgewiesen wurde -- sonst None."""
    if not res.get("isError"):
        return None
    try:
        return json.loads(res["content"][0]["text"]).get("grund")
    except (KeyError, IndexError, json.JSONDecodeError):
        return None


def test_leser_darf_nicht_schreiben(umgebung, monkeypatch):
    """P3, der Kern: ein beglaubigter Leser wird am AUFRUF abgewiesen."""
    g = ausweis.anlegen("nur-lesen", ["leser"],
                        pfad=umgebung / "a.json")
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()

    grund = _abgewiesen(_call("knowledge_add", {
        "parent_path": "/", "title": "X", "summary": "Y", "source": "test",
        "norm_entscheidung": "keine_norm", "norm_entschieden_grund": "test",
        "neuer_ast": True}))

    assert grund is not None, "Leser durfte schreiben — tools/call prueft nicht"
    assert grund.startswith("rolle_ohne_recht"), grund


def test_leser_darf_lesen(umgebung, monkeypatch):
    """Gegenprobe: die Schranke darf nicht alles abweisen."""
    g = ausweis.anlegen("nur-lesen", ["leser"], pfad=umgebung / "a.json")
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()
    assert _abgewiesen(_call("knowledge_search", {"query": "test"})) is None


def test_ohne_ausweis_laeuft_alles_weiter(umgebung):
    """Vorgabe 'weich': kein Bruch fuer Skripte und Zugaenge ohne Ausweis.
    Das ist kein Schutz und soll auch keiner sein -- es ist die Zusage, dass
    diese Aenderung nichts anhaelt."""
    assert _abgewiesen(_call("knowledge_search", {"query": "test"})) is None
    assert _abgewiesen(_call("knowledge_add", {
        "parent_path": "/", "title": "X", "summary": "Y", "source": "test",
        "norm_entscheidung": "keine_norm", "norm_entschieden_grund": "test",
        "neuer_ast": True})) is None


def test_streng_sperrt_schreiben_ohne_ausweis(umgebung, monkeypatch):
    monkeypatch.setenv("BRAINLEHR_DURCHSETZUNG", "streng")
    assert _abgewiesen(_call("knowledge_search", {"query": "t"})) is None
    grund = _abgewiesen(_call("lesson_record", {
        "type": "insight", "description": "x"}))
    assert grund is not None and grund.startswith("kein_ausweis_streng"), grund


def test_unbekanntes_werkzeug_ist_gesperrt_nicht_frei(umgebung):
    """Vorgabe deny: ein Werkzeug ohne Rechtezuordnung darf niemand aufrufen.
    Hier ueber ein in TOOLS eingehaengtes Werkzeug geprueft, damit die
    Antwort nicht schon vorher am 'Unknown tool' haengenbleibt."""
    kms.TOOLS["werkzeug_ohne_recht_test"] = {
        "description": "nur fuer den Test", "inputSchema": {"type": "object"},
        "handler": lambda a: {"status": "haette nicht laufen duerfen"}}
    try:
        grund = _abgewiesen(_call("werkzeug_ohne_recht_test"))
        assert grund is not None and grund.startswith("werkzeug_ohne_recht"), grund
    finally:
        del kms.TOOLS["werkzeug_ohne_recht_test"]


def test_abweisung_steht_im_protokoll(umgebung, monkeypatch):
    """Eine stille Abweisung ist von einem Absturz nicht zu unterscheiden --
    sichtbarkeit.py liest access_log, also muss sie dort stehen."""
    g = ausweis.anlegen("nur-lesen", ["leser"], pfad=umgebung / "a.json")
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)
    ausweis._pruefe.cache_clear()
    _call("kurator_lauf", {})

    conn = sqlite3.connect(str(kms.DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT action, query, status FROM access_log WHERE status='rejected'"
    ).fetchall()
    conn.close()
    assert rows, "Abweisung wurde nicht protokolliert"
    assert rows[-1]["action"] == "kurator_lauf"
    assert "rolle_ohne_recht" in rows[-1]["query"]


def test_jedes_werkzeug_hat_eine_zuordnung():
    """Ohne diese Probe faellt ein neu hinzugefuegtes Werkzeug erst auf, wenn
    es jemand aufruft und wegen der Deny-Vorgabe abgewiesen wird."""
    import werkzeugrechte
    fehlt = werkzeugrechte.fehlende_zuordnung(kms.TOOLS)
    assert not fehlt, f"Werkzeuge ohne Rechtezuordnung: {fehlt}"


def test_prompt_profil_ist_auch_am_aufruf_default_deny(umgebung, monkeypatch):
    monkeypatch.setenv("BEGOD_KNOWLEDGE_PROFIL", "prompt-invariance")
    listed = kms.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert [tool["name"] for tool in listed["result"]["tools"]] == list(kms.PROMPT_INVARIANZ_TOOLS)
    assert _abgewiesen(_call("knowledge_search", {"query": "privat"})) == "profil:prompt-invariance"
    result = _call("prompt_invarianz_planen", {"task_type": "rangfolge", "security": True})
    assert _abgewiesen(result) is None
    assert json.loads(result["content"][0]["text"])["profile"] == "strong"
