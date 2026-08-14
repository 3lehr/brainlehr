"""Ein Widerruf loeschte den Wortlaut -- damit vernichtete das KORRIGIEREN
eines falschen Eintrags den Beweis des falschen Eintrags.

Gefunden im Architektur-Konsil vom 2026-08-13, am Quelltext verifiziert:
knowledge_zurueckziehen setzte `content = ''` und `summary = ''`, ohne
Sicherung. Betreiberentscheidung 2026-08-14 auf die Rueckfrage, ob
Archivieren schlecht sei: „zu 1 ist archevieren schlecht? ich glaube nicht!"

DIE TRENNLINIE, die diese Datei absichert -- sie ist der ganze Punkt:
Archiv, nicht Wiederauferstehung. Der bewahrte Wortlaut ist NUR auf gezielte
Frage nach genau diesem Knoten erreichbar (knowledge_read). In Suche, Abruf
und Blaettern bleibt der Knoten draussen. Ohne diese Trennung waere aus dem
Widerruf ein blosses Verstecken geworden.

Zur Zahl aus der Eilmeldung, die den Defekt meldete: dort stand,
`zurueckgezogen_grund` sei „zu 100 Prozent leer". Nachgezaehlt am 2026-08-14:
5 von 5 zurueckgezogenen Knoten TRAGEN einen Grund. Die 100 Prozent stammen
aus einer Spaltenstatistik ueber ALLE 2184 Knoten -- ein Nennerfehler,
ausgerechnet in einer Meldung ueber falsche Einheiten. Der Defekt selbst
stimmt trotzdem, er braucht nur diesen Beleg nicht.

Rot vor gruen: gegen den Stand davor existiert die Tabelle
knowledge_widerruf_archiv nicht, und knowledge_read liefert kein Feld.
"""
from __future__ import annotations

import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import pytest  # noqa: E402

import knowledge_mcp_server as kms  # noqa: E402

WORTLAUT = "Die Jahresabrechnung ist bis zum 30. Juni vorzulegen."
FALSCH = "Widerrufstest Knoten mit falscher Aussage"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    pfad = tmp_path / "widerruf.db"
    conn = sqlite3.connect(str(pfad))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", pfad)
    ergebnis = kms.knowledge_add(
        parent_path="/", title=FALSCH, summary="Kurzfassung der falschen Aussage",
        content=WORTLAUT, source="Testvorrichtung", neuer_ast=True,
        norm_entscheidung="keine_norm", norm_entschieden_grund="Testvorrichtung")
    return pfad, ergebnis["id"]


def test_wortlaut_ueberlebt_den_widerruf(db):
    """Der Kern: nach dem Zurueckziehen ist der urspruengliche Wortlaut noch
    da. Vorher war er weg."""
    _, node_id = db
    kms.knowledge_zurueckziehen(node_id=node_id, grund="war sachlich falsch")

    gelesen = kms.knowledge_read(node_id)
    assert isinstance(gelesen["widerruf_archiv"], dict)
    assert gelesen["widerruf_archiv"]["content"] == WORTLAUT
    assert gelesen["widerruf_archiv"]["grund"] == "war sachlich falsch"


def test_knoten_selbst_bleibt_geleert(db):
    """Gegenprobe zur Richtung: das Archiv darf den Widerruf nicht aufheben.
    Ohne diesen Test bestuende der obige auch bei einer Fassung, die schlicht
    nichts mehr leert -- und dann waere der Widerruf wirkungslos."""
    _, node_id = db
    kms.knowledge_zurueckziehen(node_id=node_id, grund="war sachlich falsch")

    gelesen = kms.knowledge_read(node_id)
    assert gelesen["content"] == "(kein Volltext)"
    assert not gelesen["summary"]


def test_widerrufener_knoten_bleibt_aus_der_suche_draussen(db):
    """Die Trennlinie: Archiv, nicht Wiederauferstehung. Ein bewahrter
    Wortlaut, der wieder in der Suche auftaucht, hebt den Widerruf faktisch
    auf."""
    _, node_id = db
    vorher = kms.knowledge_search("Widerrufstest")
    assert any(r["id"] == node_id for r in vorher["results"]), "Vorbedingung: vorher findbar"

    kms.knowledge_zurueckziehen(node_id=node_id, grund="war sachlich falsch")

    nachher = kms.knowledge_search("Widerrufstest")
    assert not any(r["id"] == node_id for r in nachher["results"])
    assert WORTLAUT not in str(nachher)


def test_zweiter_widerruf_ueberschreibt_den_ersten_nicht(db):
    """Ein Knoten kann zurueckgezogen, freigegeben und erneut zurueckgezogen
    werden -- es braucht also mehrere Zeilen je Knoten.

    ROT BEIM BAUEN, und der Fehler war meiner: der erste Entwurf nahm
    (node_id, zurueckgezogen_am) als Schluessel. now_iso() hat
    Sekundengranularitaet; zwei Widerrufe in derselben Sekunde teilen den
    Schluessel, und INSERT OR REPLACE loeschte die erste -- also die
    interessante -- Fassung. Ein Zeitstempel ist eine Angabe, kein
    Schluessel."""
    pfad, node_id = db
    kms.knowledge_zurueckziehen(node_id=node_id, grund="erster Widerruf")
    kms.knowledge_freigeben(node_id=node_id)
    kms.knowledge_update(node_id=node_id, content="zweite, ebenfalls falsche Fassung")
    kms.knowledge_zurueckziehen(node_id=node_id, grund="zweiter Widerruf")

    conn = sqlite3.connect(str(pfad))
    zeilen = conn.execute(
        "SELECT content, grund FROM knowledge_widerruf_archiv WHERE node_id = ? "
        "ORDER BY id", (node_id,)).fetchall()
    conn.close()
    gruende = [z[1] for z in zeilen]
    assert "erster Widerruf" in gruende and "zweiter Widerruf" in gruende, (
        f"beide Fassungen muessen im Archiv stehen, gefunden: {gruende}")


def test_altbestand_wird_ehrlich_benannt(db):
    """Vor dem 2026-08-14 zurueckgezogene Knoten haben keinen bewahrten
    Wortlaut, und er ist nicht rekonstruierbar. Ein FEHLENDES Feld saehe aus
    wie 'gab es nie' statt wie 'damals wurde geloescht'."""
    pfad, node_id = db
    conn = sqlite3.connect(str(pfad))
    conn.execute("UPDATE knowledge_nodes SET zurueckgezogen = 1, content = '', summary = '' WHERE id = ?",
                 (node_id,))
    conn.commit()
    conn.close()

    gelesen = kms.knowledge_read(node_id)
    assert isinstance(gelesen["widerruf_archiv"], str)
    assert "vor dem 2026-08-14" in gelesen["widerruf_archiv"]


def test_nicht_zurueckgezogener_knoten_traegt_kein_archivfeld(db):
    """Sonst haette jede Antwort ein Feld, das fast immer nichts sagt."""
    _, node_id = db
    assert "widerruf_archiv" not in kms.knowledge_read(node_id)
