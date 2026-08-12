"""A/B-Vergleich: volle Abrufkette (A) gegen reinen Top-3-Kosinus (B),
gegen denselben Pruefkorpus V3, im selben Lauf (Betreiber-Auftrag 2026-08-07).

B-Regel woertlich: NUR embed_text() der Anfrage + cosine_similarity() gegen
knowledge_embeddings, oben drei, fertig. Kein Rauschteppich (_radar_select),
kein Vertrauenswert (_apply_trust_score), kein Ensemble/RRF (_combine_channels),
keine Ast-Entdopplung, kein MIN_HITS. Der einzige Nicht-Relevanz-Filter, der
bleibt: zurueckgezogen=0 -- das ist Datenhygiene (geloeschter Knoten bleibt
tot), keine Rang-/Schwellen-Mechanik.

Frische pruefkorpus_v3-Knoten haben KEINE gespeicherten Vektoren (insert_nodes()
ruft embed_text() nicht auf -- s. pruefkorpus_v3.py) -- ohne eigene Nachruestung
koennte B sie nie finden, das waere ein Datenluecken-Artefakt, kein Mechanik-
Befund. Darum: nach dem Einspielen einmalig fuer alle frischen Knoten
embed_text() + INSERT INTO knowledge_embeddings, exakt im selben Textformat
wie build_embeddings.py (path\\ntitle\\nsummary\\ncontent). delete_nodes()
(pruefkorpus_v3.py) raeumt sie per ref_id-Match automatisch mit weg.
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

import json
import math
import sqlite3
import sys
import time
from pathlib import Path

SHARED_KNOWLEDGE = _w
sys.path.insert(0, str(SHARED_KNOWLEDGE.parent / "scripts"))
sys.path.insert(0, str(SHARED_KNOWLEDGE / "kern"))
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_recall_hook as hook  # noqa: E402
import embeddings  # noqa: E402
import pruefkorpus_v3 as pk3  # noqa: E402
import speicher  # noqa: E402 -- nur verbinde_bestand() gegen stilles Anlegen

OUT_PATH = SHARED_KNOWLEDGE / "runs" / "ab_vergleich_abruf_2026-08-07.json"
KATEGORIEN = ["einzelwert", "kombiniert", "kombiniert3", "kombiniert_ablenker",
              "aehnlich", "eigenschaft", "gleiche_einheit", "veraltet", "eichfall"]


def wilson(k: int, n: int, z: float = 1.96):
    """95%-Spanne, Wilson-Verfahren. n<5 -> None (Auflage 3: kein Prozentwert
    bei kleinen Stichproben)."""
    if n < 5:
        return None
    phat = k / n
    denom = 1 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return (max(0.0, (center - margin) / denom), min(1.0, (center + margin) / denom))


def _embed_fresh_nodes(conn: sqlite3.Connection) -> int:
    """Vektoren fuer alle frisch eingespielten pruefkorpus_v3-Knoten, exakt
    im Textformat von build_embeddings.py. Rueckgabe: Anzahl geschriebener
    Vektoren (fehlende best-effort uebersprungen wie im Original)."""
    rows = conn.execute(
        "SELECT id, path, project_id, title, summary, content FROM knowledge_nodes "
        "WHERE project_id=?", (pk3.PROJECT_ID,)).fetchall()
    n = 0
    for r in rows:
        text = f"{r['path']}\n{r['title']}\n{r['summary']}\n{r['content'] or ''}"
        vec = embeddings.embed_text(text, timeout=30.0)
        if vec is None:
            continue
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_embeddings "
            "(kind, ref_id, project_id, model, dim, vector, updated_at) "
            "VALUES ('node', ?, ?, ?, ?, ?, ?)",
            (r["id"], r["project_id"], embeddings.DEFAULT_EMBED_MODEL, len(vec),
             embeddings.pack_embedding(vec), _now()))
        n += 1
    conn.commit()
    return n


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def retrieve_b(conn: sqlite3.Connection, task: str) -> tuple[str | None, list]:
    """Durchlauf B: embed_text(Anfrage) + cosine_similarity je Knoten, oben
    drei absteigend. Keine Schwelle, kein MIN_HITS, kein Ensemble."""
    query_vec = embeddings.embed_text(task, timeout=30.0)
    if query_vec is None:
        return None, []
    rows = conn.execute(
        "SELECT e.ref_id, e.vector, n.path, n.title, n.summary FROM knowledge_embeddings e "
        "JOIN knowledge_nodes n ON n.id = e.ref_id "
        "WHERE e.kind='node' AND n.zurueckgezogen=0").fetchall()
    scored = []
    for r in rows:
        sim = embeddings.cosine_similarity(query_vec, embeddings.unpack_embedding(r["vector"]))
        scored.append((sim, r))
    scored.sort(key=lambda t: t[0], reverse=True)
    top3 = [dict(r) | {"id": r["ref_id"]} for _sim, r in scored[:3]]
    if not top3:
        return None, []
    context = "\n".join(f"- {n['title']}: {n['summary']}" for n in top3)
    return context, top3


def run_case(conn: sqlite3.Connection, case: dict, model: str) -> dict:
    ohne = pk3.answer(case["task"], None, model=model)
    ctx_a, nodes_a = pk3.retrieve(case["task"])
    mit_a = pk3.answer(case["task"], ctx_a, model=model)
    ctx_b, nodes_b = retrieve_b(conn, case["task"])
    mit_b = pk3.answer(case["task"], ctx_b, model=model)
    row = {
        "kennung": case["kennung"], "kategorie": case["kategorie"],
        "task": case["task"], "erwartete_zahl": case["erwartete_zahl"],
        "ohne_abruf": ohne, "ohne_bestanden": pk3.check(ohne, case["erwartete_zahl"]),
        "A": {
            "mit_abruf": mit_a, "mit_bestanden": pk3.check(mit_a, case["erwartete_zahl"]),
            "ziel_gefunden": pk3.target_hit(case, nodes_a),
            "abgerufene_pfade": [n["path"] for n in nodes_a],
            "einordnung": pk3.classify(case, mit_a, nodes_a),
        },
        "B": {
            "mit_abruf": mit_b, "mit_bestanden": pk3.check(mit_b, case["erwartete_zahl"]),
            "ziel_gefunden": pk3.target_hit(case, nodes_b),
            "abgerufene_pfade": [n["path"] for n in nodes_b],
            "einordnung": pk3.classify(case, mit_b, nodes_b),
        },
    }
    return row


def summarize(rows: list[dict]) -> dict:
    solvable = [r for r in rows if r["erwartete_zahl"] is not None]
    eichfaelle = [r for r in rows if r["erwartete_zahl"] is None]
    out = {}
    for key in ("A", "B"):
        ziel = sum(1 for r in solvable if r[key]["ziel_gefunden"])
        gel = sum(1 for r in solvable if r[key]["mit_bestanden"])
        # Eichfall "korrekt stumm": kein Zieltreffer UND keine Zahl geraten,
        # die zufaellig eine erwartete_zahl eines anderen Falls waere -- hier
        # schlicht: Antwort enthaelt nicht "weiss"/keine Ziffernkette, die wie
        # ein Ergebnis wirkt. Praxisnah: eichfall gilt als korrekt, wenn KEIN
        # Zieltreffer (ziel_pfade ist ohnehin leer) und die Klassifikation
        # 'eichfall' meldet (raw enthaelt kein Fantasiewort-Ergebnis).
        eich_still = sum(1 for r in eichfaelle if r[key]["einordnung"] == "eichfall"
                          and not r[key]["ziel_gefunden"])
        kat = {}
        for k in KATEGORIEN:
            kat_rows = [r for r in rows if r["kategorie"] == k]
            if not kat_rows:
                continue
            if k == "eichfall":
                n = len(kat_rows)
                treffer = sum(1 for r in kat_rows if r[key]["einordnung"] == "eichfall")
            else:
                n = len(kat_rows)
                treffer = sum(1 for r in kat_rows if r[key]["mit_bestanden"])
            kat[k] = {"treffer": treffer, "n": n, "ci95": wilson(treffer, n)}
        out[key] = {
            "ziel_gefunden": {"treffer": ziel, "n": len(solvable), "ci95": wilson(ziel, len(solvable))},
            "geloest": {"treffer": gel, "n": len(solvable), "ci95": wilson(gel, len(solvable))},
            "eichfall_korrekt_stumm": {"treffer": eich_still, "n": len(eichfaelle)},
            "je_kategorie": kat,
        }
    return out


def unterschiede(rows: list[dict]) -> list[dict]:
    diffs = []
    for r in rows:
        pa, pb = set(r["A"]["abgerufene_pfade"]), set(r["B"]["abgerufene_pfade"])
        if pa != pb or r["A"]["mit_bestanden"] != r["B"]["mit_bestanden"]:
            diffs.append({
                "kennung": r["kennung"], "kategorie": r["kategorie"], "task": r["task"],
                "erwartete_zahl": r["erwartete_zahl"],
                "A_pfade": sorted(pa), "A_bestanden": r["A"]["mit_bestanden"],
                "B_pfade": sorted(pb), "B_bestanden": r["B"]["mit_bestanden"],
            })
    return diffs


def main() -> None:
    model = pk3.CAL_MODEL
    # verbinde_bestand statt sqlite3.connect: misst gegen einen bestehenden
    # Bestand, legt keinen an -- siehe kern/speicher.py::verbinde_bestand.
    conn = speicher.verbinde_bestand(hook.DB)
    conn.row_factory = sqlite3.Row

    vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    pk3.insert_nodes(conn)
    n_emb = _embed_fresh_nodes(conn)
    print(f"Bestand vorher: {vorher}. {len(pk3.GEGENSTAENDE) + 2 * len(pk3.VERALTET)} Knoten "
          f"eingespielt, {n_emb} davon eigens embeddet (fuer B noetig).", flush=True)

    t0 = time.monotonic()
    rows = []
    for case in pk3.CASES:
        row = run_case(conn, case, model)
        rows.append(row)
        print(f"  {row['kennung']:8s} {row['kategorie']:22s} erwartet={row['erwartete_zahl']}  "
              f"A: {row['A']['einordnung']:24s} pfade={row['A']['abgerufene_pfade']}  "
              f"B: {row['B']['einordnung']:24s} pfade={row['B']['abgerufene_pfade']}", flush=True)

    n_vor_delete = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    n_entfernt = pk3.delete_nodes(conn)
    nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    dt = time.monotonic() - t0
    print(f"\nLoeschbefehl: vorher={n_vor_delete} entfernt={n_entfernt} nachher={nachher} "
          f"(Original {vorher} -> {'unveraendert' if nachher == vorher else 'ABWEICHUNG!'}), "
          f"Laufzeit {dt:.0f}s", flush=True)

    summary = summarize(rows)
    diffs = unterschiede(rows)
    out = {
        "model": model, "n_cases": len(rows),
        "bestand_vorher": vorher, "bestand_nachher": nachher,
        "bestand_unveraendert": nachher == vorher,
        "zusammenfassung": summary,
        "unterschiede_A_B": diffs,
        "rows": rows,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGeschrieben: {OUT_PATH}", flush=True)
    print(f"\n{len(diffs)} Faelle mit Unterschied A/B von {len(rows)}.", flush=True)


if __name__ == "__main__":
    main()
