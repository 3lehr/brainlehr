"""Misst OKKULTATION: wird ein eingespielter lesson_query-Treffer wirklich
BENUTZT? Beschluss + Begruendung: hub/docs/FACHANALOGIEN_2026-08-07.md,
Eintrag OKKULTATION (Commit d1d26ab7b), korrigierte Fassung Knoten ed25b78e.

IDEE: Nutzung eines Treffers hinterlaesst keine Spur direkt -- aber nimmt
man ihn aus dem Prompt WEG (alle anderen Treffer bleiben) und die Bewertung
kippt, war er tragend. Wie ein Himmelskoerper, den man nur an der Verdunklung
eines Sterns erkennt.

WIEDERVERWENDET aus wissensnutzen.py (nicht daneben gebaut): Ollama-Weg
(schreiblauf._call_with_retry), Aufgabe A (Dialog-Falle, Lehre L-c0e910),
deterministische Bewertung TASKS["A"]["check"], build_prompt_mit()-Wrapper-
text, aggregate() (mean/range/runs). EIN Modell (gemma4:12b, wn.MODELS[0])
reicht -- Okkultation ist pro Modell zu zeigen, kein Modellvergleich noetig.

NEU (dritter Arm, ueber wissensnutzen.py hinaus): lesson_query mit
max_results=N_HITS statt 1 -- der echte Aufruf spielt mehrere Treffer ein,
nicht nur den einschlaegigen (siehe Docstring-Beleg unten). Fuer jeden
einzelnen Treffer ein Weglass-Lauf (alle anderen bleiben im Prompt), Mehr-
heitsentscheid (ungerade N, keine Unentschieden) verglichen mit dem Voll-
lauf. Kippt die Mehrheit, gilt der Treffer als benutzt.

STREUUNG zuerst: der Volllauf (alle Treffer) wird mit N_RUNS_FULL=5
unabhaengigen Aufrufen gemessen -- range/mean derselben aggregate()-Funktion
zeigen die Streuung OHNE jede Aenderung, bevor irgendein Weglass-Ergebnis
gegen sie gehalten wird.

Geaenderte Dateien ausserhalb dieser einen: KEINE. Liest die echte
knowledge.db (lesson_query), schreibt nichts hinein.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

SHARED_KNOWLEDGE = Path(__file__).resolve().parent
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import schreiblauf as sl  # noqa: E402  -- _call_with_retry wiederverwendet
import knowledge_mcp_server as kms  # noqa: E402  -- lesson_query wiederverwendet
import wissensnutzen as wn  # noqa: E402  -- Aufgabe A, Bewertung, aggregate() uebernommen

MODEL = wn.MODELS[0]
TASK_ID = "A"
TARGET_LESSON_ID = "L-c0e910"
N_HITS = 5  # wie ein echter lesson_query-Aufruf mit max_results=5 einspielen wuerde
N_RUNS_FULL = 5  # Streuungsschaetzung + Basiswert, ungerade -> Mehrheit nie unentschieden
N_RUNS_LOO = 3  # je Weglass-Lauf, ungerade -> Mehrheit nie unentschieden
OUT_PATH = SHARED_KNOWLEDGE / "runs" / "bedeckung.json"
JSONL_PATH = OUT_PATH.with_suffix(".jsonl")


def _ts() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _append_jsonl(record: dict) -> None:
    """Ein Lauf, sofort weggeschrieben -- ueberlebt Abbruch, Muster aus
    fenstergroesse.py."""
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": _ts(), **record}, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def format_lesson(lesson: dict) -> str:
    """Derselbe Textblock wie wn.fetch_lesson_text, nur ohne die
    max_results=1-Beschraenkung -- fuer eine LISTE von Treffern gebraucht."""
    return (f"{lesson['description']}\n"
            f"Ursache: {lesson['root_cause']}\n"
            f"Loesung/Praevention: {lesson['prevention']}")


def fetch_hits(query: str, n: int) -> list[dict]:
    result = kms.lesson_query(query=query, max_results=n)
    hits = result.get("results") or []
    return [{"id": h["id"], "text": format_lesson(h)} for h in hits]


def build_lesson_block(hits: list[dict], *, exclude_id: str | None = None) -> str:
    chosen = [h["text"] for h in hits if h["id"] != exclude_id]
    return "\n\n".join(chosen)


def build_prompt(task: dict, hits: list[dict], *, exclude_id: str | None = None) -> str:
    block = build_lesson_block(hits, exclude_id=exclude_id)
    return wn.build_prompt_mit(task["prompt"], block)


def majority(flags: list[bool]) -> bool:
    """True, wenn mehr als die Haelfte der Laeufe bestanden. N ist immer
    ungerade (N_RUNS_FULL/N_RUNS_LOO) -- kein Unentschieden moeglich."""
    return sum(flags) > len(flags) / 2


def run_n(prompt: str, n: int, *, phase: str, label: str, check) -> dict:
    """n unabhaengige Ollama-Aufrufe, jeder sofort als JSONL-Zeile
    persistiert. Gibt Aggregat (wn.aggregate) + Mehrheitsentscheid zurueck."""
    runs = []
    for i in range(n):
        started = time.perf_counter()
        raw, err, retries = sl._call_with_retry(
            prompt, model=MODEL, base_url=sl.DEFAULT_OLLAMA_URL, timeout=wn.TIMEOUT)
        seconds = time.perf_counter() - started
        runs.append({"error": err, "retry_count": retries, "call_seconds": seconds,
                      "response_full": raw})
        _append_jsonl({"phase": phase, "label": label, "run_index": i,
                        "error": err, "retry_count": retries, "call_seconds": seconds,
                        "response_excerpt": (raw or "")[:200]})
        print(f"{_ts()} {phase:5s} {label:12s} run={i + 1}/{n} dauer={seconds:6.1f}s "
              f"{'FEHLER: ' + err if err else 'ok'}", flush=True)
    flags = [check(r["response_full"] or "") for r in runs]
    agg = wn.aggregate(flags)
    result = {"aggregate": agg, "majority": majority(flags), "runs": runs}
    print(f"{_ts()} {phase:5s} {label:12s}  mean={agg['mean']:.2f} range={agg['range']} "
          f"runs={agg['runs']} mehrheit={result['majority']}", flush=True)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest der Weglass-/Mehrheitslogik, kein Ollama-Aufruf")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    started_total = time.perf_counter()
    task = wn.TASKS[TASK_ID]
    check = task["check"]

    hits = fetch_hits(task["lesson_query"], N_HITS)
    assert any(h["id"] == TARGET_LESSON_ID for h in hits), (
        f"Zieltreffer {TARGET_LESSON_ID} nicht unter den {N_HITS} eingespielten "
        f"Treffern -- Voraussetzung fehlt, Abbruch. Gefunden: {[h['id'] for h in hits]}")
    assert len(hits) >= 2, "Fuer die Gegenprobe (Ziel + BELIEBIGER anderer Treffer) sind >=2 Treffer noetig"

    # Volllauf zuerst -- liefert Streuungszahl UND Vergleichsbasis in einem
    full_prompt = build_prompt(task, hits)
    full = run_n(full_prompt, N_RUNS_FULL, phase="full", label="alle", check=check)

    loo: dict[str, dict] = {}
    for hit in hits:
        prompt = build_prompt(task, hits, exclude_id=hit["id"])
        cell = run_n(prompt, N_RUNS_LOO, phase="loo", label=hit["id"], check=check)
        cell["benutzt"] = cell["majority"] != full["majority"]
        loo[hit["id"]] = cell

    target_benutzt = loo[TARGET_LESSON_ID]["benutzt"]
    other_flips = [hid for hid, r in loo.items() if hid != TARGET_LESSON_ID and r["benutzt"]]
    geeicht = target_benutzt and not other_flips

    runtime_total = time.perf_counter() - started_total

    print(f"\n--- STREUUNG (Volllauf, {N_RUNS_FULL} Wiederholungen, keine Aenderung) ---")
    print(f"mean={full['aggregate']['mean']:.2f} range={full['aggregate']['range']} "
          f"runs={full['aggregate']['runs']} -> Mehrheit={full['majority']}")
    print(f"\n--- GEGENPROBE Richtung 1: Ziel {TARGET_LESSON_ID} MUSS kippen ---")
    print(f"benutzt={target_benutzt} (Mehrheit Volllauf={full['majority']}, "
          f"Mehrheit ohne Ziel={loo[TARGET_LESSON_ID]['majority']})")
    print(f"\n--- GEGENPROBE Richtung 2: kein ANDERER Treffer darf kippen ---")
    for hid, r in loo.items():
        if hid == TARGET_LESSON_ID:
            continue
        print(f"{hid}: benutzt={r['benutzt']} (Mehrheit ohne {hid}={r['majority']})")
    print(f"\nAndere gekippte Treffer: {other_flips or 'keiner'}")
    print(f"\nVERDIKT: {'Werkzeug zeigt Nutzung' if geeicht else 'Werkzeug UNGEEICHT, zuerst Streuung bestimmen'}")

    output = {
        "model": MODEL, "task": TASK_ID, "target_lesson_id": TARGET_LESSON_ID,
        "n_hits": N_HITS, "n_runs_full": N_RUNS_FULL, "n_runs_loo": N_RUNS_LOO,
        "hits": [h["id"] for h in hits],
        "full": full, "leave_one_out": loo,
        "target_benutzt": target_benutzt, "other_flips": other_flips, "geeicht": geeicht,
        "runtime_seconds_total": runtime_total,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out_path}")
    print(f"Laufzeit gesamt: {runtime_total:.1f}s")

    if not geeicht:
        sys.exit(1)


def _selftest() -> None:
    """Prueft Mehrheits-/Weglass-/Kipplogik ohne Netz/Ollama/DB."""
    assert majority([True, True, False]) is True
    assert majority([True, False, False]) is False
    assert majority([True, True, True]) is True
    assert majority([False, False, False]) is False

    hits = [{"id": "L-x", "text": "TEXT_X"}, {"id": "L-y", "text": "TEXT_Y"}]
    assert build_lesson_block(hits) == "TEXT_X\n\nTEXT_Y"
    assert build_lesson_block(hits, exclude_id="L-x") == "TEXT_Y"
    assert build_lesson_block(hits, exclude_id="L-y") == "TEXT_X"

    # Kipplogik: Volllauf-Mehrheit True, Weglass-Mehrheit False -> benutzt
    assert (False != True) is True  # sanity: != ist die Kipp-Definition
    full_maj = True
    loo_maj_kippt = False
    loo_maj_kippt_nicht = True
    assert (loo_maj_kippt != full_maj) is True
    assert (loo_maj_kippt_nicht != full_maj) is False

    print("selftest ok: Mehrheit + Weglass-Block + Kipplogik", file=sys.stderr)


if __name__ == "__main__":
    main()
