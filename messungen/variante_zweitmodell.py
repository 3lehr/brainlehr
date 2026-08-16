#!/usr/bin/env python3
"""V3: zweites Einbettungsmodell (nomic-embed-text) gegen denselben Pruefkorpus.

Plan: docs/PLAN_EINBETTUNGSVARIANTEN_2026-08-16.md, Auftrag V3.
Kennzahl wie im Geruest (messungen/einbettungsvarianten.py): Rang des Ziels
im REINEN Bedeutungskanal -- hier mit nomic-embed-text statt bge-m3, sonst
identischer Aufbau (gleicher Korpus, gleiche Kandidatenmenge: alle Knoten+
Lehren aus der DB, keine Stichprobe -- das ist bereits dieselbe Groessenordnung
wie Stufe 0's 5964 Kandidaten, direkt vergleichbar).

Modell-Sperre (kern/embeddings.py, WHERE model = ? in den Stufe-0-Abfragen):
zwei Modelle duerfen NIE gemischt gerankt werden, ihre Vektorraeume sind nicht
kompatibel. Diese Messung rechnet deshalb ALLES -- Fragen wie Ziele -- neu in
nomic-Vektoren, ausschliesslich im Arbeitsspeicher. Nichts wird nach
knowledge_embeddings geschrieben, kern/embeddings.py und
messungen/einbettungsvarianten.py bleiben unangetastet (Tabu laut Auftrag).
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sqlite3
import sys
import time
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

import numpy as np  # noqa: E402

import embeddings  # noqa: E402
# Textbausteine 1:1 aus kern/build_embeddings.py wiederverwendet (node_text/
# lesson_text) -- Auftragsvorgabe: dieselben Bausteine wie der Produktivlauf,
# sonst misst diese Messung das Modell UND eine Textaenderung zugleich.
from build_embeddings import node_text, lesson_text  # noqa: E402

DB = _w / "brainlehr.db"
MODELL = embeddings.model_identity("nomic-embed-text")


def lade_faelle(korpus: Path) -> list[dict]:
    faelle = []
    with korpus.open(encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
            d = json.loads(zeile)
            if d.get("accepted", True) and d.get("target_kind"):
                faelle.append(d)
    return faelle


def lade_texte(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """(id, text) je Knoten (id=path) und Lehre (id=L-...) -- dieselbe
    Adressierung wie das Geruest (id_zu_pfad), damit target_id direkt passt."""
    eintraege: list[tuple[str, str]] = []
    for row in conn.execute(
            "SELECT id, path, project_id, title, summary, content FROM knowledge_nodes"):
        eintraege.append((row["path"], node_text(row)))
    for row in conn.execute(
            "SELECT id, node_path, projects, description, root_cause, prevention FROM lessons_learned"):
        eintraege.append((row["id"], lesson_text(row)))
    return eintraege


def embette_alle(texte: list[tuple[str, str]], *, timeout: float) -> tuple[list[str], np.ndarray]:
    """Sequentiell ueber embeddings.embed_text() mit Modell per Parameter --
    kern/embeddings.py bleibt unveraendert, nur der `model`-Aufrufparameter
    unterscheidet dies vom Produktivlauf mit bge-m3 (DEFAULT_EMBED_MODEL)."""
    ids: list[str] = []
    vektoren: list[list[float]] = []
    t0 = time.monotonic()
    for i, (eid, text) in enumerate(texte, start=1):
        vec = embeddings.embed_text(text, model=MODELL, timeout=timeout)
        if vec is not None:
            ids.append(eid)
            vektoren.append(vec)
        if i % 200 == 0:
            print(f"  {i}/{len(texte)} eingebettet ({time.monotonic()-t0:.0f}s)", file=sys.stderr)
    mat = np.array(vektoren, dtype=np.float32)
    mat /= np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-9)
    return ids, mat


def rang_des_ziels(frage_vec, ziel: str, ids: list[str], mat: np.ndarray) -> int | None:
    """1-basierter Rang des Ziels im Bedeutungskanal, None wenn nicht dabei
    (Frage nicht einbettbar oder leere Kandidatenmenge)."""
    if frage_vec is None or not ids:
        return None
    q = np.array(frage_vec, dtype=np.float32)
    q /= max(float(np.linalg.norm(q)), 1e-9)
    ordnung = np.argsort(-(mat @ q))
    for platz, j in enumerate(ordnung, start=1):
        if ids[j] == ziel:
            return platz
    return None


def stufe_nomic(faelle: list[dict], ids: list[str], mat: np.ndarray, *, timeout: float) -> dict:
    raenge = []
    for f in faelle:
        vec = embeddings.embed_text(f["task"], model=MODELL, timeout=timeout)
        r = rang_des_ziels(vec, f["target_id"], ids, mat)
        raenge.append({"ziel": f["target_id"], "art": f["target_kind"], "rang": r})
    return {"name": "v3-nomic", "raenge": raenge}


def auswertung(stufe: dict, kandidaten: int) -> dict:
    gefunden = [e["rang"] for e in stufe["raenge"] if e["rang"] is not None]
    fehlt = sum(1 for e in stufe["raenge"] if e["rang"] is None)
    return {
        "name": stufe["name"],
        "faelle": len(stufe["raenge"]),
        "nicht_im_kanal": fehlt,
        "median_rang": int(st.median(gefunden)) if gefunden else None,
        "bester_rang": min(gefunden) if gefunden else None,
        "schlechtester_rang": max(gefunden) if gefunden else None,
        "in_top5": sum(1 for r in gefunden if r <= 5),
        "in_top50": sum(1 for r in gefunden if r <= 50),
        "kandidaten": kandidaten,
    }


def demo() -> None:
    """Netzloser Selbsttest der Rangrechnung, wie im Geruest -- der Stelle,
    an der ein Fehler das Modellergebnis verfaelschen wuerde, ohne
    aufzufallen (ohne Netz/DB lauffaehig, Abnahmepflicht)."""
    ids = ["a", "b", "c"]
    mat = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]], dtype=np.float32)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True)
    assert rang_des_ziels([1.0, 0.0], "a", ids, mat) == 1
    assert rang_des_ziels([1.0, 0.0], "c", ids, mat) == 2
    assert rang_des_ziels([1.0, 0.0], "b", ids, mat) == 3
    assert rang_des_ziels([1.0, 0.0], "fehlt", ids, mat) is None
    assert rang_des_ziels(None, "a", ids, mat) is None
    assert rang_des_ziels([1.0, 0.0], "a", [], np.zeros((0, 2), dtype=np.float32)) is None

    probe = {"name": "probe", "raenge": [{"rang": 1}, {"rang": 7}, {"rang": 200}, {"rang": None}]}
    a = auswertung(probe, kandidaten=999)
    assert a["median_rang"] == 7 and a["in_top5"] == 1 and a["in_top50"] == 2
    assert a["nicht_im_kanal"] == 1, "ein Ziel ohne Rang wird gezaehlt, nicht verschwiegen"
    print("demo: ok", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--korpus", required=True, help="Pfad zum Pruefkorpus (kein Vorgabewert)")
    p.add_argument("--out", default=None)
    p.add_argument("--timeout", type=float, default=30.0,
                    help="je Ollama-Aufruf -- Kaltstart des Modells kann >5s dauern")
    a = p.parse_args()

    faelle = lade_faelle(Path(a.korpus))
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    texte = lade_texte(conn)
    bestand = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()

    probe = embeddings.embed_text("Erreichbarkeitstest", model=MODELL, timeout=a.timeout)
    if probe is None:
        print(f"FEHLER: Modell {MODELL} nicht erreichbar (`ollama list` pruefen).", file=sys.stderr)
        sys.exit(1)

    print(f"bette {len(texte)} Kandidaten ein ({MODELL}) ...", file=sys.stderr)
    ids, mat = embette_alle(texte, timeout=a.timeout)

    stufen = [stufe_nomic(faelle, ids, mat, timeout=a.timeout)]
    ergebnis = {
        "korpus": str(Path(a.korpus).resolve()).replace(str(_w) + "/", ""),
        "faelle": len(faelle),
        "modell": MODELL,
        "knoten_bestand": bestand,
        "kandidaten_im_kanal": len(ids),
        "gemessen_wird": ("Rang des Ziels im REINEN Bedeutungskanal mit nomic-embed-text "
                           "statt bge-m3 -- Fragen wie Ziele vollstaendig in nomic-Vektoren, "
                           "nie mit bge-m3-Vektoren gemischt"),
        "grenze": [
            "misst nicht den vollen Suchweg, nur den Bedeutungskanal",
            "35 Faelle sind klein -- ein knapper Unterschied ist kein Ergebnis",
            "misst nicht die Betriebskosten eines Modellwechsels (Neuberechnung des ganzen Bestands)",
            f"Kandidatenmenge: alle {len(texte)} Knoten+Lehren aus knowledge_nodes/lessons_learned "
            "(keine Stichprobe gezogen -- entspricht bereits derselben Groessenordnung wie "
            "Stufe 0's Kandidatenkanal, direkt vergleichbar, keine Verzerrung durch Teilmenge)",
            "kein Vektor wird nach knowledge_embeddings geschrieben (reine Arbeitsspeicher-Messung)",
        ],
        "stufen": [auswertung(s, len(ids)) for s in stufen],
        "roh": {s["name"]: s["raenge"] for s in stufen},
    }
    text = json.dumps(ergebnis, indent=2, ensure_ascii=False)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
        print(f"geschrieben: {a.out}", file=sys.stderr)
    for s in ergebnis["stufen"]:
        print(f"{s['name']:16} top5={s['in_top5']}/{s['faelle']}  top50={s['in_top50']}  "
              f"median={s['median_rang']}  von {s['kandidaten']} Kandidaten")


if __name__ == "__main__":
    demo()
    main()
