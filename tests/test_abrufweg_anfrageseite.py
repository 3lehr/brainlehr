"""Auftrag 2026-08-13 (Schritt 4, Aufgabe 41 Nachtrag): /api/abrufweg zeigte
bislang nur das ERGEBNIS eines Abrufs, nie die ANFRAGESEITE -- welche Worte
tatsaechlich an den Stichwortkanal gingen (_or_query(), FTS5-ODER-Verknuepfung,
UNGEFILTERT) und welcher Text an den Bedeutungskanal (embed_text()) ging.
Die bisherigen 'schluesselwoerter' (knowledge_recall_hook.keywords()) sind
gefiltert (Stoppwoerter raus, Laenge>=4, max. 8) und dienen nur der
MIN_HITS-Anzeige -- sie sind NICHT, was der Stichwortkanal durchsucht. Ohne
die echten Suchworte sieht man die Kandidaten einer Suche, deren Frage
unsichtbar bleibt.

Rot-Probe: vor diesem Auftrag hatte anfrage_stand()['anfrage'] keine Schluessel
'stichwort_suchworte' und 'eingebetteter_text' -- dieser Test war rot, bevor
berichte/entscheidungen_server.py::abrufweg_berechnen() sie ergaenzte.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "berichte"))
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "haken"))
sys.path.insert(0, str(REPO / "kern"))

import entscheidungen_server as es  # noqa: E402


def _stand(text: str) -> dict:
    conn = sqlite3.connect(f"file:{es.DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return es.abrufweg_berechnen(conn, text)
    finally:
        conn.close()


pytestmark = pytest.mark.skipif(not es.DB_PATH.exists(), reason="brainlehr.db fehlt auf diesem Rechner")


def test_anfrage_traegt_die_tatsaechlichen_stichwort_suchworte():
    d = _stand("Dichtung Leckage Treibstofftank Fehleranalyse Startverzoegerung")
    a = d["anfrage"]
    assert a["stichwort_suchworte"] == [
        "dichtung", "leckage", "treibstofftank", "fehleranalyse", "startverzoegerung",
    ]


def test_stichwort_suchworte_koennen_von_den_gefilterten_schluesselwoertern_abweichen():
    # "und"/"der"/"im" sind zu kurz bzw. Stoppwort -- fallen aus schluesselwoerter()
    # heraus, gehen aber trotzdem UNGEFILTERT an den Stichwortkanal (_or_query()
    # kennt keinen Stoppwortfilter). Genau dieser Unterschied war vorher unsichtbar.
    d = _stand("und der Motor im Fahrzeug")
    a = d["anfrage"]
    assert "und" not in a["schluesselwoerter"]
    assert "und" in a["stichwort_suchworte"], (
        "der Stichwortkanal filtert keine Stoppwoerter -- die Anzeige muss das zeigen"
    )


def test_eingebetteter_text_ist_der_volle_anfragetext_ungekuerzt():
    lang = "Wort " * 500  # absichtlich lang -- die Anzeige darf nicht kuerzen
    d = _stand(lang.strip())
    assert d["anfrage"]["eingebetteter_text"] == lang.strip()


def test_leere_anfrage_bleibt_ohne_anfrageseite():
    assert _stand("   ") == {"leer": True}


def test_anfrage_ohne_indexierbares_wort_traegt_trotzdem_leere_anfrageseite():
    # Text besteht nur aus Zeichen, die _QUERY_WORD_RE/_or_query nicht als Wort
    # zaehlen -- fts_query wird leer, die Anfrageseite bleibt aber sichtbar
    # (leere Liste statt fehlendem Schluessel).
    d = _stand("!!! ??? ...")
    assert d["leer"] is True
    assert d["anfrage"]["stichwort_suchworte"] == []
