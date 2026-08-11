"""Pruefkorpus V2 -- korrigiertes Anti-Zirkularitaetskriterium (Auftrag
2026-08-07, Folgeauftrag zu pruefkorpus.py). Ueberschreibt pruefkorpus.py
NICHT -- die alte Fassung bleibt als Vergleichspunkt (misst den Extremfall
ohne jede Begriffsueberschneidung, das ist selbst eine Aussage).

FEHLER DER V1-AUFLAGE: seltene Begriffe(Aufgabe) ∩ seltene Begriffe(Ziel) = leer.
bm25 findet aber GENAU ueber geteilte Begriffe -- die Auflage verbot der
generierten Aufgabe jedes Fachwort, das auch im Ziel selten vorkommt, und
machte den Korpus dadurch strukturell unloesbar (Trefferguete ~0 % in allen
drei Zustaenden A/B/C, siehe shared-knowledge/runs/messlauf_abrufguete.json).

NEUES KRITERIUM (Auftrag Punkt 1): Zitat statt Themenverwandtschaft.
    zusammenhaengende Wortfolge(Aufgabe, N=4) ∩ zusammenhaengende Wortfolge(Ziel, N=4) = leer
Einzelne Fachbegriffe -- auch seltene -- duerfen geteilt werden, das ist
normale Themenverwandtschaft und fuer bm25/Embedding-Abruf sogar noetig,
damit ein loesbarer Fall ueberhaupt loesbar ist. Verboten ist nur die
WOERTLICHE UEBERNAHME der unterscheidenden Formulierung -- vier Woerter am
Stueck in exakt gleicher Reihenfolge kommen in unabhaengig formulierten
deutschen Saetzen praktisch nie zufaellig vor (anders als ein einzelnes
seltenes Substantiv), das ist der Grund fuer 4 statt der vorgeschlagenen
Spanne 4-5: die kuerzere Zahl faengt auch kurze, aber immer noch erkennbare
Zitate, ohne dass die Falsch-Positiv-Rate spuerbar steigt (Begruendung testbar
in _selftest, nicht gemessen). KEIN IDF/keine Seltenheitsschwelle mehr noetig
-- Wortfolgen-Ueberlappung ist bestandsgroessen-unabhaengig, umgeht damit auch
L-daca0a (Schwelle nicht uebertragbar zwischen Bestaenden verschiedener Groesse).

EICHUNG ZUERST (Auftrag Punkt 2): run_v2() prueft den ERSTEN akzeptierten
Fall sofort per echtem Abruf (ueber alle drei Zustaende, Funktionen aus
messlauf_abrufguete.py wiederverwendet). Kein Treffer in keinem Zustand ->
Abbruch VOR der restlichen Erzeugung, keine 45 Faelle auf einem kaputten
Kriterium.

Wiederverwendet (Ponytail-Leiter, nur Import/Aufruf, keine der Dateien
geaendert): pruefkorpus.py (load_bestand, node_text, lesson_text,
pick_candidates, CATEGORY_TARGETS, _NEGATIVE_TOPICS, fold_de) und
messlauf_abrufguete.py (STATES, _with_state, run_case, target_hit) fuer die
Eichung. schreibpruefstand/schreiblauf.py::_call_with_retry wie in v1.

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
import json
import random
import re
import sys
from pathlib import Path

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE / "schreibpruefstand"))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "kern"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import schreiblauf as sl  # noqa: E402  -- _call_with_retry wiederverwendet
import pruefkorpus as pk1  # noqa: E402  -- nur gelesen/aufgerufen, nicht geaendert
import messlauf_abrufguete as msl  # noqa: E402  -- nur gelesen/aufgerufen, fuer die Eichung

MODEL = sl.DEFAULT_MODEL
TIMEOUT = 180.0
OUT_PATH = SHARED_KNOWLEDGE / "runs" / "pruefkorpus_v2.json"
JSONL_PATH = OUT_PATH.with_suffix(".jsonl")

SEED = pk1.SEED  # gleicher Seed wie v1 -- pick_candidates() waehlt dieselben
                  # Zieleintraege, dadurch sind v1/v2 auf denselben Faellen
                  # vergleichbar, nicht nur auf gleich grossen Stichproben.

NGRAM_N = 4  # Begruendung siehe Modul-Docstring

MAX_ATTEMPTS = pk1.MAX_ATTEMPTS
CATEGORY_TARGETS = pk1.CATEGORY_TARGETS


def ngrams(text: str, n: int = NGRAM_N) -> set[tuple[str, ...]]:
    """Zusammenhaengende Wortfolgen der Laenge n, gefaltet/lowercase. Anders
    als pk1.tokenize() KEIN Stopwortfilter -- ein Zitat bleibt ein Zitat auch
    mit 'und'/'der' darin, die Reihenfolge ist der Punkt, nicht die Seltenheit."""
    words = re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", pk1.fold_de(text))
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def is_circular_v2(task_text: str, target_text: str, n: int = NGRAM_N) -> set[tuple[str, ...]]:
    """Geteilte woertliche Wortfolgen (leer = nicht zirkulaer nach neuem Kriterium)."""
    return ngrams(task_text, n) & ngrams(target_text, n)


# Fassung 2 des Prompts (Folgeauftrag): die erste Fassung sagte nur, was
# NICHT geschehen soll ("nicht woertlich uebernehmen") -- ein Modell legt
# eine Verbots-Auflage maximal aus und meidet dann JEDE identifizierende
# Vokabel, auch die ausdruecklich erlaubte (belegt am Pilotfall L-a9ccd0:
# "Fahrtdaten nach einem Telefonanruf verschwunden" nennt weder "Timeout"
# im Fachsinn noch sonst ein Wort des Ziels). Dieselbe Form dreimal am
# selben Tag im Verbund (Anti-Zirkularitaet v1, Ensemble-Pflicht, jetzt
# hier) -- darum jetzt eine POSITIVE Anweisung ("nenn die Sache beim
# Namen") plus ein ausgearbeitetes Beispiel statt einer Verbotsregel; die
# Vier-Wort-Pruefung bleibt der Waechter im Code, nicht die Anweisung im
# Prompt.
_GEN_TEMPLATE = """Beispiel, wie eine gute Aufgabe aussieht:
  Zieleintrag: "Bei Verdacht auf Schlaganfall wird nicht der Hausarzt, \
sondern direkt 112 gerufen, weil jede Minute zaehlt (Lyse-Fenster 4,5h)."
  Gute Aufgabe: "In der Familien-Chatgruppe fragt jemand, ob man bei einer \
Verwandten mit ploetzlicher Sprachstoerung und haengendem Mundwinkel erst \
den Hausarzt anrufen soll oder direkt den Notruf."
  Warum gut: Sie nennt die Fachsache beim Namen (Schlaganfall-Symptome, \
Notruf vs. Hausarzt) -- genau wie ein Kollege im Gespraech reden wuerde --, \
uebernimmt aber keinen zusammenhaengenden Satzteil aus dem Zieleintrag \
woertlich ("Lyse-Fenster 4,5h" taucht nicht auf).

Ausgangswissen fuer deine Aufgabe:
{quelle}

Schreibe EINE realistische Alltags- oder Arbeitssituation (2-4 Saetze, \
deutsch), in der genau dieses Wissen gebraucht wuerde. Beschreibe eine \
konkrete Lage/ein Problem, KEINE Frage nach dem Eintrag selbst. Nenn die \
Fachsache beim Namen, so wie ein Kollege sie im Gespraech nennen wuerde -- \
Fachbegriffe, Systemnamen, uebliche Ausdruecke des Themas gehoeren in eine \
gute Aufgabe hinein. Nur die charakteristische FORMULIERUNG des \
Zieleintrags darf nicht abgeschrieben sein.{vermeiden}
Antworte NUR mit dem Aufgabentext, kein Vorwort, keine Ueberschrift."""


def generate_task(target_text: str, rng: random.Random, model: str = MODEL) -> dict:
    attempts = []
    vermeiden = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        prompt = _GEN_TEMPLATE.format(quelle=target_text[:1200], vermeiden=vermeiden)
        # erzeugen (Aufgabentext), lokal absichtlich -- L-a69129.
        raw, err, retries = sl._call_with_retry(prompt, model=model, base_url=sl.DEFAULT_OLLAMA_URL,
                                                 timeout=TIMEOUT, rolle="erzeugen")
        if err or not raw or not raw.strip():
            attempts.append({"attempt": attempt, "text": None, "error": err, "collision": None})
            continue
        task_text = raw.strip()
        collision = is_circular_v2(task_text, target_text)
        attempts.append({
            "attempt": attempt, "text": task_text, "error": None,
            "collision": [" ".join(c) for c in sorted(collision)] if collision else [],
        })
        if not collision:
            return {"accepted": True, "task": task_text, "attempts": attempts, "error": None}
        beispiel = ", ".join(f'"{" ".join(c)}"' for c in sorted(collision))
        vermeiden = f" Vermeide diese woertliche(n) Wortfolge(n): {beispiel}."
    return {"accepted": False, "task": None, "attempts": attempts,
            "error": "kein nicht-zirkulaerer Fall nach MAX_ATTEMPTS Versuchen"}


def _append_jsonl(record: dict, path: Path = JSONL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def _pilot_check(record: dict) -> dict:
    """Eichung Punkt 2: der ERSTE akzeptierte Fall wird sofort real abgerufen
    (alle drei Zustaende, gleiche Funktionen wie messlauf_abrufguete.py)."""
    for name in msl.STATES:
        with msl._with_state(msl.STATES[name]):
            nodes, lessons = msl.run_case(record)
            if msl.target_hit(record, nodes, lessons):
                return {"ok": True, "zustand": name, "target_id": record["target_id"], "task": record["task"]}
    return {"ok": False, "zustand": None, "target_id": record["target_id"], "task": record["task"]}


def run(out_path: Path = OUT_PATH, seed: int = SEED, model: str = MODEL) -> dict:
    rng = random.Random(seed)
    nodes, lessons = pk1.load_bestand()
    print(f"Bestand: {len(nodes)} Nodes + {len(lessons)} Lessons. Kein IDF noetig "
          f"(Kriterium ist Wortfolgen-Ueberlappung, NGRAM_N={NGRAM_N}).", flush=True)

    picks = pk1.pick_candidates(nodes, lessons, rng)
    cases: list[dict] = []
    skipped: list[dict] = []
    pilot_result: dict | None = None

    for category in ("lesson", "fact", "norm"):
        for entry in picks[category]:
            if category == "lesson":
                target_id, label, text = entry["id"], entry["description"][:80], pk1.lesson_text(entry)
            else:
                target_id, label, text = entry["path"], entry["title"], pk1.node_text(entry)
            result = generate_task(text, rng, model=model)
            record = {
                "category": category, "target_kind": "lesson" if category == "lesson" else "node",
                "target_id": target_id, "target_label": label,
                "accepted": result["accepted"], "task": result["task"],
                "attempts": result["attempts"],
            }
            _append_jsonl(record)
            if result["accepted"]:
                cases.append({"category": category, "target_kind": record["target_kind"],
                               "target_id": target_id, "target_label": label, "prompt": result["task"]})
                print(f"  {category} {target_id}: ok nach {len(result['attempts'])} Versuch(en)", flush=True)

                if pilot_result is None:
                    pilot_result = _pilot_check(record)
                    print(f"\nEICHFALL (Auftrag Punkt 2): {json.dumps(pilot_result, ensure_ascii=False)}\n", flush=True)
                    if not pilot_result["ok"]:
                        print("Korpus unbrauchbar: Eichfall in keinem Zustand gefunden -- "
                              "Abbruch VOR Vollerzeugung.", flush=True)
                        out = {"pilot": pilot_result, "aborted": True, "n_cases": 1, "cases": cases}
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
                        return out
            else:
                skipped.append({"category": category, "target_id": target_id, "target_label": label,
                                 "reason": result["error"]})
                print(f"  {category} {target_id}: UEBERSPRUNGEN ({result['error']})", flush=True)

    topics = rng.sample(pk1._NEGATIVE_TOPICS, min(CATEGORY_TARGETS["negative"], len(pk1._NEGATIVE_TOPICS)))
    for topic in topics:
        record = {"category": "negative", "target_kind": None, "target_id": None,
                   "target_label": None, "accepted": True,
                   "task": topic, "attempts": [{"attempt": 1, "text": topic, "error": None}]}
        _append_jsonl(record)
        cases.append({"category": "negative", "target_kind": None, "target_id": None,
                       "target_label": None, "prompt": topic})
        print(f"  negative: ok ({topic[:40]}...)", flush=True)

    from collections import Counter
    verteilung = Counter(c["category"] for c in cases)
    versuche = Counter()
    # Wie oft schlug der Vier-Wort-Waechter (is_circular_v2) tatsaechlich an,
    # getrennt von technischen Fehlern (Ollama-Timeout etc.) -- Auftrag:
    # "verwirft die Pruefung jetzt etwas, oder ist sie nutzlos/zu scharf?"
    zirkularitaet_verworfen = fehler_verworfen = gesamt_versuche = 0
    for c_record_line in JSONL_PATH.read_text(encoding="utf-8").splitlines():
        r = json.loads(c_record_line)
        versuche[len(r["attempts"])] += 1
        for a in r["attempts"]:
            gesamt_versuche += 1
            if a.get("error"):
                fehler_verworfen += 1
            elif a.get("collision"):
                zirkularitaet_verworfen += 1

    output = {
        "seed": seed, "model": model, "ngram_n": NGRAM_N, "max_attempts": MAX_ATTEMPTS,
        "n_cases": len(cases), "n_skipped": len(skipped),
        "verteilung": dict(verteilung), "versuche_je_fall": dict(versuche),
        "gesamt_versuche": gesamt_versuche,
        "verworfen_wegen_vier_wort_ueberlappung": zirkularitaet_verworfen,
        "verworfen_wegen_technischem_fehler": fehler_verworfen,
        "pilot": pilot_result, "aborted": False,
        "cases": cases, "skipped": skipped,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {out_path}", flush=True)
    print(f"Erzeugt: {len(cases)}  Uebersprungen: {len(skipped)}  Verteilung: {dict(verteilung)}", flush=True)
    print(f"Versuche je Fall: {dict(versuche)}", flush=True)
    return output


def _selftest() -> None:
    """Netzloser Selbsttest: n-Gramm-Kriterium, kein Ollama."""
    ziel = ("AlertDialog showDialog erzeugt Vollbild-Weissraum in ActionScreen.\n"
            "Globaler Shim faengt showDialog ab.\n"
            "ActionScreen(expandPrimaryAction:true) verwenden.")

    # 1) Woertliche Uebernahme von 4 Woertern am Stueck MUSS anschlagen.
    zitat_task = "Bei uns gilt: globaler Shim faengt showDialog ab, deshalb kennen wir das Problem."
    c1 = is_circular_v2(zitat_task, ziel)
    assert c1, "4-Wort-Zitat haette erkannt werden muessen"
    print(f"  Zitat (4 Woerter woertlich) erkannt: {[' '.join(x) for x in c1]}")

    # 2) Der alte Fehlerfall: einzelne Fachbegriffe/seltene Woerter teilen,
    #    aber KEINE zusammenhaengende Wortfolge -- darf NICHT mehr anschlagen
    #    (das genau war die zu scharfe v1-Auflage, siehe Docstring).
    fachwort_task = "Ich habe ein Problem mit ActionScreen und showDialog in meiner App."
    c2 = is_circular_v2(fachwort_task, ziel)
    assert not c2, f"Einzelne geteilte Fachbegriffe (kein Zitat) faelschlich als zirkulaer erkannt: {c2}"
    print("  Geteilte Einzelbegriffe ohne zusammenhaengende Wortfolge NICHT erkannt: ok (V1-Fehler behoben)")

    # 3) Frei formulierte Aufgabe (v1-Gegenprobe) bleibt weiterhin frei.
    freie_task = ("Im Auto-Werkstattbuch soll eine Bestaetigung erscheinen, bevor "
                  "eine Fahrt beendet wird, ohne den Bildschirm mit weissem Rand zu zeigen.")
    c3 = is_circular_v2(freie_task, ziel)
    assert not c3, f"Frei formulierte Aufgabe faelschlich als zirkulaer erkannt: {c3}"
    print("  Frei formulierte Aufgabe weiterhin NICHT als zirkulaer erkannt: ok")

    # 4) Grenzwert: 3 gemeinsame Woerter am Stueck reichen NICHT, 4 schon.
    drei = ngrams("globaler shim faengt", n=3) & ngrams(ziel, n=3)
    vier = ngrams("globaler shim faengt showdialog", n=4) & ngrams(ziel, n=4)
    assert drei and vier, "Vorbedingung fuer Grenzwerttest verletzt"
    assert not is_circular_v2("globaler shim faengt niemanden", ziel, n=4), \
        "3 gemeinsame Woerter am Stueck haetten bei N=4 nicht anschlagen duerfen"
    print("  Grenzwert N=4 (3 Woerter am Stueck reichen nicht, 4 schon): ok")

    print(f"selftest ok (NGRAM_N={NGRAM_N})", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        _selftest()
        return
    run(out_path=Path(args.out), seed=args.seed, model=args.model)


if __name__ == "__main__":
    main()
