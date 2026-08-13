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

try:
    import numpy as _np  # weicher Import -- Frischinstallation ohne numpy
except ImportError:  # pragma: no cover -- siehe test_finde_kandidaten_numpy_und_python_liefern_gleiches_ergebnis
    _np = None

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
    Sichtbarkeitsregel wie knowledge_search/Recall-Hook.

    Dedup je ref_id (Befund 2026-08-13, Auftrag 83): project_id ist Teil des
    Primaerschluessels, damit eine mehrwertige LEHRE eine Zeile je Bereich
    tragen kann (siehe migrationen/migrate_embeddings_projekt.py). Ein KNOTEN
    ist dagegen einwertig -- seine project_id aendert sich per Neuzuordnung,
    und der Schreiber (build_embeddings.py) legt dabei eine NEUE Zeile unter
    der neuen project_id an, statt die alte zu ersetzen (PK-Tripel aendert
    sich mit). Liegen gebliebene Zeilen alter Zuordnungen sind die Folge --
    ohne Dedup liefert dieser JOIN denselben Knotenpfad mehrfach, und
    finde_kandidaten faende darunter nur Selbstpaare mit Aehnlichkeit 1.0.
    Diese Stelle ist bewusst genauso robust wie
    knowledge_mcp_server._embedding_ranking (seen_ref_ids) -- unabhaengig
    davon, ob der Bestand selbst noch bereinigt wird."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT n.path AS path, n.title AS title, e.vector AS vector, e.ref_id AS ref_id
        FROM knowledge_embeddings e
        JOIN knowledge_nodes n ON n.id = e.ref_id
        WHERE e.kind = 'node' AND e.model = ? AND n.zurueckgezogen = 0
        ORDER BY n.path,
                 CASE WHEN e.project_id = n.project_id THEN 0 ELSE 1 END,
                 e.updated_at DESC
        """,
        (model,),
    )
    paths: list[str] = []
    titles: list[str] = []
    vektoren: list[list[float]] = []
    seen_ref_ids: set[str] = set()
    for r in cur.fetchall():
        if r["ref_id"] in seen_ref_ids:
            continue
        seen_ref_ids.add(r["ref_id"])
        paths.append(r["path"])
        titles.append(r["title"])
        vektoren.append(unpack_embedding(r["vector"]))
    return paths, titles, vektoren


def _paare_python(
    vektoren: list[list[float]], schwelle: float, k: int, nur_index: set[int] | None = None
) -> dict[frozenset, tuple[float, int, int]]:
    """Rueckfall ohne numpy: O(n^2) Doppelschleife in reinem Python. Bleibt
    erhalten, damit eine Frischinstallation ohne numpy funktionsfaehig ist
    (nur langsamer) -- siehe Modulkopf-Kommentar in kern/embeddings.py.

    nur_index (Auftrag 81): beschraenkt nur die Quellseite i -- als Nachbar j
    bleibt jeder Knoten waehlbar, auch ein bereits verbundener. So findet ein
    neuer, unverbundener Knoten seine Nachbarn im GESAMTEN Bestand, statt nur
    unter anderen unverbundenen Knoten."""
    n = len(vektoren)
    paare: dict[frozenset, tuple[float, int, int]] = {}
    quellen = range(n) if nur_index is None else sorted(nur_index)
    for i in quellen:
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
    return paare


def _paare_numpy(
    vektoren: list[list[float]], schwelle: float, k: int, nur_index: set[int] | None = None
) -> dict[frozenset, tuple[float, int, int]]:
    """Vektorisierter Weg: eine Matrixmultiplikation zeilenweise normierter
    Vektoren statt 2,3 Millionen einzelner Python-Kosinus-Aufrufe (2166
    Knoten, Stand 2026-08-13). Liefert -- bis auf Gleitkommarundung -- dieselben
    Paare in derselben Reihenfolge wie _paare_python, siehe
    test_finde_kandidaten_numpy_und_python_liefern_gleiches_ergebnis.

    nur_index: siehe _paare_python -- gleiche Bedeutung, gleiche Beschraenkung
    nur auf die Quellzeile i."""
    n = len(vektoren)
    arr = _np.asarray(vektoren, dtype=_np.float64)
    normen = _np.linalg.norm(arr, axis=1)
    sichere_normen = _np.where(normen == 0.0, 1.0, normen)
    normiert = arr / sichere_normen[:, None]
    sim = normiert @ normiert.T

    # Nullvektoren: cosine_similarity() liefert 0.0 (nicht NaN) bei
    # norm_a==0 oder norm_b==0 -- dieselbe Regel hier nachbilden.
    null_norm = normen == 0.0
    if null_norm.any():
        sim[null_norm, :] = 0.0
        sim[:, null_norm] = 0.0
    _np.fill_diagonal(sim, -_np.inf)  # keine Selbstkanten, nach der Nullvektor-Regel

    paare: dict[frozenset, tuple[float, int, int]] = {}
    idx = _np.arange(n)
    quellen = range(n) if nur_index is None else sorted(nur_index)
    for i in quellen:
        row = sim[i]
        # sortiert nach Aehnlichkeit absteigend, bei Gleichstand nach
        # aufsteigendem Index -- entspricht dem stabilen sort() im
        # Python-Rueckfall ueber eine nach j aufsteigend aufgebaute Liste.
        reihenfolge = idx[_np.lexsort((idx, -row))]
        gefunden = 0
        for j in reihenfolge:
            j = int(j)
            s = float(row[j])
            if s < schwelle:
                break
            key = frozenset((i, j))
            bisher = paare.get(key)
            if bisher is None or s > bisher[0]:
                paare[key] = (s, i, j)
            gefunden += 1
            if gefunden >= k:
                break
    return paare


def finde_kandidaten(
    paths: list[str],
    titles: list[str],
    vektoren: list[list[float]],
    *,
    schwelle: float = SIMILARITY_THRESHOLD,
    k: int = K_NEIGHBORS,
    nur_index: set[int] | None = None,
) -> list[Kandidat]:
    """Fuer jeden Knoten die besten bis zu k Nachbarn mit sim >= schwelle,
    danach als ungerichtete Paare dedupliziert. Keine Selbstkanten. Nutzt
    numpy (Matrixmultiplikation), wenn vorhanden -- sonst den reinen
    Python-Rueckfall (siehe _paare_python).

    nur_index (Auftrag 81, inkrementeller Lauf): beschraenkt, welche Knoten
    als QUELLE i durchsucht werden -- z.B. nur Knoten ohne jede Kante. Als
    Nachbar bleibt jeder Knoten waehlbar."""
    n = len(paths)
    if n < 2:
        return []

    if _np is not None:
        paare = _paare_numpy(vektoren, schwelle, k, nur_index)
    else:
        paare = _paare_python(vektoren, schwelle, k, nur_index)

    kandidaten = []
    for sim, i, j in paare.values():
        a, b = sorted((i, j), key=lambda x: paths[x])
        kandidaten.append(Kandidat(paths[a], titles[a], paths[b], titles[b], sim))
    kandidaten.sort(key=lambda kd: -kd.similarity)
    return kandidaten


def knoten_ohne_kanten(conn: sqlite3.Connection, paths: list[str]) -> set[str]:
    """Pfade aus `paths`, die in KEINER Zeile von knowledge_relations als
    Quelle oder Ziel vorkommen -- unabhaengig vom relation_type (eine von
    Hand gezogene Kante zaehlt genauso wie eine hieraus entstandene). Fuer
    den inkrementellen Lauf (Auftrag 81): nur diese Knoten muessen erneut
    nach Nachbarn durchsucht werden, der Rest hat schon mindestens eine
    Kante und wird nicht durch einen vollen Neulauf ersetzt."""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT source_path FROM knowledge_relations")
    verbunden = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT DISTINCT target_path FROM knowledge_relations")
    verbunden.update(r[0] for r in cur.fetchall())
    return {p for p in paths if p not in verbunden}


def automatischer_lauf(db_path: Path | None = None) -> str | None:
    """Einstiegspunkt fuer einen Haken (Auftrag 81): inkrementeller Lauf nur
    ueber Knoten ohne jede Kante, sofort geschrieben (kein Trockenlauf --
    ein Haken kann niemanden fragen, ob er --apply meint). Liefert None,
    wenn nichts zu tun war oder nichts Neues entstand -- ein Haken, der bei
    jedem Stop eine Zeile ausgibt, wird nach drei Tagen ignoriert."""
    conn = connect_db(db_path or DB_PATH)
    try:
        paths, titles, vektoren = lade_knoten_vektoren(conn)
        unverbunden = knoten_ohne_kanten(conn, paths)
        if not unverbunden:
            return None
        nur_index = {i for i, p in enumerate(paths) if p in unverbunden}
        kandidaten = finde_kandidaten(paths, titles, vektoren, nur_index=nur_index)
        if not kandidaten:
            return None
        created, skipped = schreibe_kanten(conn, kandidaten)
        if created == 0:
            return None
        return (
            f"Kanten nachgezogen: {created} neu, {skipped} bereits vorhanden "
            f"({len(unverbunden)} Knoten ohne Kante geprueft)."
        )
    finally:
        conn.close()


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
    parser.add_argument(
        "--nur-ohne-kanten", action="store_true",
        help="Inkrementell: nur Knoten ohne jede Kante als Quelle durchsuchen (Auftrag 81)",
    )
    args = parser.parse_args()

    conn = connect_db(args.db)
    paths, titles, vektoren = lade_knoten_vektoren(conn)
    nur_index = None
    if args.nur_ohne_kanten:
        unverbunden = knoten_ohne_kanten(conn, paths)
        nur_index = {i for i, p in enumerate(paths) if p in unverbunden}
    kandidaten = finde_kandidaten(paths, titles, vektoren, schwelle=args.schwelle, k=args.k, nur_index=nur_index)

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
