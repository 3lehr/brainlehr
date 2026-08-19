"""Tests fuer den rohen Kosinus-Wert je Kandidat in haken/suchpfad_abruf.py::
kandidaten() (Feld "bedeutungs_kosinus", Auftrag 2026-08-19).

Vorher lieferte kandidaten() nur RANGPOSITIONEN (embeddings.rrf_fuse addiert
1/(k+Rang), der Rohwert des Bedeutungskanals ging dabei verloren) -- derselbe
Befund, der in knowledge_mcp_server.py::knowledge_search() bereits am
2026-08-19 behoben wurde (Commit 4c88915b, siehe tests/test_kosinus_im_treffer.py,
die Vorlage fuer diese Datei). _embedding_ranking() konnte den Kosinus schon
vorher liefern (Parameter "werte"), suchpfad_abruf.kandidaten() reichte ihn nur
nicht bis in die Zeile durch.

KEINE Schwelle, KEINE Enthaltung, KEIN Filtern, KEINE Aenderung an Auswahl
oder Reihenfolge -- nur der Wert wird angehaengt (s. test_reihenfolge_*).

Fixtures nach dem Muster von tests/test_kanalwahl_haken.py::temp_db (frische
Test-DB mit echtem Schema, conn als Parameter statt DB_PATH-Monkeypatch --
sa.kandidaten() nimmt die Verbindung direkt entgegen)."""
from __future__ import annotations

import importlib.util
import struct
import subprocess
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "kern"))
sys.path.insert(0, str(ROOT / "haken"))

import knowledge_mcp_server as kms  # noqa: E402
import haken.suchpfad_abruf as sa  # noqa: E402


@pytest.fixture()
def temp_db(tmp_path):
    """Frische Test-DB mit dem echten Schema, gleicher Aufbau wie
    tests/test_kanalwahl_haken.py::temp_db."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (ROOT / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, "
        "norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
        "VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        [
            ("n1", "/steuer/aveuer-regel", "AVEUER Sonderabschreibung",
             "Regel zur Abschreibung von Anlagegütern im ersten Jahr"),
            ("n2", "/freizeit/katzen", "Katzen sind neugierig",
             "Ein Text ganz ohne Bezug zu Steuern oder Buchhaltung"),
            ("n3", "/steuer/afa-tabelle", "AfA-Tabelle Steuer",
             "Nutzungsdauer und Restwert fuer Wirtschaftsgueter, amtliche Tabelle"),
        ],
    )
    conn.executemany(
        "INSERT INTO lessons_learned (id, type, description, root_cause, prevention, projects) "
        "VALUES (?, 'insight', ?, ?, ?, '[]')",
        [
            ("L-aaa111", "Falscher Interpreter liess Tests dauerhaft als kaputt gelten",
             "System-python3 statt .venv/bin/python verwendet",
             "Immer den Projekt-Interpreter fuer Testlaeufe nutzen"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


def _fake_vec(*floats: float) -> bytes:
    return struct.pack(f"<{len(floats)}f", *floats)


def _insert_embedding(db_path: Path, kind: str, ref_id: str, vector: tuple[float, ...]):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, model, dim, vector, updated_at) "
        "VALUES (?, ?, ?, ?, ?, '2026-08-13T00:00:00+02:00')",
        (kind, ref_id, kms.embeddings.DEFAULT_EMBED_MODEL, len(vector), _fake_vec(*vector)),
    )
    conn.commit()
    conn.close()


def _open(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# --- 2. Gegenprobe in beide Richtungen: MIT Vektor eine Zahl, OHNE Vektor None -

def test_kandidat_mit_vektor_traegt_kosinuszahl(temp_db):
    _insert_embedding(temp_db, "node", "n1", (1.0, 0.0, 0.0))
    conn = _open(temp_db)
    nodes, _ = sa.kandidaten(conn, "Abschreibung", [1.0, 0.0, 0.0], 5)
    conn.close()

    by_id = {n["id"]: n for n in nodes}
    assert "n1" in by_id
    wert = by_id["n1"]["bedeutungs_kosinus"]
    assert wert is not None
    assert isinstance(wert, float)
    assert -1.0 <= wert <= 1.0
    assert wert == pytest.approx(1.0, abs=1e-6)  # exakt der Query-Vektor


def test_kandidat_ohne_vektor_traegt_none_nicht_null(temp_db):
    # n1 kommt nur ueber den Stichwortkanal -- kein knowledge_embeddings-Eintrag.
    # 0.0 waere eine (falsche) Aussage ueber Aehnlichkeit; None sagt "kein Vektor da".
    conn = _open(temp_db)
    nodes, _ = sa.kandidaten(conn, "Abschreibung", [1.0, 0.0, 0.0], 5)
    conn.close()

    by_id = {n["id"]: n for n in nodes}
    assert "n1" in by_id
    assert by_id["n1"]["bedeutungs_kosinus"] is None


def test_lesson_kandidat_traegt_ebenfalls_das_feld(temp_db):
    _insert_embedding(temp_db, "lesson", "L-aaa111", (1.0, 0.0))
    conn = _open(temp_db)
    _, lessons = sa.kandidaten(conn, "Interpreter Testlaeufe", [1.0, 0.0], 5)
    conn.close()

    by_id = {l["id"]: l for l in lessons}
    assert "L-aaa111" in by_id
    assert by_id["L-aaa111"]["bedeutungs_kosinus"] == pytest.approx(1.0, abs=1e-6)


def test_ohne_query_vec_bleibt_feld_none(temp_db):
    """query_vec=None (Bedeutungskanal nicht verfuegbar, z.B. Ollama down) --
    darf nicht crashen, jeder Kandidat traegt None."""
    conn = _open(temp_db)
    nodes, _ = sa.kandidaten(conn, "Abschreibung", None, 5)
    conn.close()
    assert nodes and all(n["bedeutungs_kosinus"] is None for n in nodes)


# --- 3. Negativfall: Auswahl UND Reihenfolge vor/nach der Aenderung identisch -

# Fixer Commit statt HEAD: HEAD wandert mit jedem weiteren Commit auf diesem
# Zweig (Leer-Commit in der Abnahme eingeschlossen) und traegt danach die
# Aenderung selbst -- der Vergleichsstand ist deshalb der Stand VOR diesem
# Auftrag, nicht HEAD (L-82415c: ein Beleg gegen HEAD ist genau einmal gruen).
_VORHER_COMMIT = "ad0a54eafe08296dd3ab14209cb54b035b114b21"


def _lade_vorher_fassung():
    """Laedt haken/suchpfad_abruf.py-Stand VOR der Kosinus-Aenderung als
    eigenstaendiges Modul, damit derselbe Testlauf beide Fassungen gegen
    dieselbe temp_db ausfuehren kann -- ohne git checkout/stash (tabu laut
    Auftrag) am Arbeitsverzeichnis. Abhaengigkeiten (embeddings,
    gattung_filter, knowledge_mcp_server) sind unveraendert und werden aus
    dem regulaeren sys.path geladen -- nur suchpfad_abruf.py selbst wird als
    Vorher-Stand eingelesen."""
    quelltext = subprocess.run(
        ["git", "show", f"{_VORHER_COMMIT}:haken/suchpfad_abruf.py"],
        cwd=str(ROOT), capture_output=True, text=True, check=True,
    ).stdout
    tmp_datei = ROOT / "haken" / "_suchpfad_abruf_vorher_tmp.py"
    tmp_datei.write_text(quelltext, encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location("suchpfad_abruf_vorher", tmp_datei)
        modul = importlib.util.module_from_spec(spec)
        sys.modules["suchpfad_abruf_vorher"] = modul
        spec.loader.exec_module(modul)
    finally:
        tmp_datei.unlink()
    return modul


def test_reihenfolge_identisch_zum_vorher_stand(temp_db):
    _insert_embedding(temp_db, "node", "n1", (-1.0, 0.0, 0.0))
    _insert_embedding(temp_db, "node", "n3", (0.9, 0.1, 0.0))

    conn = _open(temp_db)
    aktuell_nodes, aktuell_lessons = sa.kandidaten(conn, "Abschreibung Steuer", [1.0, 0.0, 0.0], 5)
    conn.close()
    aktuelle_ids = [n["id"] for n in aktuell_nodes] + [l["id"] for l in aktuell_lessons]

    vorher_mod = _lade_vorher_fassung()
    conn2 = _open(temp_db)
    vorher_nodes, vorher_lessons = vorher_mod.kandidaten(conn2, "Abschreibung Steuer", [1.0, 0.0, 0.0], 5)
    conn2.close()
    vorherige_ids = [n["id"] for n in vorher_nodes] + [l["id"] for l in vorher_lessons]

    assert aktuelle_ids == vorherige_ids, (
        "Auswahl/Reihenfolge der Kandidaten hat sich durch das neue Feld veraendert")
    assert "bedeutungs_kosinus" not in vorher_nodes[0], "Vorher-Fassung sollte das Feld noch nicht kennen"
    assert "bedeutungs_kosinus" in aktuell_nodes[0]


def test_rot_vor_dem_fix(temp_db):
    """Belegt Abnahmepunkt 1: gegen den fixen Vorher-Stand (_VORHER_COMMIT,
    vor diesem Auftrag) schlaegt genau diese Zusicherung fehl -- das Feld
    fehlte dort."""
    _insert_embedding(temp_db, "node", "n1", (1.0, 0.0, 0.0))

    vorher_mod = _lade_vorher_fassung()
    conn = _open(temp_db)
    vorher_nodes, _ = vorher_mod.kandidaten(conn, "Abschreibung", [1.0, 0.0, 0.0], 5)
    conn.close()
    with pytest.raises(KeyError):
        _ = vorher_nodes[0]["bedeutungs_kosinus"]  # rot: Feld existierte im Vorher-Stand nicht

    conn2 = _open(temp_db)
    jetzt_nodes, _ = sa.kandidaten(conn2, "Abschreibung", [1.0, 0.0, 0.0], 5)
    conn2.close()
    assert jetzt_nodes[0]["bedeutungs_kosinus"] == pytest.approx(1.0, abs=1e-6)  # gruen: jetzt vorhanden
