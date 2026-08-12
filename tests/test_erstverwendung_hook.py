#!/usr/bin/env python3
"""Rot-vor-gruen fuer die Erstverwendungs-Vorlage im Recall-Hook.

Auftrag 2026-08-12: Fremdregeln (kern/regelpaket.py) kommen mit
norm_entscheidung='offen' herein und wirken nie, bis ein Mensch einen Rang
setzt -- aber niemand wird je gefragt. berichte/erstverwendung.py beantwortet
die Frage "was liesse sich ableiten, was muss ein Mensch setzen", hatte aber
im ganzen Baum KEINEN Aufrufer (per grep bestaetigt). Dieser Test belegt: der
Recall-Hook (haken/knowledge_recall_hook.py) haengt bei einem offenen Knoten
in seiner Auswahl eine ERSTVERWENDUNG-Zeile an -- einmal, nicht bei jedem
weiteren Auftreten desselben Knotens.

Rot-Probe (im Auftrag verlangt): gegen den Stand VOR diesem Auftrag (kein
_erstverwendungs_vorschlaege(), kein _attach_norm_offen()) importiert dieser
Test gar nicht erst durch -- AttributeError beim ersten Aufruf. Belegt per
`git stash push -- haken/knowledge_recall_hook.py`, Testlauf (rot), `git
stash pop`, erneuter Lauf (gruen) -- siehe Auftragsbericht.

Alles gegen tempfile.TemporaryDirectory(), nie gegen die echte brainlehr.db
oder ein echtes recall_log.jsonl.
"""

import sys as _sys
from pathlib import Path as _Path

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

WURZEL = pathlib.Path(__file__).resolve().parent.parent
HOOK_PATH = WURZEL / "haken" / "knowledge_recall_hook.py"

_spec = importlib.util.spec_from_file_location("knowledge_recall_hook_ev", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

# Schema-Ausschnitt wie tests/test_knowledge_recall_hook.py, PLUS
# norm_entscheidung -- genau die Spalte, um die es hier geht.
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
    gilt_ab TEXT, gilt_bis TEXT,
    norm_entscheidung TEXT NOT NULL DEFAULT 'offen'
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


def _build_db(path: pathlib.Path, norm_offen: str, norm_entschieden: str) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO knowledge_nodes (id,path,title,summary,norm_entscheidung) VALUES (?,?,?,?,?)",
        ("n-offen", "/test/gobd-offen", "GoBD Hashkette Pflicht",
         "Fahrtenbuch trip repository muss Hashkette gegen GoBD-Verletzung fuehren",
         norm_offen),
    )
    conn.execute(
        "INSERT INTO knowledge_nodes (id,path,title,summary,norm_entscheidung) VALUES (?,?,?,?,?)",
        ("n-entschieden", "/test/gobd-entschieden", "GoBD Hashkette entschieden",
         "Fahrtenbuch trip repository haelt Hashkette gegen GoBD-Verletzung, bereits eingeordnet",
         norm_entschieden),
    )
    conn.commit()
    conn.close()


def _run_main_with_prompt(prompt: str) -> str:
    stdin_bak, stdout_bak = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(json.dumps({"prompt": prompt, "session_id": "sitzung1-erste-sitzung"}))
    sys.stdout = out = io.StringIO()
    try:
        hook.main()
    finally:
        sys.stdin, sys.stdout = stdin_bak, stdout_bak
    return out.getvalue()


def test_offener_knoten_erzeugt_erstverwendungs_vorlage():
    """POSITIV: norm_entscheidung == 'offen' -> ERSTVERWENDUNG-Zeile in der
    additionalContext UND in der systemMessage (der belegt gelesene Kanal)."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db, norm_offen="offen", norm_entschieden="keine_norm")
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        out = _run_main_with_prompt(TREFFER_PROMPT)
        ausgabe = json.loads(out)
        block = ausgabe["hookSpecificOutput"]["additionalContext"]
        assert "ERSTVERWENDUNG" in block, block
        assert "/test/gobd-offen" in block.split("ERSTVERWENDUNG")[1], block
        assert "erstverwendung" in ausgabe["systemMessage"].lower(), ausgabe["systemMessage"]

        zeilen = log.read_text(encoding="utf-8").strip().splitlines()
        entry = json.loads(zeilen[-1])
        assert entry.get("erstverwendung_vorschlag") == ["n-offen"], entry


def test_entschiedener_knoten_erzeugt_keine_vorlage():
    """NEGATIVFALL: norm_entscheidung != 'offen' -> keine ERSTVERWENDUNG-Zeile,
    sonst waere die Vorlage Dauerrauschen fuer laengst entschiedene Knoten."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        # BEIDE Knoten entschieden -- keiner soll eine Vorlage ausloesen.
        _build_db(db, norm_offen="keine_norm", norm_entschieden="keine_norm")
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        out = _run_main_with_prompt(TREFFER_PROMPT)
        ausgabe = json.loads(out)
        block = ausgabe["hookSpecificOutput"]["additionalContext"]
        assert "ERSTVERWENDUNG" not in block, block
        assert "systemMessage" not in ausgabe or "erstverwendung" not in ausgabe["systemMessage"].lower()

        zeilen = log.read_text(encoding="utf-8").strip().splitlines()
        entry = json.loads(zeilen[-1])
        assert "erstverwendung_vorschlag" not in entry, entry


def test_zweites_auftreten_zeigt_keine_wiederholte_vorlage():
    """Erstes Auftreten zeigt die Vorlage, das ZWEITE (selbe Sitzung, selber
    Knoten, erneuter Prompt-Treffer) nicht mehr -- 'beim ersten Auftreten',
    nicht bei jedem Abruf. Ohne diese Grenze waere jede weitere Erwaehnung
    Dauerrauschen wie ein Eintrag, der nie einen Rang bekommt."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db, norm_offen="offen", norm_entschieden="keine_norm")
        hook.DB, hook.RECALL_LOG = str(db), str(log)

        erster = json.loads(_run_main_with_prompt(TREFFER_PROMPT))
        assert "ERSTVERWENDUNG" in erster["hookSpecificOutput"]["additionalContext"]

        # dedup_session wuerde denselben Knoten in DERSELBEN Sitzung ohnehin
        # ausfiltern -- neue Sitzung, damit NUR die Erstverwendungs-Sperre
        # geprueft wird, nicht die vorhandene Session-Dedup.
        stdin_bak, stdout_bak = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(json.dumps({"prompt": TREFFER_PROMPT, "session_id": "sitzung2-zweite-sitzung"}))
        sys.stdout = out2 = io.StringIO()
        try:
            hook.main()
        finally:
            sys.stdin, sys.stdout = stdin_bak, stdout_bak
        zweiter = json.loads(out2.getvalue())
        block2 = zweiter["hookSpecificOutput"]["additionalContext"]
        assert "ERSTVERWENDUNG" not in block2, block2


if __name__ == "__main__":
    test_offener_knoten_erzeugt_erstverwendungs_vorlage()
    print("[POSITIV] offener Knoten -> ERSTVERWENDUNG-Zeile, systemMessage traegt sie")
    test_entschiedener_knoten_erzeugt_keine_vorlage()
    print("[NEGATIV] entschiedener Knoten -> keine Zeile")
    test_zweites_auftreten_zeigt_keine_wiederholte_vorlage()
    print("[DEDUP] zweites Auftreten -> keine Wiederholung")
    print("test_erstverwendung_hook: alle Zusicherungen halten")
