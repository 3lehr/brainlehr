#!/usr/bin/env python3
"""Der Betrieb sucht hybrid -- also wird auch hybrid verglichen.

ANLASS: Die lexikalische Messung vom 2026-08-11 (suchparitaet.py) ergab FTS5
9 von 35 gegen pg_trgm 7 von 35. Beides sind Halbmessungen: der echte Abruf
verschmilzt Stichwortsuche und Vektorsuche (embeddings.rrf_fuse). Wer aus 9
gegen 7 eine Entscheidung ableitet, entscheidet ueber eine Haelfte.

DER AUFBAU NUTZT AUS, DASS DIE VEKTOREN EINE KONSTANTE SIND: 3508 Vektoren,
bge-m3, 1024 Dimensionen, liegen fertig im Bestand. Sie muessen fuer einen
Datenbankwechsel nicht neu gerechnet werden -- nur gespiegelt. Und weil beide
Seiten dieselben Zahlen benutzen und exakt (nicht genaehert) suchen, ist die
Vektorrangfolge auf beiden Seiten IDENTISCH. Sie wird deshalb je Fall EINMAL
berechnet und beiden Seiten gegeben.

Daraus folgt die Aussagekraft dieses Vergleichs, und auch seine Grenze:
gemessen wird, was die lexikalische Haelfte im verschmolzenen Ergebnis noch
ausmacht. Ein Unterschied hier kommt ausschliesslich aus der Stichwortsuche --
alles andere ist gleich gehalten. Das ist der saubere Schnitt; es ist NICHT
die Aussage "so gut waere der Betrieb nach dem Umzug", denn der Betrieb kappt
zusaetzlich per Rauschteppich (_radar_select), filtert nach Vertrauen und
Geltungsbereich.

Neu gerechnet wird nur die Einbettung der ANFRAGE (35 Aufrufe an bge-m3) --
die gibt es noch nicht, weil die Prueffaelle neu sind.

Aufruf:
    python3 hybridvergleich.py --korpus runs/pruefkorpus_v2.json --dsn brainlehr_probe
    python3 hybridvergleich.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
ROOT = WURZEL.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "haken"))
sys.path.insert(0, str(ROOT / "kern"))
sys.path.insert(0, str(WURZEL))

import embeddings  # noqa: E402
import speicher  # noqa: E402
import suchparitaet as sp  # noqa: E402

DECKEL = 10


def vektorrang(anfrage_vektor: list[float], deckel: int) -> dict[str, list[str]]:
    """Exakte Kosinus-Rangfolge, GETRENNT nach Gattung -- die Spalte `kind`
    fuehrt 2190 Knoten und 1318 Lehren. Getrennt aus demselben Grund wie bei
    der Stichwortsuche: der Betrieb deckelt getrennt, und eine gemeinsame
    Liste wuerde die kleinere Gattung verdraengen.

    Kein Index, keine Naeherung: bei 3508 Zeilen schnell genug, und es haelt
    die Vektorseite als Konstante sauber. Ein Naeherungsindex (HNSW) waere die
    erste Stelle, an der die beiden Datenbanken doch auseinanderliefen.
    """
    with speicher.lesen() as conn:
        zeilen = conn.execute(
            "SELECT kind, ref_id, vector FROM knowledge_embeddings").fetchall()
    nach_art: dict[str, list[tuple[float, str]]] = {"knoten": [], "lehre": []}
    for z in zeilen:
        art = "lehre" if z["kind"] == "lesson" else "knoten"
        nach_art[art].append(
            (embeddings.cosine_similarity(anfrage_vektor,
                                          embeddings.unpack_embedding(z["vector"])),
             z["ref_id"]))
    for art in nach_art:
        nach_art[art].sort(reverse=True)
    return {art: [ref for _, ref in liste[:deckel]] for art, liste in nach_art.items()}


def fall_vorbereiten(fall: dict, rechts_lexikalisch, kandidaten: int) -> dict | None:
    """Die teuren Teile EINMAL je Fall: Anfrage einbetten, Kosinus ueber alle
    3508 Vektoren, beide Stichwortsuchen. Die Verschmelzung ist danach reine
    Rechnung und kann fuer beliebig viele Gewichte wiederholt werden."""
    anfrage_vektor = embeddings.embed_text(fall["prompt"])
    if anfrage_vektor is None:
        return None
    worte = sp.stichworte(fall["prompt"])
    return {
        "ziel": fall["target_id"],
        "gattung": sp.gattung_von(fall),
        "vektoren": vektorrang(anfrage_vektor, kandidaten),
        "links_lex": sp.suche_sqlite(worte, kandidaten),
        "rechts_lex": rechts_lexikalisch(worte, kandidaten),
    }


def messen(faelle: list[dict], rechts_lexikalisch, gewicht: float = 1.0,
           vorbereitet: list[dict] | None = None, kandidaten: int = 30) -> dict:
    """Verschmelzung und Deckel je GATTUNG -- ein Lehren-Ziel gegen die besten
    7 Lehren, ein Knoten-Ziel gegen die besten 10 Knoten, so wie im Betrieb.

    Kandidaten werden tiefer geholt als der Deckel: sonst kann ein Gewicht
    nichts bewegen, weil beide Listen schon vor der Verschmelzung beschnitten
    waeren. Der Deckel gilt erst NACH der Verschmelzung."""
    ohne_vektor = 0
    if vorbereitet is None:
        vorbereitet = []
        for fall in faelle:
            v = fall_vorbereiten(fall, rechts_lexikalisch, kandidaten)
            if v is None:
                ohne_vektor += 1
            else:
                vorbereitet.append(v)

    einzeln = []
    for v in vorbereitet:
        g = v["gattung"]
        k = sp.deckel_fuer(g)
        vek = v["vektoren"].get(g, [])
        links = embeddings.rrf_fuse(v["links_lex"].get(g, []), vek,
                                     embedding_weight=gewicht)[:k]
        rechts = embeddings.rrf_fuse(v["rechts_lex"].get(g, []), vek,
                                      embedding_weight=gewicht)[:k]
        e = sp.vergleiche_fall(v["ziel"], links, rechts)
        e["gattung"] = g
        e["gefunden_nur_vektor"] = v["ziel"] in vek[:k]
        e["gefunden_nur_lexikalisch"] = v["ziel"] in v["links_lex"].get(g, [])[:k]
        einzeln.append(e)

    n = len(einzeln)
    return {
        "faelle": n,
        "ohne_anfragevektor": ohne_vektor,
        "gewicht_vektor": gewicht,
        "hybrid_links_fts5": sum(1 for e in einzeln if e["gefunden_links"]),
        "hybrid_rechts_postgres": sum(1 for e in einzeln if e["gefunden_rechts"]),
        "nur_vektor": sum(1 for e in einzeln if e["gefunden_nur_vektor"]),
        "nur_lexikalisch": sum(1 for e in einzeln if e["gefunden_nur_lexikalisch"]),
        "lexikalisch_rettet": [e["ziel"] for e in einzeln
                                if e["gefunden_links"] and not e["gefunden_nur_vektor"]],
        "vektor_rettet": [e["ziel"] for e in einzeln
                           if e["gefunden_nur_vektor"] and not e["gefunden_nur_lexikalisch"]],
        "ueberlappung_mittel": round(sum(e["ueberlappung"] for e in einzeln) / n, 3) if n else None,
        "einzeln": einzeln,
        "vorbereitet": vorbereitet,
    }


def _selftest() -> None:
    import unittest.mock as mock

    faelle = [{"target_id": "L-Z", "prompt": "eins", "target_kind": "lesson"},
              {"target_id": "L-Q", "prompt": "zwei", "target_kind": "lesson"}]
    modul = sys.modules[__name__]
    leer = lambda w, k: {"knoten": [], "lehre": []}

    with mock.patch.object(sp, "stichworte", lambda p: [p]), \
         mock.patch.object(embeddings, "embed_text", lambda t, **kw: [1.0]), \
         mock.patch.object(modul, "vektorrang", lambda v, d: {"knoten": [], "lehre": ["L-Z"]}):

        # Vektorhaelfte findet L-Z, nicht L-Q. Eine lexikalische Seite, die
        # nichts beitraegt, darf das Ergebnis nicht verschlechtern.
        with mock.patch.object(sp, "suche_sqlite", leer):
            e = messen(faelle, leer)
        assert e["hybrid_links_fts5"] == e["hybrid_rechts_postgres"] == 1, e
        assert e["nur_vektor"] == 1 and e["nur_lexikalisch"] == 0

        # Gegenprobe: eine lexikalische Seite, die L-Q beitraegt, MUSS heben --
        # und der Fall muss in 'lexikalisch_rettet' auftauchen.
        with mock.patch.object(sp, "suche_sqlite", lambda w, k: {"knoten": [], "lehre": ["L-Q"]}):
            e2 = messen(faelle, leer)
        assert e2["hybrid_links_fts5"] == 2, e2["hybrid_links_fts5"]
        assert e2["hybrid_rechts_postgres"] == 1, "die rechte Seite darf nicht mitprofitieren"
        assert e2["lexikalisch_rettet"] == ["L-Q"], e2["lexikalisch_rettet"]

        # Mit Gewicht 0 faellt die Vektorhaelfte weg (Rollback-Weg der rrf_fuse).
        with mock.patch.object(sp, "suche_sqlite", leer):
            e3 = messen(faelle, leer, gewicht=0.0)
        assert e3["hybrid_links_fts5"] == 0, e3

    print("selftest ok (3 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--korpus", type=Path)
    p.add_argument("--dsn")
    p.add_argument("--variante", default="kurzfeld")
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return
    if not (a.korpus and a.dsn):
        p.error("--korpus und --dsn werden gebraucht")

    from suche_postgres import suche_bauen
    faelle = [f for f in json.loads(a.korpus.read_text(encoding="utf-8")).get("cases", [])
              if f.get("target_id") and f.get("prompt")]
    ergebnis = messen(faelle, suche_bauen(a.dsn, a.variante))

    print(f"Faelle: {ergebnis['faelle']} (ohne Anfragevektor: {ergebnis['ohne_anfragevektor']})")
    print(f"HYBRID  FTS5+Vektor: {ergebnis['hybrid_links_fts5']} | "
          f"pg_trgm({a.variante})+Vektor: {ergebnis['hybrid_rechts_postgres']}")
    print(f"nur Vektor (dieselbe Konstante auf beiden Seiten): {ergebnis['nur_vektor']}")
    print(f"Ueberlappung der verschmolzenen Listen: {ergebnis['ueberlappung_mittel']}")
    if a.out:
        a.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
