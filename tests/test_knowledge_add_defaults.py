"""Zwei bequeme Vorgabewerte in knowledge_add() erzeugten messbar falsche
Daten (Auftrag 2026-08-09, gemessen ueber 384 Knoten des Arbeitsbestands):

  1  project_id defaultete immer auf 'shared', auch wenn parent_path den
     Knoten eindeutig einem Projekt zuordnete (26 von 336 'shared'-Knoten
     betroffen, Beispiel /apps/fahrtenbuch/...).
  2  norm_entschieden_von wurde immer aus actor gesetzt -- bei importierten
     Direktiven (source nennt eine CLAUDE.md des Betreibers) ist das falsch,
     der Urheber ist der Betreiber, nicht die Maschine, die ihn abgeschrieben
     hat (31 von 37 hoechstrangigen Normen betroffen).

Rot-Probe: beide Faelle vor der Aenderung gegen den Stand ohne Ableitung
gefahren (siehe Auftragsbericht) -- project_id blieb 'shared' unter
/apps/fahrtenbuch, norm_entschieden_von trug 'skript:test' statt 'betreiber'.
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
    # Bekannte Projekte im Bestand -- die Ableitung liest sie hieraus
    # (SELECT DISTINCT project_id), keine hartcodierte Liste im Code.
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, level, source, "
        "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        [
            ("r1", "/apps", None, "shared", "Apps", "Wurzel je App", 0),
            ("r2", "/apps/fahrtenbuch", "/apps", "fahrtenbuch", "Fahrtenbuch", "Die Fahrtenbuch-App", 1),
            ("r3", "/methodik", None, "shared", "Methodik", "Projektuebergreifende Methodik", 0),
        ],
    )
    conn.commit()
    conn.close()
    # Cache aus vorherigen Tests darf nicht ueber DB-Grenzen hinweg gelten.
    kms._BEKANNTE_PROJEKTE_CACHE.clear()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _project_id_of(db_path, title):
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT project_id FROM knowledge_nodes WHERE title=?", (title,)).fetchone()
    conn.close()
    return row[0]


def _entschieden_von_of(db_path, title):
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("SELECT norm_entschieden_von FROM knowledge_nodes WHERE title=?", (title,)).fetchone()
    conn.close()
    return row[0]


# --- project_id-Ableitung aus parent_path ------------------------------------

def test_bekanntes_projekt_im_pfad_wird_uebernommen(temp_db):
    """Kernfall: /apps/fahrtenbuch ohne project_id -> 'fahrtenbuch', nicht 'shared'."""
    res = kms.knowledge_add("/apps/fahrtenbuch", "Ohne Projekt Angegeben", "Zusammenfassung",
                            source="test", norm_entscheidung="keine_norm", norm_entschieden_grund="g")
    assert "error" not in res, res
    assert _project_id_of(temp_db, "Ohne Projekt Angegeben") == "fahrtenbuch"


def test_ausdruecklich_uebergebenes_project_id_gewinnt(temp_db):
    """Gegenprobe: derselbe Pfad, aber project_id ausdruecklich gesetzt --
    die Ableitung darf das nicht ueberschreiben."""
    res = kms.knowledge_add("/apps/fahrtenbuch", "Mit Projekt Angegeben", "Zusammenfassung",
                            project_id="anderes-projekt", source="test",
                            norm_entscheidung="keine_norm", norm_entschieden_grund="g")
    assert "error" not in res, res
    assert _project_id_of(temp_db, "Mit Projekt Angegeben") == "anderes-projekt"


def test_kein_bekanntes_projekt_im_pfad_bleibt_shared(temp_db):
    """Negativfall: '/methodik' passt zu keinem bekannten Projekt -- 'shared'
    bleibt stehen, keine Erfindung."""
    res = kms.knowledge_add("/methodik", "Ohne Projektzuordnung", "Zusammenfassung",
                            source="test", norm_entscheidung="keine_norm", norm_entschieden_grund="g")
    assert "error" not in res, res
    assert _project_id_of(temp_db, "Ohne Projektzuordnung") == "shared"


# --- norm_entschieden_von: Betreiber statt Maschine bei belegtem Urheber ----

def test_betreiber_claude_md_import_traegt_betreiber(temp_db):
    """source belegt den Betreiber als Urheber (CLAUDE.md-Import) ->
    norm_entschieden_von='betreiber', nicht der actor."""
    res = kms.knowledge_add(
        "/methodik", "Betreiber Direktive Importiert", "Zusammenfassung",
        source="erzeugt aus /Users/lehrmacbook/.claude/CLAUDE.md (Stand 2026-08-09T00:00:00+0200)",
        norm_entscheidung="norm_unbefristet", norm_rang=1, gilt_ab="2026-08-09",
        norm_entschieden_grund="g", actor="claude-code/opus-5",
    )
    assert "error" not in res, res
    assert _entschieden_von_of(temp_db, "Betreiber Direktive Importiert") == "betreiber"


def test_fremdnorm_traegt_weiterhin_den_actor(temp_db):
    """Wichtigster Fall: eine aufgezeichnete Fremdnorm (Gesetz/Urteil/WEG-Recht)
    ist KEINE Betreiber-Entscheidung -- norm_entschieden_von bleibt actor."""
    res = kms.knowledge_add(
        "/methodik", "Aufgezeichnetes WEG Urteil", "Zusammenfassung",
        source="erzeugt aus buckeberg/recht/jahresabrechnung-BGH-Urteil (Stand 2026-08-09)",
        norm_entscheidung="norm_unbefristet", norm_rang=1, gilt_ab="2026-08-09",
        norm_entschieden_grund="g", actor="claude-code/opus-5",
        # norm_art (Auftrag 95, nachtraeglich Pflicht fuer fremde Herkunft --
        # source nennt woertlich 'Urteil'): 'sollen', weil ein Urteil eine
        # bindende Feststellung ist, keine reine Messung (Knoten dd367fd1).
        norm_art="sollen",
    )
    assert "error" not in res, res
    # B4.1: der Name traegt seine Beglaubigung mit. Ohne Ausweis heisst der
    # Aufrufer 'unbeglaubigt:<name>' -- die Herkunftsregel selbst ist
    # unveraendert, nur die Schreibweise des Namens.
    assert (_entschieden_von_of(temp_db, "Aufgezeichnetes WEG Urteil")
            == "unbeglaubigt:claude-code/opus-5")
