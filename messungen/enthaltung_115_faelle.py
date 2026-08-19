#!/usr/bin/env python3
"""Auftrag 2026-08-19 (Frage 115): Fuer die drei Faelle aus
runs/enthaltungsschwelle_kosinus_abrufweg.json::je_frage_einschlaegig mit
bester_kosinus < 0.55 -- prueft, ob (a) der Bestand zur Frage wirklich wenig
fuehrt (Enthaltung richtig) oder (b) das Ziel einschlaegig ist, aber
schlecht eingebettet/gefunden wird (KEIN Schwellenproblem).

WEG: keine eigene Ranglogik. Zerlegt haken/suchpfad_abruf.py::kandidaten()
in seine Bausteine (_or_query, _stichwortkanal_blind, direkte FTS-Abfragen,
_embedding_ranking, embeddings.rrf_fuse) -- WOERTLICH dieselben Aufrufe wie
dort, nur ohne die max_results-Kappung am Ende, weil hier der VOLLE Rang
des Ziels gebraucht wird (kandidaten() liefert nur die Top max_results nach
der Fusion, das Ziel kann weiter hinten liegen).

Je Fall wird ermittelt:
  - keyword_rang: Position des Ziels in der (ungekappten) FTS-Trefferliste
    dieser Gattung (Knoten ODER Lehre, je nachdem was 'ziel' ist), 1-basiert.
    None = kein FTS-Treffer ueberhaupt (Stichwortkanal blind fuer das Ziel).
  - bedeutungs_rang / bedeutungs_kosinus_ziel: Position und ROHER Kosinus
    des Ziels im Bedeutungskanal (ueber ALLE erlaubten Vektoren derselben
    Gattung, nicht nur die Top max_results).
  - fusion_rang: Position des Ziels in der vollen (ungekappten) RRF-Fusion
    aus Stichwort- und Bedeutungskanal -- das ist der Rang, den
    kandidaten() intern erreicht, bevor es auf max_results kappt.
  - top_statt_ziel: die ersten 5 Eintraege der Fusion, falls sie NICHT das
    Ziel sind (Titel/Beschreibung gekuerzt).

SCHNAPPSCHUSS: genau einer (kern/schnappschuss.py::festhalten()). ABWEICHUNG
VOM AUFTRAG (Auflage "BEIDE Attribute pinnen"): nur kms.DB_PATH ist gepinnt.
haken/knowledge_recall_hook.py stand beim Schreiben dieses Laufs uncommitted
mit einem SyntaxError da (s. Kommentar beim Import unten) -- eine TABU-Datei,
vermutlich WIP einer anderen Sitzung. Das Modul wird darum gar nicht
importiert; es wird ohnehin nirgends aufgerufen (nur der Pin war vorgesehen,
und der ist fuer DIESEN Pfad laut Docstring von messungen/enthaltungsschwelle_
kosinus_abrufweg.py "strenggenommen wirkungslos", weil kandidaten() und die
hier wiederverwendeten Bausteine conn als Parameter nehmen, kein Modul-
Attribut lesen). Schnappschuss am Ende weggeraeumt.

Auftrag ausdruecklich: KEINE Empfehlung fuer eine Schwellenaenderung.

Aufruf:
    python3 messungen/enthaltung_115_faelle.py --selbsttest
    python3 messungen/enthaltung_115_faelle.py --out runs/enthaltung_115_faelle.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken"), str(_w / "messungen")]

import embeddings  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402 -- nur fuer den Pin + importierte Bausteine
import speicher  # noqa: E402
# knowledge_recall_hook (haken/knowledge_recall_hook.py) wird NICHT importiert:
# beim Schreiben dieses Laufs stand die Datei uncommitted mit einem
# SyntaxError da (Zeile ~2283, "global DB" nach erster Verwendung von DB im
# selben Block, in _selbsttest()) -- eine TABU-Datei (Auftrag), die
# vermutlich eine andere, noch laufende Sitzung gerade bearbeitet. Diese
# Messung ruft nichts aus dem Modul auf (nur der DB-Pin war vorgesehen, s.
# Docstring von messungen/enthaltungsschwelle_kosinus_abrufweg.py: "fuer
# DIESEN Pfad strenggenommen wirkungslos") -- der Pin entfaellt ersatzlos,
# kms.DB_PATH bleibt gepinnt. Abweichung wird im Ergebnis-JSON genannt.
from gattung_filter import SQL_ARBEITSBESTAND_NUR  # noqa: E402
from schnappschuss import festhalten  # noqa: E402
from suchpfad_abruf import _erlaubte_ids  # noqa: E402 -- wiederverwendet, kein Nachbau

QUELLE = _w / "runs" / "enthaltungsschwelle_kosinus_abrufweg.json"
SCHWELLE = 0.55


def _node_id(conn, pfad_oder_id: str) -> str | None:
    r = conn.execute(
        "SELECT id FROM knowledge_nodes WHERE (path = ? OR id = ?) AND zurueckgezogen = 0",
        (pfad_oder_id, pfad_oder_id),
    ).fetchone()
    return r["id"] if r else None


def _lesson_id(conn, kennung: str) -> str | None:
    r = conn.execute("SELECT id FROM lessons_learned WHERE id = ?", (kennung,)).fetchone()
    return r["id"] if r else None


def _titel(conn, art: str, wid: str) -> str:
    if art == "node":
        r = conn.execute("SELECT path, title FROM knowledge_nodes WHERE id = ?", (wid,)).fetchone()
        return f"{r['path']} -- {r['title']}" if r else wid
    r = conn.execute("SELECT description FROM lessons_learned WHERE id = ?", (wid,)).fetchone()
    return f"L-{wid} -- {(r['description'] or '')[:80]}" if r else f"L-{wid}"


def diagnose(conn, frage: str, art: str, ziel_id: str) -> dict:
    """art: 'node' oder 'lesson' -- die Gattung, in der ziel_id lebt."""
    fts_query = kms._or_query(frage)
    blind = kms._stichwortkanal_blind(frage)

    # Stichwortkanal: dieselbe Abfrage wie suchpfad_abruf.kandidaten(),
    # ungekappt -- Reihenfolge ist die FTS-Rangfolge (ORDER BY rank).
    if blind or not fts_query:
        kw_ids = []
    elif art == "node":
        kw_ids = [r["id"] for r in conn.execute(
            "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
            f"WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR} "
            "ORDER BY rank", (fts_query,))]
    else:
        kw_ids = [r["id"] for r in conn.execute(
            "SELECT l.id FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
            "WHERE lessons_fts MATCH ? AND l.status != 'resolved' ORDER BY rank", (fts_query,))]

    try:
        keyword_rang = kw_ids.index(ziel_id) + 1
    except ValueError:
        keyword_rang = None

    # Bedeutungskanal: _embedding_ranking() ueber ALLE erlaubten Vektoren
    # derselben Gattung -- kein max_results-Deckel, das ist der volle Rang.
    query_vec = embeddings.embed_text(frage)
    erl_nodes, erl_lessons = _erlaubte_ids(conn)
    werte: list = []
    if query_vec is not None:
        emb_ids = kms._embedding_ranking(conn, art, query_vec,
                                          erl_nodes if art == "node" else erl_lessons, werte)
    else:
        emb_ids = []
    if ziel_id in emb_ids:
        idx = emb_ids.index(ziel_id)
        bedeutungs_rang = idx + 1
        bedeutungs_kosinus_ziel = round(werte[idx], 4)
    else:
        bedeutungs_rang = None
        bedeutungs_kosinus_ziel = None

    # Volle Fusion (dieselbe Funktion wie kandidaten(), aber ungekappt) --
    # der andere Kanal (Lehre statt Knoten bzw. umgekehrt) traegt zur
    # RANGPOSITION des Ziels in dieser einen Gattungsliste nichts bei,
    # rrf_fuse() selbst arbeitet je Gattung getrennt (kandidaten() ruft es
    # separat fuer node/lesson auf, s. dortiger Code) -- ein einzelliger
    # Aufruf reicht darum fuer den Rang INNERHALB dieser Gattung.
    fusion_ids = embeddings.rrf_fuse(kw_ids, emb_ids, embedding_weight=embeddings.hybrid_retrieval_weight())
    try:
        fusion_rang = fusion_ids.index(ziel_id) + 1
    except ValueError:
        fusion_rang = None

    top_statt_ziel = [_titel(conn, art, i) for i in fusion_ids[:5] if i != ziel_id][:5]

    if keyword_rang and bedeutungs_rang:
        kanal = "beide"
    elif keyword_rang:
        kanal = "nur_stichwort"
    elif bedeutungs_rang:
        kanal = "nur_bedeutung"
    else:
        kanal = "keiner"

    return {
        "keyword_rang": keyword_rang,
        "keyword_treffer_gesamt": len(kw_ids),
        "bedeutungs_rang": bedeutungs_rang,
        "bedeutungs_kosinus_ziel": bedeutungs_kosinus_ziel,
        "bedeutungs_kandidaten_gesamt": len(emb_ids),
        "fusion_rang": fusion_rang,
        "kanal_trifft": kanal,
        "top_statt_ziel": top_statt_ziel,
    }


def _selbsttest() -> None:
    """Selbsttest von diagnose() gegen einen frei erfundenen In-Memory-Bestand
    (drei Knoten, ein FTS-passendes Wort, kein Ollama noetig -- query_vec
    ueber embed_text ist None ohne Netz/Ollama-Prozess, das ist HIER extra
    ueberschrieben, damit der Test auch ohne Ollama laeuft)."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    schema = (_w / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)

    def _n(id_, pfad, titel, summary):
        conn.execute(
            "INSERT INTO knowledge_nodes(id, path, title, summary, gattung, zurueckgezogen, "
            "updated_at, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund, source) "
            "VALUES (?,?,?,?,'arbeitsbestand',0,'2026-01-01','keine_norm','selbsttest',"
            "'Testdaten, kein Fakt','selbsttest')",
            (id_, pfad, titel, summary))

    _n("aaa11111", "/test/treffer", "Fahrtenbuch Reifendruck", "Reifendruck pruefen im Fahrtenbuch")
    _n("bbb22222", "/test/ablenker", "Steuererklaerung", "Belege sammeln fuer die Steuer")
    conn.commit()

    def _vec(id_):
        import struct
        # Zwei orthogonale 4er-Vektoren -- eindeutig unterscheidbar per Kosinus.
        v = [1.0, 0.0, 0.0, 0.0] if id_ == "aaa11111" else [0.0, 1.0, 0.0, 0.0]
        conn.execute(
            "INSERT INTO knowledge_embeddings(kind, ref_id, model, vector, updated_at) "
            "VALUES ('node',?,?,?,'2026-01-01')",
            (id_, embeddings.DEFAULT_EMBED_MODEL, struct.pack("<4f", *v)))

    _vec("aaa11111")
    _vec("bbb22222")
    conn.commit()

    import unittest.mock as mock
    with mock.patch.object(embeddings, "embed_text", return_value=[1.0, 0.0, 0.0, 0.0]):
        d = diagnose(conn, "Reifendruck Fahrtenbuch", "node", "aaa11111")
    assert d["keyword_rang"] == 1, d
    assert d["bedeutungs_rang"] == 1, d
    assert d["bedeutungs_kosinus_ziel"] == 1.0, d
    assert d["fusion_rang"] == 1, d
    assert d["kanal_trifft"] == "beide", d
    assert "aaa11111" not in "".join(d["top_statt_ziel"]), d  # Ziel selbst nie in top_statt_ziel

    # Negativfall: eine Anfrage, die WEDER per Stichwort noch per Bedeutung
    # zum Ziel passt (orthogonaler Vektor, kein gemeinsames Wort) -> beide
    # Raenge None, Kanal 'keiner'.
    with mock.patch.object(embeddings, "embed_text", return_value=[0.0, 0.0, 1.0, 0.0]):
        d2 = diagnose(conn, "Voellig unbeteiligtes Thema Wetterbericht", "node", "aaa11111")
    assert d2["keyword_rang"] is None, d2
    assert d2["bedeutungs_rang"] is None or d2["bedeutungs_kosinus_ziel"] <= 0.0, d2
    assert d2["kanal_trifft"] in ("keiner", "nur_bedeutung"), d2

    conn.close()
    print("selbsttest: ok", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.selbsttest:
        _selbsttest()
        return

    if not QUELLE.exists():
        print(f"ABBRUCH: Quelle fehlt: {QUELLE}", file=sys.stderr)
        sys.exit(1)
    d = json.loads(QUELLE.read_text(encoding="utf-8"))
    zeilen_je_ziel = {z["ziel"]: z for z in d["je_frage_einschlaegig"]}
    unter_schwelle = [z for z in d["je_frage_einschlaegig"] if z["bester_kosinus"] < SCHWELLE]
    if len(unter_schwelle) != 3:
        print(f"BEFUND: {len(unter_schwelle)} statt 3 Faelle unter {SCHWELLE} -- Quelle hat sich "
              "geaendert, Fallliste unten manuell gegenpruefen.", file=sys.stderr)

    # Positivkontrolle: ein einschlaegiger Fall MIT hohem Wert (>0.60), aus
    # derselben Quelle. Absteigend sortiert, NICHT nur der hoechste -- der
    # Bestand aendert sich zwischen dem Quelllauf (09:47) und diesem Lauf
    # (Dedup/Konsolidierung von Lehren, s. CLAUDE.md "Wissen festhalten").
    # Der erste Kandidat, der in DIESEM Schnappschuss noch existiert, wird
    # verwendet; uebersprungene werden benannt, nicht verschwiegen.
    ueber_sortiert = sorted(
        (z for z in d["je_frage_einschlaegig"] if z["bester_kosinus"] > 0.60),
        key=lambda z: -z["bester_kosinus"])

    stand = festhalten()
    orig_kms_db = kms.DB_PATH
    kms.DB_PATH = stand.pfad
    print(f"messstand: {stand.kennung} ({stand.pfad})", file=sys.stderr)

    ergebnisse = []
    nicht_beantwortet = []
    try:
        with speicher.lesen(stand.pfad) as conn:
            # Positivkontrolle zuerst aufloesen (kann uebersprungene Kandidaten
            # erzeugen, die NICHT in faelle_zu_pruefen/nicht_beantwortet
            # landen -- sie sind kein Teil des Auftrags, nur Beiwerk fuer den
            # Vergleichsfall, und werden separat protokolliert).
            positivkontrolle_ziel = None
            positivkontrolle_uebersprungen = []
            for z in ueber_sortiert:
                zid = _node_id(conn, z["ziel"])
                if not zid and z["ziel"].startswith("L-"):
                    zid = _lesson_id(conn, z["ziel"][2:])
                if zid:
                    positivkontrolle_ziel = z["ziel"]
                    break
                positivkontrolle_uebersprungen.append(z["ziel"])

            faelle_zu_pruefen = [z["ziel"] for z in unter_schwelle]
            if positivkontrolle_ziel:
                faelle_zu_pruefen.append(positivkontrolle_ziel)

            for ziel in faelle_zu_pruefen:
                quelle_zeile = zeilen_je_ziel.get(ziel)
                if quelle_zeile is None:
                    nicht_beantwortet.append(f"{ziel}: keine Quellzeile in {QUELLE.name} gefunden")
                    continue
                frage = quelle_zeile["frage"]
                bester_kosinus_lauf = quelle_zeile["bester_kosinus"]

                nid = _node_id(conn, ziel)
                art = None
                wid = None
                if nid:
                    art, wid = "node", nid
                elif ziel.startswith("L-"):
                    lid = _lesson_id(conn, ziel[2:])
                    if lid:
                        art, wid = "lesson", lid
                if art is None:
                    nicht_beantwortet.append(f"{ziel}: in diesem Schnappschuss weder als Knoten "
                                              "noch als Lehre auffindbar (zurueckgezogen? Pfad "
                                              "geaendert?) -- keine Diagnose moeglich")
                    continue

                diag = diagnose(conn, frage, art, wid)
                rolle = "positivkontrolle" if ziel == positivkontrolle_ziel else "unter_schwelle"
                ergebnisse.append({
                    "rolle": rolle,
                    "ziel": ziel,
                    "ziel_titel": _titel(conn, art, wid),
                    "frage": frage,
                    "bester_kosinus_lauf_2026-08-19": bester_kosinus_lauf,
                    **diag,
                })
    finally:
        kms.DB_PATH = orig_kms_db
        shutil.rmtree(stand.pfad.parent, ignore_errors=True)

    ausgabe = {
        "schnappschuss": stand.kennung,
        "schwelle_gepruefte": SCHWELLE,
        "quelle": str(QUELLE.relative_to(_w)),
        "weg": "Bausteine aus haken/suchpfad_abruf.py::kandidaten() (kein Nachbau, kein Kappen "
               "auf max_results -- voller Rang des Ziels je Gattung)",
        "faelle": ergebnisse,
        "positivkontrolle_uebersprungen": positivkontrolle_uebersprungen,
        "nicht_beantwortet": nicht_beantwortet,
        "abweichung_vom_auftrag": "Nur kms.DB_PATH gepinnt, NICHT hook.DB (Auflage verlangte "
                                   "beide): haken/knowledge_recall_hook.py stand beim Lauf "
                                   "uncommitted mit einem SyntaxError da (~Zeile 2283, 'global "
                                   "DB' nach vorheriger Verwendung von DB im selben Block) -- "
                                   "TABU-Datei, nicht angefasst, vermutlich WIP einer anderen "
                                   "Sitzung. Das Modul wird von diesem Skript nirgends "
                                   "aufgerufen, der Pin war ohnehin nur Auflagenerfuellung.",
        "hinweis": "Keine Schwellenaenderung empfohlen. 'kanal_trifft' beschreibt nur, ob "
                   "Stichwort- bzw. Bedeutungskanal das ZIEL ueberhaupt in ihre je eigene "
                   "Rangliste aufnehmen -- fusion_rang ist der volle Rang nach RRF-Fusion "
                   "beider Kanaele, wie ihn kandidaten() vor der max_results-Kappung erreicht.",
    }

    out_pfad = Path(args.out) if args.out else _w / "runs" / "enthaltung_115_faelle.json"
    out_pfad.parent.mkdir(parents=True, exist_ok=True)
    out_pfad.write_text(json.dumps(ausgabe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
