"""Messläufer fuer den Abruf-Pruefstand (Plan B2,
docs/PLAN_ABRUF_PRUEFSTAND_2026-08-05.md).

Baut eine temporaere DB aus schema.sql, fuellt sie aus dem synthetischen
Korpus (korpus.py) und fährt die VORHANDENEN Abruffunktionen dagegen -- ohne
sie zu aendern:
  - scripts/knowledge_recall_hook.py::query()      (MIN_HITS=3, BM25-Ranking)
  - shared-knowledge/knowledge_mcp_server.py::knowledge_search()/lesson_query()
    (Hybrid: Stichwort + optionale Embedding-RRF-Fusion)

Kein Modellaufruf im Grundmaß: embeddings.embed_text() wird auf eine rein
synthetische, deterministische Ein-Hot-Vektor-Funktion je Themen-Kennung
umgebogen (gleiches Muster wie tests/test_knowledge_hybrid_search.py) --
kein Netzwerk, kein Ollama. Ein optionaler Zusatzlauf mit echtem Modell ist
NICHT Teil dieses Skripts (siehe Plan §5: "als getrennter Zusatzlauf sinnvoll,
nicht als Grundmaß").

Der Zeitpunkt wird als CLI-Argument uebergeben, nie zur Laufzeit gezogen --
sonst waere ein Ergebnis nicht reproduzierbar vergleichbar.

geaenderte Dateien: KEINE ausserhalb dieses Verzeichnisses. schema.sql,
knowledge_mcp_server.py, embeddings.py, knowledge_recall_hook.py werden nur
gelesen/importiert; ihre Modulattribute (DB_PATH, DB, embed_text,
hybrid_retrieval_weight) werden zur Laufzeit dieses Prozesses umgebogen --
exakt das Muster aus tests/test_knowledge_hybrid_search.py
(`monkeypatch.setattr(kms, "DB_PATH", db_path)`), hier ohne pytest von Hand.
"""
from __future__ import annotations

import argparse
import json
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
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402
import embeddings  # type: ignore  # noqa: E402
import knowledge_recall_hook as hook  # type: ignore  # noqa: E402

MESSLAUF_VERSION = "1.0.0"
DEFAULT_K = 5
_SCHEMA_SQL = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")


# --- Korpus -> DB -------------------------------------------------------

def _populate_db(db_path: Path, corpus: dict) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_SCHEMA_SQL)
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


def _combined_queries(corpus: dict) -> list[dict]:
    """Anfragen mit vereinheitlichter (namespaced) Ground Truth:
    'node:<path>' / 'lesson:<id>' -- Nodes und Lessons in einem Ranking-Raum,
    weil beide Abrufwege beides gemeinsam zurueckgeben (siehe hook.query())."""
    out = []
    for q in corpus["queries"]:
        relevant = {f"node:{p}" for p in q["relevant_node_paths"]} | \
                   {f"lesson:{i}" for i in q["relevant_lesson_ids"]}
        out.append({"id": q["id"], "text": q["text"], "topic_id": q["topic_id"], "relevant": relevant})
    return out


# --- Synthetische Vektoren (kein Modell, keine Netzwerk) -----------------

def _install_synthetic_embeddings(db_path: Path, corpus: dict, queries: list[dict]) -> None:
    """Ein-Hot-Vektor je Themen-Kennung -- Knoten/Lessons desselben Themas
    liegen exakt aufeinander (Cosine=1), verschiedene Themen orthogonal
    (Cosine=0). Reine Konstruktion, keine Bedeutung wird beurteilt."""
    topic_ids = sorted({n["topic_id"] for n in corpus["nodes"]} | {l["topic_id"] for l in corpus["lessons"]}
                        | {q["topic_id"] for q in queries})
    index = {t: i for i, t in enumerate(topic_ids)}

    def vec(topic_id: str) -> list[float]:
        v = [0.0] * len(topic_ids)
        v[index[topic_id]] = 1.0
        return v

    conn = sqlite3.connect(str(db_path))
    rows = []
    for n in corpus["nodes"]:
        rows.append(("node", n["id"], "synthetic-topic-onehot", embeddings.pack_embedding(vec(n["topic_id"])),
                     "2026-08-05T00:00:00+01:00"))
    for l in corpus["lessons"]:
        rows.append(("lesson", l["id"], "synthetic-topic-onehot", embeddings.pack_embedding(vec(l["topic_id"])),
                     "2026-08-05T00:00:00+01:00"))
    conn.executemany(
        "INSERT OR REPLACE INTO knowledge_embeddings (kind, ref_id, model, vector, updated_at) "
        "VALUES (?,?,?,?,?)", rows,
    )
    conn.commit()
    conn.close()

    text_to_vec = {q["text"]: vec(q["topic_id"]) for q in queries}
    embeddings.embed_text = lambda text, *a, **k: text_to_vec.get(text)  # type: ignore


def _disable_embeddings() -> None:
    embeddings.embed_text = lambda *a, **k: None  # type: ignore


# --- Retrieval-Adapter: vorhandene Abruffunktionen, unveraendert ---------

def _retrieve_recall_hook(q: dict, rand) -> list[str]:
    """scripts/knowledge_recall_hook.py::query() -- MIN_HITS=3, BM25-Ranking.
    Repliziert main()'s Vorab-Gate (zu wenig Keywords -> gar nicht fragen),
    ruft sonst die unveraenderte query()-Funktion."""
    kws = hook.keywords(q["text"])
    if len(kws) < hook.MIN_HITS:
        return []
    nodes, lessons = hook.query(kws, rand=rand)
    return [f"node:{n['path']}" for n in nodes] + [f"lesson:{l['id']}" for l in lessons]


def _retrieve_hybrid(q: dict, k: int) -> list[str]:
    """knowledge_mcp_server.py::knowledge_search()/lesson_query() -- Hybrid
    Stichwort + optionale Embedding-RRF-Fusion (Gewicht ueber
    embeddings.hybrid_retrieval_weight(), hier fuer Grundmaß/Vergleichslauf
    per Monkeypatch gesteuert, nicht per ENV)."""
    ns = kms.knowledge_search(q["text"], max_results=k)["results"]
    ls = kms.lesson_query(query=q["text"], max_results=k)["results"]
    return [f"node:{r['path']}" for r in ns] + [f"lesson:{r['id']}" for r in ls]


# --- Kennzahlen -----------------------------------------------------------

def compute_metrics(queries: list[dict], retrieve_fn, *, k: int = DEFAULT_K,
                     total_docs: int | None = None) -> dict:
    """retrieve_fn(q: dict) -> geordnete Liste namespaced IDs ('node:...'/
    'lesson:...'). Fuenf Kennzahlen aus Plan §4, alle ohne Modell rechenbar."""
    recalls, reciprocal_ranks = [], []
    total_retrieved = 0
    false_positive_retrieved = 0
    silence_correct = 0    # stumm UND kein relevantes Dokument vorhanden -> richtig
    silence_wrong = 0      # stumm, obwohl relevante Dokumente vorhanden waeren -> falsch
    covered = set()
    zero_rel_queries = 0

    for q in queries:
        relevant = q["relevant"]
        retrieved = retrieve_fn(q)
        total_retrieved += len(retrieved)
        false_positive_retrieved += sum(1 for r in retrieved if r not in relevant)
        covered.update(retrieved)

        if not relevant:
            zero_rel_queries += 1
            if not retrieved:
                silence_correct += 1
        else:
            if not retrieved:
                silence_wrong += 1
            hit = relevant & set(retrieved[:k])
            recalls.append(len(hit) / len(relevant))
            rank = next((i + 1 for i, r in enumerate(retrieved) if r in relevant), None)
            reciprocal_ranks.append(1.0 / rank if rank else 0.0)

    n_relevant_queries = len(recalls)
    return {
        "k": k,
        "n_queries": len(queries),
        "n_queries_with_relevant": n_relevant_queries,
        "n_queries_without_relevant": zero_rel_queries,
        "recall_at_k": (sum(recalls) / n_relevant_queries) if n_relevant_queries else None,
        "mrr": (sum(reciprocal_ranks) / n_relevant_queries) if n_relevant_queries else None,
        "false_alarm_rate": (false_positive_retrieved / total_retrieved) if total_retrieved else 0.0,
        "silence_rate_correct": (silence_correct / zero_rel_queries) if zero_rel_queries else None,
        "silence_rate_wrong": (silence_wrong / n_relevant_queries) if n_relevant_queries else None,
        "coverage": (len(covered) / total_docs) if total_docs else None,
        "covered_doc_count": len(covered),
    }


# --- Lauf -------------------------------------------------------------

def run(seed: int = korpus.DEFAULT_SEED, k: int = DEFAULT_K, timestamp: str | None = None) -> dict:
    corpus = korpus.build_corpus(seed=seed)
    queries = _combined_queries(corpus)
    total_docs = len(corpus["nodes"]) + len(corpus["lessons"])

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge_pruefstand.db"
        _populate_db(db_path, corpus)
        kms.DB_PATH = db_path
        hook.DB = str(db_path)

        started = time.perf_counter()

        # Config 1: heutige Vorgabekonfiguration -- MIN_HITS=3, BM25 (recall_hook,
        # unveraendert). Deterministisch: rand() liefert immer 1.0 -> Erkundung
        # (EXPLORE_RATE) greift nie, keine verdeckte Zufallsquelle im Messlauf.
        m_hook = compute_metrics(queries, lambda q: _retrieve_recall_hook(q, rand=lambda: 1.0),
                                  k=k, total_docs=total_docs)

        # Config 2: Hybrid ohne Vektoren == reine Stichwort/BM25-Reihenfolge
        # ueber knowledge_search()/lesson_query() (embedding_weight bleibt
        # Default, aber embed_text() liefert None -> automatischer Rueckfall).
        _disable_embeddings()
        m_hybrid_keyword_only = compute_metrics(queries, lambda q: _retrieve_hybrid(q, k),
                                                 k=k, total_docs=total_docs)

        # Config 3: Hybrid MIT synthetischen Vektoren (Ein-Hot je Thema,
        # embedding_weight=Default aus embeddings.hybrid_retrieval_weight()).
        _install_synthetic_embeddings(db_path, corpus, queries)
        m_hybrid_with_vectors = compute_metrics(queries, lambda q: _retrieve_hybrid(q, k),
                                                 k=k, total_docs=total_docs)

        runtime = time.perf_counter() - started

    result = {
        "messlauf_version": MESSLAUF_VERSION,
        "corpus_version": corpus["version"],
        "corpus_seed": seed,
        "corpus_checksum": corpus["checksum"],
        "timestamp": timestamp,
        "k": k,
        "counts": {"nodes": len(corpus["nodes"]), "lessons": len(corpus["lessons"]), "queries": len(queries)},
        "model_calls_made": False,
        "network_calls_made": False,
        "runtime_seconds": runtime,
        "configs": {
            "recall_hook_min_hits3_bm25": m_hook,
            "hybrid_bm25_only_no_vectors": m_hybrid_keyword_only,
            "hybrid_rrf_synthetic_vectors": m_hybrid_with_vectors,
        },
    }
    return result


# --- Selftest -----------------------------------------------------------

def selftest() -> None:
    corpus = korpus.build_corpus()
    queries = _combined_queries(corpus)
    total_docs = len(corpus["nodes"]) + len(corpus["lessons"])

    def all_correct(q):
        return list(q["relevant"])

    def nothing(q):
        return []

    IMPOSSIBLE = "node:/pruefstand/does-not-exist"

    def only_wrong(q):
        return [IMPOSSIBLE]

    # k gross genug fuer JEDES relevante Set (das dominante Thema hat weit
    # mehr als DEFAULT_K relevante Treffer) -- sonst kappt der Top-k-
    # Ausschnitt selbst einen vollstaendigen Treffer rechnerisch unter 1.0.
    # Das waere ein Artefakt der k-Wahl, keine Aussage ueber die Eckpunkte.
    big_k = max(len(q["relevant"]) for q in queries) + 1

    m_all = compute_metrics(queries, all_correct, k=big_k, total_docs=total_docs)
    assert m_all["recall_at_k"] == 1.0, m_all
    assert m_all["mrr"] == 1.0, m_all
    assert m_all["false_alarm_rate"] == 0.0, m_all

    m_none = compute_metrics(queries, nothing, k=big_k, total_docs=total_docs)
    assert m_none["recall_at_k"] == 0.0, m_none
    assert m_none["silence_rate_correct"] == 1.0, m_none
    assert m_none["silence_rate_wrong"] == 1.0, m_none

    m_wrong = compute_metrics(queries, only_wrong, k=big_k, total_docs=total_docs)
    assert m_wrong["recall_at_k"] == 0.0, m_wrong
    assert m_wrong["false_alarm_rate"] == 1.0, m_wrong

    # Gegenprobe (Abnahme #2): NUR die Anfragen ohne relevante Dokumente.
    zero_qs = [q for q in queries if not q["relevant"]]
    assert zero_qs, "Korpus muss zero-hit-Anfragen enthalten (Pathologie zero_hit_queries)"
    m_zero_silent = compute_metrics(zero_qs, nothing, total_docs=total_docs)
    assert m_zero_silent["silence_rate_correct"] == 1.0, "stumm bei Anfrage ohne Treffer muss 'zu Recht' zaehlen"
    m_zero_noisy = compute_metrics(zero_qs, only_wrong, total_docs=total_docs)
    assert m_zero_noisy["false_alarm_rate"] == 1.0, "jede Ausgabe bei Anfrage ohne Treffer muss Fehlalarm zaehlen"

    result = run(timestamp="2026-08-05T00:00:00+0200")
    assert result["network_calls_made"] is False
    for name, m in result["configs"].items():
        assert m["n_queries"] == len(queries), name

    print(f"messlauf.py selftest ok (version={MESSLAUF_VERSION}, "
          f"corpus_checksum={corpus['checksum'][:12]}..., runtime={result['runtime_seconds']:.2f}s)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=korpus.DEFAULT_SEED)
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--timestamp", type=str, default=None,
                     help="uebergebener Zeitstempel (ISO 8601), NICHT zur Laufzeit gezogen")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    if not args.timestamp:
        print("Fehler: --timestamp ist Pflicht (ausser bei --selftest) -- "
              "kein Zeitstempel zur Laufzeit, sonst nicht reproduzierbar vergleichbar.", file=sys.stderr)
        sys.exit(1)

    result = run(seed=args.seed, k=args.k, timestamp=args.timestamp)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
