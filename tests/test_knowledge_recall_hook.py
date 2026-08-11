#!/usr/bin/env python3
"""Selbsttest fuer das Zug-Protokoll in knowledge_recall_hook.py
(log_recall/report), `python3 hub/scripts/test_knowledge_recall_hook.py`.

Auftrag: der Recall-Hook zieht seit Monaten Wissen, aber niemand kann sagen,
welche Lehre je gelesen wurde. Dieser Test belegt: Treffer -> Protokollzeile
(Zeitpunkt + Kennung, KEIN Prompt-Text), kein Treffer -> leere Zeile, ein
unschreibbares Protokollziel darf den Abruf selbst NIE stoppen (wichtigster
Fall), die Auswertung liefert gegen ein synthetisches Protokoll plausible
Zahlen, und die Groessen-Bremse (Rotation) greift.

Rot-Probe (im Auftrag verlangt):
  - log_recall()-Aufruf aus main() entfernen -> HIT wird rot.
  - try/except in log_recall() entfernen, Ziel unschreibbar machen -> genau
    das ist KAPUTTES-ZIEL; ohne die Fehlerbehandlung fliegt main() dort.

Alles gegen tempfile.TemporaryDirectory() -- nie gegen shared-knowledge/
brainlehr.db oder ein echtes recall_log.jsonl.
"""

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
import importlib.util
import io
import json
import pathlib
import sqlite3
import sys
import tempfile

# Die Automatik liegt seit dem 2026-08-08 in brainlehr/haken, nicht in
# hub/scripts — der Test folgt ihr.
WURZEL = pathlib.Path(__file__).resolve().parent.parent
HOOK_PATH = WURZEL / "haken" / "knowledge_recall_hook.py"

_spec = importlib.util.spec_from_file_location("knowledge_recall_hook", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

# Schema-Ausschnitt wie shared-knowledge/brainlehr.db (siehe .schema dort) --
# nur die Spalten, die query()/report() tatsaechlich lesen.
SCHEMA = """
CREATE TABLE knowledge_nodes (
    id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, parent_path TEXT,
    project_id TEXT NOT NULL DEFAULT 'shared', title TEXT NOT NULL,
    summary TEXT NOT NULL, content TEXT, level INTEGER NOT NULL DEFAULT 0,
    tags TEXT DEFAULT '[]', source TEXT, confidence REAL DEFAULT 0.8,
    access_count INTEGER DEFAULT 0, zurueckgezogen INTEGER NOT NULL DEFAULT 0,
    gattung TEXT NOT NULL DEFAULT 'arbeitsbestand',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00','now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00','now','localtime')),
    gilt_ab TEXT, gilt_bis TEXT
);
CREATE VIRTUAL TABLE knowledge_fts USING fts5(
    title, summary, content, content='knowledge_nodes', content_rowid='rowid'
);
CREATE TRIGGER knowledge_ai AFTER INSERT ON knowledge_nodes BEGIN
    INSERT INTO knowledge_fts(rowid, title, summary, content)
    VALUES (new.rowid, new.title, new.summary, new.content);
END;
CREATE TABLE lessons_learned (
    id TEXT PRIMARY KEY, node_path TEXT, type TEXT NOT NULL,
    severity TEXT DEFAULT 'medium', description TEXT NOT NULL,
    root_cause TEXT, resolution TEXT, prevention TEXT,
    occurrences INTEGER DEFAULT 1, projects TEXT DEFAULT '[]',
    session TEXT,
    status TEXT DEFAULT 'active',
    first_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00','now','localtime')),
    last_seen TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S+01:00','now','localtime')),
    auto_rule_generated INTEGER DEFAULT 0
);
CREATE VIRTUAL TABLE lessons_fts USING fts5(
    description, root_cause, prevention, content='lessons_learned', content_rowid='rowid'
);
CREATE TRIGGER lessons_ai AFTER INSERT ON lessons_learned BEGIN
    INSERT INTO lessons_fts(rowid, description, root_cause, prevention)
    VALUES (new.rowid, new.description, new.root_cause, new.prevention);
END;
"""

TREFFER_PROMPT = "fahrtenbuch trip repository hash kette gobd verletzt"


def _build_db(path: pathlib.Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO knowledge_nodes (id,path,title,summary) VALUES (?,?,?,?)",
        ("n1", "/test/gobd", "GoBD Hashkette",
         "Fahrtenbuch trip repository haelt Hashkette gegen GoBD-Verletzung"),
    )
    conn.execute(
        "INSERT INTO lessons_learned (id,type,description,root_cause,prevention) VALUES (?,?,?,?,?)",
        ("L-1", "error",
         "fahrtenbuch trip repository hash kette bricht bei reconnect",
         "Sitzung verliert Bindung", "Reconnect muss Bindung neu pruefen"),
    )
    conn.commit()
    conn.close()


def _run_main_with_prompt(prompt: str) -> str:
    """Ruft hook.main() wie der echte Hook auf (Prompt-JSON auf stdin) und
    gibt zurueck, was auf stdout ging."""
    stdin_bak, stdout_bak = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(json.dumps({"prompt": prompt}))
    sys.stdout = out = io.StringIO()
    try:
        hook.main()
    finally:
        sys.stdin, sys.stdout = stdin_bak, stdout_bak
    return out.getvalue()


def treffer_erzeugt_protokollzeile() -> str:
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db)
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        _run_main_with_prompt(TREFFER_PROMPT)
        assert log.exists(), "kein Protokoll bei echtem Treffer geschrieben"
        zeilen = log.read_text(encoding="utf-8").strip().splitlines()
        assert len(zeilen) == 1, zeilen
        entry = json.loads(zeilen[0])
        assert entry["nodes"] or entry["lessons"], entry
        # Herkunft (cwd/worktree/session) seit 2026-08-06 immer dabei, 'prompt'
        # seit Herkunftsmodus-Vorgabe 'voll' (kein Schluessel in knowledge_config
        # gesetzt) ebenfalls. node_ids/agent_id/agent_type/kennung seit
        # 2026-08-08 additiv dazu (Auftrag: WER gefragt hat + unveraenderliche
        # Node-Kennung).
        assert set(entry) == {"ts", "nodes", "node_ids", "lessons", "cwd", "worktree",
                               "session", "agent_id", "agent_type", "kennung", "prompt"}, entry
        assert entry["agent_id"] == "unbekannt" and entry["agent_type"] == "unbekannt", entry
        return f"Treffer -> 1 Protokollzeile: {entry}"


def kein_treffer_leere_zeile() -> str:
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db)
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        _run_main_with_prompt("voellig unverwandtes thema ohne jeden treffer irgendwo")
        entry = json.loads(log.read_text(encoding="utf-8"))
        assert entry["nodes"] == [] and entry["lessons"] == [], entry
        return "kein Treffer -> leere Protokollzeile"


def kaputtes_ziel_bricht_abruf_nicht() -> str:
    """Wichtigster Fall: Protokollziel unschreibbar (Verzeichnis statt Datei)
    -> der Abruf selbst liefert trotzdem sein <knowledge-recall>, keine
    Exception nach oben."""
    with tempfile.TemporaryDirectory() as td:
        db = pathlib.Path(td) / "brainlehr.db"
        kaputt = pathlib.Path(td) / "kaputtes_ziel"
        kaputt.mkdir()  # Verzeichnis, nicht beschreibbar als Datei
        _build_db(db)
        hook.DB, hook.RECALL_LOG = str(db), str(kaputt)
        try:
            out = _run_main_with_prompt(TREFFER_PROMPT)
        except Exception as e:
            raise AssertionError(f"main() liess Fehler durch: {e!r}") from e
        assert "<knowledge-recall>" in out, "Abruf blieb trotz kaputtem Protokollziel stumm"
        return "Protokollziel kaputt -> Abruf laeuft unveraendert, kein Fehler nach oben"


def auswertung_liefert_plausible_zahlen() -> str:
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db)
        log.write_text(
            json.dumps({"ts": "2026-08-01T10:00:00+00:00", "nodes": ["/test/gobd"], "lessons": []}) + "\n" +
            json.dumps({"ts": "2026-08-01T11:00:00+00:00", "nodes": ["/test/gobd"], "lessons": ["L-1"]}) + "\n",
            encoding="utf-8",
        )
        stdout_bak, sys.stdout = sys.stdout, io.StringIO()
        try:
            hook.report(str(log), str(db))
            out = sys.stdout.getvalue()
        finally:
            sys.stdout = stdout_bak
        assert "Nodes nie gezogen: 0/1" in out, out
        assert "Lessons nie gezogen: 0/1" in out, out
        assert "/test/gobd', 2" in out, out  # 2x gezogen -> Top-Node
        return "Auswertung gegen synthetisches Protokoll: 0 nie gezogene Nodes/Lessons, Top-Node stimmt"


def rotation_kappt_bei_ueberlauf() -> str:
    with tempfile.TemporaryDirectory() as td:
        log = pathlib.Path(td) / "recall_log.jsonl"
        alt = hook.RECALL_LOG_MAX_BYTES
        hook.RECALL_LOG_MAX_BYTES = 200  # winzig, damit 20 Zeilen sicher ueberlaufen
        try:
            for i in range(20):
                hook.log_recall([{"path": f"/n{i}"}], [], str(log))
        finally:
            hook.RECALL_LOG_MAX_BYTES = alt
        groesse = log.stat().st_size
        assert groesse < 20 * 60, f"Protokoll waechst unbegrenzt: {groesse} Byte"
        return f"Rotation greift: {groesse} Byte nach 20 Eintraegen mit 200-Byte-Deckel"


def main() -> None:
    checks = [
        ("HIT", treffer_erzeugt_protokollzeile),
        ("MISS", kein_treffer_leere_zeile),
        ("KAPUTTES-ZIEL", kaputtes_ziel_bricht_abruf_nicht),
        ("AUSWERTUNG", auswertung_liefert_plausible_zahlen),
        ("ROTATION", rotation_kappt_bei_ueberlauf),
    ]
    for label, fn in checks:
        beleg = fn()
        print(f"[{label}] {beleg}")
    print("test_knowledge_recall_hook: alle Zusicherungen halten")


if __name__ == "__main__":
    main()


def test_selbsttest_laeuft_durch():
    """Diese Datei war ein Selbsttest zum Aufrufen von Hand und lag in
    hub/scripts. In tests/ sammelt pytest sie nur ein, wenn eine Funktion
    test_* heisst — sonst zaehlt sie als gruen, ohne je gelaufen zu sein.
    Der Aufruf hier macht aus der Ablage wieder eine Pruefung."""
    main()
