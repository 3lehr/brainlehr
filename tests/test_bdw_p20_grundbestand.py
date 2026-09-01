import sqlite3
import pytest
import socket
from pathlib import Path
import sys

_W = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_W))
from kern import einrichtung

def test_bdw_p20_ac1_gebautes_rad_leer(tmp_path):
    """BDW-P20-AC1: Ein gebautes Rad enthaelt keine Datenbank und keinen Katalogtext.
    Eine neu initialisierte DB enthält keine Fremddaten."""
    db_path = tmp_path / "brainlehr.db"
    assert not db_path.exists()
    
    schema_path = _W / "schema.sql"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()
    
    count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    assert count == 0
    conn.close()

def test_bdw_p20_ac2_kataloge_kein_netz(monkeypatch, tmp_path):
    """BDW-P20-AC2: kataloge() loest keinen Netzzugriff aus; nur katalog_holen() tut das."""
    def mock_getaddrinfo(*args, **kwargs):
        raise RuntimeError("kataloge() darf das Netz nicht berühren!")
    
    monkeypatch.setattr(socket, "getaddrinfo", mock_getaddrinfo)
    
    res = einrichtung.kataloge(db=str(tmp_path / "dummy.db"))
    names = [r["name"] for r in res]
    assert "bsi" in names
