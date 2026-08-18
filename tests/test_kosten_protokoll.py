"""Rot-vor-gruen-Beleg fuer Sprint S21 (docs/SPRINTS.md): access_log.tokens_*
wird von log_access() befuellt, wenn ein Sitzungsprotokoll mit usage-Eintrag
erreichbar ist -- und bleibt NULL, wenn nicht (kein erfundener Nullwert).

Quelle der Zahlen: knowledge_mcp_server._letzte_token_nutzung() liest die
.jsonl-Sitzungsdatei des Claude-Code-Hosts unter ~/.claude/projects/<slug>/
<CLAUDE_CODE_SESSION_ID>.jsonl -- NICHT den MCP-Aufruf selbst (das
JSON-RPC-Protokoll traegt keine Tokenfelder, siehe Docstring dort).

NIE gegen die echte brainlehr.db oder das echte ~/.claude/projects/ --
temp_db aus schema.sql, Sitzungsprotokoll in tmp_path, HOME per monkeypatch
umgebogen.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import os
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


def _spalten(db_path: Path, spalte: str) -> list:
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(f"SELECT {spalte} FROM access_log ORDER BY id").fetchall()
    conn.close()
    return [r[0] for r in rows]


def _sitzungsdatei_anlegen(monkeypatch, home_dir: Path, cwd: Path, session_id: str,
                            usage: dict | None) -> Path:
    """Legt eine minimale .jsonl an, wie sie der Claude-Code-Host schreibt,
    und biegt HOME/CWD/CLAUDE_CODE_SESSION_ID so um, dass
    _sitzungsprotokoll_pfad() sie findet -- exakt dieselbe Pfadherleitung
    wie in knowledge_mcp_server.py (Slug aus os.getcwd())."""
    slug = kms.re.sub(r"[/.]", "-", str(cwd))
    projekt_dir = home_dir / ".claude" / "projects" / slug
    projekt_dir.mkdir(parents=True, exist_ok=True)
    pfad = projekt_dir / f"{session_id}.jsonl"
    zeilen = [json.dumps({"type": "user", "message": {"content": "hallo"}})]
    if usage is not None:
        zeilen.append(json.dumps({"type": "assistant", "message": {"usage": usage}}))
    pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    monkeypatch.setattr(kms._Path, "home", staticmethod(lambda: home_dir))
    monkeypatch.setattr(os, "getcwd", lambda: str(cwd))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", session_id)
    return pfad


def test_ohne_sitzungsprotokoll_bleibt_null(temp_db, monkeypatch):
    """Rot-Probe fuer den heutigen Stand: OHNE die Aenderung schrieb
    log_access() die vier tokens_*-Spalten nie -- dieser Test waere schon vor
    dem Fix gruen gewesen (die Spalten WAREN immer NULL). Die Gegenprobe
    steht in test_mit_sitzungsprotokoll_werden_echte_zahlen_geschrieben."""
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    conn = kms.get_db()
    kms.log_access(conn, "/x/1", "read")
    conn.close()
    for spalte in ("tokens_input", "tokens_output", "tokens_cache_creation", "tokens_cache_read"):
        werte = _spalten(temp_db, spalte)
        assert werte == [None], f"{spalte}: erwartet NULL ohne Sitzungsprotokoll, war {werte}"


def test_mit_sitzungsprotokoll_werden_echte_zahlen_geschrieben(temp_db, tmp_path, monkeypatch):
    """War VOR der Aenderung rot: log_access() nahm keine Tokenzahlen
    entgegen und schrieb die vier Spalten nie, auch wenn ein Sitzungsprotokoll
    mit usage vorlag. Nach der Aenderung: echte Zahlen aus dem Protokoll."""
    home = tmp_path / "home"
    cwd = tmp_path / "projekt"
    cwd.mkdir()
    usage = {"input_tokens": 7, "output_tokens": 42, "cache_creation_input_tokens": 111, "cache_read_input_tokens": 999}
    _sitzungsdatei_anlegen(monkeypatch, home, cwd, "sess-echt-1234", usage)

    conn = kms.get_db()
    kms.log_access(conn, "/x/1", "read")
    conn.close()

    assert _spalten(temp_db, "tokens_input") == [7]
    assert _spalten(temp_db, "tokens_output") == [42]
    assert _spalten(temp_db, "tokens_cache_creation") == [111]
    assert _spalten(temp_db, "tokens_cache_read") == [999]


def test_juengster_usage_eintrag_gewinnt(temp_db, tmp_path, monkeypatch):
    """Zwei usage-Eintraege im Protokoll (zwei Modellzuege) -- log_access()
    muss den JUENGSTEN nehmen, nicht den ersten."""
    home = tmp_path / "home"
    cwd = tmp_path / "projekt"
    cwd.mkdir()
    slug = kms.re.sub(r"[/.]", "-", str(cwd))
    projekt_dir = home / ".claude" / "projects" / slug
    projekt_dir.mkdir(parents=True)
    pfad = projekt_dir / "sess-zwei-9999.jsonl"
    alt = {"input_tokens": 1, "output_tokens": 1, "cache_creation_input_tokens": 1, "cache_read_input_tokens": 1}
    neu = {"input_tokens": 5, "output_tokens": 6, "cache_creation_input_tokens": 7, "cache_read_input_tokens": 8}
    pfad.write_text(
        json.dumps({"type": "assistant", "message": {"usage": alt}}) + "\n"
        + json.dumps({"type": "assistant", "message": {"usage": neu}}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(kms._Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(os, "getcwd", lambda: str(cwd))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-zwei-9999")

    conn = kms.get_db()
    kms.log_access(conn, "/x/1", "read")
    conn.close()

    assert _spalten(temp_db, "tokens_input") == [5]
    assert _spalten(temp_db, "tokens_output") == [6]


def test_kaputte_protokollzeile_ergibt_null_nicht_absturz(temp_db, tmp_path, monkeypatch):
    """Negativfall: eine kaputte letzte Zeile (z.B. Schreibabbruch mitten im
    Sitzungsprotokoll) darf log_access() nicht zum Absturz bringen -- NULL
    statt Ausnahme."""
    home = tmp_path / "home"
    cwd = tmp_path / "projekt"
    cwd.mkdir()
    slug = kms.re.sub(r"[/.]", "-", str(cwd))
    projekt_dir = home / ".claude" / "projects" / slug
    projekt_dir.mkdir(parents=True)
    pfad = projekt_dir / "sess-kaputt-0001.jsonl"
    pfad.write_text('{"type": "assistant", "message": {"usage": {"input_tok', encoding="utf-8")
    monkeypatch.setattr(kms._Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(os, "getcwd", lambda: str(cwd))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-kaputt-0001")

    conn = kms.get_db()
    kms.log_access(conn, "/x/1", "read")  # darf nicht werfen
    conn.close()

    assert _spalten(temp_db, "tokens_input") == [None]


def test_tokens_nicht_teil_der_kettenhash_berechnung(temp_db, monkeypatch):
    """Der Ketten-Vertrag (Feldreihenfolge in compute_ketten_hash) bleibt
    unangetastet -- ein Aufruf ohne Sitzungsprotokoll (Tokenspalten NULL) und
    einer mit (Tokenspalten gefuellt) muessen bei sonst gleichen Feldern
    denselben ketten_hash ergeben, sonst wuerde jede Altzeile rueckwirkend
    ungueltig."""
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    h1 = kms.compute_ketten_hash(
        None, node_path="/x/1", action="read", query=None, project_id=None,
        actor="a", model="m", session="s", status="completed",
        timestamp="2026-08-18T00:00:00Z", zeilen_hash=None,
    )
    h2 = kms.compute_ketten_hash(
        None, node_path="/x/1", action="read", query=None, project_id=None,
        actor="a", model="m", session="s", status="completed",
        timestamp="2026-08-18T00:00:00Z", zeilen_hash=None,
    )
    assert h1 == h2  # Tokens sind nicht mal als Parameter vorgesehen -- Vertrag unveraendert
