"""Tests fuer wirkung.py -- Wirkungssignal des passiven Recall-Abrufs
(Auftrag 2026-08-07, Plan: docs/PLAN_SELBSTLERNEN_2026-08-07.md Schritt 1).

Drei Zustaende (genutzt/ignoriert/widerlegt), je ein eigener Fall, plus
Negativfall (ignoriert darf nicht stillschweigend fehlen) und Grenzfall
(Mehrfacheinspielung derselben Sitzung zaehlt einmal)."""
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

import json
import sqlite3
import sys
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import wirkung  # type: ignore  # noqa: E402


def _db(tmp_path):
    db_path = tmp_path / "wirkung_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.close()
    return db_path


def _node(db_path, node_id, path):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, title, summary, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) VALUES (?, ?, 't', 's', 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')",
        (node_id, path),
    )
    conn.commit()
    conn.close()


def _lesson(db_path, lesson_id):
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description, occurrences) VALUES (?, 'insight', 'd', 1)",
        (lesson_id,),
    )
    conn.commit()
    conn.close()


def _access(db_path, **kw):
    conn = sqlite3.connect(str(db_path))
    cols = ", ".join(kw.keys())
    qs = ", ".join("?" for _ in kw)
    conn.execute(f"INSERT INTO access_log ({cols}) VALUES ({qs})", list(kw.values()))
    conn.commit()
    conn.close()


def _recall_line(**kw) -> str:
    base = {"ts": "2026-08-07T10:00:00+00:00", "session": "s1", "nodes": [], "lessons": []}
    base.update(kw)
    return json.dumps(base) + "\n"


def test_genutzt_node_wird_nach_recall_gelesen(tmp_path):
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/gelesen")
    _access(db_path, node_path="/x/gelesen", action="read", status="completed",
            session="s1", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/gelesen"]), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["genutzt"] == 1
    assert r["ignoriert"] == 0
    assert r["widerlegt"] == 0


def test_ignoriert_node_bleibt_unberuehrt_und_erscheint_nicht_still(tmp_path):
    """Negativfall: eine eingespielte Node ohne jede Beruehrung MUSS als
    'ignoriert' auftauchen, nicht als fehlender Datensatz."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/unberuehrt")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/unberuehrt"]), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["ignoriert"] == 1
    assert r["genutzt"] == 0
    assert r["widerlegt"] == 0


def test_widerlegt_node_in_gleicher_sitzung_zurueckgezogen(tmp_path):
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/zurueckgezogen")
    _access(db_path, node_path="/x/zurueckgezogen", action="zurueckziehen", status="completed",
            session="s1", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/zurueckgezogen"]), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["widerlegt"] == 1
    assert r["genutzt"] == 0
    assert r["ignoriert"] == 0


def test_widerlegt_hat_vorrang_vor_gelesen(tmp_path):
    """Wurde ein Knoten sowohl gelesen als auch zurueckgezogen, zaehlt
    widerlegt -- die staerkere Aussage gewinnt, kein doppeltes Zaehlen."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/beides")
    _access(db_path, node_path="/x/beides", action="read", status="completed",
            session="s1", timestamp="2026-08-07T10:00:03Z")
    _access(db_path, node_path="/x/beides", action="zurueckziehen", status="completed",
            session="s1", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/beides"]), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["widerlegt"] == 1
    assert r["genutzt"] == 0


def test_lesung_vor_dem_recall_zaehlt_nicht(tmp_path):
    """Ein Lesevorgang VOR der Einspielung kann nicht ihre Wirkung sein."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/vorher")
    _access(db_path, node_path="/x/vorher", action="read", status="completed",
            session="s1", timestamp="2026-08-07T09:59:00Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/vorher"]), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["ignoriert"] == 1
    assert r["genutzt"] == 0


def test_genutzt_node_ueber_neue_verknuepfung(tmp_path):
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/quelle")
    _node(db_path, "n2", "/x/ziel")
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO knowledge_relations (id, source_path, target_path, relation_type, session, created_at) "
        "VALUES ('r1', '/x/quelle', '/x/ziel', 'siehe_auch', 's1', '2026-08-07T10:00:05Z')"
    )
    conn.commit()
    conn.close()
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/ziel"]), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["genutzt"] == 1


def test_genutzt_lesson_wird_nach_recall_geaendert(tmp_path):
    db_path = _db(tmp_path)
    _lesson(db_path, "L-1")
    _access(db_path, node_path=None, action="lesson_update", status="completed",
            session="s1", query="L-1", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(lessons=["L-1"]), encoding="utf-8")

    r = wirkung.report("lesson", log, db_path)
    assert r["genutzt"] == 1


def test_widerlegt_lesson_geloescht(tmp_path):
    db_path = _db(tmp_path)
    _lesson(db_path, "L-2")
    _access(db_path, node_path=None, action="lesson_delete", status="completed",
            session="s1", query="L-2", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(lessons=["L-2"]), encoding="utf-8")

    r = wirkung.report("lesson", log, db_path)
    assert r["widerlegt"] == 1


def test_mehrfacheinspielung_gleicher_sitzung_zaehlt_einmal(tmp_path):
    """Grenzfall (Auftrag): derselbe Knoten in einer Sitzung mehrfach
    eingespielt -- zaehlt einmal, nicht mehrfach."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/mehrfach")
    _access(db_path, node_path="/x/mehrfach", action="read", status="completed",
            session="s1", timestamp="2026-08-07T10:10:00Z")
    log = tmp_path / "recall_log.jsonl"
    with open(log, "w", encoding="utf-8") as f:
        f.write(_recall_line(nodes=["/x/mehrfach"], ts="2026-08-07T10:00:00+00:00"))
        f.write(_recall_line(nodes=["/x/mehrfach"], ts="2026-08-07T10:05:00+00:00"))

    r = wirkung.report("node", log, db_path)
    assert r["genutzt"] == 1  # nicht 2


# --- Auftrag 2026-08-07 (Nachtrag): Session-Formatfehler --------------------
# recall_log.jsonl schreibt IMMER die 8-stellig gekuerzte Form (siehe
# knowledge_recall_hook.py::log_recall). access_log/knowledge_relations
# trugen fuer Altzeilen (vor der Kuerzung von knowledge_mcp_server.py's
# _PROZESS_SITZUNG) die volle 36-stellige UUID -- ein exakter
# Gleichheitstest zwischen 8 und 36 Zeichen war nie wahr, 'genutzt' also
# strukturell unerreichbar. Praefixvergleich ohne Migration der Altzeilen.

def test_altzeile_mit_voller_uuid_wird_trotz_gekuerzter_recall_session_zugeordnet(tmp_path):
    """ROT VOR GRUEN: recall_log traegt die gekuerzte Form ('abcdef12'),
    access_log (Altzeile, vor der Kuerzung) die volle UUID -- muss trotzdem
    als 'genutzt' erkannt werden."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/altzeile")
    _access(db_path, node_path="/x/altzeile", action="read", status="completed",
            session="abcdef12-2ceb-4433-9a11-000000000000", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/altzeile"], session="abcdef12"), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["genutzt"] == 1, r
    assert r["ignoriert"] == 0, r


def test_praefixvergleich_zaehlt_keine_fremde_sitzung_mit(tmp_path):
    """NEGATIVFALL: Einspielung in Sitzung X, gelesen in Sitzung Y (anderes
    Praefix) -> NICHT genutzt. Sonst wuerde der Praefixvergleich fremde
    Sitzungen mitzaehlen."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/fremde-sitzung")
    _access(db_path, node_path="/x/fremde-sitzung", action="read", status="completed",
            session="fedcba98-lang-anders", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/fremde-sitzung"], session="abcdef12"), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["genutzt"] == 0, r
    assert r["ignoriert"] == 1, r


def test_widerlegt_bleibt_wirksam_bei_voller_uuid_altzeile(tmp_path):
    """NEGATIVFALL-Gegenprobe: 'widerlegt' ist ein eindeutiger Vorgang und
    muss auch bei einer Altzeile mit voller UUID weiterhin greifen."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/widerlegt-alt")
    _access(db_path, node_path="/x/widerlegt-alt", action="zurueckziehen", status="completed",
            session="abcdef12-2ceb-4433-9a11-000000000000", timestamp="2026-08-07T10:00:05Z")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/widerlegt-alt"], session="abcdef12"), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["widerlegt"] == 1, r


def test_ohne_sitzung_nicht_auswertbar_aber_gezaehlt(tmp_path):
    """Recall-Zeile ohne Sitzung darf nicht als 'ignoriert' verbucht werden
    (waere geraten) -- sie fehlt auch nicht still, sondern zaehlt eigens."""
    db_path = _db(tmp_path)
    _node(db_path, "n1", "/x/ohne-sitzung")
    log = tmp_path / "recall_log.jsonl"
    log.write_text(_recall_line(nodes=["/x/ohne-sitzung"], session=None), encoding="utf-8")

    r = wirkung.report("node", log, db_path)
    assert r["genutzt"] == 0 and r["ignoriert"] == 0 and r["widerlegt"] == 0
    assert r["unauswertbar"] == 1
