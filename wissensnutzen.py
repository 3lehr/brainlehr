"""Misst, was brainlehr BEITRAEGT -- nicht welches Modell besser ist.
Vergleich: dasselbe Modell MIT gegen OHNE Wissenszugang (lesson_query-Treffer
im Prompt), nicht Modell gegen Modell.

ZWEI AUFGABEN aus echten Fallen des Bestands (Wortlaut per lesson_query
gegen die echte knowledge.db geholt, nicht aus dem Gedaechtnis geschrieben):
  A) Dialog-Falle (Lehre L-c0e910): AlertDialog+showDialog wird in
     fahrtenbuch_legacy durch einen globalen Shim zum Vollbild-Screen mit
     Weissraum. Richtig: ActionScreen(expandPrimaryAction:true) ueber
     eigenen Navigator.push(fullscreenDialog:true).
  B) Stummer Testlauf (Lehre L-68ff10): `flutter test` ueberspringt
     Debug-Schnittstellen-Faelle still ohne --dart-define=DEBUG_STATE_API=true.

ABWEICHUNG vom Auftrag, hier begruendet (Auftrag: "Sieh Code an, melde
Abweichung" -- gilt sinngemaess auch fuer den eigenen methodischen Aufbau):
Auftrag nennt knowledge_search als Quelle der Treffer. Geprueft (2026-08-06):
knowledge_search('AlertDialog showDialog ActionScreen Vollbild') UND
knowledge_search('DEBUG_STATE_API flutter test dart-define') liefern je 5
Treffer, aber KEINER davon ist die einschlaegige Lehre (L-c0e910 / L-68ff10)
-- knowledge_search durchsucht knowledge_nodes/FTS, nicht die
lessons_learned-Tabelle, in der genau diese zwei Lehren stehen. Mit
knowledge_search als Quelle wuerde der MIT-Arm irrelevantes Wissen
einspeisen und die Messung entwerten. Stattdessen: lesson_query (dieselbe
Funktion, mit der die Aufgaben oben recherchiert wurden), geprueft:
liefert L-c0e910 bzw. L-68ff10 exakt als Treffer 1.

Ollama-Aufruf wiederverwendet aus schreibpruefstand/schreiblauf.py
(_call_with_retry: ein Retry bei Werkzeugausfall, kein stilles Endlos-Retry).
Zweites Modell: gemma4:e4b (kleinste verfuegbare Groesse aus `ollama list` --
haelt 24 Aufrufe gesamt in vertretbarer Laufzeit; `ollama list` zeigte am
2026-08-06 gemma4:e4b/12b/31b + nomic-embed-text, e4b und 12b sind die zwei
generativen Groessen ohne die 19-GB-Stufe).

BEWERTUNG deterministisch (kein Modellurteil):
  A) trifft zu, wenn 'ActionScreen' in der Antwort vorkommt UND 'showDialog'
     NICHT vorkommt -- genau die zwei Textmerkmale, die Code vs. Antipattern
     unterscheiden, laut Lehre L-c0e910.
  B) trifft zu, wenn 'DEBUG_STATE_API' vorkommt -- das fehlende Flag IST der
     ganze Unterschied laut Lehre L-68ff10.
Jede andere Bewertung (Teilpunkte, Wortlaut-Aehnlichkeit) waere ein
Modellurteil durch die Hintertuer -- deshalb bewusst nicht gemacht.

Geaenderte Dateien ausserhalb dieser einen: KEINE. Liest die echte
knowledge.db (lesson_query), schreibt nichts hinein.
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

import schreiblauf as sl  # noqa: E402  -- _call_with_retry wiederverwendet
import knowledge_mcp_server as kms  # noqa: E402  -- lesson_query wiederverwendet

MODELS = ["gemma4:12b", "gemma4:e4b"]
N_RUNS = 3
TIMEOUT = 180.0
OUT_PATH = SHARED_KNOWLEDGE / "runs" / "wissensnutzen.json"

PROMPT_A = """Du arbeitest im Flutter-Repo fahrtenbuch_legacy. Schreibe den \
Dart-Code fuer einen Bestaetigungsdialog "Fahrt beenden?" mit zwei Buttons \
(Ja / Nein), der bei Tippen auf einen Button-Handler in car_home_screen.dart \
angezeigt wird. Antworte nur mit dem Dart-Code."""

PROMPT_B = """Du arbeitest im Flutter-Repo fahrtenbuch_legacy. Nenne den \
exakten Shell-Befehl, um `flutter test` so auszufuehren, dass die \
Debug-Schnittstellen-Testfaelle des Projekts tatsaechlich mitlaufen (nicht \
nur gruen aussehen). Antworte nur mit dem Befehl."""

TASKS = {
    "A": {
        "name": "Dialog-Falle",
        "prompt": PROMPT_A,
        "lesson_query": "AlertDialog showDialog ActionScreen Vollbild fahrtenbuch_legacy",
        "check": lambda text: "ActionScreen" in text and "showDialog" not in text,
    },
    "B": {
        "name": "Stummer Testlauf",
        "prompt": PROMPT_B,
        "lesson_query": "DEBUG_STATE_API flutter test dart-define fahrtenbuch",
        "check": lambda text: "DEBUG_STATE_API" in text,
    },
}


def fetch_lesson_text(query: str) -> str | None:
    """Erster Treffer aus lesson_query, als Wissensblock formatiert. None,
    wenn nichts gefunden wurde -- dann fehlt eine Voraussetzung des Laufs."""
    result = kms.lesson_query(query=query, max_results=1)
    hits = result.get("results") or []
    if not hits:
        return None
    lesson = hits[0]
    return (
        f"{lesson['description']}\n"
        f"Ursache: {lesson['root_cause']}\n"
        f"Loesung/Praevention: {lesson['prevention']}"
    )


def build_prompt_mit(base_prompt: str, lesson_text: str) -> str:
    return f"{base_prompt}\n\nBekanntes Wissen aus fruehreren Sessions:\n{lesson_text}"


def run_cell(prompt: str, model: str) -> list[dict]:
    """N_RUNS unabhaengige Ollama-Aufrufe mit demselben Prompt. Streuung
    ist der Punkt, kein Einzellauf zaehlt als Beleg (siehe Docstring-Anlass:
    2026-08-06 schwankte derselbe Aufbau zwischen 1 und 3 von 7)."""
    runs = []
    for _ in range(N_RUNS):
        started = time.perf_counter()
        raw, err, retries = sl._call_with_retry(
            prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL, timeout=TIMEOUT)
        seconds = time.perf_counter() - started
        passed = False if err else bool(raw)
        runs.append({
            "error": err,
            "retry_count": retries,
            "call_seconds": seconds,
            "response_excerpt": (raw or "")[:400],
            "response_full": raw,
        })
    return runs


def aggregate(passed_flags: list[bool]) -> dict:
    vals = [1 if p else 0 for p in passed_flags]
    return {"mean": sum(vals) / len(vals), "range": max(vals) - min(vals), "runs": vals}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest der Bewertungs-/Aggregationslogik, kein Ollama-Aufruf")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    started_total = time.perf_counter()
    cells: dict[str, dict] = {}
    prompts_for_honesty_check: dict[str, str] = {}

    for task_id, task in TASKS.items():
        lesson_text = fetch_lesson_text(task["lesson_query"])
        assert lesson_text, f"Keine Lehre gefunden fuer Aufgabe {task_id} -- Voraussetzung fehlt, Abbruch"
        prompt_ohne = task["prompt"]
        prompt_mit = build_prompt_mit(task["prompt"], lesson_text)
        if task_id == "A":
            prompts_for_honesty_check = {"ohne": prompt_ohne, "mit": prompt_mit}

        for model in MODELS:
            for condition, prompt in (("OHNE", prompt_ohne), ("MIT", prompt_mit)):
                key = f"{task_id}|{model}|{condition}"
                runs = run_cell(prompt, model)
                passed_flags = [task["check"](r["response_full"] or "") for r in runs]
                cell_agg = aggregate(passed_flags)
                cells[key] = {"task": task_id, "model": model, "condition": condition,
                              "aggregate": cell_agg, "runs": runs}
                print(f"{task_id} {model:12s} {condition:5s} "
                      f"mean={cell_agg['mean']:.2f} range={cell_agg['range']} "
                      f"runs={cell_agg['runs']}")

    runtime_total = time.perf_counter() - started_total

    output = {
        "models": MODELS,
        "n_runs": N_RUNS,
        "cells": cells,
        "honesty_check_task_a_prompts": prompts_for_honesty_check,
        "runtime_seconds_total": runtime_total,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nGeschrieben: {out_path}")
    print(f"Laufzeit gesamt: {runtime_total:.1f}s")
    print("\n--- EHRLICHKEITSPROBE Aufgabe A: Prompt OHNE Wissen ---")
    print(prompts_for_honesty_check["ohne"])
    print("\n--- EHRLICHKEITSPROBE Aufgabe A: Prompt MIT Wissen ---")
    print(prompts_for_honesty_check["mit"])


def _selftest() -> None:
    """Prueft Bewertungs- und Aggregationslogik ohne Netz/Ollama/DB."""
    assert TASKS["A"]["check"]("class X { ActionScreen(); }") is True
    assert TASKS["A"]["check"]("showDialog(context: c, builder: (_) => ActionScreen());") is False, \
        "Aufgabe A muss ablehnen, wenn showDialog im Text vorkommt, auch neben ActionScreen"
    assert TASKS["A"]["check"]("AlertDialog + showDialog") is False
    assert TASKS["B"]["check"]("flutter test --dart-define=DEBUG_STATE_API=true") is True
    assert TASKS["B"]["check"]("flutter test") is False

    agg_all_pass = aggregate([True, True, True])
    assert agg_all_pass == {"mean": 1.0, "range": 0, "runs": [1, 1, 1]}
    agg_mixed = aggregate([True, False, True])
    assert agg_mixed["mean"] == 2 / 3 and agg_mixed["range"] == 1 and agg_mixed["runs"] == [1, 0, 1]
    agg_none = aggregate([False, False, False])
    assert agg_none == {"mean": 0.0, "range": 0, "runs": [0, 0, 0]}

    print("selftest ok: Bewertungslogik A/B + Aggregation (mean/range)", file=sys.stderr)


if __name__ == "__main__":
    main()
