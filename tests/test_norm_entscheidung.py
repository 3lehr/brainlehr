"""Tests fuer norm_entscheidung (Auftrag 2026-08-08, Konsil
docs/KONSIL_WISSENSRAUM_ANSICHT_2026-08-08.md): norm_rang/gilt_bis IS NULL
war doppeldeutig -- "Fakt, bewusst keine Norm" UND "nie jemand hat
hingesehen" sahen identisch aus. Diese Datei belegt, dass die Entscheidung
jetzt Pflicht ist und die drei Zustaende (Altbestand offen / neu keine_norm /
neu Norm mit Rang) unterscheidbar sind -- ohne den Altbestand zu raten.

Nutzt bewusst die UNGEPATCHTE kms.knowledge_add()-Referenz (vor dem
Default-Fixture in conftest.py gesichert, siehe Modul-Kopf unten) -- diese
Datei prueft die ECHTE Durchsetzung, nicht die Testbequemlichkeit, die
conftest.py fuer alle anderen (norm-fernen) Tests bereitstellt."""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

# Gesichert VOR jedem Fixture-Lauf (Modul-Import passiert vor Testausfuehrung,
# monkeypatch.setattr in conftest.py greift erst danach je Test) -- ruft
# echte, ungeschminkte Durchsetzung auf.
_REAL_ADD = kms.knowledge_add


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


def _echter_altbestand(tmp_path, monkeypatch) -> Path:
    """Baut eine DB OHNE die Spalte norm_entscheidung (Slice aus dem echten
    schema.sql, dieselbe Technik wie test_anlass_schema_backfill.py fuer
    anlass), fuegt eine Zeile normal ein (gelingt, Spalte existiert ja noch
    nicht), dann laesst kms.ensure_schema() ueber get_db() die Spalte per
    ALTER TABLE nachziehen. Das ist der EINZIGE Weg, wie eine Zeile im
    echten Betrieb 'offen' traegt -- ein rohes INSERT auf einer DB, die die
    Spalte SCHON hat, wuerde vom Pflicht-Trigger abgewiesen (das ist ja der
    Witz der Zusicherung), waehrend ALTER TABLE ADD COLUMN keine Trigger
    feuert (Schema-, keine DML-Operation)."""
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    vor_spalte = schema.index("    norm_entscheidung TEXT NOT NULL DEFAULT 'offen',\n")
    nach_spalte = vor_spalte + len("    norm_entscheidung TEXT NOT NULL DEFAULT 'offen',\n")
    vor_trigger = schema.index("CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_entscheidung_check_bi")
    nach_trigger_marker = "CREATE TRIGGER IF NOT EXISTS knowledge_nodes_gilt_bis_vor_gilt_ab_bu"
    nach_trigger = schema.index(nach_trigger_marker)
    nach_trigger = schema.index("END;\n", nach_trigger) + len("END;\n")
    old_schema = schema[:vor_spalte] + schema[nach_spalte:vor_trigger] + schema[nach_trigger:]
    assert "norm_entscheidung TEXT NOT NULL DEFAULT" not in old_schema
    assert "knowledge_nodes_norm_entscheidung_check_bi" not in old_schema
    assert "knowledge_nodes_gilt_bis_vor_gilt_ab_bu" not in old_schema

    db_path = tmp_path / "alt_ohne_norm_entscheidung.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(old_schema)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source) "
        "VALUES ('alt1', '/alt', 'shared', 'Altbestand', 'x', 'x', 0, 'x')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


# --- 1) ROT VOR GRUEN: Anlegeversuch ohne Entscheidung -----------------------

def test_ohne_norm_entscheidung_wird_abgelehnt(temp_db):
    """Vor Auftrag 2026-08-08 ging dieser Aufruf klaglos durch (norm_rang
    blieb NULL, ununterscheidbar von 'nie entschieden'). Jetzt: sprechende
    Ablehnung, kein stiller Erfolg."""
    result = _REAL_ADD("/", "Ohne Entscheidung", "Zusammenfassung", source="test")
    assert "error" in result, result
    assert "norm_entscheidung" in result["error"]

    conn = sqlite3.connect(str(temp_db))
    count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert count == 0, "abgelehnter Aufruf darf keine Zeile hinterlassen"


def test_mit_norm_entscheidung_geht_durch(temp_db):
    """Gegenprobe: derselbe Aufruf mit expliziter Entscheidung gelingt."""
    result = _REAL_ADD("/", "Mit Entscheidung", "Zusammenfassung", source="test",
                        norm_entscheidung="keine_norm",
                        norm_entschieden_grund="Testvorrichtung, keine echte Norm-Pruefung")
    assert "error" not in result, result


# --- 2) Drei Zustaende unterscheidbar ----------------------------------------

def test_drei_zustaende_unterscheidbar(tmp_path, monkeypatch):
    """(a) Altbestand nie entschieden -- echte Alt-DB ohne die Spalte, per
    ensure_schema()-Nachzug auf 'offen' gebracht (siehe _echter_altbestand).
    (b) neu, ausdruecklich keine Norm. (c) neu, Norm mit Rang."""
    db_path = _echter_altbestand(tmp_path, monkeypatch)
    kms.get_db().close()  # loest den Spalten-Nachzug aus (ensure_schema)

    fakt = _REAL_ADD("/", "Neuer Fakt", "x", source="test", norm_entscheidung="keine_norm",
                     norm_entschieden_grund="Testvorrichtung, keine echte Norm-Pruefung")
    assert "error" not in fakt, fakt
    norm = _REAL_ADD("/", "Neue Norm", "x", source="test", norm_rang=2,
                      gilt_ab="2026-08-08", norm_entscheidung="norm_unbefristet",
                      norm_entschieden_grund="Testvorrichtung, echte Norm zu Testzwecken")
    assert "error" not in norm, norm

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # (a) Altbestand, nie entschieden.
    offen = conn.execute(
        "SELECT id FROM knowledge_nodes WHERE norm_entscheidung = 'offen'"
    ).fetchall()
    assert [r["id"] for r in offen] == ["alt1"], offen

    # (b) neu, ausdruecklich keine Norm.
    keine_norm = conn.execute(
        "SELECT id FROM knowledge_nodes WHERE norm_entscheidung = 'keine_norm'"
    ).fetchall()
    assert [r["id"] for r in keine_norm] == [fakt["id"]], keine_norm

    # (c) neu, Norm mit Rang.
    norm_rows = conn.execute(
        "SELECT id FROM knowledge_nodes WHERE norm_entscheidung IN ('norm_befristet','norm_unbefristet')"
    ).fetchall()
    assert [r["id"] for r in norm_rows] == [norm["id"]], norm_rows

    conn.close()


# --- 3) Negativfall + Gegenprobe: Norm mit Rang ohne gilt_ab -----------------

def test_norm_mit_rang_ohne_gilt_ab_wird_abgewiesen(temp_db):
    result = _REAL_ADD("/", "Norm ohne gilt_ab", "x", source="test",
                        norm_rang=2, norm_entscheidung="norm_unbefristet",
                        norm_entschieden_grund="Testvorrichtung, echte Norm zu Testzwecken")
    assert "error" in result, result
    assert "gilt_ab" in result["error"]


def test_nicht_norm_braucht_kein_gilt_ab(temp_db):
    """Gegenprobe: eine Nicht-Norm (keine_norm) geht ohne gilt_ab durch."""
    result = _REAL_ADD("/", "Fakt ohne gilt_ab", "x", source="test",
                        norm_entscheidung="keine_norm",
                        norm_entschieden_grund="Testvorrichtung, keine echte Norm-Pruefung")
    assert "error" not in result, result


# --- 4) Grenzwert gilt_bis vs. gilt_ab (Doku: siehe test_normschicht_mcp.py
# fuer die volle Parametrisierung inkl. "einen Tag davor") -------------------

def test_gilt_bis_gleich_gilt_ab_erlaubt(temp_db):
    result = _REAL_ADD("/", "Gleicher Tag", "x", source="test", norm_rang=3,
                        gilt_ab="2026-08-08", gilt_bis="2026-08-08",
                        norm_entscheidung="norm_befristet",
                        norm_entschieden_grund="Testvorrichtung, echte Norm zu Testzwecken")
    assert "error" not in result, result


def test_gilt_bis_vor_gilt_ab_abgewiesen(temp_db):
    result = _REAL_ADD("/", "Vor Beginn", "x", source="test", norm_rang=3,
                        gilt_ab="2026-08-08", gilt_bis="2026-08-07",
                        norm_entscheidung="norm_befristet",
                        norm_entschieden_grund="Testvorrichtung, echte Norm zu Testzwecken")
    assert "error" in result, result


# --- 5) Altbestand bleibt unveraendert (Zaehlung) ----------------------------

def test_altbestand_zahl_unveraendert_durch_neue_schreibvorgaenge(tmp_path, monkeypatch):
    db_path = _echter_altbestand(tmp_path, monkeypatch)
    kms.get_db().close()  # loest den Spalten-Nachzug aus (ensure_schema)

    conn = sqlite3.connect(str(db_path))
    vor_gesamt = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    vor_rang = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE norm_rang IS NOT NULL").fetchone()[0]
    conn.close()

    _REAL_ADD("/", "Neuer Fakt", "x", source="test", norm_entscheidung="keine_norm",
              norm_entschieden_grund="Testvorrichtung, keine echte Norm-Pruefung")

    conn = sqlite3.connect(str(db_path))
    nach_alt_gesamt = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE id = 'alt1'"
    ).fetchone()[0]
    nach_alt_rang = conn.execute(
        "SELECT norm_rang, norm_entscheidung FROM knowledge_nodes WHERE id = 'alt1'"
    ).fetchone()
    conn.close()

    assert nach_alt_gesamt == 1, "Altzeile darf durch neuen Schreibvorgang nicht verschwinden"
    assert nach_alt_rang == (None, "offen"), nach_alt_rang
    assert vor_rang == 0  # in dieser Test-DB hatte der Altbestand keinen Rang


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
