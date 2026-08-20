"""Ein vergebener Normrang muss zurueckgenommen werden koennen.

DER BEFUND (2026-08-21): Zehn Knoten trugen Rang 1 -- die Stufe der globalen
Arbeitsanweisung --, obwohl sie projektgebunden sind: Rechtslage fuer
buckeberg, Namenskonventionen fuer openlehr, zwei Einzelfreigaben. Rang 1
gewinnt bei Widerspruch gegen jede andere Norm; eine Einzelfreigabe auf
dieser Stufe entwertet die ganze Rangfolge.

Beim Zurueckstufen zeigte sich: ES GEHT NICHT.
* `knowledge_update` weist `norm_entscheidung=keine_norm` zurueck, solange
  ein Rang gesetzt ist ("widerspruechlich") -- richtig, aber der Rang laesst
  sich nicht im selben Zug leeren.
* `kern/normkraft.py` kann nur AUSSER KRAFT setzen (`gilt_bis`). Das waere
  hier falsch: Die Rechtslage GILT weiter, sie ist nur keine Direktive.

Damit ist jede Fehleinstufung dauerhaft. Das ist die eigentliche Luecke --
nicht die zehn Knoten.

WARUM NICHT PER SQL AM TRIGGER VORBEI: Die Schranke ist richtig. Sie
verhindert genau den Zustand "Fakt mit Rang". Wer sie umgeht, statt das Verb
zu bauen, das ihr entspricht, hinterlaesst einen Bestand, den die Schranke
selbst nicht mehr erklaeren kann.
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent),
                str(Path(__file__).resolve().parent.parent / "kern"),
                str(Path(__file__).resolve().parent.parent / "haken")]


def test_rang_laesst_sich_zurueckgeben(tmp_path, monkeypatch):
    """DIE PROBE: Ein Knoten mit Rang 1 wird zu einem Fakt ohne Rang."""
    import sqlite3, importlib
    db = tmp_path / "p.db"
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", str(db))
    c = sqlite3.connect(db)
    c.executescript((Path(__file__).resolve().parent.parent / "schema.sql").read_text())
    c.execute("""insert into knowledge_nodes
                 (id, path, parent_path, title, summary, source, freigabe, norm_rang,
                  gilt_ab, norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
                  norm_entschieden_grund, created_at, updated_at)
                 values ('probe1','/p',NULL,'Probe','s','Probe','intern',1,
                         '2026-01-01','norm_unbefristet','betreiber',datetime('now'),
                         'Probe',datetime('now'),datetime('now'))""")
    c.commit(); c.close()

    import knowledge_mcp_server as kms
    importlib.reload(kms)
    aus = kms.knowledge_update(
        node_id="probe1", norm_entscheidung="keine_norm",
        norm_rang=0,                       # 0 = Rang zurueckgeben
        norm_entschieden_grund="Probe: projektgebunden, keine globale Direktive")
    assert "error" not in str(aus).lower(), aus

    c = sqlite3.connect(db)
    rang, ent = c.execute(
        "select norm_rang, norm_entscheidung from knowledge_nodes where id='probe1'").fetchone()
    c.close()
    assert rang is None, f"Rang nicht zurueckgegeben: {rang}"
    assert ent == "keine_norm"


def test_rang_null_ohne_keine_norm_bleibt_abgewiesen(tmp_path, monkeypatch):
    """NEGATIVFALL: Die Schranke darf nicht insgesamt fallen. Wer den Rang
    zurueckgibt, muss auch sagen, dass es keine Norm mehr ist -- sonst
    entstuende eine Norm ohne Rang, und genau diese Mehrdeutigkeit soll das
    Feld beseitigen."""
    import sqlite3, importlib
    db = tmp_path / "q.db"
    monkeypatch.setenv("BEGOD_KNOWLEDGE_DB", str(db))
    c = sqlite3.connect(db)
    c.executescript((Path(__file__).resolve().parent.parent / "schema.sql").read_text())
    c.execute("""insert into knowledge_nodes
                 (id, path, parent_path, title, summary, source, freigabe, norm_rang,
                  gilt_ab, norm_entscheidung, norm_entschieden_von, norm_entschieden_am,
                  norm_entschieden_grund, created_at, updated_at)
                 values ('probe2','/q',NULL,'Probe','s','Probe','intern',1,
                         '2026-01-01','norm_unbefristet','betreiber',datetime('now'),
                         'Probe',datetime('now'),datetime('now'))""")
    c.commit(); c.close()
    import knowledge_mcp_server as kms
    importlib.reload(kms)
    aus = kms.knowledge_update(node_id="probe2", norm_rang=0)
    assert "error" in str(aus).lower(), "Rang 0 ohne keine_norm muss abgewiesen werden"
