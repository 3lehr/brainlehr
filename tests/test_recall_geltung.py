#!/usr/bin/env python3
"""Selbsttest fuer die Geltungsanzeige im Recall-Block (Sprint S1d,
"Geltung als eigene Achse", docs/SPRINTS.md).

Auftrag: der Recall-Block (haken/knowledge_recall_hook.py) zeigte bisher
weder norm_rang noch gilt_bis je Trefferzeile -- eine Rang-1-Weisung und
eine beilaeufige Notiz sahen identisch aus. Dieser Test belegt: Rang und
Ablaufdatum erscheinen NUR wenn gesetzt, ein Eintrag ohne beides bleibt
zeichengleich zum bisherigen Stand, und ein bald ablaufender Eintrag traegt
einen Zusatz.

Rot-Probe (2026-08-18, gegen den Stand VOR diesem Auftrag): `_geltung_tag`
existierte nicht -> `AttributeError: module 'knowledge_recall_hook' has no
attribute '_geltung_tag'`. Nach dem Fix: siehe unten, alle Zusicherungen
halten.

Alles gegen tempfile.TemporaryDirectory() -- nie gegen shared-knowledge/
brainlehr.db oder ein echtes recall_log.jsonl.
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
import os
import pathlib
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone

WURZEL = pathlib.Path(__file__).resolve().parent.parent
HOOK_PATH = WURZEL / "haken" / "knowledge_recall_hook.py"

_spec = importlib.util.spec_from_file_location("knowledge_recall_hook_geltung", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

# Schema-Ausschnitt wie tests/test_knowledge_recall_hook.py, zusaetzlich
# norm_rang (Gegenstand dieses Auftrags -- die Spalte existiert in schema.sql
# auf knowledge_nodes, s. dort Zeile 37).
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
    gilt_ab TEXT, gilt_bis TEXT, norm_rang INTEGER
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


def _build_db(path: pathlib.Path, norm_rang=None, gilt_bis=None) -> None:
    """updated_at wird explizit als echtes UTC-jetzt gesetzt statt dem
    Schema-Vorgabewert ueberlassen: dessen strftime(...,'+01:00','now',
    'localtime') schreibt einen FEST +01:00-Offset auf die lokale Wanduhrzeit
    der Maschine -- ausserhalb UTC+1 (z.B. Sommerzeit) landet der Zeitstempel
    dadurch VOR der echten UTC-Zeit, alter() liest daraus eine negative
    Differenz und gibt "" statt "[heute]" zurueck. Ein bekannter Nebeneffekt
    des Schemas (nicht Gegenstand dieses Auftrags), hier nur umgangen."""
    jetzt = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO knowledge_nodes (id,path,title,summary,norm_rang,gilt_bis,updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("n1", "/test/gobd", "GoBD Hashkette",
         "Fahrtenbuch trip repository haelt Hashkette gegen GoBD-Verletzung",
         norm_rang, gilt_bis, jetzt),
    )
    conn.commit()
    conn.close()


def _run_main_with_prompt(prompt: str) -> str:
    """Ruft hook.main() wie der echte Hook auf und gibt den additionalContext-
    Block zurueck (main() schreibt Hook-JSON auf stdout, kein Rohtext).
    BEGOD_KNOWLEDGE_PROJECT='test' verhindert die 'anderes Projekt'-Markierung
    fuer /test/gobd -- der Testknoten liegt im eigenen Projekt, nicht in
    einem fremden (nicht Gegenstand dieses Auftrags, s. _tag_node_scope)."""
    stdin_bak, stdout_bak = sys.stdin, sys.stdout
    env_bak = os.environ.get("BEGOD_KNOWLEDGE_PROJECT")
    sys.stdin = io.StringIO(json.dumps({"prompt": prompt}))
    sys.stdout = out = io.StringIO()
    os.environ["BEGOD_KNOWLEDGE_PROJECT"] = "test"
    try:
        hook.main()
    finally:
        sys.stdin, sys.stdout = stdin_bak, stdout_bak
        if env_bak is None:
            os.environ.pop("BEGOD_KNOWLEDGE_PROJECT", None)
        else:
            os.environ["BEGOD_KNOWLEDGE_PROJECT"] = env_bak
    payload = json.loads(out.getvalue())
    return payload["hookSpecificOutput"]["additionalContext"]


def _node_zeile(block_text: str) -> str:
    for zeile in block_text.splitlines():
        if zeile.startswith("- [/test/gobd]"):
            return zeile
    raise AssertionError(f"keine Node-Zeile fuer /test/gobd gefunden:\n{block_text}")


def negativfall_zeichengleich_wie_vorher() -> str:
    """Kein norm_rang, kein gilt_bis -> Zeile traegt keinen Geltungs-Zusatz,
    exakt die Form vor diesem Auftrag (Alter-Tag, dann direkt Titel). Titel/
    Summary ueber hook.entschaerfe_fuer_ausgabe() erwartet statt die
    Abgrenzungszeichen fest zu verdrahten -- das ist Sache jenes Moduls,
    nicht dieses Tests (TABU: kern/einschleusung.py)."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db, norm_rang=None, gilt_bis=None)
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        zeile = _node_zeile(_run_main_with_prompt(TREFFER_PROMPT))
        titel = hook.entschaerfe_fuer_ausgabe("GoBD Hashkette")
        summary = hook.entschaerfe_fuer_ausgabe(
            "Fahrtenbuch trip repository haelt Hashkette gegen GoBD-Verletzung")
        erwartet = f"- [/test/gobd] [heute] {titel}: {summary}"
        assert zeile == erwartet, zeile
        assert " [Rang" not in zeile and " [bis " not in zeile, zeile
        return f"ohne Rang/Frist zeichengleich zum alten Format: {zeile!r}"


def positivfall_rang_und_frist_beide_sichtbar() -> str:
    """norm_rang=1 UND gilt_bis (weit in der Zukunft, kein 'bald') -> beide
    erscheinen in EINEM Klammerpaar."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db, norm_rang=1, gilt_bis="2099-01-01")
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        zeile = _node_zeile(_run_main_with_prompt(TREFFER_PROMPT))
        assert "[Rang 1, bis 2099-01-01]" in zeile, zeile
        assert "bald" not in zeile, zeile
        return f"Rang UND Frist sichtbar, EIN Klammerpaar: {zeile!r}"


def _geltung_tag_grenzwerte() -> str:
    """Grenzwertpruefung direkt gegen _geltung_tag(): heute (0 Tage),
    morgen (1 Tag) -> 'bald'; in 31 Tagen -> kein 'bald' mehr. jetzt fest auf
    2026-08-18 (aktuelles Sitzungsdatum) injiziert, kein `datetime.now()`."""
    jetzt = datetime(2026, 8, 18, 12, 0, 0, tzinfo=timezone.utc)
    heute = hook._geltung_tag(None, "2026-08-18", jetzt=jetzt)
    morgen = hook._geltung_tag(None, "2026-08-19", jetzt=jetzt)
    in_31 = hook._geltung_tag(None, "2026-09-18", jetzt=jetzt)
    assert heute == " [bis 2026-08-18 bald]", heute
    assert morgen == " [bis 2026-08-19 bald]", morgen
    assert in_31 == " [bis 2026-09-18]", in_31
    assert "bald" not in in_31, in_31
    return (f"Grenzwerte: heute={heute!r} morgen={morgen!r} "
            f"+31Tage={in_31!r} (nur die ersten beiden tragen 'bald')")


def _geltung_tag_leer_ohne_beides() -> str:
    assert hook._geltung_tag(None, None) == ""
    assert hook._geltung_tag(0, None) == ""  # 0 ist kein gueltiger Rang, faellt wie None
    return "ohne Rang und ohne Frist -> leerer String (kein Platzhalter)"


def _geltung_tag_nur_rang() -> str:
    tag = hook._geltung_tag(2, None)
    assert tag == " [Rang 2]", tag
    return f"nur Rang gesetzt: {tag!r}"


def main() -> None:
    checks = [
        ("NEGATIV", negativfall_zeichengleich_wie_vorher),
        ("POSITIV", positivfall_rang_und_frist_beide_sichtbar),
        ("GRENZWERTE", _geltung_tag_grenzwerte),
        ("LEER", _geltung_tag_leer_ohne_beides),
        ("NUR-RANG", _geltung_tag_nur_rang),
    ]
    for label, fn in checks:
        beleg = fn()
        print(f"[{label}] {beleg}")
    print("test_recall_geltung: alle Zusicherungen halten")


if __name__ == "__main__":
    main()


def test_selbsttest_laeuft_durch():
    main()
