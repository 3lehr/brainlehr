"""Tests fuer actor/model/session bei jedem Schreibvorgang (Auftrag
2026-08-06, Mangel: access_log.actor nur 9%, .session nur 0,5% gefuellt, kein
Feld fuer den Schreiber auf knowledge_nodes/lessons_learned selbst).

Ursache (Punkt a des Auftrags): _identity() ist die EINE Stelle, durch die
jeder log_access()-Aufruf laeuft (log_access ruft sie intern IMMER auf). Ihre
Aufloesungskette war Parameter -> Umgebungsvariable -> NICHTS (still None) --
kein dritter, expliziter Schritt, obwohl die Tool-Beschreibungen in
IDENTITY_PROPERTIES bereits "else BEGOD_KNOWLEDGE_ACTOR or unknown"
versprachen. Separat: lesson_record/lesson_update hatten GAR KEINE
actor/model/session-Parameter -- strukturell unmoeglich, sie zu uebergeben.
Beides in knowledge_mcp_server.py behoben (_identity() plus die beiden
Funktionssignaturen)."""
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

import os
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
    # Ursache reproduzieren: Umgebungsvariablen sind im Regelfall NICHT
    # gesetzt -- explizit entfernen, damit dieser Testlauf nicht zufaellig
    # vom echten Environment des Bearbeiters profitiert.
    for var in ("BEGOD_KNOWLEDGE_ACTOR", "BEGOD_KNOWLEDGE_MODEL", "BEGOD_KNOWLEDGE_SESSION"):
        monkeypatch.delenv(var, raising=False)
    # Dritter Fallback-Schritt (Auftrag 2026-08-07) ist an _PROZESS_SITZUNG
    # gebunden, einmal beim Modulimport aus CLAUDE_CODE_SESSION_ID gelesen --
    # ein delenv() DANACH wirkt darauf nicht mehr. Fuer die Faelle unten, die
    # das Ende der Kette pruefen (kein Aufrufer, keine Env), wird dieser
    # dritte Schritt hier zusaetzlich stillgelegt; test_e prueft ihn gezielt.
    monkeypatch.setattr(kms, "_PROZESS_SITZUNG", None)
    return db_path


def _alte_identity(actor=None, model=None, session=None):
    """Die Formel vor der Reparatur, hier nur zum Vergleich nachgebaut
    (Aufloesung endete bei None, kein dritter Schritt)."""
    return (
        actor or os.environ.get("BEGOD_KNOWLEDGE_ACTOR"),
        model or os.environ.get("BEGOD_KNOWLEDGE_MODEL"),
        session or os.environ.get("BEGOD_KNOWLEDGE_SESSION"),
    )


# ─── a) Ursache, als Test belegt statt nur behauptet ───────────────────────

def test_a_alte_formel_liefert_none_neue_liefert_unbekannt(temp_db):
    vorher = _alte_identity()
    nachher = kms._identity()
    print(f"VORHER (alte Formel, kein Aufrufer/keine Env): {vorher}")
    print(f"NACHHER (kms._identity(), gleiche Bedingungen): {nachher}")
    assert vorher == (None, None, None), vorher
    assert nachher == ("unbekannt", "unbekannt", "unbekannt"), nachher


# ─── b) ROT VOR GRUEN: Schreibvorgang ohne ausdrueckliche Angabe ───────────

def test_b_schreibvorgang_ohne_angabe_vorher_leer_nachher_gefuellt(temp_db):
    # VORHER: mit der alten Formel waeren actor/session in access_log NULL
    # geblieben (log_access ruft _identity() intern auf -- simuliert hier
    # direkt an der Formel, da der alte Code nicht mehr im Repo steht).
    vorher_actor, _, vorher_session = _alte_identity()
    print(f"VORHER: actor={vorher_actor!r} session={vorher_session!r}")
    assert vorher_actor is None and vorher_session is None

    node = kms.knowledge_add(
        "/", "Schreiber-Testknoten", "Zusammenfassung",
        content="Inhalt", source="erzeugt aus Test (Stand 2026-08-06)",
    )
    assert node.get("status") == "created", node

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    node_row = conn.execute(
        "SELECT actor, session FROM knowledge_nodes WHERE id = ?", (node["id"],)
    ).fetchone()
    log_row = conn.execute(
        "SELECT actor, model, session FROM access_log WHERE node_path = ? AND action = 'add' "
        "ORDER BY id DESC LIMIT 1", (node["path"],)
    ).fetchone()
    conn.close()

    print(f"NACHHER: knowledge_nodes.actor={node_row['actor']!r} .session={node_row['session']!r}")
    print(f"NACHHER: access_log.actor={log_row['actor']!r} .model={log_row['model']!r} .session={log_row['session']!r}")

    assert node_row["actor"] == "unbekannt", node_row["actor"]
    assert node_row["session"] == "unbekannt", node_row["session"]
    assert log_row["actor"] == "unbekannt"
    assert log_row["model"] == "unbekannt"
    assert log_row["session"] == "unbekannt"


# ─── c) Auswertung: zwei Knoten unter verschiedenen Sitzungen, je auflisten ─

def test_c_knowledge_sitzung_trennt_nach_session(temp_db):
    a = kms.knowledge_add(
        "/", "Sitzung-A-Knoten", "Zusammenfassung A",
        source="erzeugt aus Test (Stand 2026-08-06)", session="sitzung-a",
    )
    b = kms.knowledge_add(
        "/", "Sitzung-B-Knoten", "Zusammenfassung B",
        source="erzeugt aus Test (Stand 2026-08-06)", session="sitzung-b",
    )
    assert a.get("status") == "created" and b.get("status") == "created", (a, b)

    ausgabe_a = kms.knowledge_sitzung("sitzung-a")
    ausgabe_b = kms.knowledge_sitzung("sitzung-b")
    print(f"knowledge_sitzung('sitzung-a'): {ausgabe_a}")
    print(f"knowledge_sitzung('sitzung-b'): {ausgabe_b}")

    assert [n["id"] for n in ausgabe_a["nodes"]] == [a["id"]], ausgabe_a
    assert [n["id"] for n in ausgabe_b["nodes"]] == [b["id"]], ausgabe_b
    assert ausgabe_a["nodes"][0]["session"] == "sitzung-a"
    assert ausgabe_b["nodes"][0]["session"] == "sitzung-b"
    # Reines Lesen -- kein Zurueckziehen, keine Aenderung an den Zeilen.
    conn = sqlite3.connect(str(temp_db))
    zurueckgezogen = conn.execute(
        "SELECT COUNT(*) FROM knowledge_nodes WHERE zurueckgezogen = 1"
    ).fetchone()[0]
    conn.close()
    assert zurueckgezogen == 0, "knowledge_sitzung darf nichts zurueckziehen"


def test_c_knowledge_sitzung_deckt_auch_lessons_ab(temp_db):
    lesson = kms.lesson_record("pattern", "Sitzungs-Testlesson", session="sitzung-lesson")
    assert lesson["status"] == "recorded", lesson

    ausgabe = kms.knowledge_sitzung("sitzung-lesson")
    print(f"knowledge_sitzung('sitzung-lesson'): {ausgabe}")
    assert [l["id"] for l in ausgabe["lessons"]] == [lesson["id"]], ausgabe


# ─── d) Negativfall: ohne jede Kennung wird geschrieben, nicht abgewiesen ──

def test_d_ohne_jede_kennung_wird_nicht_abgewiesen(temp_db):
    node = kms.knowledge_add(
        "/", "Anonymer-Testknoten", "Zusammenfassung ohne jede Identitaet",
        source="erzeugt aus Test (Stand 2026-08-06)",
        actor=None, model=None, session=None,
    )
    assert node.get("status") == "created", (
        "ein Schreiber ohne Kennung haette NICHT abgewiesen werden duerfen", node
    )

    lesson = kms.lesson_record("insight", "Anonyme Testlesson ohne Kennung")
    assert lesson.get("status") == "recorded", (
        "lesson_record haette einen anonymen Schreiber ebenfalls nicht abweisen duerfen", lesson
    )

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT actor, session FROM knowledge_nodes WHERE id = ?", (node["id"],)).fetchone()
    conn.close()
    assert row["actor"] == "unbekannt"
    assert row["session"] == "unbekannt"


# ─── e) Server bestimmt Kennung selbst statt sie vom Aufrufer zu erwarten ──
# (Auftrag 2026-08-07): dritter Schritt der Kette. Bisher endete die Kette
# bei "unbekannt", sobald weder Aufrufer noch BEGOD_KNOWLEDGE_SESSION einen
# Wert mitgaben -- der Regelfall, denn dieses Feld muss der Schreiber
# freiwillig fuellen. Jetzt: _PROZESS_SITZUNG, einmal beim Prozessstart aus
# CLAUDE_CODE_SESSION_ID gelesen (vom Claude-Code-Host an jeden MCP-Server-
# Kindprozess vererbt), greift VOR "unbekannt". Aufrufer-Wert bleibt Vorrang
# (Negativfall).

def test_e_prozess_sitzung_greift_vor_unbekannt(temp_db, monkeypatch):
    monkeypatch.setattr(kms, "_PROZESS_SITZUNG", "43459d92-fallback-probe")

    node = kms.knowledge_add(
        "/", "Prozesssitzung-Testknoten", "Zusammenfassung",
        source="erzeugt aus Test (Stand 2026-08-07)",
    )
    assert node.get("status") == "created", node

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT session FROM knowledge_nodes WHERE id = ?", (node["id"],)).fetchone()
    conn.close()
    print(f"NACHHER: knowledge_nodes.session={row['session']!r}")
    assert row["session"] == "43459d92-fallback-probe", row["session"]


def test_e_aufrufer_wert_hat_vorrang_vor_prozess_sitzung(temp_db, monkeypatch):
    monkeypatch.setattr(kms, "_PROZESS_SITZUNG", "43459d92-fallback-probe")

    node = kms.knowledge_add(
        "/", "Prozesssitzung-Negativtest", "Zusammenfassung",
        source="erzeugt aus Test (Stand 2026-08-07)", session="eigene-kennung",
    )
    assert node.get("status") == "created", node

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT session FROM knowledge_nodes WHERE id = ?", (node["id"],)).fetchone()
    conn.close()
    assert row["session"] == "eigene-kennung", row["session"]


# ─── Nachtrag: model, gleiche Machart wie actor/session ────────────────────
#
# a) Pruefung: model war NICHT an knowledge_nodes/lessons_learned (nur an
# access_log) -- schema.sql trug bis zu diesem Nachtrag einen expliziten
# Kommentar "model bewusst NICHT hier dupliziert". Jetzt ergaenzt, gleiche
# Migration erweitert (migrate_schreiber.py, NEW_COLUMNS um 'model').

def test_b_schreibvorgang_mit_model_steht_am_datensatz(temp_db):
    mit_model = kms.knowledge_add(
        "/", "Modell-Testknoten-explizit", "Zusammenfassung",
        source="erzeugt aus Test (Stand 2026-08-06)", model="claude-opus-5",
    )
    ohne_model = kms.knowledge_add(
        "/", "Modell-Testknoten-implizit", "Zusammenfassung",
        source="erzeugt aus Test (Stand 2026-08-06)",
    )
    assert mit_model.get("status") == "created" and ohne_model.get("status") == "created"

    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row_mit = conn.execute("SELECT model FROM knowledge_nodes WHERE id = ?", (mit_model["id"],)).fetchone()
    row_ohne = conn.execute("SELECT model FROM knowledge_nodes WHERE id = ?", (ohne_model["id"],)).fetchone()
    conn.close()

    print(f"MIT ausdruecklichem model: {row_mit['model']!r}")
    print(f"OHNE Angabe: {row_ohne['model']!r}")
    assert row_mit["model"] == "claude-opus-5", row_mit["model"]
    assert row_ohne["model"] == "unbekannt", row_ohne["model"]


def test_c_knowledge_modell_trennt_nach_modell(temp_db):
    a = kms.knowledge_add(
        "/", "Modell-A-Knoten", "Zusammenfassung A",
        source="erzeugt aus Test (Stand 2026-08-06)", model="modell-a",
    )
    b = kms.knowledge_add(
        "/", "Modell-B-Knoten", "Zusammenfassung B",
        source="erzeugt aus Test (Stand 2026-08-06)", model="modell-b",
    )
    assert a.get("status") == "created" and b.get("status") == "created", (a, b)

    ausgabe_a = kms.knowledge_modell("modell-a")
    ausgabe_b = kms.knowledge_modell("modell-b")
    print(f"knowledge_modell('modell-a'): {ausgabe_a}")
    print(f"knowledge_modell('modell-b'): {ausgabe_b}")

    assert [n["id"] for n in ausgabe_a["nodes"]] == [a["id"]], ausgabe_a
    assert [n["id"] for n in ausgabe_b["nodes"]] == [b["id"]], ausgabe_b
    assert ausgabe_a["nodes"][0]["model"] == "modell-a"
    assert ausgabe_b["nodes"][0]["model"] == "modell-b"


def test_lesson_record_traegt_model_auch(temp_db):
    lesson = kms.lesson_record("pattern", "Modell-Testlesson", model="modell-lesson")
    assert lesson["status"] == "recorded", lesson
    ausgabe = kms.knowledge_modell("modell-lesson")
    assert [l["id"] for l in ausgabe["lessons"]] == [lesson["id"]], ausgabe
