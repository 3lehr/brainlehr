#!/usr/bin/env python3
"""Selbsttest: die Lage des Bedeutungskanals (kern/relevanzlage.py) im
Recall-Block sichtbar machen -- KENNZEICHNEN, NICHT FILTERN (Auftrag
2026-08-18).

BEFUND VOR DIESEM AUFTRAG: relevanzlage.beurteile() bewertet Treffer schon
im MCP-Werkzeug (knowledge_mcp_server.py::knowledge_search() ->
out["bestandslage"]), aber der automatische Recall-Block
(haken/knowledge_recall_hook.py), den JEDE Sitzung bei JEDEM Prompt bekommt,
nennt relevanzlage nirgends -- der Zustand "der Speicher raet gerade" war im
Block unsichtbar.

ZWEITER BEFUND, ERST BEIM BAUEN AUFGEFALLEN: der seit 2026-08-09 AKTIVE
Abrufweg (_suchpfad_aktiv()==True, S9) verwirft die rohen Kosinuswerte des
Bedeutungskanals VOR der Rueckgabe -- haken/suchpfad_abruf.py::kandidaten()
fusioniert nur noch RANGPOSITIONEN (embeddings.rrf_fuse), nie die Werte
selbst. Der Hook hatte die noetigen Werte fuer relevanzlage.beurteile() im
aktiven Pfad also NICHT. Behoben, indem knowledge_recall_hook.query() den in
DIESER Datei bereits vorhandenen Helfer _embedding_scores() (Teil 1, Auftrag
2026-08-07 -- bisher nur im deaktivierten Nicht-Suchpfad-Zweig benutzt)
zusaetzlich und astunabhaengig aufruft, sobald ein `bedeutungswerte`-Param
uebergeben wird (Bauform wie werte= bei knowledge_mcp_server.py::
_embedding_ranking). Kein Tabu-Modul angefasst, keine Kandidatenauswahl
veraendert -- reines Beiwerk fuer die Kennzeichnung.

Rot-Probe (2026-08-18, gegen den Stand VOR diesem Auftrag, woertlich):
  schwache_lage_zeigt_hinweis(): AssertionError, block enthielt den Satz
  nicht -- der Block bestand nur aus Kopfzeile/Frageform, den zwei
  Treffern (n1/L-1) und der Bilanzzeile, kein Hinweis auf die Lage.
  mengengleichheit_mit_ohne_bedeutungswerte(): TypeError: query() got an
  unexpected keyword argument 'bedeutungswerte' (hook.query() kannte den
  Parameter nicht).

Alles gegen tempfile.TemporaryDirectory() -- nie gegen shared-knowledge/
brainlehr.db oder ein echtes recall_log.jsonl. Kein Ollama-Aufruf: embed_fn/
embeddings.embed_text wird injiziert bzw. gepatcht (Walkthrough-Doktrin).
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

_spec = importlib.util.spec_from_file_location("knowledge_recall_hook_lage", HOOK_PATH)
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)

# Gleicher Schema-Ausschnitt wie tests/test_knowledge_recall_hook.py, dazu
# eine SCHLANKE knowledge_embeddings-Tabelle (keine Modell-Trigger -- die
# stehen nur in der vollen schema.sql, hier bewusst nicht nachgebaut, s.
# hook._embedding_scores(): liest ohne model-Filter).
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

TREFFER_PROMPT = "fahrtenbuch trip repository hash kette gobd verletzt"
QUERY_VEC = [1.0, 0.0]  # Einheitsvektor, s. _vec() unten fuer die Gegenseite


def _vec(cos_theta: float) -> list[float]:
    """Vektor auf dem Einheitskreis, dessen Kosinus-Aehnlichkeit zu QUERY_VEC
    EXAKT cos_theta ist -- so lassen sich die drei Lagen (passend/schwach/
    uneindeutig) ueber gezielte Werte statt Zufallsdaten herstellen."""
    return [cos_theta, math.sqrt(1 - cos_theta ** 2)]


def _build_db(path: pathlib.Path, dummy_cosines: list[float] | None = None) -> None:
    """n1/L-1 wie test_knowledge_recall_hook.py (garantierter FTS-Treffer
    auf TREFFER_PROMPT) + optionale Dummy-Knoten mit gezielt gesetzten
    Embedding-Vektoren -- diese Knoten sind KEINE FTS-Kandidaten (ihr Text
    passt nicht zum Prompt), sie tragen nur die Werte des Bedeutungskanals."""
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
    for i, cos in enumerate(dummy_cosines or []):
        nid = f"dummy{i}"
        conn.execute(
            "INSERT INTO knowledge_nodes (id,path,title,summary) VALUES (?,?,?,?)",
            (nid, f"/test/dummy{i}", "belangloser Titel", "belangloser Inhalt ohne Ueberschneidung"),
        )
        conn.execute(
            "INSERT INTO knowledge_embeddings (kind,ref_id,model,vector,updated_at) VALUES (?,?,?,?,?)",
            ("node", nid, "test-modell", embeddings.pack_embedding(_vec(cos)), "2026-08-18T00:00:00+00:00"),
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


def _block_text(stdout_json: str) -> str:
    if not stdout_json.strip():
        return ""
    payload = json.loads(stdout_json)
    return payload["hookSpecificOutput"]["additionalContext"]


class _FesterEmbedFn:
    """Patcht hook.embeddings.embed_text auf einen festen Vektor -- kein
    Ollama-Aufruf im Test. hook.embeddings ist dasselbe Modulobjekt wie das
    hier importierte 'embeddings' (sys.modules-Singleton), Patch wirkt also
    auf beide Importwege; try/finally stellt das Original wieder her, damit
    andere Tests im selben Prozess nichts davon merken."""

    def __enter__(self):
        self._original = embeddings.embed_text
        embeddings.embed_text = lambda *a, **k: list(QUERY_VEC)
        return self

    def __exit__(self, *exc):
        embeddings.embed_text = self._original


def schwache_lage_zeigt_hinweis() -> str:
    """POSITIVFALL: drei Dummy-Kosinuswerte [0.70, 0.699, 0.698] -- hoher
    bester Wert, aber praktisch kein Abstand zum Rest (der 'breit'-Fall aus
    kern/relevanzlage.py::demo()). beurteile() liefert 'schwach', der Satz
    MUSS im Block stehen."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db, dummy_cosines=[0.70, 0.699, 0.698])
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        with _FesterEmbedFn():
            block = _block_text(_run_main_with_prompt(TREFFER_PROMPT))
        assert "<knowledge-recall>" in block, "kein Block trotz echtem FTS-Treffer"
        satz = "Dazu steht wenig Passendes im Bestand"
        assert satz in block, block
        # Der Speicher raet-Hinweis darf keinen Treffer verdraengen: n1/L-1
        # muessen trotzdem drinstehen.
        assert "/test/gobd" in block and "L-1" in block, block
        return f"schwache Lage -> Hinweis steht im Block ({len(block)} Zeichen)"


def starke_lage_zeigt_keinen_hinweis() -> str:
    """NEGATIVFALL (Pflicht): drei Dummy-Kosinuswerte [0.9, 0.5, 0.4] -- hoher
    bester Wert UND deutlicher Abstand -> beurteile() liefert 'passend', der
    Satz ist LEER. Steht trotzdem ein Hinweis im Block, ist das Rauschen."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db, dummy_cosines=[0.9, 0.5, 0.4])
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        with _FesterEmbedFn():
            block = _block_text(_run_main_with_prompt(TREFFER_PROMPT))
        assert "<knowledge-recall>" in block, "kein Block trotz echtem FTS-Treffer"
        for verboten in ("Dazu steht wenig Passendes", "nicht eindeutig einzuordnen"):
            assert verboten not in block, block
        assert "/test/gobd" in block and "L-1" in block, block
        return f"starke Lage -> KEIN Hinweis im Block ({len(block)} Zeichen)"


def keine_treffer_kein_block() -> str:
    """GRENZFALL: ein Prompt, der nirgends passt (weder Stichwort- noch
    Bedeutungskanal liefern einen Kandidaten -- leere knowledge_embeddings-
    Tabelle) -> kein Block, kein leerer Hinweis. Die Embedding-Tabelle
    absichtlich LEER (nicht mit hoher Aehnlichkeit gefuellt): ein gefuellter
    Bedeutungskanal WUERDE hier einen Kandidaten liefern (siehe
    schwache_lage_zeigt_hinweis -- das ist der Suchweg, nicht ein Testfehler),
    dieser Fall prueft ausschliesslich, dass die Lage-Kennzeichnung selbst
    nie einen Block ohne jeden Kandidaten erzeugt."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        _build_db(db)  # keine dummy_cosines -> Embedding-Tabelle bleibt leer
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        with _FesterEmbedFn():
            out = _run_main_with_prompt("voellig unverwandtes thema ohne jeden treffer irgendwo")
        assert out == "", f"Ausgabe haette leer sein muessen, war: {out!r}"
        return "kein Kandidat in beiden Kanaelen -> kein Block"


def mengengleichheit_mit_ohne_bedeutungswerte() -> str:
    """WICHTIGSTE ZUSICHERUNG: hook.query() mit und ohne bedeutungswerte-
    Parameter liefert IDENTISCHE nodes/lessons -- der Parameter ist reines
    Beiwerk fuer die Kennzeichnung, er filtert und sortiert nicht mit."""
    with tempfile.TemporaryDirectory() as td:
        db = pathlib.Path(td) / "brainlehr.db"
        _build_db(db, dummy_cosines=[0.9, 0.5, 0.4])
        hook.DB = str(db)
        kws = hook.keywords(TREFFER_PROMPT)
        fixer_embed_fn = lambda *a, **k: list(QUERY_VEC)  # noqa: E731

        nodes_ohne, lessons_ohne = hook.query(kws, cwd=None, prompt=TREFFER_PROMPT, embed_fn=fixer_embed_fn)
        bedeutungswerte: list = []
        nodes_mit, lessons_mit = hook.query(
            kws, cwd=None, prompt=TREFFER_PROMPT, embed_fn=fixer_embed_fn,
            bedeutungswerte=bedeutungswerte)

        assert nodes_ohne == nodes_mit, (nodes_ohne, nodes_mit)
        assert lessons_ohne == lessons_mit, (lessons_ohne, lessons_mit)
        assert len(nodes_ohne) >= 1 and len(lessons_ohne) >= 1, "Testaufbau ohne Treffer ist wertlos"
        # Und die Werte selbst kommen tatsaechlich an -- sonst waere die
        # Mengengleichheit oben trivial (leerer Parameter aendert nichts an
        # nichts).
        assert bedeutungswerte == sorted(bedeutungswerte, reverse=True), bedeutungswerte
        assert len(bedeutungswerte) == 3, bedeutungswerte
        return (f"query() mit/ohne bedeutungswerte: {len(nodes_ohne)} Node(s)/"
                f"{len(lessons_ohne)} Lesson(s) identisch, bedeutungswerte gefuellt "
                f"({bedeutungswerte})")


def ohne_bedeutungskanal_kein_block_fehler() -> str:
    """Hat der Hook keine Embedding-Tabelle (aeltere/schlanke DB-Kopie ohne
    knowledge_embeddings) oder ist ZWEITER_KANAL aus, bleibt bedeutungswerte
    leer -- main() darf dann weder abstuerzen noch faelschlich einen Satz
    einfuegen."""
    with tempfile.TemporaryDirectory() as td:
        db, log = pathlib.Path(td) / "brainlehr.db", pathlib.Path(td) / "recall_log.jsonl"
        # Schema OHNE knowledge_embeddings -- wie eine DB-Kopie vor dem
        # Bedeutungskanal.
        conn = sqlite3.connect(db)
        conn.executescript(SCHEMA.split("CREATE TABLE knowledge_embeddings")[0])
        conn.execute(
            "INSERT INTO knowledge_nodes (id,path,title,summary) VALUES (?,?,?,?)",
            ("n1", "/test/gobd", "GoBD Hashkette",
             "Fahrtenbuch trip repository haelt Hashkette gegen GoBD-Verletzung"),
        )
        conn.execute(
            "INSERT INTO lessons_learned (id,type,description,root_cause,prevention) VALUES (?,?,?,?,?)",
            ("L-1", "error", "fahrtenbuch trip repository hash kette bricht bei reconnect",
             "Sitzung verliert Bindung", "Reconnect muss Bindung neu pruefen"),
        )
        conn.commit()
        conn.close()
        hook.DB, hook.RECALL_LOG = str(db), str(log)
        block = _block_text(_run_main_with_prompt(TREFFER_PROMPT))
        assert "<knowledge-recall>" in block, "kein Block trotz echtem FTS-Treffer"
        for verboten in ("Dazu steht wenig Passendes", "nicht eindeutig einzuordnen"):
            assert verboten not in block, block
        return "keine knowledge_embeddings-Tabelle -> kein Absturz, kein Hinweis"


def zeichenzuwachs_je_block() -> str:
    """Misst, wieviele Zeichen die Kennzeichnung EINEM Block hinzufuegt --
    genau die Zeile, die beurteile() liefert, plus den Zeilenumbruch, mit
    dem main() sie an den Block haengt."""
    schwach = hook.relevanzlage.beurteile([0.70, 0.699, 0.698])["satz"]
    uneindeutig = hook.relevanzlage.beurteile([0.45, 0.44, 0.43])["satz"]
    passend = hook.relevanzlage.beurteile([0.9, 0.5, 0.4])["satz"]
    assert passend == "", "Positivkontrolle: starke Lage darf keinen Zuwachs haben"
    zuwachs_schwach = len(schwach) + 1  # +1 fuer den Zeilenumbruch in lines.append()
    zuwachs_uneindeutig = len(uneindeutig) + 1
    return (f"Zeichenzuwachs je Block: 'schwach' +{zuwachs_schwach} Zeichen, "
            f"'uneindeutig' +{zuwachs_uneindeutig} Zeichen, 'passend'/kein Kanal +0")


def main() -> None:
    checks = [
        ("POSITIV", schwache_lage_zeigt_hinweis),
        ("NEGATIV", starke_lage_zeigt_keinen_hinweis),
        ("GRENZFALL", keine_treffer_kein_block),
        ("MENGENGLEICHHEIT", mengengleichheit_mit_ohne_bedeutungswerte),
        ("OHNE-KANAL", ohne_bedeutungskanal_kein_block_fehler),
        ("ZUWACHS", zeichenzuwachs_je_block),
    ]
    for label, fn in checks:
        beleg = fn()
        print(f"[{label}] {beleg}")
    print("test_recall_lage: alle Zusicherungen halten")


if __name__ == "__main__":
    main()


def test_selbsttest_laeuft_durch():
    main()
