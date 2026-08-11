#!/usr/bin/env python3
"""Kanten aus Bedeutung: knowledge_relations aus vorhandenen Embeddings ziehen.

Nutzt die in knowledge_embeddings VORHANDENEN Vektoren (kind='node',
Modell bge-m3) -- erzeugt keine neuen Embeddings, ruft kein Ollama. Fuer
jeden Knoten werden bis zu K_NEIGHBORS aehnlichste andere Knoten mit
Kosinus-Aehnlichkeit >= SIMILARITY_THRESHOLD als Kante eingetragen, je
Knotenpaar hoechstens eine Kante (ungerichtet dedupliziert -- kommt ein Paar
aus der Top-k-Liste beider beteiligter Knoten, entsteht trotzdem nur eine
Zeile).

relation_type = 'aehnlich_bedeutung' -- eigene Herkunftskennung, klar
unterschieden von 'analogous_to'/'constrains' (von Hand gezogen, siehe
knowledge_relation_add) und 'lesson_mentions_file' (aus Lehrentext
extrahiert, siehe kanten_aus_lehren.py): diese Kanten entstehen
AUSSCHLIESSLICH aus Vektor-Aehnlichkeit.

SCHWELLE -- gemessen, nicht geraten (Messung 2026-08-08, echter Bestand
/Volumes/daten/Begod2026/brainlehr/brainlehr.db, 2013 Knoten mit
bge-m3-Embedding, 2 025 078 Paare):

Das Histogramm der Kosinus-Aehnlichkeit faellt von 0.50 bis 1.00 in
0.01-Schritten LUECKENLOS MONOTON (keine Senke, kein zweiter Gipfel):
p50=0.494 p90=0.587 p95=0.611 p99=0.659 p99.9=0.729 p99.99=0.840 max=0.9997.
Nach der Vorgabe fuer dieses Modul ist eine Verteilung OHNE Luecke ein
Zeichen, dass die Metrik nicht sauber trennt -- das wird hier ausdruecklich
gemeldet, nicht verschwiegen: es gibt KEINEN Punkt, an dem "verwandt" und
"unverwandt" als zwei getrennte Haeufungen sichtbar wuerden.

Stichproben auf beiden Seiten zeigen aber ein reales, nur GRADUELLES (statt
zweigeteiltes) Signal: bei 0.50-0.60 sind Zufallspaare thematisch nur lose
verwandt ("Suspended Load Operations" <-> "Ultrasound Testing", 0.55; beide
nur "irgendein NASA-Verfahren"). Ab 0.65-0.70 werden Paare fachlich konkret
("Electrical Grounding Practices for Aerospace Hardware" <-> "Electrostatic
Discharge Control in GSE", 0.696; "In-Flight Spacecraft Fault Recovery" <->
"Space Shuttle Program - Process Control Focus Group", 0.675). Ab 0.70 sind
Paare durchgehend eng verwandt bis zu Beinahe-Duplikaten (RSRM-Teildokumente,
0.85-0.999). SIMILARITY_THRESHOLD=0.65 (~P99 der Verteilung) ist daher ein
PERZENTIL- UND STICHPROBEN-belegter Wert, kein luecken-belegter -- diese
Abweichung von der Vorgabe wird hier bewusst offen vermerkt statt als
Luecke ausgegeben, die es nicht gibt.
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
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(_w))
from haken.ort import DB as DB_PATH  # noqa: E402
from embeddings import cosine_similarity, unpack_embedding  # noqa: E402

RELATION_TYPE = "aehnlich_bedeutung"
SIMILARITY_THRESHOLD = 0.65
K_NEIGHBORS = 5
EMBED_MODEL = "bge-m3"


@dataclass
class Kandidat:
    a_path: str
    a_title: str
    b_path: str
    b_title: str
    similarity: float


def connect_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def lade_knoten_vektoren(conn: sqlite3.Connection, *, model: str = EMBED_MODEL):
    """Liest vorhandene Knoten-Embeddings (kind='node') samt path/title.
    Zurueckgezogene Knoten (zurueckgezogen=1) werden ausgeschlossen -- gleiche
    Sichtbarkeitsregel wie knowledge_search/Recall-Hook."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT n.path AS path, n.title AS title, e.vector AS vector
        FROM knowledge_embeddings e
        JOIN knowledge_nodes n ON n.id = e.ref_id
        WHERE e.kind = 'node' AND e.model = ? AND n.zurueckgezogen = 0
        ORDER BY n.path
        """,
        (model,),
    )
    rows = cur.fetchall()
    paths = [r["path"] for r in rows]
    titles = [r["title"] for r in rows]
    vektoren = [unpack_embedding(r["vector"]) for r in rows]
    return paths, titles, vektoren


def finde_kandidaten(
    paths: list[str],
    titles: list[str],
    vektoren: list[list[float]],
    *,
    schwelle: float = SIMILARITY_THRESHOLD,
    k: int = K_NEIGHBORS,
) -> list[Kandidat]:
    """Fuer jeden Knoten die besten bis zu k Nachbarn mit sim >= schwelle,
    danach als ungerichtete Paare dedupliziert. Keine Selbstkanten (i==j wird
    uebersprungen)."""
    n = len(paths)
    paare: dict[frozenset, tuple[float, int, int]] = {}

    for i in range(n):
        nachbarn = []
        vi = vektoren[i]
        for j in range(n):
            if i == j:
                continue
            sim = cosine_similarity(vi, vektoren[j])
            if sim >= schwelle:
                nachbarn.append((sim, j))
        nachbarn.sort(key=lambda x: x[0], reverse=True)
        for sim, j in nachbarn[:k]:
            key = frozenset((i, j))
            bisher = paare.get(key)
            if bisher is None or sim > bisher[0]:
                paare[key] = (sim, i, j)

    kandidaten = []
    for sim, i, j in paare.values():
        a, b = sorted((i, j), key=lambda x: paths[x])
        kandidaten.append(Kandidat(paths[a], titles[a], paths[b], titles[b], sim))
    kandidaten.sort(key=lambda kd: -kd.similarity)
    return kandidaten


def edge_exists(conn: sqlite3.Connection, a_path: str, b_path: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM knowledge_relations
        WHERE source_path = ? AND target_path = ? AND relation_type = ?
        LIMIT 1
        """,
        (a_path, b_path, RELATION_TYPE),
    )
    return cur.fetchone() is not None


def schreibe_kanten(conn: sqlite3.Connection, kandidaten: list[Kandidat]) -> tuple[int, int]:
    """Legt Kanten fuer noch nicht vorhandene Paare an. NIE ein Ueberschreiben
    bestehender Kanten anderer Herkunft: es wird ausschliesslich per
    (source_path, target_path, RELATION_TYPE) geprueft/eingefuegt, andere
    relation_type-Zeilen bleiben unberuehrt. Idempotent: zweiter Lauf mit
    denselben Kandidaten legt nichts Neues an."""
    created = 0
    skipped = 0
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()

    for kd in kandidaten:
        if edge_exists(conn, kd.a_path, kd.b_path):
            skipped += 1
            continue
        cur.execute(
            """
            INSERT INTO knowledge_relations
            (id, source_path, target_path, relation_type, confidence, weight,
             evidence, source, creator, model, session, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                kd.a_path,
                kd.b_path,
                RELATION_TYPE,
                round(kd.similarity, 4),
                1.0,
                f"Kosinus-Aehnlichkeit {kd.similarity:.4f} (Modell {EMBED_MODEL})",
                "kanten_aus_bedeutung.py",
                "mechanik",
                EMBED_MODEL,
                None,
                now,
                now,
            ),
        )
        created += 1

    conn.commit()
    return created, skipped


def ist_nasa(path: str) -> bool:
    return path.startswith("/nasa-llis")


def dry_run(kandidaten: list[Kandidat], node_count: int, *, zeige: int = 10) -> None:
    nasa_treffer = sum(1 for kd in kandidaten if ist_nasa(kd.a_path) or ist_nasa(kd.b_path))
    print(f"Trockenlauf: {node_count} Knoten mit Embedding betrachtet")
    print(f"  Kandidatenkanten: {len(kandidaten)}")
    print(f"  davon beruehren einen /nasa-llis-Knoten: {nasa_treffer}")
    print()
    print(f"Beispielpaare (top {min(zeige, len(kandidaten))} nach Aehnlichkeit):")
    for kd in kandidaten[:zeige]:
        print(f"  {kd.similarity:.4f}  {kd.a_title!r}  <->  {kd.b_title!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Kanten wirklich schreiben (sonst Trockenlauf)")
    parser.add_argument("--schwelle", type=float, default=SIMILARITY_THRESHOLD)
    parser.add_argument("--k", type=int, default=K_NEIGHBORS)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()

    conn = connect_db(args.db)
    paths, titles, vektoren = lade_knoten_vektoren(conn)
    kandidaten = finde_kandidaten(paths, titles, vektoren, schwelle=args.schwelle, k=args.k)

    if not args.apply:
        dry_run(kandidaten, len(paths))
        print(f"\nZum Schreiben: python {sys.argv[0]} --apply")
        conn.close()
        return

    created, skipped = schreibe_kanten(conn, kandidaten)
    print(f"Erzeugt: {created} neue Kanten, uebersprungen (bereits vorhanden): {skipped}")
    conn.close()


if __name__ == "__main__":
    main()
