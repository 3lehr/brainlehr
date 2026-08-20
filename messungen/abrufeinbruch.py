"""Einmal-Arbeitsskript, Auftrag 2026-08-20: fuer jeden der 20 nicht
getroffenen Faelle in Zustand B (B_2Kanal_an_Pflicht_aus) feststellen, ob
das Ziel (a) nicht im Index, (b) verdraengt (Rang bekannt) oder (c) schlecht
bewertet ist.

Nutzt DENSELBEN Weg wie kern/messlauf_abrufguete.py: run_case()/hook.query()
ueber messlauf_abrufguete importiert, kein zweiter Messweg. Fuer (b) wird
hook.MAX_NODES/MAX_LESSONS versuchsweise angehoben (das ist die einzige
Kappung NACH der Kandidatenbewertung, s. knowledge_recall_hook.py::query()
Kommentar zu _radar_select) -- alles davor (fts-Match, Embedding-Kanal,
Radar-Selektion, Trust/Rangfolge) bleibt unveraendert am Betriebscode.

Nur lesend: hook.query() oeffnet die DB bereits mit mode=ro; die
Diagnose-Anfragen hier ebenso.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "melder", "migrationen")]

import messlauf_abrufguete as ml  # noqa: E402
import knowledge_recall_hook as hook  # noqa: E402

STATE_NAME = "B_2Kanal_an_Pflicht_aus"
PROD_MAX_NODES = hook.MAX_NODES
PROD_MAX_LESSONS = hook.MAX_LESSONS
GROSSES_LIMIT = 100_000


def _full_rank_list(c: dict) -> tuple[list, list]:
    """run_case() mit auf GROSSES_LIMIT angehobenem MAX_NODES/MAX_LESSONS --
    die einzige Aenderung ist der Slice signal[:MAX_NODES] in query(), die
    Bewertung (Radar/Trust/Rangfolge) selbst laeuft unveraendert."""
    hook.MAX_NODES, hook.MAX_LESSONS = GROSSES_LIMIT, GROSSES_LIMIT
    try:
        return ml.run_case(c)
    finally:
        hook.MAX_NODES, hook.MAX_LESSONS = PROD_MAX_NODES, PROD_MAX_LESSONS


def _rang(c: dict, nodes: list, lessons: list) -> int | None:
    if c["target_kind"] == "node":
        for i, n in enumerate(nodes):
            if n["path"] == c["target_id"]:
                return i + 1
        return None
    for i, l in enumerate(lessons):
        if l["id"] == c["target_id"]:
            return i + 1
    return None


def _bester_treffer(nodes: list, lessons: list) -> str:
    if nodes:
        return f"node:{nodes[0]['path']}"
    if lessons:
        return f"lesson:{lessons[0]['id']}"
    return "(keiner)"


def _diagnose_index(conn, c: dict, kws: list[str]) -> str:
    """(a) vs (c) fuer Faelle, die auch im vollen Rang nicht auftauchen:
    dieselben Roh-Anfragen wie der nicht-suchpfad-Zweig von query()
    (Zustand B hat KNOWLEDGE_SUCHPFAD_ABRUF=0, s. STATES)."""
    if c["target_kind"] == "node":
        row = conn.execute(
            "SELECT id, path, zurueckgezogen, gilt_ab, gilt_bis, title, summary "
            "FROM knowledge_nodes WHERE path = ?", (c["target_id"],)).fetchone()
        if row is None:
            return "NICHT IM INDEX (Knoten existiert nicht/anderer Pfad)"
        if row["zurueckgezogen"]:
            return "NICHT IM INDEX (zurueckgezogen)"
        if not hook._ist_geltend(row["gilt_ab"], row["gilt_bis"]):
            return "NICHT IM INDEX (nicht geltend: gilt_ab/gilt_bis)"
        fts_hit = conn.execute(
            "SELECT 1 FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid=f.rowid "
            "WHERE knowledge_fts MATCH ? AND n.id = ?",
            (hook.fts_match(kws), row["id"])).fetchone() is not None
        fts_hits_n = hook.hits(f"{row['path']} {row['title']} {row['summary']}", kws) if fts_hit else 0
        emb_row = conn.execute(
            "SELECT 1 FROM knowledge_embeddings WHERE kind='node' AND ref_id=?",
            (row["id"],)).fetchone()
        if not fts_hit and emb_row is None:
            return "NICHT IM INDEX (weder Volltext- noch Bedeutungs-Treffer)"
        return (f"SCHLECHT BEWERTET (fts_match={fts_hit}, hits={fts_hits_n}>=MIN_HITS={hook.MIN_HITS}"
                f"={fts_hits_n>=hook.MIN_HITS}, embedding_vorhanden={emb_row is not None})")
    else:
        row = conn.execute(
            "SELECT id, status, description, root_cause, prevention FROM lessons_learned WHERE id = ?",
            (c["target_id"],)).fetchone()
        if row is None:
            return "NICHT IM INDEX (Lehre existiert nicht)"
        if row["status"] == "resolved":
            return "NICHT IM INDEX (status=resolved)"
        fts_hit = conn.execute(
            "SELECT 1 FROM lessons_fts f JOIN lessons_learned l ON l.rowid=f.rowid "
            "WHERE lessons_fts MATCH ? AND l.id = ?",
            (hook.fts_match(kws), row["id"])).fetchone() is not None
        fts_hits_n = hook.hits(f"{row['description']} {row['root_cause']} {row['prevention']}", kws) if fts_hit else 0
        emb_row = conn.execute(
            "SELECT 1 FROM knowledge_embeddings WHERE kind='lesson' AND ref_id=?",
            (row["id"],)).fetchone()
        if not fts_hit and emb_row is None:
            return "NICHT IM INDEX (weder Volltext- noch Bedeutungs-Treffer)"
        return (f"SCHLECHT BEWERTET (fts_match={fts_hit}, hits={fts_hits_n}>=MIN_HITS={hook.MIN_HITS}"
                f"={fts_hits_n>=hook.MIN_HITS}, embedding_vorhanden={emb_row is not None})")


def main() -> None:
    cases = ml.load_cases()
    solvable = [c for c in cases if c["category"] != "negative"]
    assert len(solvable) == 35

    befunde = []
    treffer_faelle = []
    miss_faelle = []

    with ml._gegen_schnappschuss() as stand:
        with ml._with_state(ml.STATES[STATE_NAME]):
            for c in solvable:
                nodes, lessons = ml.run_case(c)
                if ml.target_hit(c, nodes, lessons):
                    treffer_faelle.append((c, nodes, lessons))
                else:
                    miss_faelle.append((c, nodes, lessons))

            assert len(treffer_faelle) == 15 and len(miss_faelle) == 20, (
                f"erwartet 15/20, gemessen {len(treffer_faelle)}/{len(miss_faelle)} -- "
                "Bestand/Code seit Auftragserteilung veraendert (Abweichung melden)")

            # Positivkontrolle: 2 Treffer per _full_rank_list gegenpruefen --
            # muessen als Rang 1..Limit erscheinen (Limit = MAX_NODES fuer
            # node-Faelle, MAX_LESSONS fuer lesson-Faelle).
            kontrolle = []
            for c, nodes, lessons in treffer_faelle[:2]:
                full_nodes, full_lessons = _full_rank_list(c)
                rang = _rang(c, full_nodes, full_lessons)
                limit = PROD_MAX_NODES if c["target_kind"] == "node" else PROD_MAX_LESSONS
                ok = rang is not None and rang <= limit
                kontrolle.append({
                    "target_kind": c["target_kind"], "target_id": c["target_id"],
                    "rang": rang, "limit": limit, "ok": ok,
                })
                assert ok, f"Positivkontrolle fehlgeschlagen fuer {c['target_id']!r}: Rang {rang}, Limit {limit}"

            conn = __import__("sqlite3").connect(f"file:{hook.DB}?mode=ro", uri=True)
            conn.row_factory = __import__("sqlite3").Row

            for c, nodes, lessons in miss_faelle:
                kws = hook.keywords(c["task"])
                bester = _bester_treffer(nodes, lessons)
                full_nodes, full_lessons = _full_rank_list(c)
                rang = _rang(c, full_nodes, full_lessons)
                limit = PROD_MAX_NODES if c["target_kind"] == "node" else PROD_MAX_LESSONS
                if rang is not None:
                    kategorie = "b"
                    detail = f"VERDRAENGT, Rang {rang} (ausgeliefertes Limit={limit})"
                else:
                    diag = _diagnose_index(conn, c, kws)
                    kategorie = "a" if diag.startswith("NICHT IM INDEX") else "c"
                    detail = diag
                befunde.append({
                    "target_kind": c["target_kind"],
                    "target_id": c["target_id"],
                    "kategorie": kategorie,
                    "rang": rang,
                    "detail": detail,
                    "bester_ausgelieferter_treffer": bester,
                })
            conn.close()

    zaehlung = {"a": 0, "b": 0, "c": 0}
    for b in befunde:
        zaehlung[b["kategorie"]] += 1
    assert sum(zaehlung.values()) == 20, zaehlung

    ergebnis = {
        "zustand": STATE_NAME,
        "produktions_limit": {"MAX_NODES": PROD_MAX_NODES, "MAX_LESSONS": PROD_MAX_LESSONS},
        "grosses_limit_fuer_volle_rangliste": GROSSES_LIMIT,
        "trefferguete_gemessen": [len(treffer_faelle), 35],
        "positivkontrolle": kontrolle,
        "befunde": befunde,
        "zaehlung": {
            "nenner": 20,
            "bezugsrahmen": "die 20 in kern/messlauf_abrufguete.py::messe() "
                            "nicht getroffenen der 35 loesbaren Faelle in Zustand "
                            f"{STATE_NAME}",
            **zaehlung,
        },
        "stand": {"kennung": stand.kennung, "aufgenommen": stand.aufgenommen},
    }
    out = _w / "runs/abrufeinbruch_2026-08-20.json"
    out.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"geschrieben: {out}")
    print(json.dumps(ergebnis["zaehlung"], indent=2, ensure_ascii=False))
    for b in befunde:
        print(f"{b['target_kind']:6} {b['target_id']:12} {b['kategorie']}  {b['detail']}  "
              f"beste_lieferung={b['bester_ausgelieferter_treffer']}")


if __name__ == "__main__":
    main()
