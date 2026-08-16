#!/usr/bin/env python3
"""Drei Richtungen gegen den Abstraktionssprung, vergleichbar gemessen.

Plan: docs/PLAN_EINBETTUNGSVARIANTEN_2026-08-16.md
Befund, der dazu fuehrte: Knoten 291c2e3f -- von 35 Faellen des eigenen
Pruefkorpus liegen 23 ausserhalb der Top-50, und diese 23 stehen auch im
REINEN Bedeutungskanal auf Median-Rang 134 von 5963. Fusion, Sockel,
Stichwortkanal und Schwellwert scheiden damit als Ursache aus.

DIE KENNZAHL IST DER RANG IM BEDEUTUNGSKANAL, nicht die Trefferquote des
vollen Suchwegs. Grund: der volle Weg mischt Stichwortkanal und Fusion hinein
und macht die Varianten ununterscheidbar -- eine Verbesserung der Einbettung
verschwaende dort hinter Rauschen, das mit ihr nichts zu tun hat.

WAS DIESES WERKZEUG NICHT ANFASST: den Produktivbestand. Alle Varianten
rechnen mit zusaetzlichen Vektoren im Arbeitsspeicher gegen dieselbe
Kandidatenmenge. Auf knowledge_embeddings wird nichts geschrieben, bevor eine
Richtung gewaehlt ist.

STUFE 0 IST PFLICHT UND LAEUFT IMMER MIT. Sie ist die Ausgangslage, und sie
wird nicht aus der Erinnerung an eine fruehere Messung genommen -- ein
Messwerkzeug, das die bekannte Ausgangslage nicht reproduziert, misst etwas
anderes als gedacht (Plan §5, bindend).
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

import numpy as np  # noqa: E402

import embeddings  # noqa: E402

DB = _w / "brainlehr.db"


def lade_faelle(korpus: Path) -> list[dict]:
    """Der Korpus wird VERLANGT, nicht per Vorgabewert gewaehlt.

    L-3bf6c7: eine Vorher- und eine Nachher-Messung liefen ueber verschiedene
    Korpora, weil ein Vorgabewert auf eine andere Datei zeigte. Beide Zahlen
    sahen plausibel aus und waren nicht vergleichbar."""
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


def lade_kandidaten(conn: sqlite3.Connection) -> tuple[list[str], np.ndarray]:
    """Alle Einbettungen als eine Matrix -- Knoten unter ihrem PATH, Lehren
    unter ihrer id, weil der Pruefkorpus beides so adressiert."""
    id_zu_pfad = {r[0]: r[1] for r in conn.execute("SELECT id, path FROM knowledge_nodes")}
    ids: list[str] = []
    vektoren: list[list[float]] = []
    gesehen = set()
    for kind in ("node", "lesson"):
        for ref, vec in conn.execute(
                "SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = ? AND model = ?",
                (kind, embeddings.DEFAULT_EMBED_MODEL)):
            if (kind, ref) in gesehen:
                continue
            gesehen.add((kind, ref))
            ids.append(id_zu_pfad.get(ref, ref) if kind == "node" else ref)
            vektoren.append(embeddings.unpack_embedding(vec))
    mat = np.array(vektoren, dtype=np.float32)
    mat /= np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-9)
    return ids, mat


def rang_des_ziels(frage_vec, ziel: str, ids: list[str], mat: np.ndarray) -> int | None:
    """1-basierter Rang des Ziels im Bedeutungskanal, None wenn nicht dabei."""
    if frage_vec is None:
        return None
    q = np.array(frage_vec, dtype=np.float32)
    q /= max(float(np.linalg.norm(q)), 1e-9)
    ordnung = np.argsort(-(mat @ q))
    for platz, j in enumerate(ordnung, start=1):
        if ids[j] == ziel:
            return platz
    return None


def stufe_null(faelle: list[dict], ids: list[str], mat: np.ndarray) -> dict:
    """Ausgangslage: die Frage so, wie sie gestellt wird, gegen den Bestand
    so, wie er eingebettet ist."""
    raenge = []
    for f in faelle:
        r = rang_des_ziels(embeddings.embed_text(f["task"]), f["target_id"], ids, mat)
        raenge.append({"ziel": f["target_id"], "art": f["target_kind"], "rang": r})
    return {"name": "0-ausgangslage", "raenge": raenge}


def auswertung(stufe: dict, kandidaten: int) -> dict:
    """Abgeleitete Groessen -- sie kosten eine Division und sind die
    haeufigste Fundstelle (L-0a05b2)."""
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
    """Netzloser Selbsttest der Rangrechnung -- der Stelle, an der ein Fehler
    alle Varianten gleichermassen verfaelschen wuerde, ohne aufzufallen."""
    ids = ["a", "b", "c"]
    mat = np.array([[1.0, 0.0], [0.0, 1.0], [0.7, 0.7]], dtype=np.float32)
    mat /= np.linalg.norm(mat, axis=1, keepdims=True)
    assert rang_des_ziels([1.0, 0.0], "a", ids, mat) == 1
    assert rang_des_ziels([1.0, 0.0], "c", ids, mat) == 2
    assert rang_des_ziels([1.0, 0.0], "b", ids, mat) == 3
    assert rang_des_ziels([1.0, 0.0], "fehlt", ids, mat) is None
    assert rang_des_ziels(None, "a", ids, mat) is None

    probe = {"name": "probe", "raenge": [{"rang": 1}, {"rang": 7}, {"rang": 200}, {"rang": None}]}
    a = auswertung(probe, kandidaten=999)
    assert a["median_rang"] == 7 and a["in_top5"] == 1 and a["in_top50"] == 2
    assert a["nicht_im_kanal"] == 1, "ein Ziel ohne Rang wird gezaehlt, nicht verschwiegen"
    print("demo: ok", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--korpus", required=True, help="Pfad zum Pruefkorpus (kein Vorgabewert)")
    p.add_argument("--out", default=None)
    a = p.parse_args()

    faelle = lade_faelle(Path(a.korpus))
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    ids, mat = lade_kandidaten(conn)
    bestand = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()

    stufen = [stufe_null(faelle, ids, mat)]
    ergebnis = {
        # Pfad relativ, wenn er unterhalb des Repos liegt, sonst absolut --
        # relative_to() wirft bei einem bereits relativen Pfad, und die
        # Korpusangabe ist Pflichtfeld jeder Vergleichsmessung.
        "korpus": str(Path(a.korpus).resolve()).replace(str(_w) + "/", ""),
        "faelle": len(faelle),
        "modell": embeddings.DEFAULT_EMBED_MODEL,
        "knoten_bestand": bestand,
        "kandidaten_im_kanal": len(ids),
        "gemessen_wird": ("Rang des Ziels im REINEN Bedeutungskanal -- nicht der volle "
                          "Suchweg, der Stichwortkanal und Fusion hineinmischt"),
        "grenze": ["misst nicht den vollen Suchweg",
                   "35 Faelle sind klein -- ein knapper Unterschied ist kein Ergebnis",
                   "misst nicht die Betriebskosten je Variante"],
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
