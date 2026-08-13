"""Tests fuer norm_art-Pflicht bei fremder Herkunft (Auftrag 95 = Schritt 1,
docs/PLAN_RECHTSRAUM_2026-08-13.md). Vor diesem Auftrag war norm_art bei 0
von 2166 Knoten gefuellt und der Schreibpfad verlangte nie einen Wert --
weder fuer fremde Zitate (Gesetz/DIN/ISO/BSI/RFC/WCAG) noch fuer eigenes
Wissen. Diese Datei belegt: fremde Herkunft (erkannt an source, dieselbe
Wortliste wie der bestehende Trigger normrang_herkunft) verlangt jetzt
norm_art (sein/sollen/duerfen, Knoten dd367fd1); eigenes Wissen bleibt ohne
Aufwand (NULL).

Nutzt bewusst die UNGEPATCHTE kms.knowledge_add()-Referenz (wie
test_norm_entscheidung.py) -- diese Datei prueft die ECHTE Durchsetzung."""
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

# Gesichert VOR jedem Fixture-Lauf, wie test_norm_entscheidung.py -- ruft
# echte, ungeschminkte Durchsetzung auf.
_REAL_ADD = kms.knowledge_add

_NORM_KWARGS = dict(norm_entscheidung="keine_norm",
                     norm_entschieden_grund="Testvorrichtung, keine echte Norm-Pruefung")


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


def _echter_altbestand_ohne_norm_art(tmp_path, monkeypatch) -> Path:
    """Baut eine DB OHNE die Spalte norm_art (Slice aus dem echten
    schema.sql, gleiche Technik wie test_norm_entscheidung.py::
    _echter_altbestand), fuegt eine Zeile mit fremd aussehender source ein
    (gelingt, weder Spalte noch Trigger existieren dort schon), dann laesst
    kms.ensure_schema() ueber get_db() Spalte UND Trigger per ALTER TABLE /
    executescript nachziehen. ALTER TABLE feuert keine Trigger -- das ist
    der einzige Weg, wie eine Zeile im echten Betrieb norm_art NULL bei
    fremder source traegt (ein rohes INSERT auf der fertigen DB wuerde vom
    Pflicht-Trigger abgewiesen)."""
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    vor_spalte = schema.index("    norm_art TEXT,\n")
    nach_spalte = vor_spalte + len("    norm_art TEXT,\n")
    vor_trigger = schema.index("CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_art_check_bi")
    nach_trigger_marker = "CREATE TRIGGER IF NOT EXISTS knowledge_nodes_norm_art_pflicht_bi"
    nach_trigger = schema.index(nach_trigger_marker)
    nach_trigger = schema.index("END;\n", nach_trigger) + len("END;\n")
    old_schema = schema[:vor_spalte] + schema[nach_spalte:vor_trigger] + schema[nach_trigger:]
    assert "norm_art TEXT," not in old_schema
    assert "knowledge_nodes_norm_art_check_bi" not in old_schema
    assert "knowledge_nodes_norm_art_pflicht_bi" not in old_schema

    db_path = tmp_path / "alt_ohne_norm_art.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(old_schema)
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, "
        "level, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) VALUES "
        "('alt1', '/alt', 'shared', 'Altbestand', 'x', 'x', 0, 'Gesetz: altes Fundstueck', "
        "'keine_norm', 'test', 'Testvorrichtung')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


# --- 1) ROT VOR GRUEN: fremde Herkunft ohne norm_art -------------------------

def test_fremde_quelle_ohne_norm_art_wird_abgewiesen(temp_db):
    """Vor Auftrag 95 ging dieser Aufruf klaglos durch (norm_art blieb NULL,
    ununterscheidbar von einem eigenen Satz). Jetzt: sprechende Ablehnung."""
    result = _REAL_ADD("/", "DSGVO-Auszug", "Zusammenfassung",
                        source="Gesetz: DSGVO Art. 6", **_NORM_KWARGS)
    assert "error" in result, result
    assert "norm_art" in result["error"]

    conn = sqlite3.connect(str(temp_db))
    count = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert count == 0, "abgelehnter Aufruf darf keine Zeile hinterlassen"


def test_fremde_quelle_mit_norm_art_geht_durch(temp_db):
    """Gegenprobe: derselbe Aufruf mit gesetztem norm_art gelingt."""
    result = _REAL_ADD("/", "DSGVO-Auszug mit Art", "Zusammenfassung",
                        source="Gesetz: DSGVO Art. 6", norm_art="sollen", **_NORM_KWARGS)
    assert "error" not in result, result


# --- 2) NEGATIVFALL, der wichtigere: eigene Regel ohne Zitat läuft durch ----

def test_eigene_quelle_ohne_norm_art_geht_unveraendert_durch(temp_db):
    """Eine Schranke, die auch eigenes Wissen blockiert, macht jeden
    Schreibvorgang teurer -- genau das darf nicht passieren."""
    result = _REAL_ADD("/", "Eigene Beobachtung", "Zusammenfassung",
                        source="Selbsterfahrung, Sitzung 2026-08-13", **_NORM_KWARGS)
    assert "error" not in result, result

    conn = sqlite3.connect(str(temp_db))
    row = conn.execute("SELECT norm_art FROM knowledge_nodes WHERE id = ?",
                        (result["id"],)).fetchone()
    conn.close()
    assert row[0] is None, "eigenes Wissen bleibt ohne norm_art, kein Rateversuch"


# --- 3) Wertebereich: nur sein/sollen/duerfen (oder NULL) -------------------

def test_norm_art_unzulaessiger_wert_wird_abgewiesen(temp_db):
    result = _REAL_ADD("/", "Falscher Wert", "Zusammenfassung",
                        source="Gesetz: BGB", norm_art="voellig_unbekannt", **_NORM_KWARGS)
    assert "error" in result, result
    assert "norm_art" in result["error"]


# --- 4) Grenzwert: Altbestand bleibt unangetastet ---------------------------

def test_altbestand_ohne_norm_art_bleibt_unangetastet(tmp_path, monkeypatch):
    """Eine echte Altzeile (norm_art NULL trotz fremd aussehender source, wie
    alle 2166 gemessenen Knoten -- die Pflicht existierte bei ihrer Anlage
    noch nicht) darf durch einen NEUEN Schreibvorgang weder veraendert noch
    mitgezaehlt werden -- NULL bleibt ihr Zustand, kein Rueckfuellen."""
    db_path = _echter_altbestand_ohne_norm_art(tmp_path, monkeypatch)
    kms.get_db().close()  # loest den Spalten-/Trigger-Nachzug aus (ensure_schema)

    vor = sqlite3.connect(str(db_path))
    vor_null = vor.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE norm_art IS NULL").fetchone()[0]
    vor.close()
    assert vor_null == 1, "die nachgezogene Altzeile bleibt NULL"

    result = _REAL_ADD("/", "Neuer Fremdsatz", "x", source="ISO 9241-210",
                        norm_art="sein", **_NORM_KWARGS)
    assert "error" not in result, result

    nach = sqlite3.connect(str(db_path))
    alt_zeile = nach.execute("SELECT norm_art FROM knowledge_nodes WHERE id = 'alt1'").fetchone()
    nach_null = nach.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE norm_art IS NULL").fetchone()[0]
    nach.close()
    assert alt_zeile[0] is None, "Altzeile darf nicht rueckwirkend befuellt werden"
    assert nach_null == 1, "nur die unveraenderte Altzeile bleibt NULL, der neue Knoten hat norm_art"


# --- 5) Fehlerweg: eine abgewiesene Schreiboperation darf die DB nicht -------
#        sperren -- L-f3edbf, zweimal vorgekommen. Direkt gegen den
#        DB-Trigger getestet (nicht ueber knowledge_add, das schon vorab in
#        Python ablehnt), weil genau DORT die Verbindung 2026-08-08 haengen
#        blieb.

def test_abgewiesene_verbindung_sperrt_nicht_zweite_verbindung(temp_db):
    conn1 = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError, match="norm_art"):
        conn1.execute(
            "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, "
            "level, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) VALUES "
            "('x1', '/x1', 'shared', 'x', 'x', 'x', 0, 'Gesetz: BGB', 'keine_norm', 'test', 'Testvorrichtung')"
        )
    conn1.rollback()
    conn1.close()

    # Zweite, unabhaengige Verbindung muss ungehindert schreiben koennen.
    conn2 = sqlite3.connect(str(temp_db))
    conn2.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, "
        "level, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) VALUES "
        "('x2', '/x2', 'shared', 'x', 'x', 'x', 0, 'eigene Notiz', 'keine_norm', 'test', 'Testvorrichtung')"
    )
    conn2.commit()
    count = conn2.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE id = 'x2'").fetchone()[0]
    conn2.close()
    assert count == 1, "zweite Verbindung muss nach Abweisung der ersten schreiben koennen"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
