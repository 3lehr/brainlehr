"""Auswertung des Schreiblaufs (Plan C3,
docs/PLAN_SCHREIBPRUEFSTAND_2026-08-05.md).

Nimmt ein oder zwei Protokolle aus schreiblauf.py (--out-Datei) und einen
frisch gebauten Demo-DB-Pfad, und liefert:
  - Annahmequote, Ablehnungen nach Grund, unbrauchbare Antworten
  - bei zwei Laeufen: Streuung der Annahmequote
  - knowledge_lint.py::run() gegen die Demo-DB (importiert, nie geaendert)
    im Vergleich zur echten Datenbank (NUR LESEND, mode=ro erzwungen von
    knowledge_lint.py selbst), Befunde je Kategorie auf Bestandsgroesse
    (Knotenzahl) bezogen.

Bewertet nichts, empfiehlt nichts (Plan §7 Abnahme 7) -- reine Zahlen.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

SCHREIBPRUEFSTAND_DIR = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = SCHREIBPRUEFSTAND_DIR.parent
sys.path.insert(0, str(SCHREIBPRUEFSTAND_DIR))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import demo_db  # noqa: E402
import knowledge_lint  # noqa: E402
import schreiblauf  # noqa: E402

REAL_DB_PATH = SHARED_KNOWLEDGE / "brainlehr.db"
NO_RECALL_LOG = SCHREIBPRUEFSTAND_DIR / "demo" / "no_recall_log.jsonl"  # existiert nicht -> leere Treffermenge


def _node_count(db_path: Path) -> int:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    n = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    return n


_FINDING_LIST_KEYS = [
    "orphans", "stale", "never_pulled_nodes", "never_pulled_lessons",
    "vector_gaps", "near_duplicate_lessons", "path_hygiene",
    "truncated_embeddings",
]


def lint_per_bestand(lint_result: dict, node_count: int) -> dict:
    """Fundzahl je Kategorie, absolut und auf 100 Knoten normiert."""
    out = {}
    for key in _FINDING_LIST_KEYS:
        count = len(lint_result[key])
        out[key] = {
            "count": count,
            "per_100_nodes": (count / node_count * 100) if node_count else None,
        }
    esc = lint_result["escalated_without_rule"]
    esc_count = len(esc["never_linked"]) + len(esc["dangling_ref"])
    out["escalated_without_rule"] = {
        "count": esc_count,
        "per_100_nodes": (esc_count / node_count * 100) if node_count else None,
    }
    return out


def compare_lint(demo_db_path: Path) -> dict:
    demo_result = knowledge_lint.run(db_path=demo_db_path, log_path=NO_RECALL_LOG)
    demo_nodes = _node_count(demo_db_path)

    real_result = None
    real_nodes = None
    if REAL_DB_PATH.exists():
        real_result = knowledge_lint.run(db_path=REAL_DB_PATH)  # echter recall_log.jsonl-Default, nur gelesen
        real_nodes = _node_count(REAL_DB_PATH)

    comparison = {
        "demo": {"node_count": demo_nodes, "per_category": lint_per_bestand(demo_result, demo_nodes)},
        "real": {"node_count": real_nodes, "per_category": lint_per_bestand(real_result, real_nodes)}
                if real_result else None,
    }
    return comparison


def acceptance_spread(summaries: list[dict]) -> dict:
    rates = [s["acceptance_rate"] for s in summaries if s["acceptance_rate"] is not None]
    if len(rates) < 2:
        return {"n_runs": len(rates), "rates": rates, "spread": None}
    return {"n_runs": len(rates), "rates": rates, "spread": max(rates) - min(rates)}


def run(protocol_paths: list[Path]) -> dict:
    results = [json.loads(p.read_text(encoding="utf-8")) for p in protocol_paths]
    summaries = [schreiblauf.summarize(r) for r in results]

    demo_db_path = Path(results[-1]["db_path"])  # letzter Lauf hat die Demo-DB gefuellt

    return {
        "runs": [{"protocol_path": str(p), **s} for p, s in zip(protocol_paths, summaries)],
        "acceptance_spread": acceptance_spread(summaries),
        "lint_comparison": compare_lint(demo_db_path),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("protocols", nargs="+", type=Path, help="ein oder zwei schreiblauf.py --out Dateien")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    result = run(args.protocols)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"geschrieben: {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
