"""S12 (docs/PLAN_DESTILLE_2026-08-09.md): zwei billige Stufen VOR einem
Modell-Query-Rewriting -- jede EINZELN gegen runs/pruefkorpus.jsonl (35
Faelle mit target_kind) gemessen, ueber abrufguete.py/liefermenge.py
(beide unveraendert, nur importiert/aufgerufen).

Ausgangslage (S9, suchpfad_abruf.kandidaten, MEHRSTUFIGER_ABRUF=AUS):
7/35 Zieltreffer (Lehren 4/15, Knoten 3/20), 4769 Zeichen/Prompt.

GEMESSENES ERGEBNIS BEIDER STUFEN, 2026-08-09 (Rohlauf in der Auftrags-
Antwort, kein synth. Wert): KEINE der beiden Stufen verbessert die
Trefferzahl. Beide bleiben deshalb auf AUS -- das ist keine Randnotiz,
sondern das ganze Ergebnis dieses Schritts.

Stufe 1 -- Kompositum-/Stammform-Praefix (deterministisch, ohne Modell).
Umlautfaltung existiert bereits beidseitig (knowledge_mcp_server.fold_de,
ueber _or_query() auch auf der Anfrage-Seite) -- NICHT nachgebaut. Neu hier:
FTS5-Praefixsuche ("stamm"*) fuer Woerter ab STAMM_MIN_LEN Zeichen,
zusaetzlich zur bestehenden Exaktphrase (siehe _erweiterte_fts_query()).
Gemessen (Stufe 2 aus): 7/35, UNVERAENDERT gegenueber der Ausgangslage --
weder ein Fall gewonnen noch verloren. Preis: 4820 statt 4769 Zeichen/Prompt
(+1%, mehr Kandidaten treffen die FTS-Praefixterme, aber die MAX_NODES/
MAX_LESSONS-Deckelung faengt das meiste ab). Der Pruefkorpus vermeidet
woertliche Ueberschneidung ABSICHTLICH (Moduldoc pruefkorpus.jsonl) --
Kompositum-Praefixe helfen nur bei geteiltem WORTSTAMM, dieser Korpus bietet
davon fast keinen (Stichprobe: 6 von 28 Fehlschlaegen zeigen ueberhaupt
einen Stammueberlappung, und selbst dort reicht das Signal nicht, um unter
die Top-MAX_NODES/MAX_LESSONS zu kommen). Bleibt AUS.

Stufe 2 -- Kandidatenpool VOR der Deckelung vergroessern. suchpfad_abruf.
kandidaten() deckelt selbst schon INNERHALB (max_results an
_fuse_with_keyword_floor durchgereicht, vom Hook mit MAX_NODES+MAX_LESSONS=5
aufgerufen) -- trust_score/rangfolge (Knoten) bzw. hits/severity/occurrences
(Lehren) in knowledge_recall_hook.query() reranken also bislang nur 5 schon
vorab gekappte Kandidaten. Hier: derselbe suchpfad_abruf.kandidaten()
(unveraendert, nur importiert), aber mit POOL_GROESSE=20 aufgerufen --
die eigentliche Deckelung auf MAX_NODES/MAX_LESSONS bleibt unveraendert im
Hook. Gemessen (Stufe 1 aus): 6/35 -- ein NETTOVERLUST. L-606b63 (Lehre)
faellt heraus, kein Fall kommt dazu. Ursache gefunden, nicht nur vermutet:
knowledge_recall_hook.query() sortiert Lehren-Kandidaten mit
`scored.sort(key=lambda s: s[1:3], reverse=True)` -- der Schluessel ist
(severity, occurrences), der Stichworttreffer-Zaehler (s[0] = hits(...))
geht NICHT in die Sortierung ein. Ein groesserer Pool bringt also mehr
Lehren mit hoher severity/occurrences aber SCHWAECHEREM Bezug zum Prompt
in Konkurrenz um die MAX_LESSONS=2 Plaetze -- und die verdraengen L-606b63.
Das ist bestehende, hier NICHT geaenderte Hook-Logik (Datei steht unter der
Sperre dieses Auftrags) -- Stufe 2 deckt sie nur auf. Bleibt AUS.

Kombiniert (beide an): 6/35, 5552 Zeichen/Prompt -- deckt sich mit Stufe 2
allein (Stufe 1 traegt nichts bei, weder positiv noch negativ).

Kein Rot-vor-gruen-Beleg im geforderten Sinn ("eine Lehre/ein Knoten, den
der Abruf mit der neuen Stufe findet und ohne sie nie fand") ist herstellbar,
weil keine der beiden Stufen einen einzigen Fall NEU gewinnt. Was sich statt-
dessen belegen laesst und in _selftest() steht: (a) Byte-Gleichheit bei AUS,
(b) die Stufe-2-Regression an L-606b63, namentlich und reproduzierbar --
als Warnung, damit niemand POOL_GROESSE ohne diese Kenntnis hochsetzt.

Empfehlung an den Betreiber: MEHRSTUFIGER_ABRUF bleibt AUS. Weder Stufe 1
noch Stufe 2 schliessen die gemessene Luecke (20% gegen den schwachen
Referenzwert von 25-33%) -- der Rueckstand liegt, wie im Plan vermerkt,
nicht am Trichter/an der Kappstelle, sondern an der PARAPHRASIERUNG des
Pruefkorpus (bewusst ohne woertliche Ueberschneidung). Stufe 3
(Query-Rewriting mit Modell) ist die einzige im Plan vorgesehene Stufe, die
das ueberhaupt adressieren koennte -- Entscheidung des Betreibers, hier NICHT
gebaut.

Schalter, gleiche Bauform wie SUCHPFAD_ABRUF in knowledge_recall_hook.py:
Modul-Konstante MEHRSTUFIGER_ABRUF, Vorgabe AUS, Uebersteuerung per
KNOWLEDGE_MEHRSTUFIGER_ABRUF=1/0 in der Umgebung. Zusaetzlich je Stufe
einzeln uebersteuerbar (KNOWLEDGE_MEHRSTUFIG_STUFE1/2), damit sich die obigen
Zahlen jederzeit nachmessen lassen, ohne den Modulcode zu aendern.

knowledge_mcp_server.py und suchpfad_abruf.py werden NICHT geaendert, nur
importiert (gleiche Bauform wie suchpfad_abruf.py selbst)."""
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

import os
import re
import sqlite3
import sys
from pathlib import Path

# Beim Aufruf ueber den Haken setzt knowledge_recall_hook.py den Pfad; beim
# Direktaufruf (--selftest) niemand. Ohne diese zwei Zeilen ist der Selbsttest
# nur ueber den Umweg des Hakens fahrbar -- und ein Selbsttest, den man nicht
# direkt starten kann, wird nicht gefahren.
sys.path.insert(0, str(Path(__file__).resolve().parent))          # suchpfad_abruf
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # knowledge_mcp_server

from knowledge_mcp_server import fold_de
import suchpfad_abruf

# Stufe 1 -- ab dieser Wortlaenge gilt ein Wort als Kompositum-/
# Flexionskandidat (deutsche Komposita sind hier durchweg laenger als
# einfache Woerter; 8 ist die kuerzeste Laenge, bei der ein Praefix von
# STAMM_PRAEFIX_LEN noch einen eigenstaendigen Wortstamm uebrig laesst statt
# fast das ganze Wort).
STAMM_MIN_LEN = 8
STAMM_PRAEFIX_LEN = 6

# Stufe 2 -- Pool VOR der Deckelung. Kein Tuningwert, sondern grosszuegig
# bemessen (das 4-fache von MAX_NODES+MAX_LESSONS=5). Gemessen: dieser Wert
# hilft nicht (s. Moduldoc) -- bleibt als Parameter stehen, falls die
# Ursache (Lehren-Sortierschluessel ohne hits(), s. Moduldoc) irgendwann in
# knowledge_recall_hook.py behoben wird und ein neuer Messlauf noetig ist.
POOL_GROESSE = 20

_QUERY_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")


def _fts_phrase(word: str) -> str:
    return '"' + word.replace('"', '""') + '"'


def _erweiterte_fts_query(text: str) -> str:
    """Wie knowledge_mcp_server._or_query(), aber mit zusaetzlichem
    FTS5-Praefixterm ("stamm"*) fuer lange Woerter -- Stufe 1."""
    terms = []
    for w in _QUERY_WORD_RE.findall(text):
        w = fold_de(w)
        if not w:
            continue
        terms.append(_fts_phrase(w))
        if len(w) >= STAMM_MIN_LEN:
            terms.append(_fts_phrase(w[:STAMM_PRAEFIX_LEN]) + "*")
    return " OR ".join(terms)


def kandidaten(conn: sqlite3.Connection, text: str, query_vec: list[float] | None,
                max_results: int) -> tuple[list[dict], list[dict]]:
    """Ersetzt den Aufruf von suchpfad_abruf.kandidaten() im Hook 1:1 (gleiche
    Signatur, gleicher Rueckgabetyp) -- der Hook reranked/deckelt das
    Ergebnis danach unveraendert selbst (trust_score, rangfolge,
    MAX_NODES/MAX_LESSONS-Slice, s. Moduldoc)."""
    pool = max(max_results, POOL_GROESSE) if _stufe2_aktiv() else max_results
    # suchpfad_abruf.kandidaten() baut die FTS-Anfrage selbst aus `text` via
    # _or_query() -- Stufe 1 braucht eine ANDERE Anfrage (Praefixterme), die
    # dieser Weg nicht ausdruecken kann. Darum bei aktiver Stufe 1 der
    # duennere Direktweg unten statt des Fremdaufrufs.
    if _stufe1_aktiv():
        return _kandidaten_direkt(conn, _erweiterte_fts_query(text), query_vec, pool)
    return suchpfad_abruf.kandidaten(conn, text, query_vec, pool)


def _kandidaten_direkt(conn: sqlite3.Connection, fts_query: str,
                        query_vec: list[float] | None, pool: int) -> tuple[list[dict], list[dict]]:
    """Stufe 1: dieselbe SQL/Fusion wie suchpfad_abruf.kandidaten(), nur mit
    der erweiterten FTS-Anfrage (Praefixterme) statt _or_query(text)."""
    import embeddings
    from gattung_filter import SQL_ARBEITSBESTAND_NUR
    from knowledge_mcp_server import _embedding_ranking, _fuse_with_keyword_floor

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
        emb_node_ids = _embedding_ranking(conn, "node", query_vec, None)
        emb_lesson_ids = _embedding_ranking(conn, "lesson", query_vec, None)
    else:
        emb_node_ids, emb_lesson_ids = [], []
    embedding_ordered_ids = embeddings.rrf_fuse(emb_node_ids, emb_lesson_ids, embedding_weight=1.0)

    final_ids = _fuse_with_keyword_floor(keyword_ordered_ids, embedding_ordered_ids, pool)

    missing_node_ids = [i for i in final_ids if i in emb_node_ids and i not in node_by_id]
    if missing_node_ids:
        placeholders = ",".join("?" for _ in missing_node_ids)
        for r in conn.execute(
            "SELECT id, path, title, summary, updated_at, gilt_ab, gilt_bis "
            f"FROM knowledge_nodes WHERE id IN ({placeholders}) AND zurueckgezogen = 0 "
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


# Beide Stufen gemessen AUS (s. Moduldoc): Stufe 1 wirkungslos (7/35 ->
# 7/35), Stufe 2 schaedlich (7/35 -> 6/35, L-606b63 verliert). Keine der
# beiden hebt den Schalter -- MEHRSTUFIGER_ABRUF bleibt AUS, unabhaengig
# von diesen beiden Konstanten (s. _mehrstufig_aktiv()).
STUFE1_KOMPOSITA = False
STUFE2_POOL_VOR_DECKEL = False


def _stufe1_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_MEHRSTUFIG_STUFE1")
    if override is not None:
        return override == "1"
    return STUFE1_KOMPOSITA


def _stufe2_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_MEHRSTUFIG_STUFE2")
    if override is not None:
        return override == "1"
    return STUFE2_POOL_VOR_DECKEL


# Gesamtschalter fuers Modul, gleiche Bauform wie SUCHPFAD_ABRUF in
# knowledge_recall_hook.py (Modul-Konstante + Env-Uebersteuerung, Rueckweg
# kostenlos). Vorgabe AUS -- gemessen: keine der beiden Stufen verbessert
# die Trefferzahl (s. Moduldoc), Stufe 2 verschlechtert sie sogar. Bei AUS
# liefert kandidaten_geschaltet() byte-gleich das, was suchpfad_abruf.
# kandidaten() liefert (s. _selftest()).
MEHRSTUFIGER_ABRUF = False


def _mehrstufig_aktiv() -> bool:
    override = os.environ.get("KNOWLEDGE_MEHRSTUFIGER_ABRUF")
    if override is not None:
        return override == "1"
    return MEHRSTUFIGER_ABRUF


def kandidaten_geschaltet(conn: sqlite3.Connection, text: str, query_vec: list[float] | None,
                           max_results: int) -> tuple[list[dict], list[dict]]:
    """Einstiegspunkt fuer den Hook (Import+Aufruf ersetzt dort
    suchpfad_abruf.kandidaten() 1:1). Bei MEHRSTUFIGER_ABRUF=AUS (Vorgabe)
    byte-gleich zu suchpfad_abruf.kandidaten() (kein Pool, keine
    Praefixterme) -- s. _selftest()."""
    if not _mehrstufig_aktiv():
        return suchpfad_abruf.kandidaten(conn, text, query_vec, max_results)
    return kandidaten(conn, text, query_vec, max_results)


def _selftest() -> None:
    """Netzloser Selbsttest gegen die echte (nur gelesene) DB -- kein Ollama
    noetig, query_vec=None testet den reinen Stichwort-Pfad."""
    import ort  # noqa: E402 -- liegt in haken/, s. Modulkopf des Hooks
    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row

    nodes, lessons = kandidaten_geschaltet(conn, "", None, 5)
    assert nodes == [] and lessons == [], "leerer Text muss leere Kandidaten liefern"
    nodes, lessons = kandidaten_geschaltet(conn, "qwfpqwfpblorx zvxjkq wibbnfrx", None, 5)
    assert nodes == [] and lessons == [], "Nonsens-Text darf keine Kandidaten erfinden"

    # Byte-Gleichheit bei AUS (Vorgabe, kein Env-Override noetig): derselbe
    # Aufruf, einmal ueber suchpfad_abruf.kandidaten() direkt, einmal ueber
    # kandidaten_geschaltet() -- im selben Prozess, selben Zeitpunkt (trennt
    # Zeitdrift im trust_score vom eigentlichen Vergleich).
    assert _mehrstufig_aktiv() is False, "Vorgabe muss AUS sein, sonst misst dieser Test die falsche Sache"
    text = "Rollout Fehlermeldungen Programmierfehler Protokolle"
    a = kandidaten_geschaltet(conn, text, None, 5)
    b = suchpfad_abruf.kandidaten(conn, text, None, 5)
    assert a == b, "MEHRSTUFIGER_ABRUF=AUS muss byte-gleich zu suchpfad_abruf.kandidaten() sein"

    # Warnung statt Rot-vor-gruen (s. Moduldoc: kein Fall wird durch Stufe 2
    # NEU gewonnen -- stattdessen geht L-606b63 verloren, sobald Stufe 2 an
    # ist). Geprueft ueber den ECHTEN Weg (knowledge_recall_hook.query(), wie
    # abrufguete.py ihn ruft) -- die rohen kandidaten()-Listen allein zeigen
    # das nicht, weil der Hook danach noch nach (severity, occurrences)
    # sortiert und auf MAX_LESSONS zuschneidet (s. Moduldoc, das ist die
    # gefundene Ursache).
    import knowledge_recall_hook as _rh
    import embeddings as _embeddings

    task = ("Wenn ein Nutzer eine Bluetooth-Verbindung kurz hintereinander neu "
            "aufbaut, kann ein verspaetet eintreffender Trennbefehl aus dem ersten "
            "Versuch die gerade erst gestartete zweite Sitzung unterbrechen. Ohne "
            "eine eindeutige Zuordnung zwischen dem Signal und der spezifischen "
            "Instanz fuehrt dieser Timingfehler dazu, dass die neue Verbindung "
            "faelschlicherweise gekappt wird. Das System muss sicherstellen, dass "
            "ein Beendungsbefehl nur dann wirksam ist, wenn er gezielt auf den "
            "aktuell laufenden Vorgang abzielt.")
    kws = _rh.keywords(task)
    query_vec = _embeddings.embed_text(task)  # deterministisch fuer denselben Text (Ollama)

    class _Stand:
        kandidaten = staticmethod(kandidaten_geschaltet)

    orig_suchpfad = _rh.suchpfad_abruf
    _rh.suchpfad_abruf = _Stand
    try:
        _, lessons_aus = _rh.query(kws, rand=lambda: 1.0, cwd=None, prompt=task,
                                    embed_fn=lambda _t: query_vec)
        assert "L-606b63" in [l["id"] for l in lessons_aus], (
            "Voraussetzung der Warnung verletzt: L-606b63 muss bei AUS im Ergebnis sein")

        os.environ["KNOWLEDGE_MEHRSTUFIGER_ABRUF"] = "1"
        os.environ["KNOWLEDGE_MEHRSTUFIG_STUFE1"] = "0"
        os.environ["KNOWLEDGE_MEHRSTUFIG_STUFE2"] = "1"
        try:
            _, lessons_stufe2 = _rh.query(kws, rand=lambda: 1.0, cwd=None, prompt=task,
                                           embed_fn=lambda _t: query_vec)
        finally:
            for k in ("KNOWLEDGE_MEHRSTUFIGER_ABRUF", "KNOWLEDGE_MEHRSTUFIG_STUFE1", "KNOWLEDGE_MEHRSTUFIG_STUFE2"):
                os.environ.pop(k, None)
        assert "L-606b63" not in [l["id"] for l in lessons_stufe2], (
            "Regression nicht mehr reproduzierbar -- Moduldoc-Befund pruefen, bevor POOL_GROESSE geaendert wird")
    finally:
        _rh.suchpfad_abruf = orig_suchpfad

    conn.close()
    print("mehrstufiger_abruf._selftest ok")


if __name__ == "__main__":
    _selftest()
