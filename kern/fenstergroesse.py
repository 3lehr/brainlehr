"""Misst, ab welcher Ollama-Kontextfenstergroesse (num_ctx) brainlehr nicht
mehr traegt -- Anlass: die '60 Zeilen'-Ausgabegrenze in wiedereinstieg.py
wurde geraten, nicht hergeleitet. num_ctx ist bei Ollama einstellbar
(options.num_ctx im /api/generate-Request), also messbar statt geraten.

ACHSE: num_ctx in (4096, 8192, 32768, 131072) x mit/ohne Wiedereinstiegs-
Verweisliste (wiedereinstieg.build(), echte Sitzung 43459d92...) im Prompt.
Werkzeugliste (voll, 13 Werkzeuge) ist in JEDER Zelle Teil des Prompts --
BEKANNT laut Auftrag: 11693 Zeichen ~ 3341 Token bei 4k. Aus knowledge_mcp_
server.TOOLS zur Laufzeit erzeugt (identisch zum echten tools/list-Pfad,
Profil 'voll'), nicht als Konstante kopiert -- sonst veraltet die Zahl,
sobald ein Werkzeug dazukommt.

AUFGABE + BEWERTUNG: aus wissensnutzen.py uebernommen (Auftrag: "sieh dort
nach, baue keine zweite"). Nur Aufgabe A (Dialog-Falle) -- der Auftrag
verlangt "eine Aufgabe", nicht zwei; A ist die kuerzere und wird stellver-
tretend genommen. TASKS["A"]["check"] und der lesson_query-Text werden
importiert, nicht neu geschrieben. Die Lehre wird in JEDER Zelle mitgegeben
(nicht als eigene Achse) -- der Auftrag verlangt eine Aufgabe, "deren
richtige Antwort NUR aus dem Bestand kommt"; ohne Lehre im Prompt waere die
Aufgabe fuer KEINE Zelle loesbar und die Achse wuerde nichts zeigen ausser
"Lehre da oder nicht", was schon in wissensnutzen.py gemessen ist.

TOKENZAHL: nicht geschaetzt (kein tiktoken installiert, waere ohnehin der
falsche Tokenizer fuer gemma4). Ollamas /api/generate liefert
prompt_eval_count -- die tatsaechliche Tokenzahl des ECHTEN Modell-
Tokenizers fuer genau den gesendeten Text. Vier Kalibrierungsaufrufe mit
num_predict=1 (kein Antworttext noetig, nur der Zaehlwert) liefern:
Werkzeugliste allein, Wiedereinstieg allein, Vollprompt je Variante (mit/
ohne) bei num_ctx=CALIBRATION_CTX (groesster Wert der Achse -- dort passt
mit Sicherheit alles hinein, also keine Kuerzung durch Ollama selbst, die
den Zaehlwert verfaelschen wuerde).

PASST NICHT vs. MODELLVERSAGEN: eine Zelle gilt als 'passt nicht', wenn
reference_full_tokens[variant] + OUTPUT_MARGIN > num_ctx -- dann wird gar
nicht erst generiert (Ollama wuerde den Prompt selbst kappen und die
Bewertung waere Zufall, kein Modellbefund). OUTPUT_MARGIN ist ein Kniff,
kein Messwert: geschaetzter Platzbedarf fuer die Antwort selbst.

schreiblauf.py wird NUR gelesen (Konstanten DEFAULT_MODEL, DEFAULT_OLLAMA_URL,
CALL_TIMEOUT). Der eigentliche Ollama-Aufruf ist hier neu geschrieben, weil
schreiblauf._call_ollama() kein options.num_ctx kennt und keine
prompt_eval_count zurueckgibt -- Auftrag verbietet, schreiblauf.py dafuer zu
aendern. knowledge_mcp_server.py und knowledge_lint.py: nur gelesen (TOOLS),
nicht angefasst -- dort arbeitet laut Auftrag ein anderer Agent.

Geaenderte Dateien ausserhalb dieser einen: KEINE.
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
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE.parent / "scripts"))

import schreiblauf as sl  # noqa: E402  -- nur Konstanten gelesen
import knowledge_mcp_server as kms  # noqa: E402  -- nur TOOLS gelesen
import wissensnutzen as wn  # noqa: E402  -- Aufgabe A + Bewertung uebernommen
import wiedereinstieg as we  # noqa: E402  -- echte Verweisliste

MODEL = sl.DEFAULT_MODEL
OLLAMA_URL = sl.DEFAULT_OLLAMA_URL
TIMEOUT = sl.CALL_TIMEOUT
SESSION_ID = "43459d92-9f7a-4fca-b8cb-3f4ed6709f30"
NUM_CTX_VALUES = [4096, 8192, 32768, 131072]
CALIBRATION_CTX = max(NUM_CTX_VALUES)
N_RUNS = 3
OUT_PATH = SHARED_KNOWLEDGE / "runs" / "fenstergroesse.json"
# Jede einzelne Kalibrierungs- und Messzelle wird SOFORT hierher angehaengt
# (JSON Lines) -- bricht der Lauf ab, bevor OUT_PATH am Ende geschrieben
# wird, stehen die bis dahin fertigen Versuche trotzdem auf der Platte.
JSONL_PATH = OUT_PATH.with_suffix(".jsonl")
# ponytail: Schaetzwert, kein gemessener -- Platzbedarf fuer die Antwort
# selbst. Bei Bedarf aus echten completion-Laengen der 'passt'-Zellen herleiten.
OUTPUT_MARGIN = 64


def _tool_list_text() -> str:
    """Exakt der Textkoerper, den ein echter tools/list-Aufruf (Profil
    'voll') liefern wuerde -- aus kms.TOOLS erzeugt, nicht kopiert."""
    tool_list = [{"name": n, "description": s["description"], "inputSchema": s["inputSchema"]}
                 for n, s in kms.TOOLS.items()]
    return json.dumps(tool_list, ensure_ascii=False)


def _wiedereinstieg_text() -> str:
    return we.build(SESSION_ID)


def _task_prompt() -> str:
    task = wn.TASKS["A"]
    lesson_text = wn.fetch_lesson_text(task["lesson_query"])
    assert lesson_text, "Keine Lehre gefunden fuer Aufgabe A -- Voraussetzung fehlt, Abbruch"
    return wn.build_prompt_mit(task["prompt"], lesson_text)


def _full_prompt(tool_text: str, we_text: str, task_text: str, *, mit_wiedereinstieg: bool) -> str:
    parts = [f"Verfuegbare Werkzeuge (MCP tools/list):\n{tool_text}"]
    if mit_wiedereinstieg:
        parts.append(we_text)
    parts.append(task_text)
    return "\n\n".join(parts)


def _call_ollama(prompt: str, *, num_ctx: int, num_predict: int | None = None) -> dict:
    """Einmaliger Aufruf (kein Retry -- die Kalibrierung braucht keine
    Ausfalltoleranz, sie laeuft vor der eigentlichen Messung). Gibt das
    volle Antwortobjekt zurueck (response, prompt_eval_count, ...)."""
    options = {"num_ctx": num_ctx}
    if num_predict is not None:
        options["num_predict"] = num_predict
    payload = {"model": MODEL, "prompt": prompt, "stream": False,
               "keep_alive": sl.KEEP_ALIVE, "options": options}
    req = urllib.request.Request(
        f"{OLLAMA_URL.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _ts() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def _append_jsonl(record: dict) -> None:
    """Ein Versuch, sofort weggeschrieben -- ueberlebt Abbruch/SIGTERM/
    KeyboardInterrupt, weil er nicht auf den Abschluss von main() wartet."""
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with JSONL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": _ts(), **record}, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _call_with_retry(prompt: str, *, num_ctx: int,
                      num_predict: int | None = None) -> tuple[str | None, str | None, int, int | None]:
    """Ein Retry bei Werkzeugausfall, Muster aus schreiblauf._call_with_retry
    (dort nicht wiederverwendbar, weil options fehlen). Gibt
    (antworttext, fehler, retry_count, prompt_eval_count) zurueck. Faengt
    JEDEN Ollama-Aufruf ab -- vorher lief calibrate() ungeschuetzt direkt
    gegen _call_ollama() und riss bei Timeout/Netzfehler den ganzen Lauf vor
    der ersten Messzelle ab, ohne jede Spur (Fund 2026-08-07)."""
    last_err = "kein Versuch ausgefuehrt"
    for retry in (0, 1):
        try:
            body = _call_ollama(prompt, num_ctx=num_ctx, num_predict=num_predict)
            return body.get("response", ""), None, retry, body.get("prompt_eval_count")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            last_err = f"Ollama-Aufruf fehlgeschlagen: {exc}"
    return None, last_err, 1, None


def calibrate(tool_text: str, we_text: str, task_text: str) -> dict:
    """Vier num_predict=1-Aufrufe bei CALIBRATION_CTX -- liefert die echten
    Tokenzahlen (prompt_eval_count), keine Schaetzung. Jeder Aufruf laeuft
    ueber _call_with_retry (Zeitgrenze TIMEOUT, kein Absturz bei Ausfall) und
    wird sofort als eigener JSONL-Versuch festgehalten."""
    ref_texts = {
        False: _full_prompt(tool_text, we_text, task_text, mit_wiedereinstieg=False),
        True: _full_prompt(tool_text, we_text, task_text, mit_wiedereinstieg=True),
    }
    parts = {
        "tool_tokens": tool_text,
        "wiedereinstieg_tokens": we_text,
        "reference_full_tokens.ohne": ref_texts[False],
        "reference_full_tokens.mit": ref_texts[True],
    }
    values: dict[str, int | None] = {}
    for key, text in parts.items():
        started = time.perf_counter()
        raw, err, retries, peval = _call_with_retry(text, num_ctx=CALIBRATION_CTX, num_predict=1)
        seconds = time.perf_counter() - started
        values[key] = peval
        _append_jsonl({"phase": "calibration", "key": key, "num_ctx": CALIBRATION_CTX,
                        "duration_seconds": seconds, "prompt_eval_count": peval,
                        "retry_count": retries, "error": err})
        print(f"{_ts()} Kalibrierung {key:28s} dauer={seconds:6.1f}s "
              f"token={peval if peval is not None else 'FEHLGESCHLAGEN: ' + (err or '?')}", flush=True)
        if peval is None:
            raise RuntimeError(
                f"Kalibrierung '{key}' bei num_ctx={CALIBRATION_CTX} fehlgeschlagen: {err}. "
                f"Bisherige Kalibrierungsversuche stehen in {JSONL_PATH}."
            )
    return {"tool_tokens": values["tool_tokens"], "wiedereinstieg_tokens": values["wiedereinstieg_tokens"],
            "reference_full_tokens": {"mit": values["reference_full_tokens.mit"],
                                       "ohne": values["reference_full_tokens.ohne"]}}


def aggregate(passed_flags: list[bool]) -> dict:
    vals = [1 if p else 0 for p in passed_flags]
    return {"mean": sum(vals) / len(vals), "range": max(vals) - min(vals), "runs": vals}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest der Passt-nicht-Logik, kein Ollama-Aufruf")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    started_total = time.perf_counter()
    tool_text = _tool_list_text()
    we_text = _wiedereinstieg_text()
    task_text = _task_prompt()
    check = wn.TASKS["A"]["check"]

    try:
        cal = calibrate(tool_text, we_text, task_text)
    except RuntimeError as exc:
        # Kalibrierung liefert die Referenz-Tokenzahlen fuer ALLE Zellen (sie
        # laeuft einmalig bei CALIBRATION_CTX) -- schlaegt sie fehl, ist kein
        # einziges Zellenergebnis moeglich. Sauber melden statt Traceback,
        # die einzelnen Kalibrierungsversuche stehen bereits in JSONL_PATH.
        print(f"{_ts()} ABBRUCH: {exc}", flush=True)
        sys.exit(1)
    print(f"Kalibrierung (num_ctx={CALIBRATION_CTX}, num_predict=1): "
          f"Werkzeugliste={cal['tool_tokens']} Token, "
          f"Wiedereinstieg={cal['wiedereinstieg_tokens']} Token, "
          f"Vollprompt ohne={cal['reference_full_tokens']['ohne']}, "
          f"mit={cal['reference_full_tokens']['mit']} Token", flush=True)

    cells: dict[str, dict] = {}
    kipppunkt = None
    for num_ctx in NUM_CTX_VALUES:
        for mit_we in (False, True):
            variant = "mit" if mit_we else "ohne"
            ref_tokens = cal["reference_full_tokens"][variant]
            rest = num_ctx - cal["tool_tokens"] - (cal["wiedereinstieg_tokens"] if mit_we else 0)
            passt = (ref_tokens + OUTPUT_MARGIN) <= num_ctx
            key = f"{num_ctx}|{variant}"

            if not passt:
                cells[key] = {
                    "num_ctx": num_ctx, "variant": variant, "passt": False,
                    "rest_fuer_aufgabe_tokens": rest, "reference_full_tokens": ref_tokens,
                }
                _append_jsonl({"phase": "cell_skip", "num_ctx": num_ctx, "variant": variant,
                                "reference_full_tokens": ref_tokens, "rest_fuer_aufgabe_tokens": rest})
                print(f"{_ts()} num_ctx={num_ctx:6d} {variant:4s}  PASST NICHT "
                      f"(voll={ref_tokens} + Marge {OUTPUT_MARGIN} > {num_ctx}), rest={rest}", flush=True)
                continue

            prompt = _full_prompt(tool_text, we_text, task_text, mit_wiedereinstieg=mit_we)
            runs = []
            for run_index in range(N_RUNS):
                started = time.perf_counter()
                raw, err, retries, peval = _call_with_retry(prompt, num_ctx=num_ctx)
                seconds = time.perf_counter() - started
                # Zeitgrenze (TIMEOUT, siehe _call_ollama/urlopen) beendet den
                # einzelnen Aufruf, nicht den Lauf -- ein nicht antwortendes
                # Fenster liefert err != None und wird unten als bestandenes
                # (nicht ueberlebtes) Ergebnis gewertet und sofort persistiert.
                run_record = {
                    "error": err, "retry_count": retries, "call_seconds": seconds,
                    "prompt_eval_count": peval, "response_full": raw,
                }
                runs.append(run_record)
                _append_jsonl({"phase": "cell_run", "num_ctx": num_ctx, "variant": variant,
                                "run_index": run_index, **run_record})
                print(f"{_ts()} num_ctx={num_ctx:6d} {variant:4s} run={run_index + 1}/{N_RUNS} "
                      f"dauer={seconds:6.1f}s "
                      f"{'FEHLER: ' + err if err else 'ok'}", flush=True)
            passed_flags = [check(r["response_full"] or "") for r in runs]
            cell_agg = aggregate(passed_flags)
            cells[key] = {
                "num_ctx": num_ctx, "variant": variant, "passt": True,
                "rest_fuer_aufgabe_tokens": rest, "reference_full_tokens": ref_tokens,
                "aggregate": cell_agg, "runs": runs,
            }
            print(f"{_ts()} num_ctx={num_ctx:6d} {variant:4s}  mean={cell_agg['mean']:.2f} "
                  f"range={cell_agg['range']} runs={cell_agg['runs']} rest={rest}", flush=True)
            if kipppunkt is None and cell_agg["mean"] < 1.0:
                kipppunkt = num_ctx

    runtime_total = time.perf_counter() - started_total
    kipppunkt_text = f"{kipppunkt}" if kipppunkt is not None else "kein Kipppunkt in diesem Bereich gefunden"

    output = {
        "model": MODEL, "num_ctx_values": NUM_CTX_VALUES, "n_runs": N_RUNS,
        "output_margin_tokens": OUTPUT_MARGIN, "calibration": cal,
        "cells": cells, "kipppunkt": kipppunkt_text, "runtime_seconds_total": runtime_total,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nGeschrieben: {out_path}", flush=True)
    print(f"Kipppunkt: {kipppunkt_text}", flush=True)
    print(f"Laufzeit gesamt: {runtime_total:.1f}s", flush=True)


def _selftest() -> None:
    """Prueft die Passt-nicht-Schwelle und Aggregation ohne Netz/Ollama."""
    assert (4096 - 32) + OUTPUT_MARGIN > 4096  # 32 Token Luft, Marge 64 -> passt nicht
    assert (4096 - 128) + OUTPUT_MARGIN <= 4096  # 128 Token Luft, Marge 64 -> passt
    agg = aggregate([True, True, False])
    assert agg == {"mean": 2 / 3, "range": 1, "runs": [1, 1, 0]}
    print("selftest ok: Passt-nicht-Schwelle + Aggregation", file=sys.stderr)


if __name__ == "__main__":
    main()
