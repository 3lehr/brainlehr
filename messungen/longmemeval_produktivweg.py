#!/usr/bin/env python3
"""Misst R@5, R@10, MRR auf LongMemEval-S ueber den ECHTEN Produktivweg
(knowledge_mcp_server.knowledge_search()) -- Auftrag 2026-08-18, Vergleich
gegen die auf der Startseite von github.com/rohitg00/agentmemory (27140
Sterne) genannten, UNGEPRUEFT uebernommenen Zahlen "R@5: 95.2%, R@10: 98.6%,
MRR: 88.2%" auf "LongMemEval-S, 500 questions".

KRITERIUM, WOERTLICH GEPRUEFT (Schritt 2 des Auftrags): das offizielle
LongMemEval-Repo (github.com/xiaowu0162/LongMemEval, gelesen 2026-08-18 ueber
src/retrieval/eval_utils.py und src/evaluation/print_retrieval_metrics.py)
definiert WEDER "R@5"/"R@10" NOCH "MRR". Es definiert:

    recall_any@k -- 1, wenn IRGENDEINE der Ziel-Sitzungen unter den Top-k ist
    recall_all@k -- 1, wenn ALLE Ziel-Sitzungen unter den Top-k sind
    ndcg_any@k   -- NDCG auf Basis von recall_any

je auf Sitzungs- UND Turn-Ebene (print_retrieval_metrics.py:
sess_metric_names = ['recall_all@5', 'ndcg_any@5', 'recall_all@10', 'ndcg_any@10']).
KEIN MRR im gesamten Auswertungscode (`grep -i mrr` auf eval_utils.py,
run_retrieval.py, print_retrieval_metrics.py: 0 Treffer).

DAS IST DER BEFUND aus Schritt 2, nicht geraten: "R@5"/"R@10"/"MRR" sind
KEINE LongMemEval-eigenen Kennzahlen -- die Gegenseite hat entweder selbst
gerechnet (mit unbekannter Definition) oder generische IR-Begriffe verwendet.
Diese Messung uebernimmt deshalb NICHT eine erfundene LongMemEval-Definition,
sondern:
  - R@k als der Sitzungs-Ebene-Analog von recall_any@k (offizielle Definition,
    woertlich uebernommen: mind. eine Ziel-Sitzung unter den Top-k) -- das ist
    fuer Fragen mit genau einer Zielsitzung identisch mit dem ueblichen
    IR-Recall@k, fuer Mehrfachziel-Fragen die GROSSZUEGIGERE der beiden
    offiziellen Varianten (recall_any, nicht recall_all).
  - MRR als Standard-IR-Definition (mittlerer reziproker Rang der ERSTEN
    Ziel-Sitzung in der Rangliste, 0 wenn keine Ziel-Sitzung unter max_results
    liegt) -- KEIN LongMemEval-Wert, sondern die ueblichste generische
    Definition, weil LongMemEval selbst keine liefert.
Diese Abweichung wird in jedem Ergebnis unter "kriterium" wiederholt, nicht
nur hier im Docstring.

GRUNDLAGE (Sitzungs-Text): offizieller Baseline-Code (run_retrieval.py::
process_item_flat_index, granularity='session') baut den Sitzungstext aus
NUR den user-Turns, leerzeichen-verkettet ('  '.join). Woertlich uebernommen.
Zielmenge: das Feld answer_session_ids der Frage direkt (bereits im
Cleaned-Datensatz aufgeloest, keine eigene has_answer-Rekonstruktion noetig).

WEG: knowledge_mcp_server.knowledge_search() -- kein Nachbau, siehe
messungen/anfrageumschrift_produktivweg.py fuer dieselbe Bauform gegen den
eigenen Pruefkorpus.

ISOLATION PRO FRAGE: LongMemEval haengt jeder Frage ihren EIGENEN Heuhaufen
(38-62 Sitzungen) an -- kein gemeinsamer Korpus ueber alle 500 Fragen. Der
Produktivweg filtert scope='projekt' als project_id-Gleichheit (WHERE
project_id IN ('shared', scope)); jede Frage bekommt deshalb ihre eigene
project_id (= question_id), scope=question_id repliziert den Heuhaufen exakt,
OHNE eine zweite Suchfunktion zu bauen.

FESTVERDRAHTET, UND WELCHE FACHLOGIK ES LIEST:
  - scope=<question_id> je Frage -- project_id-Filter in knowledge_search()
    (WHERE project_id IN ('shared', scope)), repliziert den Heuhaufen.
  - max_results=70 -- deckt den groessten beobachteten Heuhaufen (62) plus
    Marge ab; _fuse_with_keyword_floor() kappt VOR der Rueckgabe, ein Rang
    jenseits davon ist mit diesem Aufbau nicht von Ausfall unterscheidbar.
  - nachschlagewerk=True -- siehe Befund zum Gattungsfilter unten.
  - stichtag/actor/model/session=None (jetzt/keine Identitaet).
  - Sprache: Fragen und Sitzungen sind ENGLISCH (LongMemEval), unsere
    Einbettung bge-m3 ist mehrsprachig, der Stichwortkanal (FTS5) ist deutsch
    gefaltet -- ein moeglicher Nachteil fuer den Stichwortkanal auf
    englischem Text, hier NICHT gesondert gemessen (siehe "grenze" im
    Ergebnis).

GATTUNGSFILTER-BEFUND (Auftrag Punkt 4): der Korpus wird MIT
gattung='nachschlagewerk' angelegt (Auftrag verlangt das ausdruecklich, um
den Arbeitsbestand nicht zu verunreinigen). knowledge_search() filtert
gattung='nachschlagewerk' PER VORGABE aus (kern/gattung_filter.
SQL_ARBEITSBESTAND_NUR) -- ein Aufruf OHNE nachschlagewerk=True liefert damit
fuer JEDE Frage dieses Laufs GENAU NULL Treffer, weil ausnahmslos alle
eingelesenen Knoten diese Gattung tragen. Das wird unten tatsaechlich EINMAL
gemessen (Kontrollmessung "gattungsfilter_default") und ist der geforderte
Befund. Die Hauptmessung selbst ruft danach nachschlagewerk=True -- der
Auftrag verbietet das Umgehen des Filters, nicht die Nutzung des dafuer
vorgesehenen, offiziellen Parameters ("wer wirklich in
germanquad/nasa-llis/hier: longmemeval nachschlagen will, sagt es
explizit" -- knowledge_search()-Docstring). Ohne ihn ist keine einzige Zahl
in diesem Lauf messbar.

GRENZE: diese Zahlen bewerten ausschliesslich den Produktivweg auf englischem
Text in einer isolierten, projektweise abgeschotteten Test-DB (BRAINLEHR_DB,
keine Produktivdatenbank beruehrt). Keine Aussage ueber Mehrsprachigkeit
generell, ueber den vollen 500-Fragen-Satz (Stichprobe, siehe --n) oder ueber
die von der Gegenseite tatsaechlich verwendete Berechnung (unbekannt, siehe
Kriterium oben).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import statistics as st
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

KORPUS_DATEI = _w / "korpora" / "longmemeval" / "longmemeval_s_cleaned.json"
STANDARD_DB = _w / "korpora" / "longmemeval" / "messstand.db"
MAX_RESULTS = 70  # groesster beobachteter Heuhaufen (62) + Marge, siehe Docstring
SOURCE_HERKUNFT = "korpora/longmemeval/longmemeval_s_cleaned.json (LongMemEval-S, xiaowu0162/longmemeval-cleaned)"

KRITERIUM = (
    "LongMemEval (github.com/xiaowu0162/LongMemEval, src/retrieval/eval_utils.py + "
    "src/evaluation/print_retrieval_metrics.py, gelesen 2026-08-18) definiert weder "
    "'R@5'/'R@10' noch 'MRR' -- nur recall_any@k, recall_all@k, ndcg_any@k (session- "
    "und turn-level). R@k hier = recall_any@k (offizielle, woertliche Definition: "
    "mind. eine Ziel-Sitzung unter Top-k) -- die grosszuegigere der beiden offiziellen "
    "Varianten. MRR ist KEINE LongMemEval-Kennzahl, sondern die generische IR-Definition "
    "(reziproker Rang der ersten Ziel-Sitzung, 0 falls nicht unter max_results). "
    "Sitzungstext = nur user-Turns, leerzeichenverkettet (process_item_flat_index, "
    "granularity='session', woertlich uebernommen)."
)
GRENZE = (
    "Nur Produktivweg auf englischem Text, isolierte Test-DB (BRAINLEHR_DB), "
    "Stichprobe statt aller 500 Fragen (siehe n), MRR/R@k-Definition ist NICHT "
    "die der Gegenseite (unbekannt) sondern die naeheste belegbare (siehe kriterium). "
    "Gattungsfilter schliesst den gesamten Korpus per Vorgabe aus (siehe "
    "gattungsfilter_default) -- Hauptmessung nutzt bewusst nachschlagewerk=True."
)


def lade_datensatz() -> list[dict]:
    if not KORPUS_DATEI.exists():
        print(f"ABBRUCH: LongMemEval-Datei fehlt: {KORPUS_DATEI}", file=sys.stderr)
        sys.exit(1)
    return json.loads(KORPUS_DATEI.read_text(encoding="utf-8"))


def sitzungstext(sitzung: list[dict]) -> str:
    """Nur user-Turns, leerzeichenverkettet -- process_item_flat_index()
    granularity='session' im offiziellen Repo, woertlich uebernommen."""
    return " ".join(t["content"] for t in sitzung if t.get("role") == "user")


def baue_korpus(kms, faelle: list[dict]) -> None:
    """Legt Wurzel + je Frage einen Projektast mit ihrem eigenen Heuhaufen an,
    gattung='nachschlagewerk' (Auftrag Punkt 4). Ueberspringt Fragen, deren
    Wurzelpfad schon existiert (Wiederholungslauf gegen dieselbe DB-Datei)."""
    root = kms.knowledge_add(
        "/", "LongMemEval S", "LongMemEval-S Heuhaufen, importiert fuer Produktivweg-Messung",
        content="", source=SOURCE_HERKUNFT, gattung="nachschlagewerk",
        norm_entscheidung="keine_norm", norm_entschieden_grund="Fremdkorpus, kein Normanspruch",
        neuer_ast=True, anlass="skript", actor="messlauf_longmemeval", project_id="longmemeval-root",
    )
    if "error" in root and "existiert bereits" not in str(root.get("error", "")):
        # existierender Ast ist ok (Wiederholungslauf); jeder andere Fehler ist ein Abbruch
        vorhanden = kms.get_db().execute(
            "SELECT 1 FROM knowledge_nodes WHERE path='/longmemeval-s'").fetchone()
        if not vorhanden:
            print(f"ABBRUCH beim Wurzelknoten: {root}", file=sys.stderr)
            sys.exit(1)

    conn = kms.get_db()
    for f in faelle:
        qid = f["question_id"]
        # knowledge_add() slugifiziert den Titel fuer den Pfad (_ -> -) --
        # der tatsaechliche Pfad wird darum aus der eigenen Slugify-Funktion
        # berechnet, nicht aus qid selbst geraten (L-Fund dieses Laufs).
        qpath = f"/longmemeval-s/{kms._slugify(qid)}"
        vorhanden = conn.execute("SELECT 1 FROM knowledge_nodes WHERE path=?", (qpath,)).fetchone()
        if vorhanden:
            continue  # dieser Fall ist schon eingelesen (Wiederholungslauf)
        qroot = kms.knowledge_add(
            "/longmemeval-s", qid, f["question_type"], content=f["question"],
            source=f"{SOURCE_HERKUNFT}, Frage {qid}", gattung="nachschlagewerk",
            norm_entscheidung="keine_norm", norm_entschieden_grund="Fremdkorpus, kein Normanspruch",
            anlass="skript", actor="messlauf_longmemeval", project_id=qid,
        )
        if "error" in qroot:
            print(f"ABBRUCH bei Frage {qid}: {qroot}", file=sys.stderr)
            sys.exit(1)
        qpath = qroot["path"]
        gesehen: set[str] = set()
        for sid, sitzung in zip(f["haystack_session_ids"], f["haystack_sessions"]):
            # Heuhaufen wiederholen dieselbe session_id gelegentlich als
            # Fuellmaterial (gemessen bei diesem Lauf, Frage caf03d32) --
            # zweiter Knoten am selben Pfad waere ein Fehler, kein neuer Fall.
            if sid in gesehen:
                continue
            gesehen.add(sid)
            text = sitzungstext(sitzung)
            if not text.strip():
                continue
            r = kms.knowledge_add(
                qpath, sid, sid, content=text,
                source=f"{SOURCE_HERKUNFT}, Frage {qid}, Sitzung {sid}",
                gattung="nachschlagewerk", norm_entscheidung="keine_norm",
                norm_entschieden_grund="Fremdkorpus, kein Normanspruch",
                anlass="skript", actor="messlauf_longmemeval", project_id=qid,
            )
            if "error" in r:
                print(f"ABBRUCH bei Sitzung {sid} (Frage {qid}): {r}", file=sys.stderr)
                sys.exit(1)
    conn.close()


def rangliste(kms, query: str, scope: str, *, nachschlagewerk: bool) -> list[str]:
    """Liefert die Rangliste als Sitzungs-IDs (== Knotentitel, siehe
    baue_korpus: title=sid). Der Fragen-Wurzelknoten selbst traegt title=qid,
    NICHT der Sitzungs-ID-Form -- wird ueber den path-Praefix erkannt und
    ausgefiltert (er ist keine Sitzung, kann kein Zieltreffer sein)."""
    out = kms.knowledge_search(query, scope=scope, max_results=MAX_RESULTS,
                                nachschlagewerk=nachschlagewerk)
    return [r["title"] for r in out["results"] if r.get("path", "").count("/") > 2]


def reziproker_rang(rang_liste: list[str], ziel: set[str]) -> tuple[float, int | None]:
    for i, sid in enumerate(rang_liste, start=1):
        if sid in ziel:
            return 1.0 / i, i
    return 0.0, None


def recall_any_at_k(rang_liste: list[str], ziel: set[str], k: int) -> float:
    return 1.0 if any(sid in ziel for sid in rang_liste[:k]) else 0.0


def positivkontrolle(kms, faelle: list[dict]) -> dict:
    """Nimmt die ERSTE Zielsitzung des ERSTEN Falls, formt die Anfrage aus
    einem woertlichen Ausschnitt IHRES EIGENEN Textes (40 Zeichen aus der
    Mitte, damit kein Zufallstreffer durch Randformatierung) -- die
    Zielsitzung kommt damit per Konstruktion woertlich in der Frage vor.
    MUSS auf Rang 1 landen, sonst ist der Aufbau verdaechtig (Abnahmekriterium)."""
    f = faelle[0]
    ziel_sid = f["answer_session_ids"][0]
    idx = f["haystack_session_ids"].index(ziel_sid)
    text = sitzungstext(f["haystack_sessions"][idx])
    mitte = len(text) // 2
    ausschnitt = text[mitte:mitte + 60].strip()
    rl = rangliste(kms, ausschnitt, scope=f["question_id"], nachschlagewerk=True)
    rang = rl.index(ziel_sid) + 1 if ziel_sid in rl else None
    return {"frage_id": f["question_id"], "ziel_sitzung": ziel_sid,
            "anfrage_ausschnitt": ausschnitt, "rang": rang, "bestanden": rang == 1}


def messe(kms, faelle: list[dict]) -> dict:
    zeilen = []
    for f in faelle:
        ziel = set(f["answer_session_ids"])
        rl = rangliste(kms, f["question"], scope=f["question_id"], nachschlagewerk=True)
        mrr_i, rang = reziproker_rang(rl, ziel)
        zeilen.append({
            "frage_id": f["question_id"], "typ": f["question_type"],
            "n_ziel_sitzungen": len(ziel), "n_heuhaufen": len(f["haystack_session_ids"]),
            "rang_erste_zielsitzung": rang, "reziproker_rang": mrr_i,
            "recall_any_at_5": recall_any_at_k(rl, ziel, 5),
            "recall_any_at_10": recall_any_at_k(rl, ziel, 10),
        })
    n = len(zeilen)
    return {
        "n": n,
        "r_at_5": sum(z["recall_any_at_5"] for z in zeilen) / n,
        "r_at_10": sum(z["recall_any_at_10"] for z in zeilen) / n,
        "mrr": sum(z["reziproker_rang"] for z in zeilen) / n,
        "median_rang_gefunden": (
            int(st.median([z["rang_erste_zielsitzung"] for z in zeilen if z["rang_erste_zielsitzung"]]))
            if any(z["rang_erste_zielsitzung"] for z in zeilen) else None
        ),
        "totalausfaelle": sum(1 for z in zeilen if z["rang_erste_zielsitzung"] is None),
        "je_frage": zeilen,
    }


def gattungsfilter_kontrolle(kms, faelle: list[dict]) -> dict:
    """Eine einzelne Anfrage OHNE nachschlagewerk=True -- misst, ob die
    Vorgabe (gattung-Filter an) den gesamten Korpus unterdrueckt (Auftrag
    Punkt 4). Zaehlt Treffer, nicht nur True/False."""
    f = faelle[0]
    rl_default = rangliste(kms, f["question"], scope=f["question_id"], nachschlagewerk=False)
    rl_offen = rangliste(kms, f["question"], scope=f["question_id"], nachschlagewerk=True)
    return {
        "beispiel_frage": f["question_id"],
        "treffer_ohne_nachschlagewerk_true": len(rl_default),
        "treffer_mit_nachschlagewerk_true": len(rl_offen),
        "schliesst_alles_aus": len(rl_default) == 0 and len(rl_offen) > 0,
    }


def selftest() -> None:
    assert reziproker_rang(["a", "b", "c"], {"c"}) == (1 / 3, 3)
    assert reziproker_rang(["a", "b"], {"x"}) == (0.0, None)
    assert recall_any_at_k(["a", "b", "c"], {"c"}, 2) == 0.0
    assert recall_any_at_k(["a", "b", "c"], {"c"}, 3) == 1.0
    text = "Wort1 Wort2 Wort3"
    sitzung = [{"role": "user", "content": "Wort1 Wort2"}, {"role": "assistant", "content": "IGNORIERT"},
               {"role": "user", "content": "Wort3"}]
    assert sitzungstext(sitzung) == "Wort1 Wort2 Wort3"
    print("selftest: ok", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--n", type=int, default=25, help="Stichprobengroesse (von 500)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--db", type=str, default=str(STANDARD_DB))
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    # BEFUND (dieser Lauf, 2026-08-18): knowledge_mcp_server.py liest NUR
    # BEGOD_KNOWLEDGE_DB fuer DB_PATH (Zeile ~159, Modulscope, kein Aufruf von
    # haken/ort.py) -- BRAINLEHR_DB, der laut haken/ort.py "neue, massgebliche"
    # Name, wirkt HIER NICHT. Erster Versuch mit nur BRAINLEHR_DB gesetzt schrieb
    # unbemerkt 48 Testknoten in die PRODUKTIONS-brainlehr.db (seither bereinigt,
    # Sicherungskopie brainlehr.db.bak-vor-longmemeval-fehlschreibung-*). Beide
    # Namen werden deshalb gesetzt (zukunftssicher), UND eine Guard-Assertion
    # unten verhindert das Wiederauftreten strukturell, nicht nur durch die
    # richtige Env-Var.
    os.environ["BEGOD_KNOWLEDGE_DB"] = args.db
    os.environ["BRAINLEHR_DB"] = args.db
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    import knowledge_mcp_server as kms  # noqa: E402 -- Produktivweg, erst NACH Env-Setzung importiert

    produktions_db = (_w / "brainlehr.db").resolve()
    assert kms.DB_PATH.resolve() != produktions_db, (
        f"SICHERHEITSABBRUCH: kms.DB_PATH ({kms.DB_PATH}) zeigt auf die Produktions-DB "
        f"({produktions_db}) -- Env-Var griff nicht. Kein Schreibzugriff.")

    datensatz = lade_datensatz()
    rnd = random.Random(args.seed)
    stichprobe = rnd.sample(datensatz, min(args.n, len(datensatz)))

    baue_korpus(kms, stichprobe)
    pk = positivkontrolle(kms, stichprobe)
    gf = gattungsfilter_kontrolle(kms, stichprobe)
    haupt = messe(kms, stichprobe)

    ergebnis = {
        "weg": "knowledge_mcp_server.knowledge_search() -- echter Produktivweg, kein Nachbau "
               "(scope=<question_id> je Frage repliziert den LongMemEval-Heuhaufen, "
               "nachschlagewerk=True siehe gattungsfilter_default unten)",
        "kriterium": KRITERIUM,
        "grenze": GRENZE,
        "quelle_datensatz": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned "
                             "(longmemeval_s_cleaned.json), 500 Fragen gesamt",
        "stichprobe": {"n": len(stichprobe), "n_gesamt": len(datensatz), "seed": args.seed,
                        "ist_stichprobe": True},
        "festverdrahtet": {"scope": "je Frage = question_id (isoliert Heuhaufen)",
                            "max_results": MAX_RESULTS, "nachschlagewerk": True,
                            "stichtag": None, "actor/model/session": None,
                            "sprache_korpus": "englisch (LongMemEval), FTS5 deutsch gefaltet, "
                                              "Einbettung bge-m3 mehrsprachig"},
        "gattungsfilter_default": gf,
        "positivkontrolle": pk,
        "R@5": round(haupt["r_at_5"], 4),
        "R@10": round(haupt["r_at_10"], 4),
        "MRR": round(haupt["mrr"], 4),
        "median_rang_gefunden": haupt["median_rang_gefunden"],
        "totalausfaelle": haupt["totalausfaelle"],
        "je_frage": haupt["je_frage"],
    }

    if not pk["bestanden"]:
        print("BEFUND: Positivkontrolle NICHT bestanden -- Aufbau verdaechtig, nicht das System.",
              file=sys.stderr)
    if gf["schliesst_alles_aus"]:
        print("BEFUND: Gattungsfilter (Vorgabe) schliesst den gesamten Korpus aus ohne "
              "nachschlagewerk=True -- Hauptmessung nutzt bewusst diesen Parameter.",
              file=sys.stderr)

    out_path = Path(args.out) if args.out else (
        _w / "runs" / f"longmemeval_produktivweg_{__import__('datetime').datetime.now():%Y-%m-%dT%H%M%S}.json"
    )
    out_path.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_path}")
    print(f"R@5={ergebnis['R@5']} R@10={ergebnis['R@10']} MRR={ergebnis['MRR']} "
          f"(n={len(stichprobe)}, positivkontrolle_bestanden={pk['bestanden']})")


if __name__ == "__main__":
    main()
