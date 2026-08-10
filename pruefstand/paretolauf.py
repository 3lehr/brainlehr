"""Pareto-Lauf ueber die Abruf-Stellschrauben (Plan
docs/PLAN_ABRUF_PRUEFSTAND_2026-08-05.md, Ergaenzung nach Lehre L-b4b6fc).

L-b4b6fc: Recall@k und Fehlalarmquote sind Mittelwerte ueber die Anfragenmenge
eines KONSTRUIERTEN Korpus. Ein einzelnes "bestes" Ergebnis waere auf eine
Mischung optimiert, die wir selbst gewuerfelt haben. Darum hier KEINE
Einzelzahl-Optimierung, sondern eine mehrzielige Optuna-Studie, die die
Pareto-Front zeigt (Recall@5 maximieren, Fehlalarmquote minimieren, beide als
getrennte Ziele -- eine Gewichtung waere die Vorwegnahme der Entscheidung, die
der Mensch treffen soll). Die Wahl des Punktes bleibt beim Menschen.

Stellschrauben (nur was messlauf.py/vergleichslauf.py tatsaechlich
durchreichen, siehe deren Code -- nichts erfunden):
  - MIN_HITS               (recall_hook, vergleichslauf.run_config-Parameter)
  - Erkundungsanteil       (recall_hook, hook.EXPLORE_RATE -- modul-globale
                             Konstante, hier wie MIN_HITS in vergleichslauf.py
                             per Monkeypatch vor dem Aufruf gesetzt/restauriert;
                             vergleichslauf.py selbst reicht nur einen festen
                             An/Aus-Wuerfel durch, keinen numerischen Wert)
  - Fusionsgewicht         (hybrid, embeddings.hybrid_retrieval_weight() --
                             derselbe Modul-Seam, den messlauf.py fuer
                             embed_text() schon per Monkeypatch umbiegt)
Nicht durchgereicht und darum NICHT erfunden: Index-Feld-Auswahl ist in
vergleichslauf.py nur binaer (voll/ablatiert), kein kontinuierlicher Parameter
-- bleibt hier aussen vor.

Deterministisch: fester TPESampler-Seed (--sampler-seed). Zwei Anfragen mit
identischem Korpus-Seed und Sampler-Seed liefern dieselbe Zugfolge und damit
dieselbe Pareto-Front (siehe selftest()).

geaenderte Dateien: KEINE ausserhalb dieses Skripts. korpus.py, messlauf.py,
vergleichslauf.py werden importiert, nicht geaendert.

VORBEHALT (gehoert in jeden Bericht, nicht nur hierhin): Die Front gilt fuer
GENAU die Anfragenmischung der angegebenen CORPUS_VERSION. Eine andere
Mischung kann eine andere Front zeigen (siehe Lehre L-b4b6fc).
"""
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

import argparse
import json
import random
import sys
import time
from pathlib import Path

PRUEFSTAND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PRUEFSTAND_DIR))

import korpus  # type: ignore  # noqa: E402
import messlauf as ml  # type: ignore  # noqa: E402
import vergleichslauf as vl  # type: ignore  # noqa: E402

import optuna  # type: ignore  # noqa: E402

PARETOLAUF_VERSION = "1.0.0"
DEFAULT_SAMPLER_SEED = 20260805
DEFAULT_N_TRIALS = 40
EXPLORE_DICE_SEED = 99  # derselbe feste Wuerfel-Seed wie vergleichslauf.EXPLORE_SEED

optuna.logging.set_verbosity(optuna.logging.WARNING)


# --- Eine Konfiguration fahren (wiederverwendet vergleichslauf.run_config,
# patcht nur die zwei Stellschrauben, die dort nicht als Parameter existieren)

def _run_recall_hook(corpus, queries, total_docs, k, *, min_hits: int, explore_rate: float) -> dict:
    old_rate = ml.hook.EXPLORE_RATE
    ml.hook.EXPLORE_RATE = explore_rate
    try:
        rand = random.Random(EXPLORE_DICE_SEED).random  # deterministischer Erkundungs-Wuerfel
        return vl.run_config(corpus, queries, total_docs, retrieval="recall_hook", k=k,
                              min_hits=min_hits, explore_rand=rand)
    finally:
        ml.hook.EXPLORE_RATE = old_rate


def _run_hybrid(corpus, queries, total_docs, k, *, embedding_weight: float) -> dict:
    old_weight_fn = ml.embeddings.hybrid_retrieval_weight
    ml.embeddings.hybrid_retrieval_weight = lambda: embedding_weight
    try:
        return vl.run_config(corpus, queries, total_docs, retrieval="hybrid", k=k, embeddings_mode="rrf")
    finally:
        ml.embeddings.hybrid_retrieval_weight = old_weight_fn


def _objective(trial: "optuna.Trial", corpus, queries, total_docs, k: int) -> tuple[float, float]:
    retrieval = trial.suggest_categorical("retrieval", ["recall_hook", "hybrid"])
    if retrieval == "recall_hook":
        min_hits = trial.suggest_int("min_hits", 1, 6)
        explore_rate = trial.suggest_float("explore_rate", 0.0, 0.5)
        metrics = _run_recall_hook(corpus, queries, total_docs, k, min_hits=min_hits, explore_rate=explore_rate)
    else:
        embedding_weight = trial.suggest_float("embedding_weight", 0.0, 2.0)
        metrics = _run_hybrid(corpus, queries, total_docs, k, embedding_weight=embedding_weight)
    trial.set_user_attr("metrics", metrics)
    recall = metrics["recall_at_k"] or 0.0
    false_alarm = metrics["false_alarm_rate"]
    return recall, false_alarm


# --- Pareto-Front: selbst geprueft, nicht nur optuna.study.best_trials geglaubt

def _dominates(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """a dominiert b: mindestens so gut in beiden Zielen, echt besser in min. einem
    (Ziel 0 = Recall, maximieren; Ziel 1 = Fehlalarm, minimieren)."""
    return a[0] >= b[0] and a[1] <= b[1] and (a[0] > b[0] or a[1] < b[1])


def pareto_front_indices(values: list[tuple[float, float]]) -> list[int]:
    return [i for i, v in enumerate(values)
            if not any(j != i and _dominates(values[j], v) for j in range(len(values)))]


def assert_valid_front(values: list[tuple[float, float]]) -> None:
    """Abnahme #2: kein Punkt der Front darf von einem anderen Punkt der Front
    in BEIDEN Zielen geschlagen werden."""
    for i, a in enumerate(values):
        for j, b in enumerate(values):
            if i != j:
                assert not _dominates(b, a), f"Front-Punkt {a} wird von {b} dominiert -- Front ungueltig"


# --- Lauf -------------------------------------------------------------

def run(seed: int = korpus.DEFAULT_SEED, sampler_seed: int = DEFAULT_SAMPLER_SEED,
        n_trials: int = DEFAULT_N_TRIALS, k: int = ml.DEFAULT_K,
        corpus_version: str = korpus.CORPUS_VERSION_1_2, timestamp: str | None = None) -> dict:
    corpus = korpus.build_corpus(seed=seed, version=corpus_version)
    queries = ml._combined_queries(corpus)
    total_docs = len(corpus["nodes"]) + len(corpus["lessons"])

    study = optuna.create_study(directions=["maximize", "minimize"],
                                 sampler=optuna.samplers.TPESampler(seed=sampler_seed))
    # Referenzpunkte fest einreihen, statt zu hoffen, der Sampler trifft sie:
    # heutige Vorgabe (MIN_HITS=3, EXPLORE_RATE=0.15) und Hybrid-Default
    # (Fusionsgewicht 1.0, siehe embeddings.hybrid_retrieval_weight()-Default).
    study.enqueue_trial({"retrieval": "recall_hook", "min_hits": 3, "explore_rate": 0.15})
    study.enqueue_trial({"retrieval": "hybrid", "embedding_weight": 1.0})

    started = time.perf_counter()
    study.optimize(lambda trial: _objective(trial, corpus, queries, total_docs, k), n_trials=n_trials)
    runtime = time.perf_counter() - started

    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    values = [tuple(t.values) for t in completed]
    front_idx = pareto_front_indices(values)
    front_values = [values[i] for i in front_idx]
    assert_valid_front(front_values)

    front = sorted(
        [{"params": completed[i].params, "recall_at_5": values[i][0], "false_alarm_rate": values[i][1]}
         for i in front_idx],
        key=lambda e: e["recall_at_5"], reverse=True,
    )

    # Die eigentliche Frage: liegt MIN_HITS=3 (heutige Vorgabe) auf der Front?
    ref = next((i for i, t in enumerate(completed)
                if t.params.get("retrieval") == "recall_hook" and t.params.get("min_hits") == 3
                and abs(t.params.get("explore_rate", -1.0) - 0.15) < 1e-9), None)
    min_hits3_on_front = None
    if ref is not None:
        on_front = ref in front_idx
        dominator = None
        if not on_front:
            better = next((i for i in front_idx if _dominates(values[i], values[ref])), None)
            if better is not None:
                dominator = {"params": completed[better].params,
                             "recall_at_5": values[better][0], "false_alarm_rate": values[better][1]}
        min_hits3_on_front = {
            "on_front": on_front,
            "recall_at_5": values[ref][0], "false_alarm_rate": values[ref][1],
            "dominated_by": dominator,
        }

    return {
        "paretolauf_version": PARETOLAUF_VERSION,
        "corpus_version": corpus["version"],
        "corpus_seed": seed,
        "corpus_checksum": corpus["checksum"],
        "sampler_seed": sampler_seed,
        "n_trials_requested": n_trials,
        "n_trials_completed": len(completed),
        "timestamp": timestamp,
        "k": k,
        "counts": {"nodes": len(corpus["nodes"]), "lessons": len(corpus["lessons"]), "queries": len(queries)},
        "model_calls_made": False,
        "network_calls_made": False,
        "runtime_seconds": runtime,
        "front": front,
        "n_dominated": len(completed) - len(front_idx),
        "min_hits3_on_front": min_hits3_on_front,
        "vorbehalt": (f"Front gilt nur fuer Korpus {corpus['version']} -- andere Anfragenmischung "
                      "kann eine andere Front zeigen (Lehre L-b4b6fc)."),
    }


def format_report(result: dict) -> str:
    lines = [
        f"Pareto-Front Abruf-Stellschrauben (Korpus {result['corpus_version']}, "
        f"{result['n_trials_completed']} Versuche, Laufzeit {result['runtime_seconds']:.2f}s)",
        result["vorbehalt"],
        "",
        f"{'Params':<60}{'Recall@5':>12}{'Fehlalarm':>12}",
        "-" * 84,
    ]
    for e in result["front"]:
        lines.append(f"{json.dumps(e['params'], ensure_ascii=False):<60}"
                      f"{e['recall_at_5']:>12.3f}{e['false_alarm_rate']:>12.3f}")
    lines.append("")
    lines.append(f"dominierte Versuche: {result['n_dominated']}")
    m3 = result["min_hits3_on_front"]
    if m3 is None:
        lines.append("MIN_HITS=3 (heutige Vorgabe): nicht im Versuchssatz gefunden.")
    elif m3["on_front"]:
        lines.append(f"MIN_HITS=3 (heutige Vorgabe): liegt AUF der Front "
                      f"(Recall@5={m3['recall_at_5']:.3f}, Fehlalarm={m3['false_alarm_rate']:.3f}).")
    else:
        d = m3["dominated_by"]
        lines.append(f"MIN_HITS=3 (heutige Vorgabe): WIRD DOMINIERT "
                      f"(Recall@5={m3['recall_at_5']:.3f}, Fehlalarm={m3['false_alarm_rate']:.3f}) "
                      f"von {json.dumps(d['params'], ensure_ascii=False)} "
                      f"(Recall@5={d['recall_at_5']:.3f}, Fehlalarm={d['false_alarm_rate']:.3f}).")
    return "\n".join(lines)


# --- Selftest -----------------------------------------------------------

def selftest() -> None:
    # Pareto-Mechanik selbst, ohne Optuna/DB -- bekannte geometrische Faelle.
    pts = [(0.9, 0.1), (0.5, 0.5), (0.9, 0.3), (0.2, 0.9), (0.9, 0.1)]
    front = pareto_front_indices(pts)
    assert set(front) == {0, 4}, front  # (0.9,0.1) zweimal, dominiert alle anderen, unter sich gleich -> beide auf Front
    assert_valid_front([pts[i] for i in front])
    strictly_worse = [(0.1, 0.9), (0.05, 0.95)]  # zweiter Punkt in BEIDEN Zielen schlechter -> dominiert
    front2 = pareto_front_indices(strictly_worse)
    assert front2 == [0], front2
    incomparable = [(0.9, 0.9), (0.1, 0.1)]  # je ein Ziel besser -> keiner dominiert den anderen
    front3 = pareto_front_indices(incomparable)
    assert set(front3) == {0, 1}, front3

    # Determinismus: gleicher Sampler-Seed -> identische Front.
    r_a = run(n_trials=8, sampler_seed=123, timestamp="2026-08-06T00:00:00+0200")
    r_b = run(n_trials=8, sampler_seed=123, timestamp="2026-08-06T00:00:00+0200")
    assert r_a["front"] == r_b["front"], "gleicher sampler_seed muss identische Front liefern"

    # Verschiedener Seed DARF abweichen -- Beleg, dass der Seed ueberhaupt wirkt.
    r_c = run(n_trials=8, sampler_seed=456, timestamp="2026-08-06T00:00:00+0200")
    seeds_differ = r_a["front"] != r_c["front"]
    print(f"  verschiedener sampler_seed liefert {'ABWEICHENDE' if seeds_differ else 'GLEICHE'} Front "
          f"(kein Assert -- beides zulaessig, hier: {'wirkt' if seeds_differ else 'wirkt in diesem Lauf nicht'})")

    assert r_a["model_calls_made"] is False
    assert r_a["network_calls_made"] is False

    print(f"paretolauf.py selftest ok (version={PARETOLAUF_VERSION}, "
          f"front_a={len(r_a['front'])} Punkte, runtime={r_a['runtime_seconds']:.2f}s)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=korpus.DEFAULT_SEED, help="Korpus-Seed")
    ap.add_argument("--sampler-seed", type=int, default=DEFAULT_SAMPLER_SEED)
    ap.add_argument("--n-trials", type=int, default=DEFAULT_N_TRIALS)
    ap.add_argument("--k", type=int, default=ml.DEFAULT_K)
    ap.add_argument("--corpus-version", type=str, default=korpus.CORPUS_VERSION_1_2,
                     choices=list(korpus.CORPUS_VERSIONS))
    ap.add_argument("--timestamp", type=str, default=None,
                     help="uebergebener Zeitstempel (ISO 8601), NICHT zur Laufzeit gezogen")
    ap.add_argument("--out", type=str, default=None, help="Ergebnis als JSON schreiben")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    if not args.timestamp:
        print("Fehler: --timestamp ist Pflicht (ausser bei --selftest) -- "
              "kein Zeitstempel zur Laufzeit, sonst nicht reproduzierbar vergleichbar.", file=sys.stderr)
        sys.exit(1)

    result = run(seed=args.seed, sampler_seed=args.sampler_seed, n_trials=args.n_trials, k=args.k,
                 corpus_version=args.corpus_version, timestamp=args.timestamp)
    print(format_report(result))
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\ngeschrieben: {args.out}")


if __name__ == "__main__":
    main()
