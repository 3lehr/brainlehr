"""S9 (docs/PLAN_DESTILLE_2026-08-09.md): Kandidaten fuer den Abruf ueber
denselben Suchpfad wie knowledge_search (knowledge_mcp_server.py), statt
ueber das MIN_HITS/ENSEMBLE_PFLICHT-Sieb von knowledge_recall_hook.query().

Gemessen 2026-08-09, gegen dieselben 35 Faelle (runs/pruefkorpus.jsonl):
  Abruf, Vorgabe (MIN_HITS=3, ein Kanal):      0/35, 2540 Zeichen/Prompt
  Abruf, beide Kanaele offen:                  4/35, 6924 Zeichen/Prompt
  knowledge_search, gezielt (max_results=5):   7/35 (Lehren 4/15, Knoten
                                                3/20), 3480 Zeichen/Anfrage

Der Unterschied ist die Bauform, nicht eine Einstellung: knowledge_search
verschmilzt Stichwort- und Bedeutungs-Rangliste per RRF (embeddings.rrf_fuse)
und wirft nichts vor der Rangfolge weg. knowledge_recall_hook.query() wirft
Kandidaten VOR jeder Rangfolge weg (MIN_HITS auf der Anfrage-Seite,
ENSEMBLE_PFLICHT). Dieses Modul liefert NUR die Kandidaten -- ueber exakt die
Bausteine, die knowledge_search selbst benutzt (_embedding_ranking,
_fuse_with_keyword_floor, embeddings.rrf_fuse). Alles danach (trust_score,
rangfolge, Scope-Tag, Explore, MAX_NODES/MAX_LESSONS-Deckel,
gattung_filter/geltend-Filter) bleibt unveraendert in
knowledge_recall_hook.query() -- die Strenge wandert an den AUSGANG, nicht
an den EINGANG (Auftrag).

knowledge_mcp_server.py wird NICHT geaendert, nur importiert."""
from __future__ import annotations

import sqlite3

import embeddings
from gattung_filter import SQL_ARBEITSBESTAND_NUR
from knowledge_mcp_server import _embedding_ranking, _or_query


def _erlaubte_ids(conn: sqlite3.Connection) -> tuple[set, set]:
    """Der Bedeutungskanal rankte bisher ueber ALLE Vektoren -- auch ueber die
    1638 Nachschlagewerk-Knoten, die der Stichwortkanal per
    SQL_ARBEITSBESTAND_NUR ausschliesst und die der Abruf am Ende ohnehin
    nicht liefert. Gemessen 2026-08-09 ueber runs/pruefkorpus.jsonl (35
    Faelle): Median-Rang des Ziels im Bedeutungskanal 96 ungefiltert, 34
    gefiltert; Ziel unter den ersten 10: 8/35 ungefiltert, 14/35 gefiltert."""
    nodes = {r["id"] for r in conn.execute(
        f"SELECT n.id FROM knowledge_nodes n WHERE n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR}")}
    lessons = {r["id"] for r in conn.execute(
        "SELECT id FROM lessons_learned WHERE status != 'resolved'")}
    return nodes, lessons


def kandidaten(conn: sqlite3.Connection, text: str, query_vec: list[float] | None,
                max_results: int) -> tuple[list[dict], list[dict]]:
    """text: der Rohtext (Prompt, oder ersatzweise die Keyword-Liste zu
    einem String verbunden), aus dem HIER -- ueber _or_query(), denselben
    Baustein wie knowledge_search() -- die FTS5-Anfrage entsteht. Bewusst
    NICHT der vorgefilterte Weg aus knowledge_recall_hook.fts_match(kws)
    (STOP-Woerter raus, <4 Zeichen raus, auf 8 Woerter gekappt) -- genau
    dieses Vorfiltern ist Teil des alten Siebs, das dieser Auftrag umgeht.
    Liefert (node_rows, lesson_rows), je in Rangfolge, ungekappt bis auf den
    gemeinsamen max_results-Deckel von _fuse_with_keyword_floor (Empfehlung:
    MAX_NODES+MAX_LESSONS des Aufrufers, s. Moduldoc zur Messung mit
    max_results=5)."""
    fts_query = _or_query(text)
    if not fts_query:
        return [], []
    node_rows = conn.execute(
        "SELECT n.id, n.path, n.title, n.summary, n.updated_at, n.gilt_ab, n.gilt_bis "
        "FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        f"WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR} "
        "ORDER BY rank",
        (fts_query,),
    ).fetchall()
    lesson_rows = conn.execute(
        "SELECT l.id, l.description, l.root_cause, l.prevention, l.severity, "
        "l.occurrences, l.type, l.last_seen, l.first_seen, l.session, l.projects "
        "FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
        "WHERE lessons_fts MATCH ? AND l.status != 'resolved' "
        "ORDER BY rank",
        (fts_query,),
    ).fetchall()
    node_by_id = {r["id"]: dict(r) for r in node_rows}
    lesson_by_id = {r["id"]: dict(r) for r in lesson_rows}

    keyword_ordered_ids = embeddings.rrf_fuse(
        list(node_by_id.keys()), list(lesson_by_id.keys()), embedding_weight=1.0)

    if query_vec is not None:
        erl_nodes, erl_lessons = _erlaubte_ids(conn)
        emb_node_ids = _embedding_ranking(conn, "node", query_vec, erl_nodes)
        emb_lesson_ids = _embedding_ranking(conn, "lesson", query_vec, erl_lessons)
    else:
        emb_node_ids, emb_lesson_ids = [], []
    embedding_ordered_ids = embeddings.rrf_fuse(emb_node_ids, emb_lesson_ids, embedding_weight=1.0)

    # Kein Stichwort-Sockel (_fuse_with_keyword_floor) mehr: er reservierte die
    # ersten max_results Plaetze fuer den Stichwortkanal -- und weil dieser bei
    # einem Prompt als Anfrage per _or_query praktisch den ganzen Bestand zieht
    # (Median 348 von 383 Knoten, 674 von 674 Lehren), war die Kandidatenliste
    # in 35 von 35 gemessenen Faellen BYTE-GLEICH mit seinen Top 5. Der
    # Bedeutungskanal wurde gerechnet (ein Ollama-Aufruf je Prompt) und hatte
    # null Einfluss. Reine RRF-Verschmelzung: 9/35 statt 7/35, bei gleicher
    # Liefermenge. Der Sockel bleibt in knowledge_search unangetastet -- dort
    # ist die Anfrage ein Suchbegriff, kein Prompt, und zieht nicht den Bestand.
    final_ids = embeddings.rrf_fuse(
        keyword_ordered_ids, embedding_ordered_ids,
        embedding_weight=embeddings.hybrid_retrieval_weight())[:max_results]

    # Embedding-Kanal kann IDs liefern, die die FTS-Abfrage oben nicht
    # gezogen hat (das ist der ganze Witz des zweiten Kanals) -- fehlende
    # Zeilen nachladen, wie knowledge_search() es fuer final_ids selbst tut
    # (dort "missing"-Block).
    missing_node_ids = [i for i in final_ids if i in emb_node_ids and i not in node_by_id]
    if missing_node_ids:
        placeholders = ",".join("?" for _ in missing_node_ids)
        for r in conn.execute(
            # Alias n: SQL_ARBEITSBESTAND_NUR spricht n.gattung an. Ohne ihn warf
            # diese Abfrage "no such column: n.gattung" -- unbemerkt, weil der
            # Stichwort-Sockel bis 2026-08-09 jeden Platz belegte und der Block
            # damit nie lief. Der Bedeutungskanal macht ihn erst scharf.
            "SELECT n.id, n.path, n.title, n.summary, n.updated_at, n.gilt_ab, n.gilt_bis "
            f"FROM knowledge_nodes n WHERE n.id IN ({placeholders}) AND n.zurueckgezogen = 0 "
            f"{SQL_ARBEITSBESTAND_NUR}",
            missing_node_ids,
        ):
            node_by_id[r["id"]] = dict(r)
    missing_lesson_ids = [i for i in final_ids if i in emb_lesson_ids and i not in lesson_by_id]
    if missing_lesson_ids:
        placeholders = ",".join("?" for _ in missing_lesson_ids)
        for r in conn.execute(
            "SELECT id, description, root_cause, prevention, severity, occurrences, "
            "type, last_seen, first_seen, session, projects FROM lessons_learned "
            f"WHERE id IN ({placeholders}) AND status != 'resolved'",
            missing_lesson_ids,
        ):
            lesson_by_id[r["id"]] = dict(r)

    return (
        [node_by_id[i] for i in final_ids if i in node_by_id],
        [lesson_by_id[i] for i in final_ids if i in lesson_by_id],
    )


def _selftest() -> None:
    """Netzloser Selbsttest gegen die echte (nur gelesene) DB -- kein Ollama
    noetig, query_vec=None testet den reinen Stichwort-Pfad."""
    import ort  # noqa: E402 -- liegt in haken/, s. Modulkopf des Hooks
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    import speicher  # noqa: E402 -- eine Tuer zur Datenbank statt einer eigenen
    with speicher.lesen() as conn:
        nodes, lessons = kandidaten(conn, "", None, 5)
    assert nodes == [] and lessons == [], "leerer Text muss leere Kandidaten liefern"
    nodes, lessons = kandidaten(conn, "qwfpqwfpblorx zvxjkq wibbnfrx", None, 5)
    assert nodes == [] and lessons == [], "Nonsens-Text darf keine Kandidaten erfinden"

    # Negativfall zum Gattungsfilter im Bedeutungskanal: als Anfragevektor
    # dient der Vektor eines Nachschlagewerk-Knotens selbst. Ungefiltert steht
    # er damit auf Rang 1 seines eigenen Kanals -- er darf trotzdem nirgends
    # auftauchen. Gegenprobe in die andere Richtung gleich darunter: derselbe
    # Aufruf mit allowed_ids=None kennt ihn sehr wohl (sonst pruefte der Test
    # nur, dass irgendetwas leer ist).
    zeile = conn.execute(
        "SELECT e.ref_id, e.vector FROM knowledge_embeddings e JOIN knowledge_nodes n "
        "ON n.id = e.ref_id WHERE e.kind = 'node' AND n.gattung = 'nachschlagewerk' "
        "AND e.model = ? LIMIT 1", (embeddings.DEFAULT_EMBED_MODEL,)).fetchone()
    if zeile is not None:  # DB ohne Nachschlagewerk-Bestand: nichts zu pruefen
        vec = embeddings.unpack_embedding(zeile["vector"])
        erl_nodes, _ = _erlaubte_ids(conn)
        assert zeile["ref_id"] not in erl_nodes, "Fixtur falsch: Knoten ist kein Nachschlagewerk"
        ohne_filter = _embedding_ranking(conn, "node", vec, None)
        assert ohne_filter and ohne_filter[0] == zeile["ref_id"], (
            "Gegenprobe: ungefiltert muesste der Knoten sein eigener Rang 1 sein")
        mit_filter = _embedding_ranking(conn, "node", vec, erl_nodes)
        assert zeile["ref_id"] not in mit_filter, "Nachschlagewerk im Bedeutungskanal durchgekommen"
        nodes, lessons = kandidaten(conn, "Nachschlagewerk", vec, 5)
        assert zeile["ref_id"] not in [n["id"] for n in nodes], (
            "Nachschlagewerk in der Kandidatenliste gelandet")
    conn.close()
    print("suchpfad_abruf._selftest ok")


if __name__ == "__main__":
    _selftest()
