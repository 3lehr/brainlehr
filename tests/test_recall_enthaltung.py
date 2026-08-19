#!/usr/bin/env python3
"""Selbsttest: Enthaltungsschwelle bedeutungs_kosinus im aktiven Suchpfad
(haken/knowledge_recall_hook.py::query()/main(), Auftrag 2026-08-19).

BEFUND VOR DIESEM AUFTRAG: der aktive Suchpfad (_suchpfad_aktiv()==True,
Vorgabe seit 2026-08-09) liefert Kandidaten unabhaengig davon, wie schwach
der Bedeutungskanal sie stuetzt -- gemessen ueber
runs/enthaltungsschwelle_kosinus_abrufweg.json (GENAU dieser Weg, n=35
einschlaegig / 41 fachfremd): bei einer Schwelle von 0.55 sind 3/35
faelschlich enthalten, aber 0/41 faelschlich geliefert. Ohne Enthaltung wird
zu schwachen Anfragen (Beleg: Plane-Frage bester Kosinus 0.4501) trotzdem
etwas eingespielt, und ein Modell macht daraus ("Mastwurf" -> "Kalibrierbremse")
eine falsche Antwort statt gar keiner.

Rot-Probe (2026-08-19, gegen Commit 833e7ef4, VOR diesem Auftrag): query()
kannte den Parameter enthaltung_satz nicht (TypeError), und
ENTHALTUNGSSCHWELLE_KOSINUS existierte nicht -- s. auch
scratchpad/knowledge_recall_hook_VORHER.py fuer den woertlichen Stand.

Alles gegen tempfile.TemporaryDirectory() -- nie gegen shared-knowledge/
brainlehr.db oder ein echtes recall_log.jsonl. Kein Ollama-Aufruf: embed_fn/
embeddings.embed_text wird injiziert bzw. gepatcht (Walkthrough-Doktrin).
Gleicher Schema-/Fixtur-Aufbau wie tests/test_recall_lage.py (dort bereits
erprobt, hier nicht importiert -- eigene Datei bleibt unabhaengig lauffaehig).
"""
from __future__ import annotations

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
import math
import pathlib
import sqlite3
import sys
import tempfile

import embeddings  # kern/embeddings.py, s. Suchpfad oben

WURZEL = pathlib.Path(__file__).resolve().parent.parent
HOOK_PATH = WURZEL / "haken" / "knowledge_recall_hook.py"

_spec = importlib.util.spec_from_file_location("knowledge_recall_hook_enthaltung", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

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
CREATE TABLE knowledge_embeddings (
    kind TEXT NOT NULL, ref_id TEXT NOT NULL, project_id TEXT NOT NULL DEFAULT 'shared',
    model TEXT NOT NULL, dim INTEGER, vector BLOB NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY (kind, ref_id, project_id)
);
"""

PROMPT = "fahrtenbuch trip repository hash kette gobd verletzt"
QUERY_VEC = [1.0, 0.0]


def _vec(cos_theta: float) -> list[float]:
    """Vektor auf dem Einheitskreis, dessen Kosinus-Aehnlichkeit zu QUERY_VEC
    EXAKT cos_theta ist (gleicher Trick wie tests/test_recall_lage.py) --
    so laesst sich der beste bedeutungs_kosinus-Wert gezielt auf einen
    Grenzwert legen, statt ihn ueber echte Vektoren erst auszurechnen."""
    return [cos_theta, math.sqrt(1 - cos_theta ** 2)]


def _build_db(path: pathlib.Path, node_cos: float | None) -> None:
    """EIN FTS-Kandidat (n1, passt auf PROMPT), dessen Embedding-Vektor auf
    genau node_cos gesetzt wird -- node_cos=None laesst die
    knowledge_embeddings-Tabelle fuer n1 leer (kein Vektor, s. Negativfall)."""
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO knowledge_nodes (id,path,title,summary) VALUES (?,?,?,?)",
        ("n1", "/test/gobd", "GoBD Hashkette",
         "Fahrtenbuch trip repository haelt Hashkette gegen GoBD-Verletzung"),
    )
    if node_cos is not None:
        conn.execute(
            "INSERT INTO knowledge_embeddings (kind,ref_id,model,vector,updated_at) VALUES (?,?,?,?,?)",
            ("node", "n1", embeddings.DEFAULT_EMBED_MODEL, embeddings.pack_embedding(_vec(node_cos)),
             "2026-08-19T00:00:00+00:00"),
        )
    conn.commit()
    conn.close()


def _run_main_with_prompt(prompt: str) -> str:
    stdin_bak, stdout_bak = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(json.dumps({"prompt": prompt}))
    sys.stdout = out = io.StringIO()
    try:
        hook.main()
    finally:
        sys.stdin, sys.stdout = stdin_bak, stdout_bak
    return out.getvalue()


class _FesterEmbedFn:
    def __enter__(self):
        self._original = embeddings.embed_text
        embeddings.embed_text = lambda *a, **k: list(QUERY_VEC)
        return self

    def __exit__(self, *exc):
        embeddings.embed_text = self._original


def _setup(td: str, node_cos: float | None):
    db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
    _build_db(db, node_cos)
    hook.DB, hook.RECALL_LOG = str(db), str(log)
    return db


def plane_frage_wird_enthalten() -> str:
    """POSITIVFALL: bester Kosinus 0.4501 (belegter Schadensfall aus dem
    Auftrag) liegt unter ENTHALTUNGSSCHWELLE_KOSINUS=0.55 -> nichts wird
    eingespielt, aber SICHTBAR (systemMessage + additionalContext tragen den
    Satz), kein stilles Nichts."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td, 0.4501)
        with _FesterEmbedFn():
            out = _run_main_with_prompt(PROMPT)
        assert out.strip(), "Enthaltung muss sichtbar sein, Ausgabe war leer"
        payload = json.loads(out)
        satz = "Zu dieser Frage steht nichts Belastbares im Speicher."
        assert payload["systemMessage"] == satz, payload
        assert satz in payload["hookSpecificOutput"]["additionalContext"], payload
        assert "/test/gobd" not in payload["hookSpecificOutput"]["additionalContext"], payload
        return f"Kosinus 0.4501 -> enthalten, sichtbarer Satz ({out.strip()!r})"


def hoher_kosinus_liefert_unveraendert() -> str:
    """GEGENPROBE: bester Kosinus 0.6477 (oberes Ende des einschlaegigen
    Bereichs aus der Messung) liegt klar ueber der Schwelle -> derselbe
    Treffer wie ohne Enthaltungslogik (mit ENTHALTUNGSSCHWELLE_KOSINUS
    verglichen gegen denselben Aufbau ohne Enthaltung: byte-gleiche
    nodes/lessons)."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td, 0.6477)
        kws = hook.keywords(PROMPT)
        fixer_embed_fn = lambda *a, **k: list(QUERY_VEC)  # noqa: E731

        satz_mit: list[str] = []
        nodes_mit, lessons_mit = hook.query(
            kws, cwd=None, prompt=PROMPT, embed_fn=fixer_embed_fn, enthaltung_satz=satz_mit)
        nodes_ohne, lessons_ohne = hook.query(
            kws, cwd=None, prompt=PROMPT, embed_fn=fixer_embed_fn)

        assert satz_mit == [], satz_mit
        assert nodes_mit == nodes_ohne, (nodes_mit, nodes_ohne)
        assert lessons_mit == lessons_ohne, (lessons_mit, lessons_ohne)
        assert len(nodes_mit) == 1 and nodes_mit[0]["path"] == "/test/gobd", nodes_mit
        return f"Kosinus 0.6477 -> unveraendert geliefert ({len(nodes_mit)} Node(s))"


def _grenzwert(cos: float) -> tuple[bool, list]:
    with tempfile.TemporaryDirectory() as td:
        _setup(td, cos)
        kws = hook.keywords(PROMPT)
        fixer_embed_fn = lambda *a, **k: list(QUERY_VEC)  # noqa: E731
        satz: list[str] = []
        nodes, _ = hook.query(kws, cwd=None, prompt=PROMPT, embed_fn=fixer_embed_fn,
                               enthaltung_satz=satz)
        return bool(satz), nodes


def grenzwert_0_55_liefert() -> str:
    """GRENZWERT: bester Wert EXAKT 0.55 -> Gleichstand gewinnt fuer den
    Abruf (NICHT enthalten, s. Kommentar bei ENTHALTUNGSSCHWELLE_KOSINUS)."""
    enthalten, nodes = _grenzwert(0.55)
    assert not enthalten, "0.55 muss NICHT enthalten werden (Gleichstand liefert)"
    assert len(nodes) == 1, nodes
    return "0.55 exakt -> geliefert (Gleichstand gewinnt fuer den Abruf)"


def grenzwert_unter_0_55_enthaelt() -> str:
    enthalten, nodes = _grenzwert(0.5499)
    assert enthalten, "0.5499 muss enthalten werden"
    assert nodes == [], nodes
    return "0.5499 -> enthalten"


def grenzwert_ueber_0_55_liefert() -> str:
    enthalten, nodes = _grenzwert(0.5501)
    assert not enthalten, "0.5501 muss NICHT enthalten werden"
    assert len(nodes) == 1, nodes
    return "0.5501 -> geliefert"


def kein_vektor_wird_nicht_enthalten() -> str:
    """NEGATIVFALL (Pflicht): kein einziger Kandidat traegt einen Vektor
    (bedeutungs_kosinus=None ueberall) -> KEINE Enthaltung, weil None eine
    Aussage ueber Verfuegbarkeit ist, nicht ueber Aehnlichkeit -- sonst
    wuerde eine DB ohne Embeddings (aeltere Kopie, Ollama down) systematisch
    verstummen, obwohl der Stichwort-Kanal traegt."""
    with tempfile.TemporaryDirectory() as td:
        _setup(td, None)  # keine Embedding-Zeile fuer n1 -> bedeutungs_kosinus None
        kws = hook.keywords(PROMPT)
        satz: list[str] = []
        # embed_fn liefert trotzdem einen query_vec (Ollama erreichbar) --
        # nur der KANDIDAT selbst hat keinen Vektor, s. suchpfad_abruf.py:
        # kosinus_je_id deckt nur IDs ab, die der Embedding-Kanal traf.
        fixer_embed_fn = lambda *a, **k: list(QUERY_VEC)  # noqa: E731
        nodes, _ = hook.query(kws, cwd=None, prompt=PROMPT, embed_fn=fixer_embed_fn,
                               enthaltung_satz=satz)
        assert satz == [], satz
        assert len(nodes) == 1 and nodes[0]["path"] == "/test/gobd", nodes
        return "alle bedeutungs_kosinus=None -> keine Enthaltung, Stichwort-Treffer bleibt"


def abschaltbar_ueber_env(monkeypatch=None) -> str:
    """Abschaltbarkeit: KNOWLEDGE_ENTHALTUNG_KOSINUS=0 liefert trotz
    schwachem Kosinus (0.30) den Kandidaten."""
    import os
    with tempfile.TemporaryDirectory() as td:
        _setup(td, 0.30)
        kws = hook.keywords(PROMPT)
        fixer_embed_fn = lambda *a, **k: list(QUERY_VEC)  # noqa: E731
        os.environ["KNOWLEDGE_ENTHALTUNG_KOSINUS"] = "0"
        try:
            satz: list[str] = []
            nodes, _ = hook.query(kws, cwd=None, prompt=PROMPT, embed_fn=fixer_embed_fn,
                                   enthaltung_satz=satz)
        finally:
            del os.environ["KNOWLEDGE_ENTHALTUNG_KOSINUS"]
        assert satz == [], satz
        assert len(nodes) == 1, nodes
        return "KNOWLEDGE_ENTHALTUNG_KOSINUS=0 -> Enthaltung abgeschaltet, Treffer bleibt"


def main() -> None:
    checks = [
        ("POSITIV", plane_frage_wird_enthalten),
        ("GEGENPROBE", hoher_kosinus_liefert_unveraendert),
        ("GRENZWERT-0.55", grenzwert_0_55_liefert),
        ("GRENZWERT-0.5499", grenzwert_unter_0_55_enthaelt),
        ("GRENZWERT-0.5501", grenzwert_ueber_0_55_liefert),
        ("NEGATIV", kein_vektor_wird_nicht_enthalten),
        ("ABSCHALTBAR", abschaltbar_ueber_env),
    ]
    for label, fn in checks:
        beleg = fn()
        print(f"[{label}] {beleg}")
    print("test_recall_enthaltung: alle Zusicherungen halten")


if __name__ == "__main__":
    main()


def test_selbsttest_laeuft_durch():
    main()
