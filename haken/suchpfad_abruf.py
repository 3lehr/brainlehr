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

knowledge_mcp_server.py wird NICHT geaendert, nur importiert.

SELBSTLAUF-VERMERK (Aufgabe wirkkette-6, 2026-08-15): Dieses Modul ist reine
Bibliothek -- kein eigener stdin-Haken, `__main__` startet nur den Selbsttest.
Der einzige Aufrufer ist haken/knowledge_recall_hook.py (Import), darum
erbt es dessen Ereignisse 1:1 -- eine eigene Verdrahtung waere Attrappe, das
Ereignis haengt am Aufrufer, nicht an dieser Datei. Der Blindfleck ist damit
identisch mit dem von knowledge_recall_hook.py (siehe Vermerk dort, 6,0s
Kosten) und nicht separat zu loesen.

NACHTRAG P18 (2026-08-21, docs/PLAN_NAECHSTE_STUFE_2026-08-21.md §4.1/§9):
eine natuerliche Namensfrage ("zeige mir alles was mit Frau X zu tun hat")
verdampft im Satz-OR oben zu Fuellwoertern + Anrede -- der Name selbst
konkurriert dann mit jedem anderen Wort des Satzes und landet weit hinten
im bm25-Rang (gemessen: Rang 0 fuer den blossen Namen, Rang 6/20 fuer
dieselben zwei Ziele in der natuerlichen Frage). kern/namensfrage.py loest
den Eigennamen ueber eine Anrede (Frau/Herr/Herrn/Familie) heraus, OHNE die
Anrede selbst zu durchsuchen; _namenskandidaten() sucht NUR mit diesem
Namen exakt, _voranstellen() draengt die Treffer im Stichwortkanal UND im
fertig fusionierten final_ids VOR -- Belegs. runs/namensfrage_2026-08-21.json.
Ausloest nur bei erkannter Anrede (0 von 45 Faellen in runs/pruefkorpus.jsonl
tragen eine), also byte-gleich zum bisherigen Weg fuer jede Sachfrage."""
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

import sqlite3

import embeddings
import namensfrage
from gattung_filter import SQL_ARBEITSBESTAND_NUR
from knowledge_mcp_server import (
    _embedding_ranking, _or_query, _stichwortkanal_blind, _fts_phrase, fold_de,
)


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


def _namenskandidaten(conn: sqlite3.Connection, name: str) -> tuple[list[str], list[str]]:
    """P18: exakte FTS-Suche NUR auf dem herausgeloesten Eigennamen (kern.
    namensfrage.eigennamen()) -- Gegenmittel zur Verduennung, die entsteht,
    wenn derselbe Name Teil der Satz-OR-Anfrage aus _or_query(text) ist
    (dort konkurriert er mit jedem anderen Wort des Satzes, s. Moduldoc von
    kern/namensfrage.py). Gleiche Filter wie der Hauptweg oben
    (SQL_ARBEITSBESTAND_NUR, nicht zurueckgezogen, Lehre nicht resolved).
    Rueckgabe nur IDs in bm25-Rangfolge -- kandidaten() setzt sie vorn an,
    nicht anstelle des Hauptfunds."""
    query = _fts_phrase(fold_de(name))
    node_ids = [r["id"] for r in conn.execute(
        "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        f"WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR} "
        "ORDER BY rank",
        (query,),
    ).fetchall()]
    lesson_ids = [r["id"] for r in conn.execute(
        "SELECT l.id FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
        "WHERE lessons_fts MATCH ? AND l.status != 'resolved' "
        "ORDER BY rank",
        (query,),
    ).fetchall()]
    return node_ids, lesson_ids


def _voranstellen(vorn: list[str], rest: list[str]) -> list[str]:
    """vorn zuerst (in seiner Reihenfolge), danach rest ohne Dubletten --
    der Namensfund draengt den Hauptfund nicht heraus, er geht ihm nur vor."""
    ergebnis = list(vorn)
    gesehen = set(ergebnis)
    for i in rest:
        if i not in gesehen:
            ergebnis.append(i)
            gesehen.add(i)
    return ergebnis


def _kappen_mit_ausgleich(a_ids: list[str], b_ids: list[str],
                            cap_a: int, cap_b: int) -> tuple[list[str], list[str]]:
    """Getrennte Kandidatenbudgets (docs/PLAN_NAECHSTE_STUFE_2026-08-21.md
    S4.2): a und b werden JEDER FUER SICH gekappt, nicht als eine gemeinsame
    Liste -- das ist der ganze Unterschied zum alten Weg (dort konkurrierten
    Knoten und Lehren um dieselben max_results Plaetze, s. Moduldoc-Nachtrag).

    NEGATIVFALL: bleibt eine Sorte unter ihrem Kontingent (weniger
    Kandidaten als das Kontingent, im Extrem 0), darf der Rest nicht
    verfallen -- er geht an die andere Sorte, sonst waere der Abruf nach
    dieser Aenderung STRENGER als vorher, wenn eine Sorte leer ist. Beide
    Richtungen werden unabhaengig behandelt (freier Platz bei a erweitert
    NUR cap_b und umgekehrt), es kann also nie eine Sorte doppelt von ihrem
    eigenen Ueberschuss profitieren."""
    frei_a = max(0, cap_a - len(a_ids))
    frei_b = max(0, cap_b - len(b_ids))
    return a_ids[:cap_a + frei_b], b_ids[:cap_b + frei_a]


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
    max_results=5).

    NACHTRAG S4.2 (2026-08-21, docs/PLAN_NAECHSTE_STUFE_2026-08-21.md,
    Konsil-Befund runs/beurteilung_blind_2026-08-20.json): max_results als
    EIN int liess Knoten und Lehren in EINER fusionierten Liste um denselben
    Deckel konkurrieren, obwohl der Aufrufer sie mit getrennten Kontingenten
    (MAX_NODES, MAX_LESSONS) weiterverarbeitet -- faellt eine Sorte im Rang
    zurueck, verlor sie Plaetze an die andere, die ihr nicht zustanden.
    max_results akzeptiert deshalb jetzt ZUSAETZLICH ein Tupel (max_nodes,
    max_lessons): dann werden Knoten- und Lehrenrang JE FUER SICH fusioniert
    und gekappt (_kappen_mit_ausgleich), bevor sie zurueckgegeben werden --
    ungenutztes Kontingent einer Sorte geht an die andere (Negativfall),
    verfaellt aber nicht. Ein einzelner int bleibt BYTE-GLEICH zum alten Weg
    (gemeinsame Fusion+Deckel) -- jeder bestehende Aufrufer (mehrstufiger_
    abruf.py, die messungen/*.py-Skripte, aeltere Tests), der weiterhin ein
    int uebergibt, ist unveraendert. Jede Zeile traegt zusaetzlich 'bedeutungs_kosinus' -- der
    rohe Kosinus des Bedeutungskanals fuer GENAU diesen Kandidaten, None wenn
    kein Vektor vorliegt (Auftrag 2026-08-19, gleiche Bauform wie
    knowledge_search() in knowledge_mcp_server.py). Reines Beiwerk: aendert
    weder Auswahl noch Reihenfolge der final_ids.

    Auftrag 89 (Kanalwahl an die Anfragelaenge binden), gemessen statt
    geplant: DIESER Pfad (kein _fuse_with_keyword_floor-Sockel, reine
    RRF-Fusion embeddings.rrf_fuse(keyword_ordered_ids, embedding_ordered_ids))
    war schon VOR diesem Auftrag laengenblind sicher -- ein Stichwortkanal,
    der bei kurzen Woertern (tokenize='trigram', schema.sql, min. 3 Zeichen
    je Trigramm) leer bleibt, traegt zu rrf_fuse() nachweislich nichts bei
    (addiert nur ueber tatsaechlich vorhandene Listenelemente), der
    Bedeutungskanal entscheidet dann allein -- WORTWEISE, nicht als
    Alles-oder-Nichts-Schalter ueber die ganze Anfrage: ein einzelnes langes
    Wort neben zwei kurzen laesst den Kanal weiterhin (mit-)wirken. Belegt
    2026-08-15 an echtem Bestand (2210 Knoten): 'KI' (2 Zeichen, Node
    91c3f181) und '知識' (2 Zeichen, Node 5f85be35) 0 FTS-Treffer, aber
    beide Knoten ueber den Bedeutungskanal unter den Top 3 der vollen
    hook.query()-Kette. Rot-vor-gruen war an DIESEM Pfad nicht herstellbar
    -- kein Fall gefunden, der heute den falschen Kanal nimmt und dadurch
    nichts findet (anders als bei der frueheren MIN_HITS-Schwelle in
    knowledge_recall_hook.query(), die _suchpfad_aktiv()=True seit 2026-08-09
    umgeht, und anders als knowledge_search() vor a31f6f7, das denselben
    Bestand traf).
    _stichwortkanal_blind() unten ist deshalb KEIN Korrekturmechanismus,
    sondern Parity/Performance: erspart zwei SQL-Anfragen, deren Ergebnis
    (leer) beim blinden Fall ohnehin feststeht -- explizit erzwungen statt
    dem Zufall ueberlassen, gleiche Begruendung wie in knowledge_search()."""
    fts_query = _or_query(text)
    if not fts_query:
        # Kein Wort ueberhaupt (leer/Interpunktion) -- fehlt der Rohtext,
        # den Kanaele auswerten koennten. WICHTIG: nur dieser Fall darf die
        # ganze Funktion abbrechen, der naechste (blind) NICHT -- sonst
        # verliert eine kurze/CJK-Anfrage auch ihren Bedeutungskanal, den
        # query_vec vom Aufrufer unabhaengig vom Stichwortkanal mitbringt.
        return [], []
    # Auftrag 89: alle Woerter < 3 Zeichen -> der Trigramm-Tokenizer kann
    # NIE treffen (schema.sql), die zwei MATCH-Abfragen unten liefern in
    # diesem Fall nachweislich 0 Zeilen (gemessen, s. Funktionsdoc). Nur die
    # SQL-Anfragen werden uebersprungen -- query_vec/embedding-Kanal bleibt
    # unveraendert unten aktiv.
    blind = _stichwortkanal_blind(text)
    node_rows = [] if blind else conn.execute(
        "SELECT n.id, n.path, n.title, n.summary, n.updated_at, n.gilt_ab, n.gilt_bis "
        "FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        f"WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR} "
        "ORDER BY rank",
        (fts_query,),
    ).fetchall()
    lesson_rows = [] if blind else conn.execute(
        "SELECT l.id, l.description, l.root_cause, l.prevention, l.severity, "
        "l.occurrences, l.type, l.last_seen, l.first_seen, l.session, l.projects "
        "FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
        "WHERE lessons_fts MATCH ? AND l.status != 'resolved' "
        "ORDER BY rank",
        (fts_query,),
    ).fetchall()
    node_by_id = {r["id"]: dict(r) for r in node_rows}
    lesson_by_id = {r["id"]: dict(r) for r in lesson_rows}

    # P18: eine Namensfrage ("zeige mir alles was mit Frau X zu tun hat")
    # verduennt den herausgeloesten Namen im Satz-OR oben mit Fuellwoertern
    # und der Anrede selbst -- der Namenstreffer LANDET im Fund (er ist ja
    # eines der OR-Woerter), nur weit hinten. Hier vorgezogen, nicht ersetzt:
    # ein zusaetzlicher Fund (moeglich, wenn der Name allein traf, wo der
    # ganze Satz es nicht tat) wird direkt nachgeladen.
    node_id_order = list(node_by_id.keys())
    lesson_id_order = list(lesson_by_id.keys())
    namen_node_ids: list[str] = []
    namen_lesson_ids: list[str] = []
    for name in namensfrage.eigennamen(text):
        name_node_ids, name_lesson_ids = _namenskandidaten(conn, name)
        namen_node_ids = _voranstellen(namen_node_ids, name_node_ids)
        namen_lesson_ids = _voranstellen(namen_lesson_ids, name_lesson_ids)
        node_id_order = _voranstellen(name_node_ids, node_id_order)
        lesson_id_order = _voranstellen(name_lesson_ids, lesson_id_order)
        for nid in name_node_ids:
            if nid in node_by_id:
                continue
            zeile = conn.execute(
                "SELECT n.id, n.path, n.title, n.summary, n.updated_at, n.gilt_ab, n.gilt_bis "
                f"FROM knowledge_nodes n WHERE n.id = ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR}",
                (nid,),
            ).fetchone()
            if zeile is not None:
                node_by_id[nid] = dict(zeile)
        for lid in name_lesson_ids:
            if lid in lesson_by_id:
                continue
            zeile = conn.execute(
                "SELECT id, description, root_cause, prevention, severity, occurrences, "
                "type, last_seen, first_seen, session, projects FROM lessons_learned "
                "WHERE id = ? AND status != 'resolved'",
                (lid,),
            ).fetchone()
            if zeile is not None:
                lesson_by_id[lid] = dict(zeile)

    bedeutungswerte: list = []
    lesson_bedeutungswerte: list = []
    if query_vec is not None:
        erl_nodes, erl_lessons = _erlaubte_ids(conn)
        emb_node_ids = _embedding_ranking(conn, "node", query_vec, erl_nodes, bedeutungswerte)
        emb_lesson_ids = _embedding_ranking(conn, "lesson", query_vec, erl_lessons, lesson_bedeutungswerte)
    else:
        emb_node_ids, emb_lesson_ids = [], []
    # Roher Kosinus je Treffer (Auftrag 2026-08-19, wie knowledge_search() in
    # knowledge_mcp_server.py): rrf_fuse unten verwirft ihn zugunsten einer reinen
    # Rangposition -- hier vor dem Verlust als id->Kosinus-Dict aufgehoben.
    # emb_*_ids und ihre Werte-Listen sind noch parallel sortiert (_embedding_ranking
    # gibt beide aus demselben "scored" hervor), ein zip genuegt.
    kosinus_je_id = dict(zip(emb_node_ids, bedeutungswerte))
    kosinus_je_id.update(zip(emb_lesson_ids, lesson_bedeutungswerte))

    if isinstance(max_results, tuple):
        # S4.2: getrennte Kandidatenbudgets -- Knoten und Lehren werden JE
        # FUER SICH fusioniert (Stichwort x Bedeutung derselben Sorte), nicht
        # mehr ueber eine gemeinsame Liste, die um einen einzigen Deckel
        # konkurriert. Gleiche Fusionsformel wie im alten Weg (reine RRF,
        # hybrid_retrieval_weight()), nur ohne den Sorten-Mischschritt davor.
        max_nodes, max_lessons = max_results
        final_node_ids = embeddings.rrf_fuse(
            node_id_order, emb_node_ids,
            embedding_weight=embeddings.hybrid_retrieval_weight())
        final_lesson_ids = embeddings.rrf_fuse(
            lesson_id_order, emb_lesson_ids,
            embedding_weight=embeddings.hybrid_retrieval_weight())
        # P18-Namensweg wie im alten Zweig unten: NACH der Fusion vorangestellt,
        # je Sorte getrennt (vorher schon getrennt vorgehalten).
        if namen_node_ids:
            final_node_ids = _voranstellen(namen_node_ids, final_node_ids)
        if namen_lesson_ids:
            final_lesson_ids = _voranstellen(namen_lesson_ids, final_lesson_ids)
        # Negativfall: eine leere/kurze Sorte darf ihr Kontingent nicht
        # verfallen lassen -- der Rest geht an die andere (s. Funktionsdoc
        # von _kappen_mit_ausgleich).
        final_node_ids, final_lesson_ids = _kappen_mit_ausgleich(
            final_node_ids, final_lesson_ids, max_nodes, max_lessons)
    else:
        # Alter Weg, byte-gleich: EIN gemeinsamer Deckel ueber eine EINE
        # fusionierte Liste aus beiden Sorten (Kein Stichwort-Sockel
        # (_fuse_with_keyword_floor) mehr: er reservierte die ersten
        # max_results Plaetze fuer den Stichwortkanal -- und weil dieser bei
        # einem Prompt als Anfrage per _or_query praktisch den ganzen Bestand
        # zieht (Median 348 von 383 Knoten, 674 von 674 Lehren), war die
        # Kandidatenliste in 35 von 35 gemessenen Faellen BYTE-GLEICH mit
        # seinen Top 5. Der Bedeutungskanal wurde gerechnet (ein Ollama-Aufruf
        # je Prompt) und hatte null Einfluss. Reine RRF-Verschmelzung: 9/35
        # statt 7/35, bei gleicher Liefermenge. Der Sockel bleibt in
        # knowledge_search unangetastet -- dort ist die Anfrage ein
        # Suchbegriff, kein Prompt, und zieht nicht den Bestand.)
        keyword_ordered_ids = embeddings.rrf_fuse(
            node_id_order, lesson_id_order, embedding_weight=1.0)
        embedding_ordered_ids = embeddings.rrf_fuse(emb_node_ids, emb_lesson_ids, embedding_weight=1.0)
        final_ids = embeddings.rrf_fuse(
            keyword_ordered_ids, embedding_ordered_ids,
            embedding_weight=embeddings.hybrid_retrieval_weight())[:max_results]

        # P18: der Namensweg darf vom Bedeutungskanal nicht verdraengt werden --
        # RRF allein reicht dafuer nicht, weil ein exakter Namenstreffer, den der
        # Bedeutungskanal NICHT auch fuer relevant haelt (kein gemeinsamer Rang),
        # in der Fusion nur sein Stichwort-Gewicht traegt und so von Kandidaten
        # ueberholt wird, die in BEIDEN Kanaelen auftauchen (gemessen am
        # Auftragsfall: Rang 2 im Stichwortkanal reichte nicht, s. runs/
        # namensfrage_2026-08-21.json). Exakte Namenstreffer werden deshalb HIER,
        # NACH der Fusion, vorangestellt -- der Rest der Fusion bleibt die
        # Reihenfolge, es wird nichts entfernt, nur der Deckel neu gezogen.
        if namen_node_ids or namen_lesson_ids:
            final_ids = _voranstellen(namen_node_ids + namen_lesson_ids, final_ids)[:max_results]
        final_node_ids = final_ids
        final_lesson_ids = final_ids

    # Embedding-Kanal kann IDs liefern, die die FTS-Abfrage oben nicht
    # gezogen hat (das ist der ganze Witz des zweiten Kanals) -- fehlende
    # Zeilen nachladen, wie knowledge_search() es fuer final_ids selbst tut
    # (dort "missing"-Block).
    missing_node_ids = [i for i in final_node_ids if i in emb_node_ids and i not in node_by_id]
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
    missing_lesson_ids = [i for i in final_lesson_ids if i in emb_lesson_ids and i not in lesson_by_id]
    if missing_lesson_ids:
        placeholders = ",".join("?" for _ in missing_lesson_ids)
        for r in conn.execute(
            "SELECT id, description, root_cause, prevention, severity, occurrences, "
            "type, last_seen, first_seen, session, projects FROM lessons_learned "
            f"WHERE id IN ({placeholders}) AND status != 'resolved'",
            missing_lesson_ids,
        ):
            lesson_by_id[r["id"]] = dict(r)

    # Roher Kosinus des Bedeutungskanals je Kandidat (Auftrag 2026-08-19): None
    # (nicht 0.0) wenn kein Vektor vorliegt -- 0.0 waere eine Aussage ueber
    # Aehnlichkeit, None eine ueber Verfuegbarkeit. Nur angehaengt, keine
    # Auswahl/Reihenfolge geaendert -- final_node_ids/final_lesson_ids und
    # ihre Zuordnung zu node_by_id/lesson_by_id bleiben wie zuvor.
    for i, d in node_by_id.items():
        d["bedeutungs_kosinus"] = kosinus_je_id.get(i)
    for i, d in lesson_by_id.items():
        d["bedeutungs_kosinus"] = kosinus_je_id.get(i)

    return (
        [node_by_id[i] for i in final_node_ids if i in node_by_id],
        [lesson_by_id[i] for i in final_lesson_ids if i in lesson_by_id],
    )


def _selftest() -> None:
    """Netzloser Selbsttest gegen die echte (nur gelesene) DB -- kein Ollama
    noetig, query_vec=None testet den reinen Stichwort-Pfad.

    BEHOBEN 2026-08-19: Der `with speicher.lesen()`-Block endete nach der
    ersten Zusicherung, der ganze Rest lief gegen eine bereits geschlossene
    Verbindung und brach mit `sqlite3.ProgrammingError: Cannot operate on a
    closed database` ab. Der Selbsttest ist also NIE durchgelaufen -- ein
    Pruefer, der immer abstuerzt, prueft so wenig wie ein Melder ohne
    Ausloeser. Belegt als vorbestehend: derselbe Absturz im Stand
    1e2b40ee~1, also vor dem Einbau von `bedeutungs_kosinus`.
    """
    import sys as _sys
    from pathlib import Path as _Path
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
    _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "kern"))
    import speicher  # noqa: E402 -- eine Tuer zur Datenbank statt einer eigenen

    with speicher.lesen() as conn:
        nodes, lessons = kandidaten(conn, "", None, 5)
        assert nodes == [] and lessons == [], "leerer Text muss leere Kandidaten liefern"
        nodes, lessons = kandidaten(conn, "qwfpqwfpblorx zvxjkq wibbnfrx", None, 5)
        assert nodes == [] and lessons == [], "Nonsens-Text darf keine Kandidaten erfinden"

        # Negativfall zum Gattungsfilter im Bedeutungskanal: als Anfragevektor
        # dient der Vektor eines Nachschlagewerk-Knotens selbst. Ungefiltert
        # steht er damit auf Rang 1 seines eigenen Kanals -- er darf trotzdem
        # nirgends auftauchen. Gegenprobe in die andere Richtung gleich
        # darunter: derselbe Aufruf mit allowed_ids=None kennt ihn sehr wohl
        # (sonst pruefte der Test nur, dass irgendetwas leer ist).
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

        # Ergaenzt 2026-08-19, weil der Selbsttest ab hier zum ersten Mal
        # ueberhaupt ankommt: jeder gelieferte Kandidat traegt das Feld
        # `bedeutungs_kosinus` -- eine Zahl in [-1, 1] oder None, wenn kein
        # Vektor vorliegt. 0.0 waere falsch: das waere eine Aussage ueber
        # Aehnlichkeit, None ist eine ueber Verfuegbarkeit.
        nodes, lessons = kandidaten(conn, "Governance", None, 5)
        for r in nodes + lessons:
            assert "bedeutungs_kosinus" in r, "Feld fehlt am Kandidaten"
            w = r["bedeutungs_kosinus"]
            assert w is None or (isinstance(w, float) and -1.0 <= w <= 1.0), w

    print("suchpfad_abruf._selftest ok")


if __name__ == "__main__":
    # --selftest ist der Vertrag, auf den tests/test_alle_selftests.py ruft;
    # ohne Argument bleibt der bisherige Direktaufruf erhalten.
    _selftest()
