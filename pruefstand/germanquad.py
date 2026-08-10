"""GermanQuAD-Retrieval-Zusatzlauf gegen das echte lokale Modell (Auftrag
2026-08-05: "Ob nomic-embed-text fuer deutsche Texte taugt, wurde nie
geprüft").

Oeffentliches Vergleichsmaterial statt synthetischem Korpus: mteb/germanquad-
retrieval (Dokumente+Fragen, Apache-Arrow-Format) und
mteb/germanquad-retrieval-qrels (Ground-Truth-Zuordnung Frage->Dokument),
beides auf huggingface.co, oeffentlich, ohne Anmeldung.

Bezugsweg (Abnahme #1, gemessen 2026-08-05, nicht angenommen):
  https://datasets-server.huggingface.co/first-rows
      ?dataset=mteb/germanquad-retrieval&config=corpus&split=corpus
      ?dataset=mteb/germanquad-retrieval&config=queries&split=queries
    JSON, Feld "rows" -> [{"row": {"_id": "...", "text": "..."}}, ...].
    Deprecated-aber-live HF-Endpunkt. HARTE GRENZE: liefert nur die ERSTEN
    ~97-100 Zeilen (dataset-seitiges truncated=true, kein offset-Parameter).
  https://datasets-server.huggingface.co/rows
      ?dataset=mteb/germanquad-retrieval-qrels&config=default&split=test
      &offset=<n>&length=100
    JSON, paginiert (num_rows_total=2204), funktioniert fuer DIESES Dataset
    einwandfrei -- alle Query/Dokument-Zuordnungen erreichbar.

ABWEICHUNG vom Auftrag, hier ausdruecklich gemeldet statt verschwiegen: der
identische /rows-Endpunkt liefert fuer die Configs "corpus" und "queries"
DESSELBEN Datasets reproduzierbar HTTP 500 ("Unexpected error") -- gemessen
in >10 Versuchen ueber mehrere Minuten, waehrend derselbe Endpunkt fuer
config=qrels (selbes Dataset) UND fuer ein Kontroll-Dataset (rajpurkar/squad)
sofort funktioniert. Kein Auth-/Rate-Limit-Symptom (kein 401/429), sondern
ein serverseitiger Fehler nur fuer diese zwei Configs. /filter meldet dazu
einmalig "the dataset index is loading" und bleibt danach beim selben 500.
Die rohen .arrow-Dateien selbst liegen vor (siehe API-Antwort), aber ihr
Parsen braucht pyarrow -- laut Auftrag keine neue Abhaengigkeit. Konsequenz:
Korpus und Fragen sind auf die ersten ~97 bzw. 100 Zeilen dieses einen
Datasets gedeckelt, NICHT auf die im Auftrag genannten ~300/100 (die waeren
mit mehr Datensaetzen erreichbar, hier limitiert der kaputte Endpunkt, nicht
die Vorgabe). Die tatsaechlich genutzte Zahl steht wie gefordert im Ergebnis.

Zwischenspeicher: shared-knowledge/pruefstand/daten/germanquad/ (gitignored,
Wiederholungslauf laedt nicht neu, wenn die drei JSON-Dateien schon da sind).

WAS DIESE ZAHLEN NICHT AUSSAGEN: sie bewerten ausschliesslich das
Einbettungsmodell nomic-embed-text auf einem fremden, allgemeinsprachlichen
Korpus (Wikipedia-Ausschnitte). Keine Aussage ueber unser Wissenssystem
(BM25/Hybrid-Suche, MIN_HITS, Rueckruf-Hook) -- dafuer gilt weiterhin
messlauf.py mit dem synthetischen Korpus. Auch keine Aussage ueber die
GESAMTE GermanQuAD-Verteilung, da nur der erste, nicht-zufaellige Ausschnitt
des Datasets erreichbar war (moeglicher Stichproben-Bias durch Alphabet-/
Einfuegereihenfolge).

geaenderte Dateien: KEINE ausserhalb dieser Datei und ihres Datenverzeichnisses.
messlauf.py (compute_metrics), korpus.py, vergleichslauf.py, embeddings.py
werden nur importiert.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PRUEFSTAND_DIR = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = PRUEFSTAND_DIR.parent
HUB_ROOT = SHARED_KNOWLEDGE.parent
DATA_DIR = PRUEFSTAND_DIR / "daten" / "germanquad"
sys.path.insert(0, str(PRUEFSTAND_DIR))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(HUB_ROOT / "scripts"))

import messlauf as ml  # type: ignore  # noqa: E402
import embeddings  # type: ignore  # noqa: E402

GERMANQUAD_VERSION = "1.0.0"
DEFAULT_DOCS = 300      # Vorgabe laut Auftrag -- real gedeckelt durch first-rows, siehe Modul-Docstring
DEFAULT_QUERIES = 100
DEFAULT_K = 5
CHARS_PER_TOKEN_APPROX = 4.0  # ponytail: kein Tokenizer als neue Abhaengigkeit; grobe Naeherung,
# nach oben zu korrigieren (mehr Treffer ueber 2048) sollte ein echter Tokenizer je verfuegbar werden.

HF_DATASET = "mteb/germanquad-retrieval"
HF_QRELS_DATASET = "mteb/germanquad-retrieval-qrels"
FIRST_ROWS_URL = "https://datasets-server.huggingface.co/first-rows"
ROWS_URL = "https://datasets-server.huggingface.co/rows"


def _get_json(url: str, timeout: float = 30.0) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _fetch_first_rows(dataset: str, config: str, split: str) -> list[dict]:
    url = f"{FIRST_ROWS_URL}?dataset={dataset}&config={config}&split={split}"
    data = _get_json(url)
    return [r["row"] for r in data["rows"]]


def _fetch_all_qrels(dataset: str, config: str, split: str, page_size: int = 100) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        url = f"{ROWS_URL}?dataset={dataset}&config={config}&split={split}&offset={offset}&length={page_size}"
        data = _get_json(url)
        page = [r["row"] for r in data["rows"]]
        rows.extend(page)
        total = data.get("num_rows_total", len(rows))
        offset += len(page)
        if not page or offset >= total:
            break
    return rows


def download(force: bool = False) -> dict:
    """Laedt corpus/queries/qrels einmalig und legt sie unter DATA_DIR ab.
    Vorhandene Dateien werden wiederverwendet (kein erneuter Netzzugriff),
    ausser force=True."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / ".gitignore").write_text("*\n", encoding="utf-8")

    paths = {
        "corpus": DATA_DIR / "corpus.json",
        "queries": DATA_DIR / "queries.json",
        "qrels": DATA_DIR / "qrels.json",
    }

    if force or not paths["corpus"].exists():
        rows = _fetch_first_rows(HF_DATASET, "corpus", "corpus")
        paths["corpus"].write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    if force or not paths["queries"].exists():
        rows = _fetch_first_rows(HF_DATASET, "queries", "queries")
        paths["queries"].write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    if force or not paths["qrels"].exists():
        rows = _fetch_all_qrels(HF_QRELS_DATASET, "default", "test")
        paths["qrels"].write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    return {name: json.loads(p.read_text(encoding="utf-8")) for name, p in paths.items()}


# --- Korpus/Fragen zusammenbauen -----------------------------------------

def build_dataset(n_docs: int, n_queries: int, *, force_download: bool = False) -> dict:
    raw = download(force=force_download)
    corpus_rows = raw["corpus"][:n_docs]
    corpus_ids = {r["_id"] for r in corpus_rows}

    # Ground Truth nach Korpus-Teilmenge filtern -- eine Anfrage, deren
    # Zieldokument nicht im gedeckelten Korpus liegt, kann per Konstruktion
    # nie gefunden werden; das waere ein Artefakt der Deckelung, kein
    # Modellfehler (gleiches Prinzip wie messlauf.py: Ground Truth gehoert
    # zum tatsaechlich befragten Bestand).
    relevant_by_query: dict[str, set[str]] = {}
    for r in raw["qrels"]:
        if r["corpus-id"] in corpus_ids:
            relevant_by_query.setdefault(r["query-id"], set()).add(r["corpus-id"])

    query_rows = [r for r in raw["queries"] if r["_id"] in relevant_by_query][:n_queries]

    queries = [{"id": r["_id"], "text": r["text"], "relevant": {f"doc:{c}" for c in relevant_by_query[r["_id"]]}}
               for r in query_rows]

    return {
        "corpus": [{"id": r["_id"], "text": r["text"]} for r in corpus_rows],
        "queries": queries,
    }


def count_oversized(corpus: list[dict], limit_tokens: int = 2048) -> dict:
    limit_chars = limit_tokens * CHARS_PER_TOKEN_APPROX
    over = [d["id"] for d in corpus if len(d["text"]) > limit_chars]
    return {"limit_tokens": limit_tokens, "chars_per_token_approx": CHARS_PER_TOKEN_APPROX,
            "over_limit_count": len(over), "over_limit_ids": over, "total": len(corpus)}


# --- Einbettung + Retrieval -------------------------------------------

def embed_corpus_and_queries(corpus: list[dict], queries: list[dict], *, model: str) -> tuple[dict, dict]:
    doc_vecs: dict[str, list[float]] = {}
    for d in corpus:
        vec = embeddings.embed_text(d["text"], model=model)
        if vec is None:
            raise RuntimeError(f"Ollama/{model} nicht erreichbar oder Fehler beim Einbetten von Dokument {d['id']}")
        doc_vecs[f"doc:{d['id']}"] = vec

    query_vecs: dict[str, list[float]] = {}
    for q in queries:
        vec = embeddings.embed_text(q["text"], model=model)
        if vec is None:
            raise RuntimeError(f"Ollama/{model} nicht erreichbar oder Fehler beim Einbetten von Frage {q['id']}")
        query_vecs[q["id"]] = vec

    return doc_vecs, query_vecs


def make_retrieve_fn(doc_vecs: dict[str, list[float]], query_vecs: dict[str, list[float]], *, k: int):
    """Liefert nur die Top-k, wie ein echtes Retrieval-System (hook.query()/
    knowledge_search() in messlauf.py schneiden ebenfalls vor der Rueckgabe
    ab) -- sonst zaehlt compute_metrics() jeden ungenutzten Rest-Kandidaten
    als Fehlalarm und false_alarm_rate misst nur die Korpusgroesse, nicht
    die Rankingqualitaet."""
    def retrieve(q: dict) -> list[str]:
        qvec = query_vecs[q["id"]]
        ranked = sorted(doc_vecs.items(), key=lambda kv: embeddings.cosine_similarity(qvec, kv[1]), reverse=True)
        return [doc_id for doc_id, _ in ranked[:k]]
    return retrieve


# --- Gegenprobe: gemischte (falsch zugeordnete) Fragen --------------------

def shuffled_queries(queries: list[dict], *, seed: int = 1) -> list[dict]:
    """Text bleibt, relevant-Menge wird zwischen Fragen vertauscht (fixe
    Permutation ohne Fixpunkt wo moeglich) -- die Gegenprobe aus Abnahme #4:
    misst dasselbe Verfahren, aber mit falscher Ground Truth. Ein Recall/MRR,
    das dabei nicht deutlich einbricht, zeigt, dass nicht das Retrieval
    gemessen wurde."""
    rnd = random.Random(seed)
    relevants = [q["relevant"] for q in queries]
    shuffled = relevants[:]
    rnd.shuffle(shuffled)
    # Fixpunkte (Frage behaelt zufaellig ihre eigene relevant-Menge) einmal nachschieben
    for i in range(len(shuffled)):
        if shuffled[i] == relevants[i] and len(shuffled) > 1:
            j = (i + 1) % len(shuffled)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return [{"id": q["id"], "text": q["text"], "relevant": rel} for q, rel in zip(queries, shuffled)]


# --- Lauf -------------------------------------------------------------

def run(*, n_docs: int, n_queries: int, k: int, model: str, timestamp: str,
        force_download: bool = False) -> dict:
    started = time.perf_counter()
    ds = build_dataset(n_docs, n_queries, force_download=force_download)
    corpus, queries = ds["corpus"], ds["queries"]

    oversized = count_oversized(corpus)

    doc_vecs, query_vecs = embed_corpus_and_queries(corpus, queries, model=model)
    retrieve = make_retrieve_fn(doc_vecs, query_vecs, k=k)
    metrics = ml.compute_metrics(queries, retrieve, k=k, total_docs=len(corpus))

    shuffled = shuffled_queries(queries)
    metrics_shuffled = ml.compute_metrics(shuffled, retrieve, k=k, total_docs=len(corpus))

    runtime = time.perf_counter() - started

    return {
        "germanquad_version": GERMANQUAD_VERSION,
        "timestamp": timestamp,
        "model": model,
        "source_dataset": HF_DATASET,
        "source_qrels_dataset": HF_QRELS_DATASET,
        "requested": {"n_docs": n_docs, "n_queries": n_queries},
        "used": {"n_docs": len(corpus), "n_queries": len(queries)},
        "k": k,
        "runtime_seconds": runtime,
        "oversized_2048_tokens": oversized,
        "metrics": metrics,
        "metrics_shuffled_control": metrics_shuffled,
        "caveat": ("Diese Zahlen bewerten nur das Einbettungsmodell auf einem fremden "
                   "Wikipedia-Ausschnitt, nicht unser Wissenssystem. Korpus/Fragen sind auf "
                   "die ersten Zeilen des Datasets gedeckelt (Endpunkt-Grenze, siehe Modul-Docstring), "
                   "keine Zufallsstichprobe -- moeglicher Bias."),
    }


# --- Selftest (kein Netz) --------------------------------------------

def selftest() -> None:
    """Winziges eingebautes Beispiel, bekanntes Ergebnis -- belegt, dass
    messlauf.compute_metrics() hier wiederverwendet wird (kein Netz, kein
    Ollama)."""
    queries = [
        {"id": "q1", "text": "alles richtig", "relevant": {"doc:a", "doc:b"}},
        {"id": "q2", "text": "nichts gefunden", "relevant": {"doc:c"}},
    ]

    # Feste, von q["relevant"] UNABHAENGIGE Modellantwort (simuliert ein
    # Retrieval, das immer dieselbe, fuer die urspruengliche Zuordnung
    # richtige Reihenfolge liefert) -- sonst wuerde ein retrieve_fn, das
    # q["relevant"] direkt zurueckgibt, auch nach dem Vertauschen der
    # Ground Truth trivial "perfekt" aussehen und die Gegenprobe waere
    # zirkulaer.
    fixed_answer = {"q1": ["doc:a", "doc:b"], "q2": ["doc:c"]}

    def retrieve_fixed(q: dict) -> list[str]:
        return fixed_answer[q["id"]]

    def retrieve_nothing(q: dict) -> list[str]:
        return []

    m_all = ml.compute_metrics(queries, retrieve_fixed, k=5, total_docs=3)
    assert m_all["recall_at_k"] == 1.0, m_all
    assert m_all["mrr"] == 1.0, m_all

    m_none = ml.compute_metrics(queries, retrieve_nothing, k=5, total_docs=3)
    assert m_none["recall_at_k"] == 0.0, m_none

    # Gegenprobe-Mechanik isoliert pruefen: geshuffelte Ground Truth gegen
    # dasselbe FESTE Retrieval -- Recall muss einbrechen, weil die Antwort
    # jetzt zur falschen relevant-Menge passt.
    shuffled = shuffled_queries(queries, seed=7)
    assert {q["id"] for q in shuffled} == {q["id"] for q in queries}
    m_shuffled = ml.compute_metrics(shuffled, retrieve_fixed, k=5, total_docs=3)
    assert m_shuffled["recall_at_k"] is not None
    assert m_shuffled["recall_at_k"] < m_all["recall_at_k"], "Gegenprobe muss schlechter sein als korrekte Zuordnung"

    over = count_oversized([{"id": "x", "text": "a" * 100}, {"id": "y", "text": "a" * (2049 * 4 + 1)}])
    assert over["over_limit_count"] == 1, over

    print(f"germanquad.py selftest ok (version={GERMANQUAD_VERSION})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--docs", type=int, default=DEFAULT_DOCS)
    ap.add_argument("--queries", type=int, default=DEFAULT_QUERIES)
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--model", type=str, default=embeddings.DEFAULT_EMBED_MODEL)
    ap.add_argument("--timestamp", type=str, default=None,
                     help="uebergebener Zeitstempel (ISO 8601), NICHT zur Laufzeit gezogen")
    ap.add_argument("--force-download", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    if not args.timestamp:
        print("Fehler: --timestamp ist Pflicht (ausser bei --selftest) -- "
              "kein Zeitstempel zur Laufzeit, sonst nicht reproduzierbar vergleichbar.", file=sys.stderr)
        sys.exit(1)

    result = run(n_docs=args.docs, n_queries=args.queries, k=args.k, model=args.model,
                 timestamp=args.timestamp, force_download=args.force_download)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
