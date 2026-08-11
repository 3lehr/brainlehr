"""Wie wissensnutzen.py, aber Abruf entsteht aus der AUFGABE, nicht aus der
Kenntnis der Loesung (Auftrag 2026-08-07, Knoten 34ef6d8e).

wissensnutzen.py holte den Wissensblock per lesson_query MIT der Kennung der
passenden Lehre im Suchtext -- das misst "hilft es, dem Modell die Loesung in
den Prompt zu schreiben", nicht ob der Abruf sie selbst findet. Hier laeuft
derselbe Weg wie eine echte Sitzung: knowledge_recall_hook.keywords() zerlegt
den unveraenderten Aufgabentext, knowledge_recall_hook.query() sucht damit in
derselben knowledge.db (FTS-Nodes + Lessons-LIKE) -- keine Handauswahl.

ZWEI GROESSEN GETRENNT gemessen, das ist der Kern:
  TREFFERGUETE  war die passende Lehre unter den tatsaechlichen Treffern?
  NUTZEN        loeste das Modell die Aufgabe MIT DEN TATSAECHLICHEN
                Treffern (nicht mit der richtigen Lehre wie in wissensnutzen.py)?
Ein Fall mit Fehlgriff+Modellversagen ist ein anderer Befund als Treffer+
Modellversagen -- die alte Messung konnte das nicht trennen.

AUFGABEN A/B: Prompt-Text und Bewertungsfunktion 1:1 aus wissensnutzen.py
uebernommen (Auftrag: "Uebernimm die deterministische Bewertung von dort,
erfinde keine neue"). target_lesson_id je Aufgabe wortwoertlich aus deren
Docstring (L-c0e910 / L-68ff10), geprueft per lesson_query (2026-08-07).

AUFGABE C (neu, Auftrag Punkt 4): kubectl-Frage, domaenenfremd -- nichts im
Bestand ist dafuer einschlaegig. target_lesson_id=None: es gibt keine
"passende Lehre", Trefferguete ist bei C also per Definition nie "ja".
Bewertung: generisches Fachwissen, Modell muss das nicht aus der DB haben.
Probelauf (2026-08-07) zeigte: der blinde Abruf liefert HIER TROTZDEM einen
Treffer (L-14a742, Codesign-Fehler -- Wortueberschneidung auf Allerwelts-
woertern). Das wird nicht weggefiltert, sondern als Fehlgriff mitgezaehlt --
genau der Fall, den Punkt 4 des Auftrags verlangt ("liefert Trefferguete
nein" heisst: es KANN nicht ja sein, nicht dass der Abruf leer bleiben muss).

Modelle/N_RUNS/Ollama-Aufruf: identisch zu wissensnutzen.py (Vergleichbarkeit).

Geaenderte Dateien ausserhalb dieser einen: KEINE. wissensnutzen.py nicht
angefasst. Liest knowledge.db (query()/lesson_query), schreibt nichts hinein.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE.parent / "scripts"))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "haken"))  # knowledge_recall_hook liegt seit 2026-08-08 hier, nicht mehr im Wurzelverzeichnis

import schreiblauf as sl  # noqa: E402  -- _call_with_retry wiederverwendet
import wissensnutzen as wn  # noqa: E402  -- Aufgaben A/B + Bewertung uebernommen
import knowledge_recall_hook as rh  # noqa: E402  -- echter Abrufweg (keywords+query)
from messparameter import schnappschuss  # noqa: E402

MODELS = wn.MODELS
N_RUNS = wn.N_RUNS
TIMEOUT = wn.TIMEOUT
OUT_PATH = SHARED_KNOWLEDGE / "runs" / "wissensnutzen_blind.json"
JSONL_PATH = OUT_PATH.with_suffix(".jsonl")
RECALL_CWD = "/Volumes/daten/Begod2026/fahrtenbuch/apps/fahrtenbuch_legacy"

PROMPT_C = ("Nenne den kubectl-Befehl, um alle Pods im Namespace default "
            "aufzulisten. Antworte nur mit dem Befehl.")

TASKS = {
    "A": {**wn.TASKS["A"], "target_lesson_id": "L-c0e910", "cwd": RECALL_CWD},
    "B": {**wn.TASKS["B"], "target_lesson_id": "L-68ff10", "cwd": RECALL_CWD},
    "C": {
        "name": "Kubernetes (kein Treffer im Bestand erwartet)",
        "prompt": PROMPT_C,
        "target_lesson_id": None,
        "cwd": None,
        "check": lambda text: "kubectl" in text and "get pods" in text,
    },
}


def _append_jsonl(record: dict) -> None:
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def blind_retrieve(task_prompt: str, cwd: str | None) -> tuple[list, list, list]:
    """Derselbe Weg wie der echte UserPromptSubmit-Hook: Aufgabentext ->
    Keywords -> query(). Kein Handstichwort, keine Lehren-Kennung."""
    kws = rh.keywords(task_prompt)
    if len(kws) < rh.MIN_HITS:
        return [], [], kws
    nodes, lessons = rh.query(kws, cwd=cwd)
    return nodes, lessons, kws


def format_recall_block(nodes: list, lessons: list) -> str | None:
    """Exakt dasselbe Ausgabeformat wie knowledge_recall_hook.main() baut --
    was ein echter Prompt tatsaechlich zu sehen bekaeme."""
    if not nodes and not lessons:
        return None
    lines = ["<knowledge-recall>",
             "Relevantes Wissen aus der Knowledge-DB (Auto-Recall, ungeprüft — "
             "vor Nutzung kurz verifizieren):"]
    for n in nodes:
        tag = " (Erkundung -- selten gezogen)" if n.get("explore") else ""
        fremd = f" [anderes Projekt: {n['foreign_project']}]" if n.get("foreign_project") else ""
        lines.append(f"- [{n['path']}]{rh.alter(n.get('updated_at'))}{tag}{fremd} "
                     f"{rh.entschaerfe_fuer_ausgabe(n['title'])}: {rh.entschaerfe_fuer_ausgabe(n['summary'])}")
    for l in lessons:
        tag = "⚠ LESSON" if l["severity"] in ("critical", "high") else "Lesson"
        prev = f" → {rh.entschaerfe_fuer_ausgabe(l['prevention'])}" if l.get("prevention") else ""
        fremd = f" [andere Projekte: {l['foreign_projects']}]" if l.get("foreign_projects") else ""
        lines.append(f"- {tag} ({l['type']}, {l['occurrences']}×){rh.alter(l.get('last_seen'))}{fremd}: "
                     f"{rh.entschaerfe_fuer_ausgabe(l['description'])}{prev}")
    lines.append("</knowledge-recall>")
    return "\n".join(lines)


def run_cell(prompt: str, model: str) -> list[dict]:
    runs = []
    for _ in range(N_RUNS):
        started = time.perf_counter()
        raw, err, retries = sl._call_with_retry(
            # beantworten -- das dritte Vorkommen von L-a69129 war genau dieser
            # Lauf (2026-08-09, gemma4:12b/e4b). Ab jetzt gesperrt statt still
            # mit dem falschen Modell gemessen.
            prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL, timeout=TIMEOUT,
            rolle="beantworten")
        seconds = time.perf_counter() - started
        runs.append({
            "error": err, "retry_count": retries, "call_seconds": seconds,
            "response_full": raw,
        })
    return runs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest von Trefferguete/Blockformat, kein Ollama-Aufruf")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    started_total = time.perf_counter()
    cells: dict[str, dict] = {}
    retrieval: dict[str, dict] = {}

    for task_id, task in TASKS.items():
        nodes, lessons, kws = blind_retrieve(task["prompt"], task["cwd"])
        lesson_ids = [l["id"] for l in lessons]
        target = task["target_lesson_id"]
        trefferguete = (target is not None) and (target in lesson_ids)
        block = format_recall_block(nodes, lessons)
        retrieval[task_id] = {
            "keywords": kws, "node_paths": [n["path"] for n in nodes],
            "lesson_ids": lesson_ids, "target_lesson_id": target,
            "trefferguete": trefferguete, "retrieval_empty": not nodes and not lessons,
        }
        print(f"{task_id} Abruf: kws={kws} nodes={[n['path'] for n in nodes]} "
              f"lessons={lesson_ids} ziel={target} trefferguete={trefferguete}", flush=True)
        _append_jsonl({"phase": "retrieval", "task": task_id, **retrieval[task_id]})

        prompt_ohne = task["prompt"]
        prompt_mit = f"{prompt_ohne}\n\n{block}" if block else prompt_ohne

        for model in MODELS:
            for condition, prompt in (("OHNE", prompt_ohne), ("MIT", prompt_mit)):
                key = f"{task_id}|{model}|{condition}"
                runs = run_cell(prompt, model)
                passed_flags = [task["check"](r["response_full"] or "") for r in runs]
                cell_agg = wn.aggregate(passed_flags)
                cells[key] = {"task": task_id, "model": model, "condition": condition,
                              "aggregate": cell_agg, "runs": runs}
                print(f"{task_id} {model:12s} {condition:5s} "
                      f"mean={cell_agg['mean']:.2f} range={cell_agg['range']} "
                      f"runs={cell_agg['runs']}", flush=True)
                _append_jsonl({"phase": "cell", "key": key, **cells[key]})

    runtime_total = time.perf_counter() - started_total
    output = {
        "models": MODELS, "n_runs": N_RUNS, "retrieval": retrieval, "cells": cells,
        "runtime_seconds_total": runtime_total, "konfiguration": schnappschuss(),
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    fehlgriffe = sum(1 for r in retrieval.values() if r["target_lesson_id"] and not r["trefferguete"])
    print(f"\nGeschrieben: {out_path}", flush=True)
    print(f"Laufzeit gesamt: {runtime_total:.1f}s", flush=True)
    print(f"Fehlgriffe (Ziel-Lehre vorhanden, aber verpasst): {fehlgriffe}/"
          f"{sum(1 for r in retrieval.values() if r['target_lesson_id'])}", flush=True)


def _selftest() -> None:
    """Prueft Blockformat + Trefferguete-Logik ohne Netz/Ollama/DB."""
    assert format_recall_block([], []) is None
    block = format_recall_block(
        [{"path": "/x", "title": "T", "summary": "S", "updated_at": None}],
        [{"id": "L-1", "severity": "low", "type": "insight", "occurrences": 1,
          "description": "D", "prevention": "P", "last_seen": None}],
    )
    assert block is not None and "<knowledge-recall>" in block and "insight" in block

    # Trefferguete-Logik wie in main(): Ziel vorhanden+getroffen -> True,
    # Ziel vorhanden+verpasst -> False, kein Ziel -> immer False.
    def treffer(target, ids):
        return (target is not None) and (target in ids)
    assert treffer("L-c0e910", ["L-c0e910", "L-x"]) is True
    assert treffer("L-68ff10", ["L-c0e910"]) is False  # Fehlgriff (echter Probelauf 2026-08-07)
    assert treffer(None, ["L-14a742"]) is False  # C: nie "ja", auch bei echtem Treffer

    # Aufgabe C: kein Ziel, aber gemessener Fehlgriff (echter Probelauf) zaehlt als retrieval_empty=False.
    assert TASKS["C"]["target_lesson_id"] is None
    assert TASKS["A"]["target_lesson_id"] == "L-c0e910"
    assert TASKS["B"]["target_lesson_id"] == "L-68ff10"
    assert TASKS["C"]["check"]("kubectl get pods -n default") is True
    assert TASKS["C"]["check"]("kubectl get pod default") is False

    print("selftest ok: Blockformat + Trefferguete-Logik + Aufgabe-C-Check", file=sys.stderr)


if __name__ == "__main__":
    main()
