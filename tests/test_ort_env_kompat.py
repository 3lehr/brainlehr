"""BRAINLEHR_DB (neu) vs. BEGOD_KNOWLEDGE_DB (alt) -- haken/ort.py."""
from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture(autouse=True)
def _sauberer_zustand_danach(monkeypatch):
    """haken.ort landet ueber sys.modules global -- andere Tests importieren
    es spaeter unveraendert weiter. Nach jedem Testfall sauber neu laden,
    ohne die hier gesetzten Umgebungsvariablen, sonst erbt der naechste
    Import (z. B. in build_node_index) den hier praeparierten DB-Pfad.
    """
    yield
    monkeypatch.delenv("BEGOD_KNOWLEDGE_DB", raising=False)
    monkeypatch.delenv("BRAINLEHR_DB", raising=False)
    sys.modules.pop("haken.ort", None)
    importlib.import_module("haken.ort")


def _lade(monkeypatch, alt=None, neu=None):
    if alt is None:
        monkeypatch.delenv("BEGOD_KNOWLEDGE_DB", raising=False)
    else:
        monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", alt)
    if neu is None:
        monkeypatch.delenv("BRAINLEHR_DB", raising=False)
    else:
        monkeypatch.setenv("BRAINLEHR_DB", neu)
    sys.modules.pop("haken.ort", None)
    return importlib.import_module("haken.ort")


def test_nur_alter_name(monkeypatch, capsys):
    mod = _lade(monkeypatch, alt="/tmp/alt.db")
    assert str(mod.DB) == "/tmp/alt.db"
    assert "veraltet" in capsys.readouterr().err


def test_nur_neuer_name(monkeypatch, capsys):
    mod = _lade(monkeypatch, neu="/tmp/neu.db")
    assert str(mod.DB) == "/tmp/neu.db"
    assert capsys.readouterr().err == ""


def test_beide_gesetzt_neuer_gewinnt(monkeypatch, capsys):
    mod = _lade(monkeypatch, alt="/tmp/alt.db", neu="/tmp/neu.db")
    assert str(mod.DB) == "/tmp/neu.db"
    assert capsys.readouterr().err == ""


def test_keiner_gesetzt_kein_brainlehr_db_am_ort(tmp_path, monkeypatch, capsys):
    mod = _lade(monkeypatch)
    capsys.readouterr()  # Hinweis aus dem Modul-Reload gegen die echte WURZEL verwerfen
    pfad = mod._ermittle_db(tmp_path, None, None)
    assert pfad == tmp_path / "knowledge.db"
    assert "knowledge.db ist der alte Dateiname" in capsys.readouterr().err


def test_keiner_gesetzt_brainlehr_db_existiert_am_ort(tmp_path, monkeypatch, capsys):
    (tmp_path / "brainlehr.db").touch()
    mod = _lade(monkeypatch)
    capsys.readouterr()  # Hinweis aus dem Modul-Reload gegen die echte WURZEL verwerfen
    pfad = mod._ermittle_db(tmp_path, None, None)
    assert pfad == tmp_path / "brainlehr.db"
    assert capsys.readouterr().err == ""


def test_hinweis_nur_einmal_pro_prozess(monkeypatch, capsys):
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", "/tmp/alt.db")
    monkeypatch.delenv("BRAINLEHR_DB", raising=False)
    sys.modules.pop("haken.ort", None)
    importlib.import_module("haken.ort")
    assert "veraltet" in capsys.readouterr().err

    # zweiter Zugriff im selben Prozess ohne erneutes Modul-Neuladen:
    # Python cached das Modul, der Hinweis darf nicht nochmal erscheinen.
    importlib.import_module("haken.ort")
    assert capsys.readouterr().err == ""
