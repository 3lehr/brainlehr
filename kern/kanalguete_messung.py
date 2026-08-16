"""Messwerkzeug fuer docs/PLAN_KANALGUETE_2026-08-15.md -- misst die DREI
Zahlen (Trefferquote / Falschmeldequote / einsprachiger Normalfall) fuer
drei Zustaende (vorher / nach Schritt 1 / nach Schritt 2) auf demselben
Bestand, gegen dieselben Faelle.

WARUM EIN EIGENER, PARALLELER SUCHPFAD -- keine Umgehung des Auftrags,
sondern seine Voraussetzung: tests/test_kanalguete_flooranalyse.py belegt,
dass der ECHTE Weg (knowledge_mcp_server.knowledge_search) eine Aenderung an
kern/embeddings.py::rrf_fuse() strukturell nicht sehen kann, sobald der
Stichwortkanal den Sockel saettigt (_fuse_with_keyword_floor() kappt VOR
jeder Fusion). knowledge_mcp_server.py und haken/knowledge_recall_hook.py
(der zweite reale Weg, siehe kern/abrufguete.py) stehen beide auf der
TABU-Liste dieses Auftrags -- die Sockel-Verdraengung selbst ist NICHT
Teil dieser Aenderung. Um Schritt 1/2 UEBERHAUPT messbar zu machen, baut
dieses Modul dieselben Bausteine (FTS-MATCH, Kosinus-Ranking, RRF) NEU
zusammen, unter direktem Aufruf von kern/embeddings.py -- ohne den Sockel.
Das macht den Effekt von Schritt 1/2 auf die reine Fusion sichtbar, sagt
aber NICHTS darueber aus, ob der Leitfall ueber den echten MCP-Weg
(mit Sockel) heute anders ausfaellt -- siehe Bericht im Auftrag.

fold_de/_or_query/_stichwortkanal_blind werden aus knowledge_mcp_server.py
IMPORTIERT (nur gelesen, nicht veraendert) statt neu erfunden -- zwei
Implementierungen derselben Faltung waeren eine zusaetzliche Fehlerquelle.

numpy fuer die Kosinus-Matrix: kern/embeddings.py::cosine_similarity bleibt
bewusst reines Python (Ponytail-Begruendung dort, Einzelvergleiche). Hier
sind es Zehntausende Vergleiche je Messlauf -- numpy ist bereits Dependency
(kern/kanten_aus_bedeutung.py nutzt es ebenso bei groesserem Volumen)."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken"), str(_w / "melder")]

import argparse
import json
import random
import sqlite3
import time
from dataclasses import dataclass, field

import numpy as np

import embeddings
import relevanzlage
import knowledge_mcp_server as kms  # noqa: E402 -- nur gelesen: fold_de, _or_query, _stichwortkanal_blind

DB = _w / "brainlehr.db"


@dataclass
class Kanaele:
    """Die rohen, noch unfusionierten Kanaldaten fuer EINE Anfrage --
    einmal berechnet (teuer: FTS + ein Ollama-Aufruf), dreimal fusioniert
    (billig: reines Python)."""
    kw_node_ids: list = field(default_factory=list)
    kw_node_scores: dict = field(default_factory=dict)   # id -> -bm25 (hoeher=besser)
    kw_node_text: dict = field(default_factory=dict)
    kw_lesson_ids: list = field(default_factory=list)
    kw_lesson_scores: dict = field(default_factory=dict)
    kw_lesson_text: dict = field(default_factory=dict)
    emb_node_ids: list = field(default_factory=list)
    emb_node_scores: dict = field(default_factory=dict)
    emb_lesson_ids: list = field(default_factory=list)
    emb_lesson_scores: dict = field(default_factory=dict)


def lade_id_zu_pfad(conn: sqlite3.Connection) -> dict:
    """knowledge_nodes.id (kurzer Hash, z.B. 'nasa-llis-812') ist NICHT
    dasselbe wie knowledge_nodes.path ('/nasa-llis/812') -- FTS-Zeilen und
    knowledge_embeddings.ref_id tragen id, BEIDE Pruefkorpora (GermanQuAD-
    Import UND runs/pruefkorpus.jsonl, gespiegelt an
    haken/knowledge_recall_hook.py, das Knoten unter 'path' zurueckgibt)
    tragen aber PATH als target_id. Ohne diese Uebersetzung vergleicht die
    Messung id gegen path und findet NIE einen Knotentreffer -- genau der
    Fehler, der die erste Messung dieses Laufs auf 0/40 setzte (siehe
    runs/kanalguete_2026-08-15T20.json, verworfen)."""
    return {r["id"]: r["path"] for r in conn.execute("SELECT id, path FROM knowledge_nodes")}


def _kw_kanal(conn: sqlite3.Connection, query: str, id_zu_pfad: dict) -> tuple[list, list]:
    """Reproduziert exakt die Kanalwahl aus knowledge_mcp_server.knowledge_search
    (Zeilen um 2364ff, dort gelesen, hier nicht veraendert): blind bei
    ausschliesslich <3-Zeichen-Woertern, sonst FTS5 MATCH ueber die
    gefaltete OR-Verknuepfung. Knoten-Identitaet ist PATH (siehe
    lade_id_zu_pfad), Lehren-Identitaet bleibt ihre id (kein Path-Feld)."""
    fts_query = kms._or_query(query)
    if not fts_query or kms._stichwortkanal_blind(query):
        return [], []
    node_rows = conn.execute(
        """SELECT n.id, n.title, n.summary, n.content, bm25(knowledge_fts) AS score
           FROM knowledge_fts f JOIN knowledge_nodes n ON f.rowid = n.rowid
           WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0
           ORDER BY rank""", (fts_query,)).fetchall()
    lesson_rows = conn.execute(
        """SELECT l.id, l.description, l.root_cause, l.prevention, bm25(lessons_fts) AS score
           FROM lessons_fts f JOIN lessons_learned l ON f.rowid = l.rowid
           WHERE lessons_fts MATCH ? AND l.status = 'active'
           ORDER BY rank""", (fts_query,)).fetchall()
    node_rows = [dict(r) | {"path": id_zu_pfad.get(r["id"], r["id"])} for r in node_rows]
    return node_rows, lesson_rows


def _lade_embeddings(conn: sqlite3.Connection, kind: str, id_zu_pfad: dict | None = None) -> tuple[list, np.ndarray]:
    """Dedup auf ref_id (wie knowledge_mcp_server._embedding_ranking
    seen_ref_ids): mehrwertige Lehren tragen je Bereich eine Zeile, gleicher
    Vektor -- ohne Dedup zaehlt dieselbe Aehnlichkeit mehrfach in die
    RRF-Fusion. Erste Zeile je ref_id gewinnt, Rest verworfen.

    id_zu_pfad (nur kind='node'): uebersetzt ref_id (=knowledge_nodes.id)
    auf path -- siehe lade_id_zu_pfad."""
    rows = conn.execute(
        "SELECT ref_id, vector FROM knowledge_embeddings WHERE kind = ? AND model = ?",
        (kind, embeddings.DEFAULT_EMBED_MODEL)).fetchall()
    if not rows:
        return [], np.zeros((0, 0))
    gesehen = set()
    dedup_rows = []
    for r in rows:
        if r["ref_id"] in gesehen:
            continue
        gesehen.add(r["ref_id"])
        dedup_rows.append(r)
    rows = dedup_rows
    if id_zu_pfad is not None:
        ids = [id_zu_pfad.get(r["ref_id"], r["ref_id"]) for r in rows]
    else:
        ids = [r["ref_id"] for r in rows]
    mat = np.array([embeddings.unpack_embedding(r["vector"]) for r in rows], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return ids, mat / norms


def kanaele_bauen(conn: sqlite3.Connection, node_ids: list, node_mat: np.ndarray,
                   lesson_ids: list, lesson_mat: np.ndarray, query: str,
                   id_zu_pfad: dict) -> Kanaele:
    k = Kanaele()
    node_rows, lesson_rows = _kw_kanal(conn, query, id_zu_pfad)
    k.kw_node_ids = [r["path"] for r in node_rows]
    k.kw_node_scores = {r["path"]: -r["score"] for r in node_rows}  # bm25: kleiner=besser -> Vorzeichen drehen
    k.kw_node_text = {r["path"]: " ".join(filter(None, (r["title"], r["summary"], r["content"]))) for r in node_rows}
    k.kw_lesson_ids = [r["id"] for r in lesson_rows]
    k.kw_lesson_scores = {r["id"]: -r["score"] for r in lesson_rows}
    k.kw_lesson_text = {r["id"]: " ".join(filter(None, (r["description"], r["root_cause"], r["prevention"]))) for r in lesson_rows}

    vec = embeddings.embed_text(query)
    if vec is not None:
        qv = np.array(vec, dtype=np.float32)
        qn = np.linalg.norm(qv)
        if qn > 0:
            qv = qv / qn
        if node_mat.shape[0]:
            sims = node_mat @ qv
            order = np.argsort(-sims)
            k.emb_node_ids = [node_ids[i] for i in order]
            k.emb_node_scores = {node_ids[i]: float(sims[i]) for i in order}
        if lesson_mat.shape[0]:
            sims = lesson_mat @ qv
            order = np.argsort(-sims)
            k.emb_lesson_ids = [lesson_ids[i] for i in order]
            k.emb_lesson_scores = {lesson_ids[i]: float(sims[i]) for i in order}
    return k


def fusion_vorher(k: Kanaele, max_results: int) -> list:
    """Heutige Formel (embeddings.rrf_fuse ohne Scores) -- byte-identisch zu
    dem, was knowledge_mcp_server.py an dieser Stelle rechnet, NUR ohne den
    Stichwort-Sockel danach (siehe Modul-Docstring)."""
    kw = embeddings.rrf_fuse(k.kw_node_ids, k.kw_lesson_ids, embedding_weight=1.0)
    emb = embeddings.rrf_fuse(k.emb_node_ids, k.emb_lesson_ids, embedding_weight=1.0)
    return embeddings.rrf_fuse(kw, emb, embedding_weight=1.0)[:max_results]


def fusion_echt(k: Kanaele, max_results: int) -> list:
    """Der PRODUKTIVE Weg, einschliesslich des Stichwort-Sockels: ruft
    knowledge_mcp_server._fuse_with_keyword_floor() selbst auf (importiert,
    nicht nachgebaut -- zwei Implementierungen desselben Sockels waeren
    genau die Prueffstand-Abweichung, die dieses Modul messen soll).

    Der Unterschied zu fusion_vorher() ist der ganze Punkt: fusion_vorher()
    laesst den Sockel weg (Modul-Docstring), misst also eine Formel, die
    der echte Suchweg an dieser Stelle gar nicht ausfuehrt. Jede Zahl aus
    runs/kanalguete_vorher_schritt1_schritt2_2026-08-15.json gilt darum fuer
    den sockellosen Pfad, nicht fuer den Produktivweg."""
    kw = embeddings.rrf_fuse(k.kw_node_ids, k.kw_lesson_ids, embedding_weight=1.0)
    emb = embeddings.rrf_fuse(k.emb_node_ids, k.emb_lesson_ids, embedding_weight=1.0)
    return kms._fuse_with_keyword_floor(kw, emb, max_results)


def sockel_kennzahl(k: Kanaele, max_results: int) -> dict:
    """Die Verteilungsmessung, die der Plan vor jedem weiteren Formelentwurf
    verlangt: WIE OFT saettigt der Sockel, und wie viele Endplaetze bleiben
    dem Bedeutungskanal ueberhaupt?

    `gesaettigt` bedeutet: der Stichwortkanal allein koennte alle
    max_results Plaetze fuellen. Bis zum 2026-08-16 tat er das auch -- dann
    war das Ergebnis byte-identisch mit der reinen Stichwortreihenfolge und
    keine Aenderung an rrf_fuse() konnte es bewegen. Seit der Umstellung von
    _fuse_with_keyword_floor() auf embeddings.fuse_semantic_led() ist
    `gesaettigt` nur noch die Gelegenheit zur Verdraengung, nicht mehr ihr
    Beleg: die aussagekraeftige Zahl ist seither
    `endplaetze_nur_bedeutung` (vorher 4 von 585)."""
    kw = embeddings.rrf_fuse(k.kw_node_ids, k.kw_lesson_ids, embedding_weight=1.0)
    emb = embeddings.rrf_fuse(k.emb_node_ids, k.emb_lesson_ids, embedding_weight=1.0)
    final = kms._fuse_with_keyword_floor(kw, emb, max_results)
    kw_menge = set(kw)
    return {
        "gesaettigt": len(kw) >= max_results,
        "n_stichwortkanal": len(kw),
        "n_bedeutungskanal": len(emb),
        "endplaetze": len(final),
        "endplaetze_nur_bedeutung": sum(1 for i in final if i not in kw_menge),
        "identisch_mit_stichwortreihenfolge": final == kw[:len(final)],
    }


def fusion_schritt1(k: Kanaele, query: str, max_results: int) -> list:
    """+ nur GANZE Stichworttreffer (embeddings.filter_whole_word_hits)."""
    kw_node = embeddings.filter_whole_word_hits(query, k.kw_node_ids, k.kw_node_text)
    kw_lesson = embeddings.filter_whole_word_hits(query, k.kw_lesson_ids, k.kw_lesson_text)
    kw = embeddings.rrf_fuse(kw_node, kw_lesson, embedding_weight=1.0)
    emb = embeddings.rrf_fuse(k.emb_node_ids, k.emb_lesson_ids, embedding_weight=1.0)
    return embeddings.rrf_fuse(kw, emb, embedding_weight=1.0)[:max_results]


_DISKRIMINATIONSFENSTER = 50  # siehe _fenster_scores-Docstring


def _fenster_scores(ordered_ids: list, score_dict: dict, n: int = _DISKRIMINATIONSFENSTER) -> dict:
    """channel_discrimination() ueber den GANZEN Kanal zu rechnen (Tausende
    Kandidaten bis in den irrelevanten Schwanz der Kosinus-Verteilung)
    macht die Kennzahl zu einer Eigenschaft der Bestandsgroesse, nicht der
    Anfrage -- GENAU der Fehler, den der verworfene Schwellwert-Ansatz vom
    2026-08-12 schon hatte, nur eine Ebene tiefer (siehe
    fuse_semantic_led-Docstring in kern/embeddings.py). Fuer RRF zaehlt
    ohnehin nur die FUEHRENDE Kante eines Kanals (1/(k+position+1) faellt
    jenseits weniger Dutzend Positionen praktisch auf 0) -- die Messung
    beschraenkt sich deshalb auf die ersten n Rangplaetze."""
    return {i: score_dict[i] for i in ordered_ids[:n] if i in score_dict}


def fusion_schritt2(k: Kanaele, query: str, max_results: int) -> list:
    """+ Kanal-Trennschaerfe (embeddings.channel_discrimination via rrf_fuse'
    fts_scores=/embedding_scores=), auf Schritt 1 aufsetzend (Reihenfolge
    laut Plan bindend: Schritt 1 zuerst, Schritt 2 danach). Discrimination
    je Kanal NUR ueber die fuehrenden _DISKRIMINATIONSFENSTER Rangplaetze
    (siehe _fenster_scores)."""
    kw_node = embeddings.filter_whole_word_hits(query, k.kw_node_ids, k.kw_node_text)
    kw_lesson = embeddings.filter_whole_word_hits(query, k.kw_lesson_ids, k.kw_lesson_text)
    kw = embeddings.rrf_fuse(kw_node, kw_lesson, embedding_weight=1.0,
                              fts_scores=_fenster_scores(kw_node, k.kw_node_scores),
                              embedding_scores=None)
    emb = embeddings.rrf_fuse(k.emb_node_ids, k.emb_lesson_ids, embedding_weight=1.0,
                               fts_scores=_fenster_scores(k.emb_node_ids, k.emb_node_scores),
                               embedding_scores=None)
    kw_scores = _fenster_scores(kw, {**k.kw_node_scores, **k.kw_lesson_scores})
    emb_scores = _fenster_scores(emb, {**k.emb_node_scores, **k.emb_lesson_scores})
    fused = embeddings.rrf_fuse(kw, emb, embedding_weight=1.0,
                                 fts_scores=kw_scores, embedding_scores=emb_scores)
    return fused[:max_results]


def lade_germanquad_faelle() -> list:
    d = json.load((_w / "runs" / "wissenskorpus_import_germanquad_voll.json").open(encoding="utf-8"))
    return d["pruefkorpus_faelle"]


def lade_einsprachig_faelle() -> list:
    faelle = []
    with (_w / "runs" / "pruefkorpus.jsonl").open(encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if zeile:
                faelle.append(json.loads(zeile))
    return [f for f in faelle if f.get("accepted", True) and f.get("target_kind")]


def messlauf(*, n_ja: int, n_nein: int, max_results: int = 5, seed: int = 20260815) -> dict:
    rnd = random.Random(seed)
    alle = lade_germanquad_faelle()
    ja = [f for f in alle if f.get("label_antwort_im_bestand") == "ja"]
    nein = [f for f in alle if f.get("label_antwort_im_bestand") == "nein"]
    ja_stichprobe = rnd.sample(ja, min(n_ja, len(ja)))
    nein_stichprobe = rnd.sample(nein, min(n_nein, len(nein)))
    einsprachig = lade_einsprachig_faelle()

    leitfall = {"prompt": "Dichtung Leckage Treibstofftank Fehleranalyse Startverzoegerung",
                "target_id": "/nasa-llis/812", "target_kind": "node"}
    leitfall_sinnlos = {"prompt": "Kaffeemaschine Bueroklammer Regenschirm Wochenendausflug",
                        "target_id": None, "target_kind": None}

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    id_zu_pfad = lade_id_zu_pfad(conn)
    node_ids, node_mat = _lade_embeddings(conn, "node", id_zu_pfad)
    lesson_ids, lesson_mat = _lade_embeddings(conn, "lesson")

    # "echt" zuerst: die Stufe mit dem Sockel, also der einzige Zustand, den
    # der Produktivweg tatsaechlich rechnet. Die drei anderen sind der
    # sockellose Vergleichspfad des Auftrags vom 2026-08-15.
    stufen = {"echt": fusion_echt, "vorher": fusion_vorher,
              "schritt1": fusion_schritt1, "schritt2": fusion_schritt2}
    ergebnis = {
        "erzeugt_am": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "knoten_bestand": conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0],
        "modell": embeddings.DEFAULT_EMBED_MODEL,
        "n_ja": len(ja_stichprobe), "n_nein": len(nein_stichprobe),
        "n_einsprachig": len(einsprachig), "max_results": max_results, "seed": seed,
        "stufen": {},
    }

    sockel_proben: list = []

    def _fusionieren(query: str, stufe_name: str, k: Kanaele) -> list:
        if stufe_name == "echt":
            # Die Sockelverteilung faellt hier gratis ab: die Kanaele sind
            # bereits gebaut (der teure Teil, ein Ollama-Aufruf je Anfrage).
            sockel_proben.append(sockel_kennzahl(k, max_results))
            return fusion_echt(k, max_results)
        if stufe_name == "vorher":
            return fusion_vorher(k, max_results)
        if stufe_name == "schritt1":
            return fusion_schritt1(k, query, max_results)
        return fusion_schritt2(k, query, max_results)

    for stufe_name in stufen:
        t0 = time.monotonic()
        treffer_ja = 0
        for fall in ja_stichprobe:
            k = kanaele_bauen(conn, node_ids, node_mat, lesson_ids, lesson_mat, fall["prompt"], id_zu_pfad)
            final = _fusionieren(fall["prompt"], stufe_name, k)
            if fall["target_id"] in final:
                treffer_ja += 1
        gemeldet_nein = 0
        unerkannt_nein = 0   # geliefert UND als passend ausgegeben
        for fall in nein_stichprobe:
            k = kanaele_bauen(conn, node_ids, node_mat, lesson_ids, lesson_mat, fall["prompt"], id_zu_pfad)
            final = _fusionieren(fall["prompt"], stufe_name, k)
            if final:
                gemeldet_nein += 1
                # Seit dem 2026-08-16 liefert der Suchweg eine Einschaetzung mit
                # (kern/relevanzlage.py). Damit zerfaellt "gemeldet" in zwei sehr
                # verschiedene Faelle: geliefert UND als passend ausgegeben ist
                # eine Falschmeldung; geliefert MIT Hinweis ist eine ehrliche
                # Auskunft. Ohne diese Trennung bliebe die Zahl bei 40/40 und
                # die Kennzeichnung waere in der Messung unsichtbar.
                werte = sorted(k.emb_node_scores.values(), reverse=True)
                if relevanzlage.beurteile(werte)["lage"] == "passend":
                    unerkannt_nein += 1
        treffer_einsprachig = 0
        for fall in einsprachig:
            k = kanaele_bauen(conn, node_ids, node_mat, lesson_ids, lesson_mat, fall["task"], id_zu_pfad)
            final = _fusionieren(fall["task"], stufe_name, k)
            ziel = fall["target_id"]
            if ziel in final:
                treffer_einsprachig += 1
        k_leit = kanaele_bauen(conn, node_ids, node_mat, lesson_ids, lesson_mat, leitfall["prompt"], id_zu_pfad)
        leitfall_ok = leitfall["target_id"] in _fusionieren(leitfall["prompt"], stufe_name, k_leit)
        k_sinnlos = kanaele_bauen(conn, node_ids, node_mat, lesson_ids, lesson_mat, leitfall_sinnlos["prompt"], id_zu_pfad)
        sinnlos_final = _fusionieren(leitfall_sinnlos["prompt"], stufe_name, k_sinnlos)

        dauer = time.monotonic() - t0
        n_gesamt = len(ja_stichprobe) + len(nein_stichprobe) + len(einsprachig)
        ergebnis["stufen"][stufe_name] = {
            "trefferquote": treffer_ja / len(ja_stichprobe) if ja_stichprobe else None,
            "trefferquote_zaehler_nenner": f"{treffer_ja}/{len(ja_stichprobe)}",
            "falschmeldequote": gemeldet_nein / len(nein_stichprobe) if nein_stichprobe else None,
            "falschmeldequote_zaehler_nenner": f"{gemeldet_nein}/{len(nein_stichprobe)}",
            "als_passend_ausgegeben": f"{unerkannt_nein}/{len(nein_stichprobe)}",
            "einsprachig_trefferquote": treffer_einsprachig / len(einsprachig) if einsprachig else None,
            "einsprachig_zaehler_nenner": f"{treffer_einsprachig}/{len(einsprachig)}",
            "leitfall_deutsch_trifft": leitfall_ok,
            "leitfall_sinnlos_bleibt_leer_oder_verworfen": sinnlos_final == [] or leitfall_sinnlos["target_id"] not in sinnlos_final,
            "dauer_s_gesamt": round(dauer, 2),
            "dauer_s_je_anfrage": round(dauer / n_gesamt, 3) if n_gesamt else None,
            "anfragen_gemessen": n_gesamt,
        }
    conn.close()
    if sockel_proben:
        n = len(sockel_proben)
        ergebnis["sockel"] = {
            "anfragen": n,
            "gesaettigt": sum(1 for p in sockel_proben if p["gesaettigt"]),
            "gesaettigt_anteil": sum(1 for p in sockel_proben if p["gesaettigt"]) / n,
            "identisch_mit_stichwortreihenfolge": sum(
                1 for p in sockel_proben if p["identisch_mit_stichwortreihenfolge"]),
            "endplaetze_nur_bedeutung_summe": sum(p["endplaetze_nur_bedeutung"] for p in sockel_proben),
            "endplaetze_summe": sum(p["endplaetze"] for p in sockel_proben),
            "n_stichwortkanal_median": sorted(p["n_stichwortkanal"] for p in sockel_proben)[n // 2],
            "erlaeuterung": (
                "gesaettigt = Stichwortkanal koennte allein alle max_results Plaetze "
                "fuellen. Bis zur Umstellung auf embeddings.fuse_semantic_led() "
                "(2026-08-16) tat er das auch, dann war das Ergebnis identisch mit der "
                "Stichwortreihenfolge und jede Aenderung an rrf_fuse folgenlos. "
                "Seither ist die aussagekraeftige Zahl endplaetze_nur_bedeutung "
                "(vor der Umstellung 4 von 585)."),
        }
    return ergebnis


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-ja", type=int, default=40)
    parser.add_argument("--n-nein", type=int, default=40)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()
    ergebnis = messlauf(n_ja=args.n_ja, n_nein=args.n_nein)
    text = json.dumps(ergebnis, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        (_w / args.out).write_text(text, encoding="utf-8")


def demo() -> None:
    """Netzloser Selbsttest: nur die Fusionsfunktionen mit synthetischen
    Kanaelen (kein DB-/Ollama-Zugriff) -- belegt, dass fusion_schritt1/2
    tatsaechlich unterschiedliche Ergebnisse liefern koennen und dass
    fusion_vorher exakt embeddings.rrf_fuse ohne Extras entspricht."""
    k = Kanaele(
        kw_node_ids=["noise-1", "noise-2"], kw_node_scores={"noise-1": 1.0, "noise-2": 1.0},
        kw_node_text={"noise-1": "Verdichtung im Boden", "noise-2": "andere Verdichtung"},
        emb_node_ids=["target"], emb_node_scores={"target": 0.9},
    )
    v = fusion_vorher(k, 5)
    s1 = fusion_schritt1(k, "Startverzoegerung", 5)
    assert "noise-1" in v and "noise-1" not in s1, (
        "Schritt 1 haette den reinen Fragmenttreffer 'noise-1' (kein GANZES "
        "Anfragewort im Text) aus dem Stichwortkanal entfernen muessen")

    # Stichwortkanal saettigt (2 Treffer bei max_results=2). Bis zum
    # 2026-08-16 verdraengte das den reinen Bedeutungstreffer vollstaendig;
    # seit der Umstellung von _fuse_with_keyword_floor() auf
    # embeddings.fuse_semantic_led() kommt er durch, waehrend der BESTE
    # Stichworttreffer garantiert bleibt.
    kennzahl = sockel_kennzahl(k, 2)
    assert kennzahl["gesaettigt"], "Stichwortkanal hat 2 Treffer, max_results=2 -- muss saettigen"
    assert "target" in fusion_vorher(k, 2), "ohne Sockel traegt der Bedeutungskanal bei"
    assert "target" in fusion_echt(k, 2), (
        "der Produktivweg muss den besten Bedeutungstreffer auch bei "
        "gesaettigtem Stichwortkanal durchlassen -- faellt er heraus, ist "
        "die Umstellung auf fuse_semantic_led() zurueckgenommen worden")
    assert "noise-1" in fusion_echt(k, 2), (
        "und der beste Stichworttreffer bleibt garantiert (keyword_floor_size)")
    assert kennzahl["endplaetze_nur_bedeutung"] == 1, (
        "genau ein Endplatz stammt allein aus dem Bedeutungskanal ('target')")
    print("demo: ok")


if __name__ == "__main__":
    demo()
    main()
