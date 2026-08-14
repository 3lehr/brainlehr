"""Wie wissensnutzen.py, aber Abruf entsteht aus der AUFGABE, nicht aus der
Kenntnis der Loesung (Auftrag 2026-08-07, Knoten 34ef6d8e).

wissensnutzen.py holte den Wissensblock per lesson_query MIT der Kennung der
passenden Lehre im Suchtext -- das misst "hilft es, dem Modell die Loesung in
den Prompt zu schreiben", nicht ob der Abruf sie selbst findet. Hier laeuft
derselbe Weg wie eine echte Sitzung: knowledge_recall_hook.keywords() zerlegt
den unveraenderten Aufgabentext, knowledge_recall_hook.query() sucht damit in
derselben brainlehr.db (FTS-Nodes + Lessons-LIKE) -- keine Handauswahl.

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
angefasst. Liest brainlehr.db (query()/lesson_query), schreibt nichts hinein.
"""
from __future__ import annotations

import os
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
import sys
import time
from pathlib import Path

import zeitmarke

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "haken"))
import ort  # noqa: E402  -- EINE Stelle entscheidet, wo der Verbund liegt
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
# Das Arbeitsverzeichnis, aus dem der Abruf-Hook befragt wird -- es bestimmt
# die Projektzuordnung der Treffer. Ueber BEGOD_RECALL_CWD setzbar, damit der
# Messlauf auch dort faehrt, wo dieses Nachbarprojekt nicht liegt.
RECALL_CWD = os.environ.get(
    "BEGOD_RECALL_CWD",
    str(ort.VERBUND / "fahrtenbuch" / "apps" / "fahrtenbuch_legacy"))

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
    """Der alte Einzelweg: Aufgabe lokal beantworten. Seit der Modellsperre
    (L-a69129) gesperrt und nur noch als Beleg vorhanden, dass genau dieser
    Aufruf der dritte Vorfall war (2026-08-09, gemma4:12b/e4b). Der lauffaehige
    Weg ist die Dreiteilung: --aufgaben, Hauptfaden, --auswerten."""
    runs = []
    for _ in range(N_RUNS):
        started = time.perf_counter()
        raw, err, retries = sl._call_with_retry(
            prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL, timeout=TIMEOUT,
            rolle="beantworten")
        seconds = time.perf_counter() - started
        runs.append({
            "error": err, "retry_count": retries, "call_seconds": seconds,
            "response_full": raw,
        })
    return runs


# --- Dreiteilung: erzeugen (Skript) -> beantworten (Hauptfaden) -> auswerten --
#
# Ein Python-Skript kann keinen Subagenten starten. Deshalb faellt der
# Antwortschritt aus dem Skript heraus, statt die Sperre aufzuweichen; die
# resolution von L-a69129 sagt genau das. Was bleibt, ist beidseitig billig:
# Schritt 1 und 3 sind reine Rechnung ohne Modell, Schritt 2 ist der einzige,
# der ein Modell braucht -- und laeuft dort, wo das Betriebsmodell ohnehin ist.

def aufgaben_erzeugen() -> dict:
    """Abruf + Promptbau, KEIN Modellaufruf. Ergebnis ist die Arbeitsliste fuer
    den Hauptfaden: je Zelle der fertige Prompt und wie oft er zu stellen ist."""
    retrieval: dict[str, dict] = {}
    zellen: list[dict] = []

    for task_id, task in TASKS.items():
        nodes, lessons, kws = blind_retrieve(task["prompt"], task["cwd"])
        lesson_ids = [l["id"] for l in lessons]
        target = task["target_lesson_id"]
        retrieval[task_id] = {
            "keywords": kws, "node_paths": [n["path"] for n in nodes],
            "lesson_ids": lesson_ids, "target_lesson_id": target,
            "trefferguete": (target is not None) and (target in lesson_ids),
            "retrieval_empty": not nodes and not lessons,
        }
        block = format_recall_block(nodes, lessons)
        prompt_ohne = task["prompt"]
        prompt_mit = f"{prompt_ohne}\n\n{block}" if block else prompt_ohne
        for condition, prompt in (("OHNE", prompt_ohne), ("MIT", prompt_mit)):
            zellen.append({"key": f"{task_id}|{condition}", "task": task_id,
                            "condition": condition, "prompt": prompt, "n_runs": N_RUNS})

    return {"erzeugt_am": _jetzt(), "n_runs": N_RUNS, "retrieval": retrieval,
            "zellen": zellen, "konfiguration": schnappschuss()}


def auswerten(aufgaben: dict, antworten: dict, kontaminiert: set[str] | None = None) -> dict:
    """Schritt 3: Antworten des Hauptfadens gegen dieselbe check-Funktion wie
    frueher, gleiche Aggregation. Kein Modellaufruf, keine Sperre.

    Fehlende oder zu kurze Antwortlisten werden NICHT stillschweigend auf die
    vorhandenen gekuerzt -- eine Zelle mit zwei statt drei Laeufen hat eine
    andere Streuung, und Streuung ist hier der Messgegenstand. Sie faellt als
    Fehlbestand auf, damit der Lauf sichtbar unvollstaendig ist statt still
    optimistisch."""
    model = antworten.get("model")
    if not model:
        raise ValueError("Antwortdatei nennt kein Modell -- ohne Modellangabe ist "
                          "die Zeile wertlos, sobald mehrere nebeneinander liegen.")
    gegeben = antworten.get("antworten", {})
    kontaminiert = kontaminiert or set()
    cells: dict[str, dict] = {}
    fehlbestand: list[str] = []
    verworfen: list[str] = []

    for zelle in aufgaben["zellen"]:
        key = zelle["key"]
        # Eine kontaminierte Zelle wird NICHT ausgewertet und nicht als
        # Randnotiz mitgefuehrt: der Antwortende kannte den Traeger der
        # Loesung, bevor er die Aufgabe las (kontamination.py). Ein Mittelwert
        # daneben waere eine Zahl, die aussieht wie eine Messung.
        if key in kontaminiert:
            verworfen.append(key)
            continue
        texte = gegeben.get(key)
        if not texte or len(texte) < zelle["n_runs"]:
            fehlbestand.append(f"{key}: {len(texte or [])}/{zelle['n_runs']}")
            continue
        check = TASKS[zelle["task"]]["check"]
        passed_flags = [check(t or "") for t in texte[:zelle["n_runs"]]]
        cells[f"{key}|{model}"] = {
            "task": zelle["task"], "model": model, "condition": zelle["condition"],
            "aggregate": wn.aggregate(passed_flags),
            "runs": [{"response_full": t, "error": None} for t in texte[:zelle["n_runs"]]],
        }

    return {"models": [model], "n_runs": aufgaben["n_runs"],
            "retrieval": aufgaben["retrieval"], "cells": cells,
            "fehlbestand": fehlbestand, "verworfen_kontaminiert": verworfen,
            "ausgewertet_am": _jetzt(),
            "konfiguration": aufgaben.get("konfiguration")}


def _jetzt() -> str:
    return zeitmarke.jetzt()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--aufgaben", metavar="DATEI",
                     help="Schritt 1: Abruf + Prompts schreiben, kein Modellaufruf")
    ap.add_argument("--auswerten", nargs=2, metavar=("AUFGABEN", "ANTWORTEN"),
                     help="Schritt 3: Antworten des Hauptfadens bewerten, kein Modellaufruf")
    ap.add_argument("--kontamination", metavar="DATEI",
                     help="Befund von kontamination.py -- die dort genannten Zellen "
                          "werden verworfen statt ausgewertet")
    ap.add_argument("--selftest", action="store_true",
                     help="Netzloser Selbsttest von Trefferguete/Blockformat, kein Ollama-Aufruf")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    if args.aufgaben:
        daten = aufgaben_erzeugen()
        ziel = Path(args.aufgaben)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
        for t, r in daten["retrieval"].items():
            print(f"{t} Abruf: kws={r['keywords']} lessons={r['lesson_ids']} "
                  f"ziel={r['target_lesson_id']} trefferguete={r['trefferguete']}", flush=True)
        print(f"\nGeschrieben: {ziel} ({len(daten['zellen'])} Zellen x "
              f"{daten['n_runs']} Laeufe = {len(daten['zellen']) * daten['n_runs']} Antworten)",
              flush=True)
        return

    if args.auswerten:
        aufg = json.loads(Path(args.auswerten[0]).read_text(encoding="utf-8"))
        antw = json.loads(Path(args.auswerten[1]).read_text(encoding="utf-8"))
        kont = set()
        if args.kontamination:
            kont = set(json.loads(Path(args.kontamination).read_text(
                encoding="utf-8"))["kontaminierte_zellen"])
        ergebnis = auswerten(aufg, antw, kont)
        ziel = Path(args.out)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
        for key, zelle in ergebnis["cells"].items():
            print(f"{key:28s} mean={zelle['aggregate']['mean']:.2f} "
                  f"range={zelle['aggregate']['range']}", flush=True)
        if ergebnis["verworfen_kontaminiert"]:
            print(f"\nVERWORFEN (kontaminiert, siehe kontamination.py): "
                  f"{', '.join(ergebnis['verworfen_kontaminiert'])}", flush=True)
        if ergebnis["fehlbestand"]:
            print(f"\nFEHLBESTAND (nicht ausgewertet): {', '.join(ergebnis['fehlbestand'])}",
                  flush=True)
        print(f"\nGeschrieben: {ziel}", flush=True)
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

    # Dreiteilung: auswerten() ohne Netz, mit gestellten Aufgaben/Antworten.
    aufg = {"n_runs": 2, "retrieval": {}, "konfiguration": None, "zellen": [
        {"key": "C|OHNE", "task": "C", "condition": "OHNE", "prompt": PROMPT_C, "n_runs": 2},
        {"key": "C|MIT", "task": "C", "condition": "MIT", "prompt": PROMPT_C, "n_runs": 2},
    ]}
    erg = auswerten(aufg, {"model": "claude-haiku-4-5", "antworten": {
        "C|OHNE": ["kubectl get pods -n default", "kubectl get pod"],   # 1 von 2 richtig
        "C|MIT": ["kubectl get pods", "kubectl get pods -n default"],    # 2 von 2 richtig
    }})
    assert erg["cells"]["C|OHNE|claude-haiku-4-5"]["aggregate"]["mean"] == 0.5, \
        "Bewertung der Antworten stimmt nicht"
    assert erg["cells"]["C|MIT|claude-haiku-4-5"]["aggregate"]["mean"] == 1.0
    assert erg["models"] == ["claude-haiku-4-5"], "Modell kommt aus der Antwortdatei, nicht aus MODELS"
    assert not erg["fehlbestand"] and not erg["verworfen_kontaminiert"]

    # Kontaminierte Zelle: verworfen, NICHT ausgewertet -- und die saubere
    # daneben bleibt erhalten (Gegenprobe, sonst wuerde ein Befund den
    # ganzen Lauf loeschen statt der betroffenen Zelle).
    kont = auswerten(aufg, {"model": "m", "antworten": {
        "C|OHNE": ["kubectl get pods -n default", "kubectl get pod"],
        "C|MIT": ["kubectl get pods", "kubectl get pods -n default"],
    }}, kontaminiert={"C|OHNE"})
    assert kont["verworfen_kontaminiert"] == ["C|OHNE"]
    assert "C|OHNE|m" not in kont["cells"], "kontaminierte Zelle darf keinen Mittelwert bekommen"
    assert "C|MIT|m" in kont["cells"], "die saubere Zelle muss stehen bleiben"

    # Negativfall: eine zu kurze Antwortliste wird NICHT auf die vorhandenen
    # gekuerzt -- sonst sieht eine halbe Zelle aus wie eine ganze.
    luecke = auswerten(aufg, {"model": "m", "antworten": {"C|OHNE": ["kubectl get pods -n default"]}})
    assert luecke["fehlbestand"] == ["C|OHNE: 1/2", "C|MIT: 0/2"], luecke["fehlbestand"]
    assert luecke["cells"] == {}, "unvollstaendige Zelle darf nicht ausgewertet werden"

    # Und ohne Modellangabe gar nichts -- eine Zeile ohne Modell ist wertlos.
    try:
        auswerten(aufg, {"antworten": {}})
    except ValueError:
        pass
    else:
        raise AssertionError("Antwortdatei ohne Modell wurde angenommen")

    print("selftest ok: Blockformat + Trefferguete-Logik + Aufgabe-C-Check + Dreiteilung",
          file=sys.stderr)


if __name__ == "__main__":
    main()
