"""Herkunftsfelder in zero_hit_log.jsonl (Auftrag 2026-08-06, Nachzug zu
Commit 4bcde3574). recall_log.jsonl bekam cwd/worktree/session bereits durch
knowledge_recall_hook.py::log_recall; zero_hit_log.jsonl wird von einem
ANDEREN Aufrufpfad geschrieben (knowledge_mcp_server.py::_log_zero_hit, via
knowledge_search) und war dabei ausdruecklich ausgelassen worden. Hier
nachgezogen, gleiche Feldnamen/Bedeutung, gleiche Ableitung (_cwd_project)."""
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


@pytest.fixture()
def zero_hit_log(tmp_path, monkeypatch):
    log_path = tmp_path / "zero_hit_log.jsonl"
    monkeypatch.setattr(kms, "ZERO_HIT_LOG", log_path)
    return log_path


def _letzte_zeile(log_path: Path) -> dict:
    lines = log_path.read_text(encoding="utf-8").splitlines()
    return json.loads(lines[-1])


# ─── a) ROT VOR GRUEN: Suche ohne Treffer, vorher ohne Herkunft, nachher mit ─

def test_a_suche_ohne_treffer_vorher_ohne_herkunft_nachher_mit(temp_db, zero_hit_log):
    # VORHER (alte Formel, wie sie bis zu diesem Auftrag im Code stand):
    # nur ts/query/hits, keine Herkunft moeglich.
    vorher = json.dumps({"ts": kms.now_iso(), "query": "nichts-x", "hits": 0}, ensure_ascii=False)
    vorher_entry = json.loads(vorher)
    print(f"VORHER (alte Formel): {vorher}")
    assert "cwd" not in vorher_entry and "worktree" not in vorher_entry and "session" not in vorher_entry

    # NACHHER: echte Suche ohne Treffer ueber den Produktionspfad ausloesen.
    ergebnis = kms.knowledge_search(
        "nichts-findet-das-hier-garantiert-xyz", cwd="/Volumes/daten/Begod2026/fahrtenbuch/apps/fahrtenbuch_legacy",
        session="abcdef12-lang-rest",
    )
    assert ergebnis["count"] == 0, ergebnis

    nachher_entry = _letzte_zeile(zero_hit_log)
    print(f"NACHHER (kms.knowledge_search, Produktionspfad): {json.dumps(nachher_entry, ensure_ascii=False)}")

    assert nachher_entry["cwd"] == "/Volumes/daten/Begod2026/fahrtenbuch/apps/fahrtenbuch_legacy"
    assert nachher_entry["worktree"] == "fahrtenbuch"
    assert nachher_entry["session"] == "abcdef12"
    assert nachher_entry["hits"] == 0


# ─── b) Negativfall: kein ermittelbares Arbeitsverzeichnis -> null, kein Absturz ─

def test_b_ohne_cwd_und_session_werden_felder_null_kein_absturz(temp_db, zero_hit_log):
    ergebnis = kms.knowledge_search("nichts-findet-das-hier-garantiert-xyz-zwei")
    assert ergebnis["count"] == 0, ergebnis

    entry = _letzte_zeile(zero_hit_log)
    print(f"Negativfall (kein cwd/session uebergeben): {json.dumps(entry, ensure_ascii=False)}")
    assert entry["cwd"] is None
    assert entry["worktree"] is None
    assert entry["session"] is None


# ─── c) Altbestand: Zeile ohne die neuen Felder bleibt ueber .get() lesbar ──

def test_c_altzeile_ohne_herkunft_bleibt_lesbar(zero_hit_log):
    alte_zeile = {"ts": "2026-08-01T00:00:00+02:00", "query": "alt", "hits": 0}
    zero_hit_log.write_text(json.dumps(alte_zeile, ensure_ascii=False) + "\n", encoding="utf-8")

    gelesen = [json.loads(l) for l in zero_hit_log.read_text(encoding="utf-8").splitlines()]
    assert len(gelesen) == 1
    # Kein Auswerter fuer zero_hit_log.jsonl im Repo vorhanden (grep negativ,
    # 2026-08-06) -- die Lesbarkeitsprobe ist daher ueber .get() selbst
    # gefuehrt, wie es ein kuenftiger Auswerter tun muesste.
    assert gelesen[0].get("cwd") is None
    assert gelesen[0].get("worktree") is None
    assert gelesen[0].get("session") is None
    assert gelesen[0]["query"] == "alt"


# ─── d) _cwd_project: gleiche Ableitung wie knowledge_recall_hook.py ────────

def test_d_cwd_project_gleiche_ableitung_wie_hook():
    assert kms._cwd_project("/Volumes/daten/Begod2026/fahrtenbuch/apps/fahrtenbuch_legacy") == "fahrtenbuch"
    assert kms._cwd_project("/Volumes/daten/Begod2026/hub") == "hub"
    assert kms._cwd_project(None) is None
    assert kms._cwd_project("/tmp/irgendwas") == "irgendwas"  # keine Git-Wurzel -> Ordnername als bester Schaetzwert
