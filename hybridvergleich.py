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
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import embeddings  # noqa: E402
import speicher  # noqa: E402
import suchparitaet as sp  # noqa: E402

DECKEL = 10


def vektorrang(anfrage_vektor: list[float], deckel: int) -> list[str]:
    """Exakte Kosinus-Rangfolge ueber alle Vektoren -- derselbe Weg wie
    ab_vergleich_abruf.py. Kein Index, keine Naeherung: bei 3508 Zeilen ist
    das schnell genug, und es haelt die Seite als Konstante sauber. Ein
    Naeherungsindex (HNSW) waere die erste Stelle, an der die beiden
    Datenbanken doch auseinanderliefen -- deshalb hier bewusst exakt."""
    with speicher.lesen() as conn:
        zeilen = conn.execute(
            "SELECT ref_id, vector FROM knowledge_embeddings").fetchall()
    bewertet = [
        (embeddings.cosine_similarity(anfrage_vektor, embeddings.unpack_embedding(z["vector"])),
         z["ref_id"])
        for z in zeilen
    ]
    bewertet.sort(reverse=True)
    return [ref for _, ref in bewertet[:deckel]]


def messen(faelle: list[dict], rechts_lexikalisch, deckel: int = DECKEL,
           gewicht: float = 1.0) -> dict:
    einzeln = []
    ohne_vektor = 0
    for fall in faelle:
        worte = sp.stichworte(fall["prompt"])
        anfrage_vektor = embeddings.embed_text(fall["prompt"])
        if anfrage_vektor is None:
            ohne_vektor += 1
            continue
        vektoren = vektorrang(anfrage_vektor, deckel)

        links = embeddings.rrf_fuse(sp.suche_sqlite(worte, deckel), vektoren,
                                     embedding_weight=gewicht)[:deckel]
        rechts = embeddings.rrf_fuse(rechts_lexikalisch(worte, deckel), vektoren,
                                      embedding_weight=gewicht)[:deckel]
        nur_vektor = vektoren[:deckel]

        e = sp.vergleiche_fall(fall["target_id"], links, rechts)
        e["gefunden_nur_vektor"] = fall["target_id"] in nur_vektor
        einzeln.append(e)

    n = len(einzeln)
    return {
        "faelle": n,
        "ohne_anfragevektor": ohne_vektor,
        "gewicht_vektor": gewicht,
        "hybrid_links_fts5": sum(1 for e in einzeln if e["gefunden_links"]),
        "hybrid_rechts_postgres": sum(1 for e in einzeln if e["gefunden_rechts"]),
        "nur_vektor": sum(1 for e in einzeln if e["gefunden_nur_vektor"]),
        "ueberlappung_mittel": round(sum(e["ueberlappung"] for e in einzeln) / n, 3) if n else None,
        "einzeln": einzeln,
    }


def _selftest() -> None:
    import unittest.mock as mock

    faelle = [{"target_id": "Z", "prompt": "eins"}, {"target_id": "Q", "prompt": "zwei"}]
    modul = sys.modules[__name__]

    with mock.patch.object(sp, "stichworte", lambda p: [p]), \
         mock.patch.object(embeddings, "embed_text", lambda t, **kw: [1.0]), \
         mock.patch.object(modul, "vektorrang", lambda v, d: ["Z"]):

        # Die Vektorhaelfte allein findet Z, nicht Q. Eine lexikalische Seite,
        # die nichts beitraegt, darf das Ergebnis nicht verschlechtern.
        leer = lambda w, k: []
        e = messen(faelle, leer)
        assert e["hybrid_links_fts5"] == e["hybrid_rechts_postgres"] == 1, e
        assert e["nur_vektor"] == 1

        # Gegenprobe: eine lexikalische Seite, die Q beitraegt, MUSS das
        # Ergebnis heben -- sonst misst die Verschmelzung nichts.
        with mock.patch.object(sp, "suche_sqlite", lambda w, k: ["Q"]):
            e2 = messen(faelle, leer)
        assert e2["hybrid_links_fts5"] == 2, e2["hybrid_links_fts5"]
        assert e2["hybrid_rechts_postgres"] == 1, "die rechte Seite darf nicht mitprofitieren"

        # Und mit Gewicht 0 faellt die Vektorhaelfte weg (Rollback-Weg der
        # rrf_fuse) -- dann findet die leere Seite gar nichts.
        e3 = messen(faelle, leer, gewicht=0.0)
        assert e3["hybrid_rechts_postgres"] == 0, e3

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
