#!/usr/bin/env python3
"""Misst LongMemEval-V2 (arXiv 2605.12493) ueber den ECHTEN Produktivweg
(knowledge_mcp_server.knowledge_search()) -- Auftrag 2026-08-18, Nachtrag zu
messungen/longmemeval_produktivweg.py (LongMemEval-S). Dieses Skript ist die
Vorlage fuer Bauform (Env-Var-Guard, project_id=Frage-Isolation,
nachschlagewerk=True), NICHT fuer das Kriterium -- V2 ist ein anderer
Benchmark.

KRITERIUM, WOERTLICH GEPRUEFT (offizielles Repo github.com/xiaowu0162/
LongMemEval-V2, geklont 2026-08-18, commit siehe .git/refs):

  evaluation/harness.py::aggregate_metrics() -> breakdown():
    pct_correct = correct_count / n
    correct_count = Anzahl Zeilen mit score_bool==True UND is_unknown==False
  aggregiert PRO KATEGORIE ueber CATEGORY_MAP (harness.py Zeile ~42-52):
    "errors-gotchas" -> Kategorie "gotchas"  (== "Umgebungs-Fallstricke")
    "static-environment" -> "static", "dynamic-environment" -> "dynamic",
    "procedure" -> "procedure" (je + "-abs"-Variante fuer Praemissenfragen)
  NON_ABSTENTION_CATEGORIES = ["static", "dynamic", "procedure", "gotchas"]

  V2 kennt WEDER recall@k NOCH MRR (anders als V1/S: kein retrieval-only
  Ground-Truth-Feld in questions.jsonl -- SCHEMA.md bestaetigt: nur
  id/domain/environment/question_type/question/image/answer/eval_function,
  KEIN answer_session_ids- oder evidence_trajectory_ids-Analog). Die
  Haystacks (haystacks/lme_v2_small.json) sind reine Trajektorienlisten OHNE
  Zielmarkierung. Ein retrieval-only R@k/MRR wie bei S ist bei V2 NICHT
  konstruierbar, ohne eine eigene Ground-Truth-Definition zu erfinden --
  das waere Raten, kein Uebernehmen. Uebernommen wird deshalb woertlich
  pct_correct, der einzige von V2 selbst definierte Wert.

  eval_function je Frage (evaluation/qa_eval_metrics.py, woertlich
  uebernommen): norm_phrase_set_match, norm_phrase_set_match_ordered,
  mc_choice_match, mc_choice_set_match (alle deterministisch, kein Judge)
  sowie llm_abstention_checker/llm_gotchas_checker (LLM-Richter, System-
  Prompts _ABSTENTION_JUDGE_SYSTEM_PROMPT/_GOTCHAS_JUDGE_SYSTEM_PROMPT
  woertlich in diese Datei uebernommen, siehe GOTCHAS_JUDGE_PROMPT unten).

ABWEICHUNG VOM OFFIZIELLEN AUFBAU, UND WARUM SIE NOTWENDIG WAR (kein
Verschweigen, siehe Grenze):
  - Referenz-Reader ist Qwen3.5-9B ueber einen selbst gehosteten
    OpenAI-kompatiblen Endpunkt (README.md, Abschnitt "Model Endpoints").
    Dieser Lauf hat keinen solchen Endpunkt und keinen OPENAI_API_KEY fuer
    den LLM-Richter. STATT eine Zahl vorzutaeuschen, die keiner ist, beide
    Rollen -- Antwort UND fuer die zwei LLM-Fragetypen die Bewertung --
    liegen hier in DIESEM Agentenlauf selbst, mit den woertlichen
    Richter-Prompts aus dem Repo als Massstab (siehe unten). Das ist eine
    Systemabweichung vom Paper-Aufbau, kein zweiter Benchmark -- deshalb im
    Ergebnis unter "abweichung_reader" ausdruecklich benannt.
  - "errors-gotchas" (29 von 451 Fragen) sind AUSNAHMSLOS bildabhaengig
    (image != null, gemessen: Counter({True: 29}) unter allen Gotchas-Fragen,
    Counter({False: 422, True: 29}) insgesamt) -- der Fragetext selbst sagt
    "The screenshot shows ...". Dieses Skript liest die Bilder separat
    (question_screenshots/<id>.png), sie sind NICHT im knowledge_search()-
    Produktivweg (der ist textbasiert). Fuer die Gotchas-Kategorie ist der
    Produktivweg damit PER KONSTRUKTION nur die HAELFTE des Signals
    (Text-Trajektorien-Kontext ja, Bildinhalt der Frage nein) -- als Grenze
    ausgewiesen, nicht verschwiegen.

WEG: knowledge_mcp_server.knowledge_search() liefert die Trajektorien-
Evidenz (Rangliste), project_id=<question_id> isoliert den Heuhaufen (100
Trajektorien je Domaene, gemeinsam, siehe SCHEMA.md "Within each domain, all
questions share one 100-trajectory haystack" -- project_id wird deshalb auf
DOMAENE gesetzt, nicht Frage, sonst waere der geteilte Heuhaufen 100x dupliziert).
Trajektorientext = goal + states (url + action + accessibility_tree je
Zustand), woertliche Felder aus SCHEMA.md, keine eigene Kuerzung der
Bedeutungstraeger (nur triviale Deduplizierung identischer Folgezustaende).

GRENZE: Stichprobe (siehe --n je Kategorie), Reader/Richter = dieser
Agentenlauf statt Qwen3.5-9B/gpt-5.2 (siehe oben), Gotchas-Kategorie ohne
Bildkanal im Retrieval, isolierte Test-DB (siehe --db), keine Aussage ueber
den vollen 451-Fragen-Satz.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

KORPUS_DIR = _w / "korpora" / "longmemeval_v2"
QUESTIONS_DATEI = KORPUS_DIR / "questions.jsonl"
HAYSTACK_DATEI = KORPUS_DIR / "haystacks" / "lme_v2_small.json"
TRAJ_DATEI = KORPUS_DIR / "trajectories.jsonl"
STANDARD_DB = KORPUS_DIR / "messstand.db"
MAX_RESULTS = 120  # Heuhaufen ist 100 Trajektorien, plus Marge
SOURCE_HERKUNFT = "korpora/longmemeval_v2 (xiaowu0162/longmemeval-v2, HuggingFace)"

CATEGORY_MAP = {  # woertlich aus evaluation/harness.py
    "static-environment": "static",
    "dynamic-environment": "dynamic",
    "procedure": "procedure",
    "errors-gotchas": "gotchas",
}
NON_ABSTENTION_TYPES = list(CATEGORY_MAP.keys())

# woertlich aus evaluation/qa_eval_metrics.py::_GOTCHAS_JUDGE_SYSTEM_PROMPT
GOTCHAS_JUDGE_PROMPT = (
    "You are a strict grader for gotchas-style insight questions. "
    "The reference answer describes the key insight(s). "
    "Grade 1 if the model response includes at least one correct insight point from the reference answer "
    "(paraphrase allowed), and does not contradict any reference point. "
    "If the model's direction is wrong, or it contains contradictions against any reference point, grade 0. "
    "If the model gives multiple points, partial coverage is enough for 1 as long as no contradictions appear."
)

KRITERIUM = (
    "LongMemEval-V2 (github.com/xiaowu0162/LongMemEval-V2, evaluation/harness.py::aggregate_metrics(), "
    "gelesen 2026-08-18) definiert 'pct_correct' je Kategorie = Anteil Fragen mit score_bool==True und "
    "is_unknown==False, unter CATEGORY_MAP inkl. 'errors-gotchas' -> 'gotchas' (== Umgebungs-Fallstricke). "
    "Kein R@k/MRR bei V2 (kein Ziel-Trajektorien-Feld in questions.jsonl, anders als V1/S). "
    "score_bool kommt aus eval_function je Frage (norm_phrase_set_match(_ordered), mc_choice_(set_)match "
    "deterministisch; llm_abstention_checker/llm_gotchas_checker als LLM-Richter, hier: dieser Agentenlauf "
    "mit dem woertlichen Richter-Systemprompt aus qa_eval_metrics.py, siehe abweichung_reader)."
)
GRENZE = (
    "Stichprobe je Kategorie (siehe --n-je-kategorie), Reader/Richter = dieser Agentenlauf statt "
    "Qwen3.5-9B/gpt-5.2 (kein eigener Endpunkt/Key vorhanden), Gotchas-Fragen sind bildabhaengig "
    "(29/29 mit question-image) -- der Produktivweg liefert nur den Text-Trajektorien-Kontext, das "
    "Bild wird separat gelesen, NICHT ueber knowledge_search(). Isolierte Test-DB, kein Bezug zum "
    "vollen 451-Fragen-Satz."
)


def lade_fragen() -> list[dict]:
    if not QUESTIONS_DATEI.exists():
        print(f"ABBRUCH: questions.jsonl fehlt: {QUESTIONS_DATEI}", file=sys.stderr)
        sys.exit(1)
    return [json.loads(z) for z in QUESTIONS_DATEI.read_text(encoding="utf-8").splitlines() if z.strip()]


def lade_haystack() -> dict:
    return json.loads(HAYSTACK_DATEI.read_text(encoding="utf-8"))


def trajektorientext(traj: dict) -> str:
    """goal + je Zustand url/action/accessibility_tree, woertliche Felder
    aus SCHEMA.md. Nur triviale Deduplizierung identischer Folgezustaende
    (Heuhaufen wiederholen sonst Fuellmaterial, gleiche Bauform wie S-Skript)."""
    teile = [traj.get("goal") or ""]
    letzter = None
    for st in traj.get("states", []):
        stueck = " ".join(filter(None, [
            st.get("url"), st.get("action"), st.get("accessibility_tree"),
        ]))
        if stueck and stueck != letzter:
            teile.append(stueck)
            letzter = stueck
    return " ".join(teile).strip()


def baue_trajektorien_index(traj_ids_gebraucht: set[str]) -> dict[str, str]:
    """Streamt trajectories.jsonl EINMAL (1.2 GB, keine Zufallsadressierung
    moeglich) und haelt nur die gebrauchten Trajektorien im Speicher."""
    out: dict[str, str] = {}
    if not TRAJ_DATEI.exists():
        print(f"ABBRUCH: trajectories.jsonl fehlt: {TRAJ_DATEI}", file=sys.stderr)
        sys.exit(1)
    with TRAJ_DATEI.open(encoding="utf-8") as fh:
        for zeile in fh:
            if not zeile.strip():
                continue
            rec = json.loads(zeile)
            tid = rec.get("id")
            if tid in traj_ids_gebraucht:
                out[tid] = trajektorientext(rec)
            if len(out) == len(traj_ids_gebraucht):
                break
    return out


def waehle_stichprobe(fragen: list[dict], n_je_kategorie: dict[str, int], seed: int) -> list[dict]:
    rnd = random.Random(seed)
    by_type: dict[str, list[dict]] = {}
    for f in fragen:
        by_type.setdefault(f["question_type"], []).append(f)
    out: list[dict] = []
    for qtyp, n in n_je_kategorie.items():
        pool = by_type.get(qtyp, [])
        out += rnd.sample(pool, min(n, len(pool)))
    return out


def selftest() -> None:
    assert CATEGORY_MAP["errors-gotchas"] == "gotchas"
    traj = {"goal": "G", "states": [
        {"url": "u1", "action": None, "accessibility_tree": "A1"},
        {"url": "u1", "action": None, "accessibility_tree": "A1"},  # Duplikat, muss wegfallen
        {"url": "u2", "action": "click", "accessibility_tree": "A2"},
    ]}
    text = trajektorientext(traj)
    assert text.count("A1") == 1, text
    assert "A2" in text
    print("selftest: ok", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--n-je-kategorie", type=str,
                     default="static-environment=4,dynamic-environment=4,procedure=4,errors-gotchas=6")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--db", type=str, default=str(STANDARD_DB))
    ap.add_argument("--nur-korpus-bauen", action="store_true",
                     help="Nur Fragen ziehen, Heuhaufen-IDs ausgeben, nichts in die DB schreiben")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    n_je_kategorie = {}
    for teil in args.n_je_kategorie.split(","):
        k, v = teil.split("=")
        n_je_kategorie[k.strip()] = int(v)

    fragen = lade_fragen()
    stichprobe = waehle_stichprobe(fragen, n_je_kategorie, args.seed)
    haystack = lade_haystack()

    if args.nur_korpus_bauen:
        gebraucht: set[str] = set()
        for f in stichprobe:
            gebraucht |= set(haystack.get(f["id"], []))
        print(json.dumps({
            "n_fragen": len(stichprobe),
            "n_trajektorien_gebraucht": len(gebraucht),
            "frage_ids": [f["id"] for f in stichprobe],
        }, indent=2))
        return

    # Gleiche Sicherheitsbauform wie messungen/longmemeval_produktivweg.py:
    # BEGOD_KNOWLEDGE_DB ist der Pfad, den knowledge_mcp_server.py tatsaechlich
    # liest (gemessen 2026-08-18, BRAINLEHR_DB wirkt dort NICHT).
    os.environ["BEGOD_KNOWLEDGE_DB"] = args.db
    os.environ["BRAINLEHR_DB"] = args.db
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    import knowledge_mcp_server as kms  # noqa: E402

    produktions_db = (_w / "brainlehr.db").resolve()
    assert kms.DB_PATH.resolve() != produktions_db, (
        f"SICHERHEITSABBRUCH: kms.DB_PATH ({kms.DB_PATH}) zeigt auf die Produktions-DB "
        f"({produktions_db}) -- Env-Var griff nicht. Kein Schreibzugriff.")
    print(f"DB-Ziel bestaetigt: {kms.DB_PATH.resolve()} (!= Produktions-DB)", file=sys.stderr)

    gebraucht = set()
    for f in stichprobe:
        gebraucht |= set(haystack.get(f["id"], []))
    print(f"lade {len(gebraucht)} benoetigte Trajektorien aus trajectories.jsonl ...", file=sys.stderr)
    traj_texte = baue_trajektorien_index(gebraucht)
    fehlend = gebraucht - set(traj_texte)
    if fehlend:
        print(f"BEFUND: {len(fehlend)} Trajektorien-IDs aus dem Heuhaufen fehlen in trajectories.jsonl: "
              f"{sorted(fehlend)[:5]}...", file=sys.stderr)

    root = kms.knowledge_add(
        "/", "LongMemEval V2", "LongMemEval-V2 Heuhaufen, importiert fuer Produktivweg-Messung",
        content="", source=SOURCE_HERKUNFT, gattung="nachschlagewerk",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Fremdkorpus, kein Normanspruch",
        neuer_ast=True, anlass="skript", actor="messlauf_longmemeval_v2", project_id="longmemeval-v2-root",
    )
    if "error" in root and "existiert bereits" not in str(root.get("error", "")):
        conn0 = kms.get_db()
        vorhanden = conn0.execute("SELECT 1 FROM knowledge_nodes WHERE path='/longmemeval-v2'").fetchone()
        conn0.close()
        if not vorhanden:
            print(f"ABBRUCH beim Wurzelknoten: {root}", file=sys.stderr)
            sys.exit(1)

    conn = kms.get_db()
    domaenen_geschrieben: set[str] = set()
    for domaene in {f["domain"] for f in stichprobe}:
        dpath = f"/longmemeval-v2/{kms._slugify(domaene)}"
        vorhanden = conn.execute("SELECT 1 FROM knowledge_nodes WHERE path=?", (dpath,)).fetchone()
        if vorhanden:
            domaenen_geschrieben.add(domaene)
            continue
        droot = kms.knowledge_add(
            "/longmemeval-v2", domaene, f"Heuhaufen Domaene {domaene}", content="",
            source=SOURCE_HERKUNFT, gattung="nachschlagewerk", norm_entscheidung="keine_norm",
            norm_entschieden_grund="Fremdkorpus, kein Normanspruch",
            anlass="skript", actor="messlauf_longmemeval_v2", project_id=domaene,
        )
        if "error" in droot:
            print(f"ABBRUCH bei Domaene {domaene}: {droot}", file=sys.stderr)
            sys.exit(1)
        domaenen_geschrieben.add(domaene)

    geschrieben: set[str] = set()
    for f in stichprobe:
        for tid in haystack.get(f["id"], []):
            if tid in geschrieben or tid not in traj_texte:
                continue
            text = traj_texte[tid]
            if not text.strip():
                continue
            dpath = f"/longmemeval-v2/{kms._slugify(f['domain'])}"
            r = kms.knowledge_add(
                dpath, tid, tid, content=text,
                source=f"{SOURCE_HERKUNFT}, Trajektorie {tid}",
                gattung="nachschlagewerk", norm_entscheidung="keine_norm",
                norm_entschieden_grund="Fremdkorpus, kein Normanspruch",
                anlass="skript", actor="messlauf_longmemeval_v2", project_id=f["domain"],
            )
            if "error" in r:
                print(f"ABBRUCH bei Trajektorie {tid}: {r}", file=sys.stderr)
                sys.exit(1)
            geschrieben.add(tid)
    conn.close()
    print(f"Korpus geschrieben: {len(geschrieben)} Trajektorien, {len(domaenen_geschrieben)} Domaenen",
          file=sys.stderr)

    # Rangliste je Frage -- scope=domain, weil der Heuhaufen JE DOMAENE geteilt ist
    ergebnisse = []
    for f in stichprobe:
        out = kms.knowledge_search(f["question"], scope=f["domain"], max_results=MAX_RESULTS,
                                    nachschlagewerk=True)
        rang = [r["title"] for r in out["results"] if r.get("path", "").count("/") > 2]
        ergebnisse.append({"frage": f, "rangliste_trajektorien": rang[:20]})

    out_path = Path(args.out) if args.out else (
        _w / "runs" / f"longmemeval_v2_korpus_{__import__('datetime').datetime.now():%Y-%m-%dT%H%M%S}.json"
    )
    out_path.write_text(json.dumps({
        "weg": "knowledge_mcp_server.knowledge_search() -- echter Produktivweg, kein Nachbau. "
               "Dieser Lauf liefert NUR die Retrieval-Ranglisten je Frage (Vorstufe fuer die "
               "eigentliche pct_correct-Messung, die eine Antwort + Bewertung braucht, siehe "
               "Docstring 'ABWEICHUNG VOM OFFIZIELLEN AUFBAU').",
        "kriterium": KRITERIUM,
        "grenze": GRENZE,
        "stichprobe_ids": [f["id"] for f in stichprobe],
        "ergebnisse": ergebnisse,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_path}")


if __name__ == "__main__":
    main()
