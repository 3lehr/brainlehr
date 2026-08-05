"""Tests fuer knowledge_mcp_server.py — Lesson-Unmangling + lesson_update.

Deckt den Aufrufer-Fehler ab, der 21 der 218 Lessons verstuemmelt hat: eine
verrutschte Parametergrenze laesst Feld-Tags (plain `<root_cause>...</root_cause>`
oder antml-Stil `<parameter name="root_cause">...</parameter>`) im Wert eines
anderen Feldes landen.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import migrate_relations  # type: ignore  # noqa: E402


# --- Fixtures ---------------------------------------------------------------

@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Frische Test-DB mit dem echten Schema, DB_PATH umgebogen."""
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _lesson_row(db_path: Path, lesson_id: str) -> dict:
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM lessons_learned WHERE id = ?", (lesson_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _db_rows(db_path: Path, query: str) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = [dict(row) for row in conn.execute(query)]
    conn.close()
    return rows


def test_access_identity_env_and_update_logging(temp_db, monkeypatch):
    monkeypatch.setenv("BEGOD_KNOWLEDGE_ACTOR", "codex")
    monkeypatch.setenv("BEGOD_KNOWLEDGE_MODEL", "gpt-test")
    monkeypatch.setenv("BEGOD_KNOWLEDGE_SESSION", "session-42")
    node = kms.knowledge_add("/", "Identity Node", "initial")
    kms.knowledge_update(node["id"], summary="changed")
    rows = _db_rows(temp_db, "SELECT action,actor,model,session,status FROM access_log ORDER BY id")
    assert [(row["action"], row["status"]) for row in rows] == [
        ("add", "started"), ("add", "completed"),
        ("update", "started"), ("update", "completed"),
    ]
    assert {(row["actor"], row["model"], row["session"], row["status"]) for row in rows} == {
        ("codex", "gpt-test", "session-42", "started"),
        ("codex", "gpt-test", "session-42", "completed"),
    }


def test_busy_timeout_pragma_is_set(temp_db):
    conn = kms.get_db()
    value = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    conn.close()
    assert value == kms.BUSY_TIMEOUT_MS


def test_knowledge_update_detects_lost_update_and_reports_current_state(temp_db, monkeypatch):
    """Zwei Schreiber auf demselben Knoten: der zweite muss scheitern, nicht
    lautlos den ersten ueberschreiben. Simuliert wird die Rennsituation, indem
    zwischen dem SELECT und dem UPDATE INNERHALB desselben knowledge_update()-
    Aufrufs ein zweiter, echter Schreibvorgang ueber eine eigene Verbindung
    committet -- genau das Fenster, das der optimistische Lock abdecken soll.

    now_iso() wird auf garantiert steigende Sekunden gestellt: der echte
    now_iso() rastet nur sekundengenau, zwei Schreibvorgaenge im selben Lauf
    landen sonst zufaellig im selben String und der Lock erkennt den
    Konflikt nicht zuverlaessig -- ein Hinweis, keine Behauptung ueber die
    Produktion, dort ist echte Nebenlaeufigkeit selten sub-sekundengenau."""
    ticks = iter(f"2026-01-01T00:00:{i:02d}+01:00" for i in range(30))
    monkeypatch.setattr(kms, "now_iso", lambda: next(ticks))

    node = kms.knowledge_add("/", "Race Node", "v0")
    race_state = {"armed": True, "node_id": node["id"], "db_path": temp_db}

    class RacingConnection(sqlite3.Connection):
        def execute(self, sql, params=()):
            # Race erst kurz VOR dem eigenen UPDATE einschieben -- das SELECT
            # zuvor muss den ORIGINALEN (noch nicht ueberschriebenen)
            # updated_at-Wert einsammeln, sonst wuerde der Aufrufer schon mit
            # dem fremden Stand starten statt mit einem veralteten.
            if race_state["armed"] and sql.startswith("UPDATE knowledge_nodes SET"):
                race_state["armed"] = False
                other = sqlite3.connect(str(race_state["db_path"]))
                other.execute(
                    "UPDATE knowledge_nodes SET summary = ?, updated_at = ? WHERE id = ?",
                    ("changed by other session", kms.now_iso(), race_state["node_id"]),
                )
                other.commit()
                other.close()
            return super().execute(sql, params)

    def racing_get_db():
        conn = sqlite3.connect(str(kms.DB_PATH), factory=RacingConnection)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA busy_timeout={kms.BUSY_TIMEOUT_MS}")
        conn.execute("PRAGMA foreign_keys=ON")
        kms.ensure_schema(conn)
        return conn

    monkeypatch.setattr(kms, "get_db", racing_get_db)

    result = kms.knowledge_update(node["id"], summary="changed by stale caller")
    assert "error" in result
    assert "Conflict" in result["error"]
    assert result["current"]["summary"] == "changed by other session"

    # Gegenprobe: ein Update ohne Nebenlaeufigkeit (armed ist jetzt aus) geht
    # weiterhin normal durch -- der Schutz darf den Normalfall nicht brechen.
    ok = kms.knowledge_update(node["id"], summary="third write, correct base")
    assert ok["status"] == "updated"
    assert _db_rows(temp_db, "SELECT id,summary FROM knowledge_nodes")[0]["summary"] == "third write, correct base"


def test_relation_contract_round_trip_and_validation(temp_db):
    source = kms.knowledge_add("/", "Relation Source", "source")
    target = kms.knowledge_add("/", "Relation Target", "target")
    created = kms.knowledge_relation_add(
        source["id"], target["path"], "supports", 0.9, 1.5,
        "Verified by test", "test", "shared", "codex", "gpt-test", "relation-session",
    )
    listed = kms.knowledge_relation_list(source["path"])
    assert listed["count"] == 1
    assert listed["relations"][0]["target_path"] == target["path"]
    assert listed["relations"][0]["creator"] == "codex"
    assert kms.knowledge_relation_update(created["id"], confidence=0.95, evidence="Updated proof")["status"] == "updated"
    assert _db_rows(temp_db, "SELECT confidence,evidence FROM knowledge_relations")[0] == {
        "confidence": 0.95, "evidence": "Updated proof"
    }
    with pytest.raises(ValueError, match="Invalid relation type"):
        kms.knowledge_relation_add(source["path"], target["path"], "looks_similar", evidence="none")
    with pytest.raises(ValueError, match="not found"):
        kms.knowledge_relation_add(source["path"], "/missing", "supports", evidence="none")
    assert kms.knowledge_relation_remove(created["id"])["status"] == "removed"
    assert _db_rows(temp_db, "SELECT * FROM knowledge_relations") == []


def test_legacy_migration_is_idempotent(tmp_path):
    path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(path))
    conn.executescript("""
        CREATE TABLE knowledge_nodes(id TEXT PRIMARY KEY,path TEXT UNIQUE,project_id TEXT,title TEXT);
        CREATE TABLE access_log(id INTEGER PRIMARY KEY,node_path TEXT,action TEXT,query TEXT,project_id TEXT,timestamp TEXT);
    """)
    conn.close()
    migrate_relations.migrate(path, backup=False)
    migrate_relations.migrate(path, backup=False)
    conn = sqlite3.connect(str(path))
    assert {"actor", "model", "session", "status"} <= {row[1] for row in conn.execute("PRAGMA table_info(access_log)")}
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='knowledge_relations'").fetchone()
    conn.close()


def test_tools_expose_client_independent_contract():
    for name in ("knowledge_relation_add", "knowledge_relation_list", "knowledge_relation_update", "knowledge_relation_remove"):
        assert name in kms.TOOLS
    for name in ("knowledge_read", "knowledge_add", "knowledge_update"):
        properties = kms.TOOLS[name]["inputSchema"]["properties"]
        assert {"actor", "model", "session"} <= properties.keys()


# --- _split_tagged / unmangle_lesson_fields (pure, no DB) -------------------

def test_split_tagged_plain_style():
    value = "Echte Beschreibung.</description><root_cause>Ursache X</root_cause><prevention>Vorbeugung Y</prevention>"
    parts = kms._split_tagged(value)
    assert parts["_head"] == "Echte Beschreibung."
    assert parts["root_cause"] == "Ursache X"
    assert parts["prevention"] == "Vorbeugung Y"


def test_split_tagged_antml_parameter_style():
    """Der reale Korruptionsstil: <parameter name="root_cause">...</parameter>."""
    value = ('Echte Beschreibung.</description>\n'
             '<parameter name="root_cause">Ursache X</parameter>\n'
             '<parameter name="prevention">Vorbeugung Y</parameter>')
    parts = kms._split_tagged(value)
    assert parts["_head"] == "Echte Beschreibung."
    assert parts["root_cause"] == "Ursache X"
    assert parts["prevention"] == "Vorbeugung Y"


def test_unmangle_moves_tagged_content_to_correct_fields():
    fields = {
        "type": "antipattern",
        "description": ('Echte Beschreibung.</description>\n'
                         '<root_cause>Ursache X</root_cause>\n'
                         '<prevention>Vorbeugung Y</prevention>'),
        "root_cause": "",
        "resolution": "",
        "prevention": "",
        "severity": "medium",
        "projects": [],
        "node_path": "",
    }
    fixed = kms.unmangle_lesson_fields(fields)
    assert fixed["description"] == "Echte Beschreibung."
    assert fixed["root_cause"] == "Ursache X"
    assert fixed["prevention"] == "Vorbeugung Y"
    # keine Tags mehr in irgendeinem Feld
    for col in ("description", "root_cause", "resolution", "prevention"):
        assert not kms._FIELD_TAG.search(fixed[col])


def test_unmangle_l6e48a9_pattern_tags_in_root_cause_not_description():
    """Realfall L-6e48a9: description ist sauber, aber root_cause traegt am
    Stueck auch resolution/prevention/projects/node_path in Tags."""
    fields = {
        "type": "insight",
        "description": "Saubere Beschreibung ohne Tags.",
        "root_cause": ('Echte Ursache.</root_cause>\n'
                        '<resolution>Echte Loesung.</resolution>\n'
                        '<prevention>Echte Vorbeugung.</prevention>\n'
                        '<projects>["fahrtenbuch"]</projects>\n'
                        '<node_path>/apps/fahrtenbuch</node_path>\n'
                        '</invoke>\n'),
        "resolution": "",
        "prevention": "",
        "severity": "medium",
        "projects": [],
        "node_path": "",
    }
    fixed = kms.unmangle_lesson_fields(fields)
    assert fixed["description"] == "Saubere Beschreibung ohne Tags."
    assert fixed["root_cause"] == "Echte Ursache."
    assert fixed["resolution"] == "Echte Loesung."
    assert fixed["prevention"] == "Echte Vorbeugung."
    assert fixed["projects"] == ["fahrtenbuch"]
    assert fixed["node_path"] == "/apps/fahrtenbuch"


def test_unmangle_does_not_overwrite_a_real_existing_value():
    """Ein bereits befuellter Zielfeld-Wert gewinnt immer gegen den aus Tags
    extrahierten (Regel aus unmangle_lesson_fields Docstring)."""
    fields = {
        "type": "insight",
        "description": 'Beschreibung.</description><root_cause>Aus Tag extrahiert</root_cause>',
        "root_cause": "Bereits echt gesetzter Wert",
        "resolution": "",
        "prevention": "",
        "severity": "medium",
        "projects": [],
        "node_path": "",
    }
    fixed = kms.unmangle_lesson_fields(fields)
    assert fixed["root_cause"] == "Bereits echt gesetzter Wert"


TEXT_FIELDS = ("description", "root_cause", "resolution", "prevention", "severity", "node_path")


def _useful_len(fields: dict) -> int:
    """Summe aller Nutztext-Zeichen ueber die Text-Spalten (projects zaehlt als JSON)."""
    total = sum(len((fields.get(c) or "")) for c in TEXT_FIELDS)
    projects = fields.get("projects") or []
    total += len(json.dumps(projects)) if isinstance(projects, list) else len(str(projects))
    return total


def test_unmangle_never_loses_a_character_even_when_target_is_taken():
    """Regressionstest fuer den echten Fund L-f27042/Nachtrag: Ist das Zielfeld
    schon belegt, darf der Anteil aus dem Tag nicht verworfen werden — er muss
    im Ursprungsfeld erhalten bleiben. Kriterium: Nutztext-Summe nach der
    Reparatur ist nie kleiner als vorher (abzueglich der entfernten Marker
    selbst, hier exakt bekannt: 3 Tag-Paare, ohne Trenn-Leerraum dazwischen,
    damit die Zeichenrechnung eindeutig ist). Bewusst OHNE severity-Feld, weil
    dort ein separater, gewollter Sonderfall gilt (siehe naechster Test)."""
    tag_chars = (len("</description>") + len("<root_cause>") + len("</root_cause>")
                 + len("<resolution>") + len("</resolution>"))
    fields = {
        "type": "insight",
        "description": ('Beschreibung.</description>'
                         '<root_cause>Aus dem Tag extrahierte Ursache, die erhalten bleiben muss.</root_cause>'
                         '<resolution>Aus dem Tag extrahierte Loesung, die ebenfalls erhalten bleiben muss.</resolution>'),
        "root_cause": "Bereits echt gesetzter Wert, der nicht ueberschrieben werden darf",
        "resolution": "Ebenfalls schon echt gesetzt, darf auch nicht ueberschrieben werden",
        "prevention": "",
        "severity": "medium",
        "projects": [],
        "node_path": "",
    }
    before = _useful_len(fields)
    fixed = kms.unmangle_lesson_fields(fields)
    # die real gesetzten Werte gewinnen weiterhin
    assert fixed["root_cause"] == "Bereits echt gesetzter Wert, der nicht ueberschrieben werden darf"
    assert fixed["resolution"] == "Ebenfalls schon echt gesetzt, darf auch nicht ueberschrieben werden"
    after = _useful_len(fixed)
    assert after >= before - tag_chars, (
        f"Zeichen verloren: vorher={before}, nachher={after}, erwartete Reduktion hoechstens {tag_chars}"
    )
    # die abgewiesenen Anteile aus den Tags muessen irgendwo im description-Feld
    # (dem Ursprungsfeld) auftauchen, nicht spurlos verschwunden sein
    assert "erhalten bleiben muss" in fixed["description"]
    assert "ebenfalls erhalten bleiben muss" in fixed["description"]


def test_unmangle_severity_default_is_overridden_by_extracted_value():
    """Sonderfall severity: der Schema-Default "medium" ist von einem nie
    gesetzten Wert nicht unterscheidbar. Ein aus dem Tag extrahierter
    gueltiger Enum-Wert gewinnt deshalb gegen den Default — das ist eine
    gewollte Korrektur, kein Verlust (die zwei echten Faelle L-a7043b und
    L-47e586 hatten genau dieses Muster: description enthielt `<severity>high
    </severity>`, die Spalte selbst stand noch auf dem ungenutzten Default)."""
    fields = {
        "type": "insight",
        "description": 'Beschreibung.</description>\n<severity>high</severity>',
        "root_cause": "",
        "resolution": "",
        "prevention": "",
        "severity": "medium",
        "projects": [],
        "node_path": "",
    }
    fixed = kms.unmangle_lesson_fields(fields)
    assert fixed["severity"] == "high"
    assert fixed["description"] == "Beschreibung."


def test_quoted_marker_in_prose_is_not_treated_as_field_boundary():
    """Realfall L-f27042: eine Lesson, die den Verstuemmelungs-Bug selbst
    beschreibt, zitiert Feldmarker mitten im Satz. Diese duerfen NICHT als
    Feldgrenze gelesen werden — sonst wird der Fliesstext an der Zitatstelle
    abgeschnitten (genau das ist L-f27042 vorher passiert)."""
    description = ('Zwei Stile traten auf: der eine (schliessendes </description>-Tag, '
                    'dann oeffnendes <root_cause>-Tag) und der Tool-Call-Stil mit '
                    '<parameter name="root_cause">-Attribut, direkt im Satz zitiert. '
                    'Der Rest dieses Satzes muss vollstaendig erhalten bleiben.')
    fields = {
        "type": "insight",
        "description": description,
        "root_cause": "",
        "resolution": "",
        "prevention": "",
        "severity": "medium",
        "projects": [],
        "node_path": "",
    }
    fixed = kms.unmangle_lesson_fields(fields)
    assert fixed["description"] == description
    assert fixed["root_cause"] == ""


def test_genuine_corruption_at_line_start_still_splits():
    """Positivprobe zu obigem Test: dieselben Tags, aber an echter Zeilenkante
    (jeweils allein auf ihrer Zeile) muessen weiterhin zerlegt werden."""
    fields = {
        "type": "insight",
        "description": ('Echter Text.</description>\n'
                         '<parameter name="root_cause">Echte Ursache aus echter Verstuemmelung.</parameter>'),
        "root_cause": "",
        "resolution": "",
        "prevention": "",
        "severity": "medium",
        "projects": [],
        "node_path": "",
    }
    fixed = kms.unmangle_lesson_fields(fields)
    assert fixed["description"] == "Echter Text."
    assert fixed["root_cause"] == "Echte Ursache aus echter Verstuemmelung."


# --- lesson_record end-to-end (real DB round-trip via temp_db) -------------

def test_lesson_record_unmangles_on_write(temp_db):
    description = ('Kaputt eingegebene Beschreibung.</description>\n'
                    '<root_cause>Wahre Ursache.</root_cause>\n'
                    '<prevention>Wahre Vorbeugung.</prevention>')
    result = kms.lesson_record("antipattern", description)
    assert result["status"] == "recorded"

    row = _lesson_row(temp_db, result["id"])
    assert row["description"] == "Kaputt eingegebene Beschreibung."
    assert row["root_cause"] == "Wahre Ursache."
    assert row["prevention"] == "Wahre Vorbeugung."
    assert not kms._FIELD_TAG.search(row["description"])


# --- lesson_update -----------------------------------------------------------

def test_lesson_update_changes_only_given_fields(temp_db):
    created = kms.lesson_record("insight", "Original-Beschreibung", root_cause="Original-Ursache")
    lesson_id = created["id"]

    result = kms.lesson_update(lesson_id, prevention="Neue Vorbeugung")
    assert result["status"] == "updated"

    row = _lesson_row(temp_db, lesson_id)
    assert row["description"] == "Original-Beschreibung"     # unangetastet
    assert row["root_cause"] == "Original-Ursache"            # unangetastet
    assert row["prevention"] == "Neue Vorbeugung"              # geaendert


def test_lesson_update_unmangles_given_field(temp_db):
    created = kms.lesson_record("insight", "Original")
    lesson_id = created["id"]

    mangled_description = 'Korrigierte Beschreibung.</description><root_cause>Nachtraeglich korrigierte Ursache</root_cause>'
    result = kms.lesson_update(lesson_id, description=mangled_description)
    assert result["status"] == "updated"

    row = _lesson_row(temp_db, lesson_id)
    assert row["description"] == "Korrigierte Beschreibung."
    assert row["root_cause"] == "Nachtraeglich korrigierte Ursache"


def test_lesson_update_delete(temp_db):
    created = kms.lesson_record("insight", "Wird geloescht")
    lesson_id = created["id"]

    result = kms.lesson_update(lesson_id, delete=True)
    assert result == {"id": lesson_id, "status": "deleted"}
    assert _lesson_row(temp_db, lesson_id) is None


def test_lesson_update_unknown_id_returns_error(temp_db):
    result = kms.lesson_update("L-nonexistent")
    assert "error" in result


def test_lesson_update_no_fields_reports_unchanged(temp_db):
    created = kms.lesson_record("insight", "Bleibt gleich")
    result = kms.lesson_update(created["id"])
    assert result["status"] == "unchanged"


# --- lesson_record: same_as-Wiederholungszaehler ----------------------------

def test_lesson_record_without_same_as_creates_new_entry_unchanged(temp_db):
    """Altverhalten unberuehrt: ohne same_as entsteht ein neuer Eintrag mit occurrences=1."""
    result = kms.lesson_record("antipattern", "Erstmaliger Fehler XYZ, ganz eigenstaendig.")
    assert result["status"] == "recorded"
    assert result["occurrences"] == 1
    row = _lesson_row(temp_db, result["id"])
    assert row["occurrences"] == 1


def test_lesson_record_with_same_as_increments_vorgaenger_no_second_row(temp_db):
    first = kms.lesson_record("antipattern", "Reuse-Waechter reserviert Dateien aller Agenten ueber TABU-Liste.")
    lesson_id = first["id"]

    result = kms.lesson_record(
        "antipattern",
        "Erneut aufgetreten: derselbe Reuse-Waechter-Konflikt, diesmal bei fuenf Agenten.",
        same_as=lesson_id,
    )
    assert result["status"] == "incremented"
    assert result["id"] == lesson_id
    assert result["occurrences"] == 2

    row = _lesson_row(temp_db, lesson_id)
    assert row["occurrences"] == 2
    # kein zweiter Eintrag entstanden
    conn = sqlite3.connect(str(temp_db))
    count = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    conn.close()
    assert count == 1
    # neuer Text im Vorgaenger auffindbar
    assert "fuenf Agenten" in row["description"]
    assert "Reuse-Waechter reserviert Dateien" in row["description"]  # Ursprungstext bleibt


def test_lesson_record_same_as_third_occurrence_escalates(temp_db):
    first = kms.lesson_record("antipattern", "Basisfehler fuer Eskalationstest.")
    lesson_id = first["id"]
    kms.lesson_record("antipattern", "Wiederholung Nr. 1 des Eskalationstests.", same_as=lesson_id)
    result = kms.lesson_record("antipattern", "Wiederholung Nr. 2 des Eskalationstests.", same_as=lesson_id)

    assert result["occurrences"] == 3
    assert result["escalated"] is True
    row = _lesson_row(temp_db, lesson_id)
    assert row["status"] == "escalated_to_rule"


def test_lesson_record_same_as_caps_repetition_paragraphs(temp_db):
    first = kms.lesson_record("antipattern", "Basisfehler fuer Deckelungstest.")
    lesson_id = first["id"]
    for i in range(1, 9):  # 8 Wiederholungen, Deckel liegt bei 5
        kms.lesson_record("antipattern", f"Wiederholungsmarker-{i}", same_as=lesson_id)

    row = _lesson_row(temp_db, lesson_id)
    assert row["occurrences"] == 9
    # nur die 5 juengsten Wiederholungen stehen noch drin
    for i in range(1, 4):
        assert f"Wiederholungsmarker-{i}" not in row["description"]
    for i in range(4, 9):
        assert f"Wiederholungsmarker-{i}" in row["description"]
    # Ursprungstext bleibt trotz Deckelung erhalten
    assert "Basisfehler fuer Deckelungstest." in row["description"]


def test_lesson_record_same_as_unknown_id_errors_no_silent_new_entry(temp_db):
    result = kms.lesson_record("antipattern", "Verweist auf nichts.", same_as="L-nichtvorhanden")
    assert "error" in result
    conn = sqlite3.connect(str(temp_db))
    count = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    conn.close()
    assert count == 0  # kein stiller Fallback-Eintrag


def test_lesson_record_similarity_hint_found_without_merging(temp_db):
    """Zwei bewusst aehnlich formulierte Lessons: der Hinweis erscheint, aber
    es entstehen weiterhin zwei getrennte Zeilen (kein automatisches Merge)."""
    a = ("Reuse-Waechter reservierte durch die TABU-Liste des ersten erfolgreichen "
         "Spawns die Dateien aller uebrigen Agenten; mehrere Spawns wurden abgewiesen.")
    b = ("Reuse-Waechter reserviert durch TABU-Listen die Dateien aller anderen Agenten, "
         "mehrere parallele Spawns wurden dadurch abgewiesen.")
    first = kms.lesson_record("antipattern", a)

    result = kms.lesson_record("antipattern", b)
    assert result["status"] == "recorded"
    assert "similar_lesson_hint" in result
    hint = result["similar_lesson_hint"]
    assert hint["id"] == first["id"]

    conn = sqlite3.connect(str(temp_db))
    count = conn.execute("SELECT COUNT(*) FROM lessons_learned").fetchone()[0]
    conn.close()
    assert count == 2  # kein Merge


def test_gegenprobe_l9f5e60_l_affae1_similarity_score():
    """Echte Gegenprobe am Bestand, nur lesend: haette das Aehnlichkeitsmass die
    beiden real doppelt erfassten Lessons L-9f5e60/L-affae1 als Kandidaten erkannt?"""
    conn = kms.get_db()
    try:
        rows = {
            r["id"]: r["description"]
            for r in conn.execute(
                "SELECT id, description FROM lessons_learned WHERE id IN ('L-9f5e60','L-affae1')"
            )
        }
    finally:
        conn.close()
    if len(rows) < 2:
        pytest.skip("L-9f5e60/L-affae1 nicht (mehr) im Bestand")
    a, b = rows["L-9f5e60"], rows["L-affae1"]
    ta, tb = kms._tokenize(a), kms._tokenize(b)
    score = len(ta & tb) / len(ta | tb)
    print(f"\nGegenprobe L-9f5e60/L-affae1: Jaccard-Score = {score:.3f} (Schwelle = {kms.SIMILARITY_THRESHOLD})")
    assert score >= kms.SIMILARITY_THRESHOLD


# --- unmangle_knowledge_fields / knowledge_add-Absicherung ------------------
# Gegenstueck zu unmangle_lesson_fields, fuer knowledge_add statt lesson_record.
# Realfall (2026-08-01): 18 Knoten hatten content/tags/source als
# `<content>...</content>`/`<parameter name="tags">...</parameter>`-Block im
# summary-Wert stehen (siehe migrate_unmangle_knowledge.py).

def test_unmangle_knowledge_moves_content_tags_source_out_of_summary():
    fields = {
        "title": "Titel",
        "summary": ('Echte Zusammenfassung.</summary>\n'
                     '<tags>["a", "b"]</tags>\n'
                     '<source>Quelle X</source>\n'
                     '<content>Voller Text Y</content>'),
        "content": "",
        "tags": [],
        "source": "",
    }
    fixed = kms.unmangle_knowledge_fields(fields)
    assert fixed["summary"] == "Echte Zusammenfassung."
    assert fixed["content"] == "Voller Text Y"
    assert fixed["tags"] == ["a", "b"]
    assert fixed["source"] == "Quelle X"
    assert not kms._KNOWLEDGE_FIELD_TAG.search(fixed["summary"])


def test_unmangle_knowledge_antml_parameter_style():
    """Realer Korruptionsstil bei efa1f597: <parameter name="content">...</parameter>
    gefolgt von tags/source, abgeschlossen mit </invoke>-Rauschen."""
    fields = {
        "title": "Titel",
        "summary": ('Echte Zusammenfassung.</summary>\n'
                     '<parameter name="content">Voller Text</parameter>\n'
                     '<parameter name="tags">["x"]</parameter>\n'
                     '<parameter name="source">Quelle</parameter>\n'
                     '</invoke>\n'),
        "content": "",
        "tags": [],
        "source": "",
    }
    fixed = kms.unmangle_knowledge_fields(fields)
    assert fixed["summary"] == "Echte Zusammenfassung."
    assert fixed["content"] == "Voller Text"
    assert fixed["tags"] == ["x"]
    assert fixed["source"] == "Quelle"


def test_unmangle_knowledge_does_not_overwrite_existing_content():
    """Zielfeld schon belegt -> Text bleibt im Ursprungsfeld erhalten (kein
    Datenverlust, aber auch kein stilles Ueberschreiben eines echten Werts)."""
    fields = {
        "title": "Titel",
        "summary": ('Kurzfassung.</summary>\n<content>Duplikat</content>'),
        "content": "Der ECHTE, bereits vorhandene Volltext.",
        "tags": [],
        "source": "",
    }
    fixed = kms.unmangle_knowledge_fields(fields)
    assert fixed["content"] == "Der ECHTE, bereits vorhandene Volltext."
    assert "Duplikat" in fixed["summary"]  # nicht verloren, nur nicht verschoben


def test_knowledge_add_unmangles_on_write(temp_db):
    result = kms.knowledge_add(
        parent_path="/test",
        title="Testknoten",
        summary=('Echte Zusammenfassung.</summary>\n'
                  '<tags>["a"]</tags>\n<content>Volltext</content>'),
        content="",
        tags=[],
        neuer_ast=True,  # /test existiert in dieser Fixture nicht (P1: unbekannte Elternpfade werden sonst abgelehnt)
    )
    assert result["status"] == "created"
    conn = sqlite3.connect(str(temp_db))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM knowledge_nodes WHERE id = ?", (result["id"],)).fetchone()
    conn.close()
    assert row["summary"] == "Echte Zusammenfassung."
    assert row["content"] == "Volltext"
    assert json.loads(row["tags"]) == ["a"]
