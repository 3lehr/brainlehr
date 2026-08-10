"""Wo verliert der Abruf die 26 Faelle, die nie in die Kandidatenliste kommen?

Misst je Pruefkorpus-Fall, an WELCHER Stelle des aktiven Abrufwegs
(haken/suchpfad_abruf.kandidaten, SUCHPFAD_ABRUF=True) das Ziel verloren geht.
Keine These, nur Stationen -- jede Station ist ein Zwischenstand desselben
Aufrufs, nicht ein nachgebauter zweiter Weg:

  S_FTS    Ziel in der FTS5-Ergebnismenge (Stichwortkanal, _or_query)?
  S_EMB    Ziel in _embedding_ranking (Bedeutungskanal, ungekappt)?
  S_FUSE   Rang des Ziels in der ungekappten RRF-Verschmelzung
  S_CAP    steht das Ziel in den ersten max_results IDs (der Kandidatenliste)?
  S_FILT   wie viele der max_results Plaetze belegen IDs, die danach ohnehin
           wegfallen (Gattung nachschlagewerk / zurueckgezogen / resolved) --
           belegte Plaetze ohne Lieferung

Aufruf: python3 kandidatendiagnose.py [--json runs/datei.json]
Selbsttest ohne Ollama: python3 kandidatendiagnose.py --selftest
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

# Liegt eine Ebene unter der Wurzel: die Wurzel muss auf den Suchpfad,
# sonst findet `import knowledge_mcp_server` nichts. Muster aus haken/.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent  # eine Ebene tiefer seit dem Umzug 2026-08-10
sys.path.insert(0, str(WURZEL / "haken"))
sys.path.insert(0, str(WURZEL))

import embeddings  # noqa: E402
import ort  # noqa: E402
from gattung_filter import SQL_ARBEITSBESTAND_NUR  # noqa: E402
from knowledge_mcp_server import _embedding_ranking, _fuse_with_keyword_floor, _or_query  # noqa: E402

KORPUS = WURZEL / "runs" / "pruefkorpus.jsonl"
MAX_RESULTS = 5  # MAX_NODES(3) + MAX_LESSONS(2) -- der Wert, den query() uebergibt


def lade_korpus(pfad: Path = KORPUS) -> list[dict]:
    return [json.loads(z) for z in pfad.read_text(encoding="utf-8").splitlines() if z.strip()]


def ziel_ref(conn: sqlite3.Connection, kind: str, target_id: str) -> str | None:
    """Der Pruefkorpus nennt Knoten per PFAD, die Kanaele arbeiten mit ID."""
    if kind == "lesson":
        return target_id
    r = conn.execute("SELECT id FROM knowledge_nodes WHERE path = ?", (target_id,)).fetchone()
    return r["id"] if r else None


def _rang(ids: list, ref: str) -> int | None:
    return ids.index(ref) + 1 if ref in ids else None


def diagnose(conn: sqlite3.Connection, text: str, kind: str, ref: str,
             query_vec: list[float] | None, max_results: int = MAX_RESULTS) -> dict:
    """Ein Fall, alle Stationen. Baugleich mit suchpfad_abruf.kandidaten() --
    Abweichungen waeren ein Messfehler, darum steht die Gegenprobe in demo()."""
    fts_query = _or_query(text)
    if not fts_query:
        return {"station": "LEERE_ANFRAGE"}
    node_ids = [r["id"] for r in conn.execute(
        "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        f"WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 {SQL_ARBEITSBESTAND_NUR} "
        "ORDER BY rank", (fts_query,))]
    lesson_ids = [r["id"] for r in conn.execute(
        "SELECT l.id FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
        "WHERE lessons_fts MATCH ? AND l.status != 'resolved' ORDER BY rank", (fts_query,))]
    keyword_ordered = embeddings.rrf_fuse(node_ids, lesson_ids, embedding_weight=1.0)

    if query_vec is not None:
        emb_node_ids = _embedding_ranking(conn, "node", query_vec, None)
        emb_lesson_ids = _embedding_ranking(conn, "lesson", query_vec, None)
    else:
        emb_node_ids, emb_lesson_ids = [], []
    embedding_ordered = embeddings.rrf_fuse(emb_node_ids, emb_lesson_ids, embedding_weight=1.0)

    fused_voll = embeddings.rrf_fuse(keyword_ordered, embedding_ordered,
                                     embedding_weight=embeddings.hybrid_retrieval_weight())
    final_ids = _fuse_with_keyword_floor(keyword_ordered, embedding_ordered, max_results)

    return {
        "fts_treffer_knoten": len(node_ids),
        "fts_treffer_lehren": len(lesson_ids),
        "rang_stichwort": _rang(keyword_ordered, ref),
        "rang_bedeutung": _rang(embedding_ordered, ref),
        "rang_verschmolzen": _rang(fused_voll, ref),
        "in_kandidatenliste": ref in final_ids,
        "final_ids": final_ids,
        "tote_plaetze": tote_plaetze(conn, final_ids),
    }


def tote_plaetze(conn: sqlite3.Connection, final_ids: list[str]) -> list[str]:
    """IDs, die einen Kandidatenplatz belegen, aber nie geliefert werden
    koennen: der Bedeutungskanal rankt ueber ALLE Vektoren (kein
    Gattungsfilter), der Nachladeblock in suchpfad_abruf laesst sie dann
    fallen. Ein belegter Platz ohne Lieferung."""
    tot = []
    for i in final_ids:
        n = conn.execute(
            "SELECT 1 FROM knowledge_nodes n WHERE n.id = ? AND n.zurueckgezogen = 0 "
            f"{SQL_ARBEITSBESTAND_NUR}", (i,)).fetchone()
        if n:
            continue
        l = conn.execute(
            "SELECT 1 FROM lessons_learned WHERE id = ? AND status != 'resolved'", (i,)).fetchone()
        if not l:
            tot.append(i)
    return tot


def station(d: dict) -> str:
    """Die eine Station, an der dieser Fall verloren geht -- erste, die zutrifft."""
    if d.get("station") == "LEERE_ANFRAGE":
        return "LEERE_ANFRAGE"
    if d["in_kandidatenliste"]:
        return "IN_LISTE"
    if d["rang_stichwort"] is None and d["rang_bedeutung"] is None:
        return "IN_KEINEM_KANAL"
    if d["rang_stichwort"] is None:
        return f"NUR_BEDEUTUNG_RANG_{d['rang_bedeutung']}"
    if d["rang_bedeutung"] is None:
        return f"NUR_STICHWORT_RANG_{d['rang_stichwort']}"
    return "IN_BEIDEN_KANAELEN_ZU_TIEF"


def main(argv: list[str]) -> None:
    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    faelle = [f for f in lade_korpus() if f.get("target_kind")]
    print(f"Bestand: {ort.DB}\nFaelle mit Ziel: {len(faelle)}  max_results={MAX_RESULTS}\n")
    ergebnisse = []
    for f in faelle:
        ref = ziel_ref(conn, f["target_kind"], f["target_id"])
        if ref is None:
            ergebnisse.append({"ziel": f["target_id"], "station": "ZIEL_NICHT_IM_BESTAND"})
            continue
        vec = embeddings.embed_text(f["task"])
        d = diagnose(conn, f["task"], f["target_kind"], ref, vec)
        d.update({"ziel": f["target_id"], "art": f["target_kind"], "station": station(d)})
        ergebnisse.append(d)
        print(f"{f['target_id']:<28} {d['station']:<32} "
              f"stichwort={d.get('rang_stichwort')} bedeutung={d.get('rang_bedeutung')} "
              f"verschmolzen={d.get('rang_verschmolzen')} tot={len(d.get('tote_plaetze', []))}")
    zaehl = Counter(e["station"].split("_RANG_")[0] for e in ergebnisse)
    print("\nStationen (Nenner {}):".format(len(ergebnisse)))
    for k, v in zaehl.most_common():
        print(f"  {k:<34} {v}")
    tote = sum(len(e.get("tote_plaetze", [])) for e in ergebnisse)
    print(f"\nTote Plaetze in den Kandidatenlisten: {tote} von {len(ergebnisse) * MAX_RESULTS} "
          f"({len(ergebnisse)} Faelle x {MAX_RESULTS})")
    if "--json" in argv:
        ziel = Path(argv[argv.index("--json") + 1])
        ziel.write_text(json.dumps(ergebnisse, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"geschrieben: {ziel}")
    conn.close()


def demo() -> None:
    """Netzlos (query_vec=None -> reiner Stichwortkanal). Belegt zweierlei:
    1) Gegenprobe in beide Richtungen: ein Knoten, dessen eigener Titel als
       Anfrage dient, steht in der Liste; Nonsenstext findet nichts.
    2) Baugleichheit mit dem echten Weg: suchpfad_abruf.kandidaten() liefert
       fuer dieselbe Anfrage dieselben IDs wie diagnose()['final_ids'] --
       waere die Messung ein Nachbau, faellt genau das auf."""
    import suchpfad_abruf  # noqa: E402
    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    zeile = conn.execute(
        "SELECT id, path, title, summary FROM knowledge_nodes WHERE path = ?",
        ("/testing/pytest",)).fetchone()
    assert zeile is not None, "Fixtur /testing/pytest fehlt"
    text = f"{zeile['title']} {zeile['summary']}"

    d = diagnose(conn, text, "node", zeile["id"], None)
    assert d["in_kandidatenliste"] is True, f"Selbsttreffer verfehlt: {d}"
    assert d["rang_stichwort"] is not None, "Stichwortkanal muss den Selbsttreffer kennen"

    n, l = suchpfad_abruf.kandidaten(conn, text, None, MAX_RESULTS)
    echt = [x["id"] for x in n] + [x["id"] for x in l]
    assert set(echt) <= set(d["final_ids"]), (
        f"Messung weicht vom echten Weg ab: echt={echt} gemessen={d['final_ids']}")

    leer = diagnose(conn, "qwfpqwfpblorx zvxjkq wibbnfrx", "node", zeile["id"], None)
    assert leer["in_kandidatenliste"] is False, "Nonsens darf nichts finden"
    assert leer["fts_treffer_knoten"] == 0, "Nonsens darf keine FTS-Treffer haben"
    conn.close()
    print("kandidatendiagnose.demo ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        demo()
    else:
        main(sys.argv)
