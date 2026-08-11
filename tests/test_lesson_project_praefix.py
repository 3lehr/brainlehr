"""Lehren-Projektfilter darf keine LIKE-Wildcards aus dem Suchbegriff lesen.

ABWEICHUNG VOM AUFTRAG (gemessen 2026-08-11, gemeldet statt still korrigiert):
Der Auftrag ging von reiner Praefix-Kollision aus ('wohlair' matcht
'wohlairr' via `projects LIKE '%wohlair%'`). Die tatsaechlichen Filterstellen
(knowledge_mcp_server.lesson_query/knowledge_search, kern/lesson_recorder.py
cmd_query) quotierten den Suchbegriff bereits: `LIKE '%"wohlair"%'`. Gegen
alle 761 Lehren im Bestand geprueft: 0 Falschtreffer fuer alle fuenf im
Auftrag genannten Paare (wohlair/wohlairr, aka/aka2026, aka/aka-homepage,
fahrtenbuch/fahrtenbuch_legacy, shared/shared-knowledge) -- die
Anfuehrungszeichen im Muster verhindern reine Teilstring-Kollisionen.

ROT VOR GRUEN, echter Fund: LIKE behandelt '_' und '%' im SUCHBEGRIFF als
Wildcards, nicht als Literal. 'fahrtenbuch_legacy' ist selbst ein
Projektname mit '_' (eines der App-Verzeichnisse). Eine Suche danach matcht
per altem Filter auch 'fahrtenbuchXlegacy' (ein beliebiges Zeichen statt
'_') -- verifiziert unten, vor dem Fix rot.

Fix: kern/geltungsbereich.py::sql_projects_exact() (json_each, Wertevergleich
statt Muster) statt LIKE. Aufrufer: knowledge_mcp_server.lesson_query,
knowledge_mcp_server.knowledge_search (scope-Filter, eigener Test:
test_systemweit_sichtbar.py), kern/lesson_recorder.py cmd_query.
"""
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

import pytest

sys.path.insert(0, str(_w))
import knowledge_mcp_server as kms  # noqa: E402


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript((_w / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _lehre(desc: str, projects: list[str]) -> str:
    return kms.lesson_record(
        type_="insight", description=desc, projects=projects,
        actor="test", model="test", session="test",
    )["id"]


def test_unterstrich_im_projektnamen_ist_kein_wildcard(db):
    """Der reale Fund: '_' im Suchbegriff darf kein LIKE-Wildcard sein."""
    wild = _lehre("Wildcard-Kollision", ["fahrtenbuchXlegacy"])
    exakt = _lehre("exaktes Projekt", ["fahrtenbuch_legacy"])

    treffer = kms.lesson_query(project="fahrtenbuch_legacy", max_results=50)
    ids = {r["id"] for r in treffer["results"]}

    assert exakt in ids
    assert wild not in ids, (
        "'fahrtenbuchXlegacy' im Treffer fuer 'fahrtenbuch_legacy' -- "
        "'_' wurde als LIKE-Wildcard gelesen statt als Literal."
    )


def test_gegenprobe_eigener_treffer_bleibt(db):
    lang = _lehre("eigenes Projekt", ["wohlairr"])
    ids = {r["id"] for r in kms.lesson_query(project="wohlairr", max_results=50)["results"]}
    assert lang in ids


def test_leere_projektliste(db):
    lid = _lehre("kein Projekt", [])
    ids = {r["id"] for r in kms.lesson_query(project="wohlair", max_results=50)["results"]}
    assert lid not in ids  # leer heisst NICHT "matcht alles" fuer diesen Filter


def test_einzelnes_projekt(db):
    lid = _lehre("ein Projekt", ["begod"])
    ids = {r["id"] for r in kms.lesson_query(project="begod", max_results=50)["results"]}
    assert lid in ids


def test_mehrere_projekte_gesuchtes_an_letzter_stelle(db):
    lid = _lehre("mehrere Projekte", ["aka", "aka2026", "wohlair"])
    ids = {r["id"] for r in kms.lesson_query(project="wohlair", max_results=50)["results"]}
    assert lid in ids


def test_praefix_in_beide_richtungen(db):
    kurz = _lehre("aka", ["aka"])
    lang = _lehre("aka-homepage", ["aka-homepage"])

    ids_kurz = {r["id"] for r in kms.lesson_query(project="aka", max_results=50)["results"]}
    ids_lang = {r["id"] for r in kms.lesson_query(project="aka-homepage", max_results=50)["results"]}

    assert kurz in ids_kurz and lang not in ids_kurz
    assert lang in ids_lang and kurz not in ids_lang
