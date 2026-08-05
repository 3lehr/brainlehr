"""Vergleichslauf ueber die Abruf-Stellschrauben (Plan B3,
docs/PLAN_ABRUF_PRUEFSTAND_2026-08-05.md).

Faehrt den vorhandenen Messlauf (messlauf.py) ueber einen Satz Konfigurationen
und stellt die fuenf Kennzahlen aus Plan §4 gegenueber. Jede Stellschraube wird
EINZELN variiert (Plan-Auftrag: "nicht alles gleichzeitig, sonst ist keine
Wirkung zuzuordnen"), alle uebrigen Parameter bleiben auf dem heutigen
Vorgabewert:

  MIN_HITS            2 / 3 / 4                 (heute: 3, "empirisch getunt")
  Retrieval-Methode    reines BM25 / RRF-Hybrid  (Stichwort vs. +Vektoren)
  Index-Felder         voll / ohne path+tags+project_id
  Erkundungsanteil     0 / 0,15 (EXPLORE_RATE)

korpus.py und messlauf.py werden importiert, NICHT geaendert. schema.sql wird
nicht geaendert -- die Index-Ablation patcht nur den INSERT-Trigger einer
temporaeren, in diesem Skript selbst erzeugten SQLite-Datei (siehe
`_populate_db_index_ablated`), nie die Datei schema.sql.

Kein Modellaufruf, kein Netz: gleiches Ein-Hot-Vektor-Muster wie messlauf.py.
Zeitstempel wird als CLI-Argument uebergeben, nie zur Laufzeit gezogen.
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

PRUEFSTAND_DIR = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = PRUEFSTAND_DIR.parent
HUB_ROOT = SHARED_KNOWLEDGE.parent
sys.path.insert(0, str(PRUEFSTAND_DIR))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(HUB_ROOT / "scripts"))

import korpus  # type: ignore  # noqa: E402
import messlauf as ml  # type: ignore  # noqa: E402

VERGLEICHSLAUF_VERSION = "1.0.0"
EXPLORE_SEED = 99  # fester Startwert fuer den seedbaren Erkundungs-Wuerfel

_NEVER_EXPLORE = lambda: 1.0  # >= EXPLORE_RATE -> Erkundung greift nie


def _retrieve_recall_hook_isolated(q: dict, rand, log_path: str) -> list[str]:
    """Wie messlauf._retrieve_recall_hook, aber mit explizitem log_path.
    messlauf._retrieve_recall_hook ruft hook.query() ohne log_path, das faellt
    dort auf hook.RECALL_LOG zurueck -- die ECHTE Produktionsdatei
    (shared-knowledge/recall_log.jsonl). Fuer die Erkundungs-Ablation waere
    das ein stiller Zugriff auf echten Bestand mitten im synthetischen
    Pruefstand und macht das Ergebnis vom Tagesstand dieser Datei abhaengig --
    deshalb hier eine eigene, isolierte Log-Datei je Lauf."""
    kws = ml.hook.keywords(q["text"])
    if len(kws) < ml.hook.MIN_HITS:
        return []
    nodes, lessons = ml.hook.query(kws, rand=rand, log_path=log_path)
    return [f"node:{n['path']}" for n in nodes] + [f"lesson:{l['id']}" for l in lessons]


# --- Index-Ablation: eigene Populate-Variante, patcht nur den Trigger in der
# temporaeren DB dieses Prozesses (schema.sql bleibt unberuehrt) -----------

def _populate_db_index_ablated(db_path: Path, corpus: dict) -> None:
    """Wie messlauf._populate_db, aber der INSERT-Trigger auf knowledge_fts
    schreibt fuer path/tags/project_id leere Strings statt der echten Werte.
    title/summary/content bleiben unveraendert indiziert -- isoliert die
    Ablation auf genau die drei Felder aus dem Auftrag."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(ml._SCHEMA_SQL)
    conn.executescript("""
        DROP TRIGGER IF EXISTS knowledge_ai;
        CREATE TRIGGER knowledge_ai AFTER INSERT ON knowledge_nodes BEGIN
            INSERT INTO knowledge_fts(rowid, title, summary, content, path, tags, project_id)
            VALUES (new.rowid,
                LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.title,
                    'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
                LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.summary,
                    'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
                LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(new.content,
                    'Ä','ae'),'Ö','oe'),'Ü','ue'),'ä','ae'),'ö','oe'),'ü','ue'),'ß','ss')),
                '', '', '');
        END;
    """)
    conn.executemany(
        "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, "
        "summary, content, level, tags) VALUES (?,?,?,?,?,?,?,?,?)",
        [(n["id"], n["path"], n["parent_path"], n["project_id"], n["title"],
          n["summary"], n["content"], n["level"], json.dumps(n["tags"], ensure_ascii=False))
         for n in corpus["nodes"]],
    )
    conn.executemany(
        "INSERT INTO lessons_learned (id, type, description, root_cause, "
        "prevention, projects) VALUES (?,?,?,?,?,?)",
        [(l["id"], l["type"], l["description"], l["root_cause"], l["prevention"],
          json.dumps(l["projects"], ensure_ascii=False))
         for l in corpus["lessons"]],
    )
    conn.commit()
    conn.close()


# --- Eine Konfiguration fahren --------------------------------------------

def run_config(corpus: dict, queries: list[dict], total_docs: int, *,
                retrieval: str, k: int = ml.DEFAULT_K,
                min_hits: int | None = None, explore_rand=None,
                embeddings_mode: str = "rrf", index_ablated: bool = False) -> dict:
    """retrieval: 'recall_hook' (MIN_HITS/Erkundung) oder 'hybrid'
    (Retrieval-Methode/Index). Jede Konfiguration bekommt ihre eigene
    temporaere DB -- klarer als Wiederverwendung, Korpus ist klein genug,
    dass das nicht ins Gewicht faellt."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge_vergleich.db"
        if index_ablated:
            _populate_db_index_ablated(db_path, corpus)
        else:
            ml._populate_db(db_path, corpus)
        ml.kms.DB_PATH = db_path
        ml.hook.DB = str(db_path)

        if retrieval == "hybrid":
            if embeddings_mode == "bm25":
                ml._disable_embeddings()
            else:
                ml._install_synthetic_embeddings(db_path, corpus, queries)
            return ml.compute_metrics(queries, lambda q: ml._retrieve_hybrid(q, k),
                                       k=k, total_docs=total_docs)

        assert retrieval == "recall_hook", retrieval
        old_min_hits = ml.hook.MIN_HITS
        ml.hook.MIN_HITS = min_hits if min_hits is not None else old_min_hits
        # eigene, leere Log-Datei je Lauf -- niemals das echte
        # shared-knowledge/recall_log.jsonl lesen (siehe
        # _retrieve_recall_hook_isolated); leer statt fehlend, damit
        # _node_hit_counts() einen (leeren) Counter statt None liefert und die
        # Erkundung strukturell moeglich bleibt, nicht durch eine fehlende
        # Datei verdeckt ausgeschaltet wird.
        log_path = str(Path(tmp) / "recall_log_isoliert.jsonl")
        Path(log_path).write_text("", encoding="utf-8")
        try:
            rand = explore_rand if explore_rand is not None else _NEVER_EXPLORE
            return ml.compute_metrics(
                queries,
                lambda q: _retrieve_recall_hook_isolated(q, rand, log_path),
                k=k, total_docs=total_docs)
        finally:
            ml.hook.MIN_HITS = old_min_hits


# --- Konfigurationssatz: jede Stellschraube einzeln variiert --------------

def _config_specs() -> list[dict]:
    explore_on = random.Random(EXPLORE_SEED).random  # deterministisch, fester Seed
    return [
        {"name": "recall_hook_min_hits2", "stellschraube": "MIN_HITS",
         "retrieval": "recall_hook", "min_hits": 2},
        {"name": "recall_hook_min_hits3_baseline", "stellschraube": "MIN_HITS (heutige Vorgabe)",
         "retrieval": "recall_hook", "min_hits": 3},
        {"name": "recall_hook_min_hits4", "stellschraube": "MIN_HITS",
         "retrieval": "recall_hook", "min_hits": 4},

        {"name": "hybrid_bm25_only", "stellschraube": "Retrieval-Methode",
         "retrieval": "hybrid", "embeddings_mode": "bm25"},
        {"name": "hybrid_rrf_baseline", "stellschraube": "Retrieval-Methode (heutige Vorgabe)",
         "retrieval": "hybrid", "embeddings_mode": "rrf"},

        {"name": "hybrid_index_full", "stellschraube": "Index-Felder (heutige Vorgabe)",
         "retrieval": "hybrid", "embeddings_mode": "rrf", "index_ablated": False},
        {"name": "hybrid_index_ablated", "stellschraube": "Index-Felder",
         "retrieval": "hybrid", "embeddings_mode": "rrf", "index_ablated": True},

        {"name": "recall_hook_explore_off_baseline", "stellschraube": "Erkundungsanteil (heutige Vorgabe)",
         "retrieval": "recall_hook", "min_hits": 3, "explore_rand": _NEVER_EXPLORE},
        {"name": "recall_hook_explore_on_0.15", "stellschraube": "Erkundungsanteil",
         "retrieval": "recall_hook", "min_hits": 3, "explore_rand": explore_on},
    ]


def run(seed: int = korpus.DEFAULT_SEED, k: int = ml.DEFAULT_K,
        timestamp: str | None = None, corpus_version: str = korpus.CORPUS_VERSION) -> dict:
    corpus = korpus.build_corpus(seed=seed, version=corpus_version)
    queries = ml._combined_queries(corpus)
    total_docs = len(corpus["nodes"]) + len(corpus["lessons"])

    started = time.perf_counter()
    results = {}
    for spec in _config_specs():
        kwargs = {k_: v for k_, v in spec.items() if k_ not in ("name", "stellschraube")}
        results[spec["name"]] = {"stellschraube": spec["stellschraube"],
                                  "metrics": run_config(corpus, queries, total_docs, k=k, **kwargs)}
    runtime = time.perf_counter() - started

    return {
        "vergleichslauf_version": VERGLEICHSLAUF_VERSION,
        "corpus_version": corpus["version"],
        "corpus_seed": seed,
        "corpus_checksum": corpus["checksum"],
        "timestamp": timestamp,
        "k": k,
        "counts": {"nodes": len(corpus["nodes"]), "lessons": len(corpus["lessons"]), "queries": len(queries)},
        "model_calls_made": False,
        "network_calls_made": False,
        "runtime_seconds": runtime,
        "configs": results,
    }


# --- Tabelle ----------------------------------------------------------

_COLS = [
    ("recall_at_k", "Recall@k"),
    ("mrr", "MRR"),
    ("false_alarm_rate", "Fehlalarm"),
    ("silence_rate_correct", "Stumm-zuRecht"),
    ("silence_rate_wrong", "Stumm-zuUnrecht"),
    ("coverage", "Abdeckung"),
]


def _fmt(v) -> str:
    return "-" if v is None else f"{v:.3f}"


def format_table(result: dict) -> str:
    name_w = max(len(n) for n in result["configs"]) + 1
    header = f"{'Konfiguration':<{name_w}}" + "".join(f"{label:>16}" for _, label in _COLS)
    lines = [header, "-" * len(header)]
    for name, entry in result["configs"].items():
        m = entry["metrics"]
        row = f"{name:<{name_w}}" + "".join(f"{_fmt(m[key]):>16}" for key, _ in _COLS)
        lines.append(row)
    return "\n".join(lines)


# --- Selftest -----------------------------------------------------------

def selftest() -> None:
    corpus = korpus.build_corpus()
    queries = ml._combined_queries(corpus)
    total_docs = len(corpus["nodes"]) + len(corpus["lessons"])

    # Identisch -> identisch: zweimal exakt dieselbe Konfiguration.
    m_a = run_config(corpus, queries, total_docs, retrieval="recall_hook", min_hits=3)
    m_b = run_config(corpus, queries, total_docs, retrieval="recall_hook", min_hits=3)
    assert m_a == m_b, "gleiche Konfiguration muss identische Kennzahlen liefern"

    # Kuenstlich verschieden -> verschieden: MIN_HITS so extrem auseinander
    # gezogen, dass der Unterschied durch Konstruktion feststeht (Anfragen mit
    # wenigen Keywords fallen bei MIN_HITS=99 komplett durchs Vorab-Gate),
    # unabhaengig davon, ob eine der vier echten Stellschrauben spaeter einen
    # messbaren Unterschied zeigt oder nicht.
    m_lenient = run_config(corpus, queries, total_docs, retrieval="recall_hook", min_hits=1)
    m_strict = run_config(corpus, queries, total_docs, retrieval="recall_hook", min_hits=99)
    assert m_lenient != m_strict, "kuenstlich verschiedene Konfiguration muss verschiedene Kennzahlen liefern"
    assert (m_lenient["recall_at_k"] or 0) > (m_strict["recall_at_k"] or 0), (m_lenient, m_strict)

    result = run(timestamp="2026-08-05T00:00:00+0200")
    assert result["network_calls_made"] is False
    assert len(result["configs"]) == len(_config_specs())
    # Zwei baugleiche Konfigurationen im echten Satz (min_hits3-baseline und
    # explore_off-baseline unterscheiden sich nur im Namen der Bewandtnis,
    # nicht im tatsaechlichen Parametersatz) muessen ebenfalls uebereinstimmen.
    base1 = result["configs"]["recall_hook_min_hits3_baseline"]["metrics"]
    base2 = result["configs"]["recall_hook_explore_off_baseline"]["metrics"]
    assert base1 == base2, "baugleiche Konfigurationen im Satz muessen identische Kennzahlen liefern"

    print(f"vergleichslauf.py selftest ok (version={VERGLEICHSLAUF_VERSION}, "
          f"corpus_checksum={corpus['checksum'][:12]}..., runtime={result['runtime_seconds']:.2f}s)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=korpus.DEFAULT_SEED)
    ap.add_argument("--k", type=int, default=ml.DEFAULT_K)
    ap.add_argument("--timestamp", type=str, default=None,
                     help="uebergebener Zeitstempel (ISO 8601), NICHT zur Laufzeit gezogen")
    ap.add_argument("--out", type=str, default=None, help="Ergebnis als JSON schreiben")
    ap.add_argument("--corpus-version", type=str, default=korpus.CORPUS_VERSION,
                     choices=list(korpus.CORPUS_VERSIONS))
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    if not args.timestamp:
        print("Fehler: --timestamp ist Pflicht (ausser bei --selftest) -- "
              "kein Zeitstempel zur Laufzeit, sonst nicht reproduzierbar vergleichbar.", file=sys.stderr)
        sys.exit(1)

    result = run(seed=args.seed, k=args.k, timestamp=args.timestamp, corpus_version=args.corpus_version)
    table = format_table(result)
    print(table)
    print(f"\nLaufzeit: {result['runtime_seconds']:.2f}s, Modellaufrufe: {result['model_calls_made']}, "
          f"Netzaufrufe: {result['network_calls_made']}")
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"geschrieben: {args.out}")


if __name__ == "__main__":
    main()
