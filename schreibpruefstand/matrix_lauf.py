"""Matrix: 4 Modelle x 8 Rohmaterial-Stuecke (Laufzeit-Kompromiss, nicht 23),
Demo-DB je Modell frisch (schreiblauf.run()/lmstudio_lauf.run() bauen das
selbst). Fragestellung: tragen die knowledge_add-Werkzeugbeschreibungen
modellübergreifend, wo scheitert das kleinste Modell zuerst.

Treiber-Wahl je Modell: Ollama-Modelle (gemma4:*) ueber schreiblauf.py
(/api/generate, Schema als Text im Prompt), LM-Studio-Modelle ueber
lmstudio_lauf.py (/v1/chat/completions, natives tool-calling).

geaenderte Dateien ausserhalb dieses Verzeichnisses: KEINE. runs/lauf1.json
und runs/lauf2.json werden nicht angefasst -- eigene Dateinamen (matrix-*).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

SCHREIBPRUEFSTAND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCHREIBPRUEFSTAND_DIR))

import demo_db  # noqa: E402
import lmstudio_lauf  # noqa: E402
import schreiblauf  # noqa: E402

N_PIECES = 8
OUT_DIR = SCHREIBPRUEFSTAND_DIR / "runs"

# (Anzeigename, Treiber-Modul, Modell-Kennung fuer den Treiber)
MODELS = [
    ("gemma4:e4b", schreiblauf, "gemma4:e4b"),
    ("gemma4:12b", schreiblauf, "gemma4:12b"),
    ("gemma4:31b", schreiblauf, "gemma4:31b"),
    ("qwen3-coder-30b (LM Studio)", lmstudio_lauf, lmstudio_lauf.DEFAULT_MODEL),
]


def _source_set_by_model(protocol: list[dict]) -> tuple[int, int]:
    """(Anzahl mit nicht-leerem source-Feld im Modellwunsch, Anzahl mit
    einem geparsten Modellwunsch ueberhaupt) -- Nenner ist NICHT n_pieces,
    weil ein Werkzeugausfall/unparsbare Antwort keine Aussage ueber 'source'
    zulaesst."""
    with_wanted = [r for r in protocol if r.get("model_wanted")]
    with_source = [r for r in with_wanted if str(r["model_wanted"].get("source", "")).strip()]
    return len(with_source), len(with_wanted)


def _first_failure(protocol: list[dict]) -> dict | None:
    """Erstes Rohmaterial-Stueck, das NICHT angenommen wurde -- roh, keine
    Ursachenzuschreibung ausser der vom System selbst gelieferten reason."""
    for r in protocol:
        if not r.get("accepted"):
            return {"material_id": r["material_id"], "category": r["category"], "reason": r.get("reason")}
    return None


def run_matrix() -> dict:
    OUT_DIR.mkdir(exist_ok=True)
    pieces = demo_db.RAW_MATERIAL[:N_PIECES]
    rows = []

    for display_name, driver, model_id in MODELS:
        print(f"=== {display_name} ===", file=sys.stderr)
        t0 = time.perf_counter()
        try:
            result = driver.run(model=model_id, pieces=pieces)
        except Exception as exc:  # Modell/Server nicht erreichbar -- melden, nicht ausweichen
            rows.append({
                "model": display_name,
                "n_pieces": N_PIECES,
                "run_error": f"{type(exc).__name__}: {exc}",
                "runtime_seconds": time.perf_counter() - t0,
            })
            print(f"  FEHLER: {exc}", file=sys.stderr)
            continue

        summary = driver.summarize(result)
        n_source, n_wanted = _source_set_by_model(result["protocol"])
        row = {
            "model": display_name,
            "n_pieces": summary["n_pieces"],
            "n_accepted": summary["n_accepted"],
            "acceptance_rate": summary["acceptance_rate"],
            "n_gate_rejected": summary["n_gate_rejected"],
            "n_tool_failure": summary["n_tool_failure"],
            "gate_rejection_reasons": summary["gate_rejection_reasons"],
            "tool_failure_reasons": summary["tool_failure_reasons"],
            "source_set_by_model": f"{n_source}/{n_wanted}" if n_wanted else "0/0 (kein parsbarer Wunsch)",
            "first_failure": _first_failure(result["protocol"]),
            "runtime_seconds": result["runtime_seconds"],
        }
        rows.append(row)

        safe_name = display_name.split(" ")[0].replace(":", "-").replace("/", "-")
        out_path = OUT_DIR / f"matrix-{safe_name}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(row, ensure_ascii=False, indent=2), file=sys.stderr)

    return {"n_pieces": N_PIECES, "rows": rows}


if __name__ == "__main__":
    matrix = run_matrix()
    print(json.dumps(matrix, ensure_ascii=False, indent=2))
