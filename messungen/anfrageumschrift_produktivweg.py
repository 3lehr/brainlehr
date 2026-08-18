#!/usr/bin/env python3
"""Misst V2 (Anfrageumschrift) ueber den ECHTEN Produktivweg --
knowledge_mcp_server.knowledge_search() direkt aufgerufen, nicht der reine
Bedeutungskanal aus messungen/variante_anfrageumschrift.py. Diese Funktion
ist dieselbe, die der MCP-Server fuer das Werkzeug knowledge_search benutzt
(Gattungsfilter kern/gattung_filter.SQL_ARBEITSBESTAND_NUR, Zweckprojektion,
FTS+Embedding-RRF-Fusion, Geltungspruefung) -- kein Nachbau.

Zwei Stufen, gleicher Korpus (runs/pruefkorpus.jsonl, 35 Faelle, wie in
messungen/variante_anfrageumschrift.py):
  0-ausgangslage:   query = f["task"]           (Nullmessung reproduzieren)
  2-anfrageumschrift: query = vorbereitete Umschrift aus
                      runs/v2_umschriften_2026-08-16.json (Haiku-Subagent
                      ueber Abo, siehe dortiger Docstring -- kein Paket
                      'anthropic' und kein ANTHROPIC_API_KEY in dieser
                      Umgebung, siehe demo()/main() unten: das ist ein
                      Befund, kein Umweg).

ZIELABGLEICH: target_kind=="node" -> Vergleich gegen result["path"] (NICHT
result["id"] -- L-0e0ab6, id != path bei Knoten im Pruefkorpus).
target_kind=="lesson" -> Vergleich gegen result["id"] (Lehren-IDs sind
bereits die Kennung, kein Pfadfeld).

FESTVERDRAHTET in diesem Aufbau: scope="all" (kein Projektfilter),
max_results=50 (deckt top50 ab, hoehere Raenge -> nicht_im_kanal-artig als
None gezaehlt -- siehe Grenze unten), stichtag=None (jetzt), actor/model/
session/cwd=None. Fachlogik, die genau diese Felder liest: scope steuert in
knowledge_search() die WHERE-Klausel project_id vs. 'all', max_results kappt
_fuse_with_keyword_floor() VOR der Rueckgabe (siehe Docstring dort) -- ein
Rang jenseits von max_results ist mit diesem Aufbau nicht von einem echten
Ausfall unterscheidbar, das ist eine Grenze, keine Rechenungenauigkeit.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

import knowledge_mcp_server as kms  # noqa: E402 -- der Produktivweg selbst, nicht nachgebaut

KORPUS = _w / "runs" / "pruefkorpus.jsonl"
UMSCHRIFTEN = _w / "runs" / "v2_umschriften_2026-08-16.json"
MAX_RESULTS = 50
OUT = _w / "runs" / f"anfrageumschrift_produktivweg_{__import__('datetime').datetime.now():%Y-%m-%dT%H%M%S}.json"


def lade_faelle(korpus: Path) -> list[dict]:
    """Gleiche Filterlogik wie messungen/einbettungsvarianten.py::lade_faelle
    (accepted + target_kind gesetzt) -- ergibt 35 von 45 Zeilen."""
    faelle = []
    with korpus.open(encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
            d = json.loads(zeile)
            if d.get("accepted", True) and d.get("target_kind"):
                faelle.append(d)
    return faelle


def rang_des_ziels(results: list[dict], target_kind: str, target_id: str) -> int | None:
    """1-basierter Rang in der Ergebnisliste von knowledge_search(), None
    wenn das Ziel nicht unter den max_results Treffern ist."""
    feld = "path" if target_kind == "node" else "id"
    for platz, r in enumerate(results, start=1):
        if r.get(feld) == target_id:
            return platz
    return None


def messe(faelle: list[dict], *, umschriften: dict[str, str] | None) -> dict:
    raenge = []
    for f in faelle:
        query = f["task"] if umschriften is None else umschriften[f["target_id"]]
        out = kms.knowledge_search(query, scope="all", max_results=MAX_RESULTS)
        r = rang_des_ziels(out["results"], f["target_kind"], f["target_id"])
        raenge.append({"ziel": f["target_id"], "art": f["target_kind"], "rang": r, "query": query})
    return {"raenge": raenge}


def auswertung(name: str, stufe: dict, faelle_gesamt: int) -> dict:
    gefunden = [e["rang"] for e in stufe["raenge"] if e["rang"] is not None]
    fehlt = sum(1 for e in stufe["raenge"] if e["rang"] is None)
    return {
        "name": name,
        "faelle": faelle_gesamt,
        "totalausfaelle": fehlt,
        "median_rang": int(st.median(gefunden)) if gefunden else None,
        "top5": sum(1 for r in gefunden if r <= 5),
        "top50": sum(1 for r in gefunden if r <= 50),
    }


def demo() -> None:
    """Netzloser Selbsttest der Rang- und Auswertungsfunktion -- kein DB-,
    kein Netzzugriff."""
    ergebnisse = [
        {"path": "a/b", "kind": "node"},
        {"id": "L-x", "kind": "lesson"},
        {"path": "a/c", "kind": "node"},
    ]
    assert rang_des_ziels(ergebnisse, "node", "a/c") == 3
    assert rang_des_ziels(ergebnisse, "lesson", "L-x") == 2
    assert rang_des_ziels(ergebnisse, "node", "fehlt") is None

    stufe = {"raenge": [{"rang": 1}, {"rang": 7}, {"rang": None}, {"rang": 60}]}
    a = auswertung("probe", stufe, 4)
    assert a["totalausfaelle"] == 1
    assert a["top5"] == 1
    assert a["top50"] == 2  # Rang 60 liegt ueber MAX_RESULTS/top50-Grenze
    assert a["median_rang"] == st.median([1, 7, 60])
    print("demo: ok", file=sys.stderr)


def main() -> None:
    if not KORPUS.exists():
        print(f"ABBRUCH: Pruefkorpus fehlt: {KORPUS}", file=sys.stderr)
        sys.exit(1)
    faelle = lade_faelle(KORPUS)

    # Stufe 0: Originalfrage, wie sie beim MCP-Server ankaeme.
    stufe0 = messe(faelle, umschriften=None)

    # Stufe 2: Anfrageumschrift. Kein Paket 'anthropic'/kein API-Schluessel
    # in dieser Umgebung (gemessen vor diesem Lauf) -- L-a69129 verbietet ein
    # lokales Modell als Ausweichen, deshalb wird die bereits vorbereitete
    # Umschriftendatei desselben Korpus wiederverwendet (Haiku-Subagent ueber
    # Abo, siehe messungen/variante_anfrageumschrift.py::DateiClient).
    if not UMSCHRIFTEN.exists():
        print(f"ABBRUCH: keine vorbereitete Umschriftendatei: {UMSCHRIFTEN}", file=sys.stderr)
        sys.exit(1)
    umschriften = json.loads(UMSCHRIFTEN.read_text(encoding="utf-8"))
    fehlend = [f["target_id"] for f in faelle if f["target_id"] not in umschriften]
    if fehlend:
        print(f"ABBRUCH: {len(fehlend)} Faelle ohne Umschrift, u.a. {fehlend[:3]}", file=sys.stderr)
        sys.exit(1)
    stufe2 = messe(faelle, umschriften=umschriften)

    aus0 = auswertung("0-ausgangslage", stufe0, len(faelle))
    aus2 = auswertung("2-anfrageumschrift", stufe2, len(faelle))

    ergebnis = {
        "weg": "knowledge_mcp_server.knowledge_search() -- der echte MCP-Produktivweg "
               "(Gattungsfilter kern/gattung_filter.SQL_ARBEITSBESTAND_NUR, Zweckprojektion, "
               "FTS+Embedding-RRF-Fusion), NICHT der reine Bedeutungskanal aus "
               "messungen/variante_anfrageumschrift.py",
        "korpus": str(KORPUS.relative_to(_w)),
        "umschriften_quelle": str(UMSCHRIFTEN.relative_to(_w)) + " (Haiku-Subagent ueber Abo, "
                               "vorbereitet -- kein API-Aufruf in diesem Lauf, Paket 'anthropic' "
                               "fehlt und ANTHROPIC_API_KEY ist nicht gesetzt)",
        "faelle": len(faelle),
        "max_results": MAX_RESULTS,
        "festverdrahtet": {
            "scope": "all -- knowledge_search() waehlt darueber die WHERE-Klausel "
                     "(project_id IN ('shared', scope) vs. kein Projektfilter)",
            "max_results": f"{MAX_RESULTS} -- _fuse_with_keyword_floor() kappt darauf VOR der "
                            "Rueckgabe; ein Rang jenseits davon ist nicht von einem echten "
                            "Ausfall unterscheidbar",
            "stichtag/actor/model/session/cwd": "None -- Vorgabewerte von knowledge_search(), "
                                                 "wirken nur auf Normen-Geltung bzw. Protokollierung, "
                                                 "nicht auf die Rangfolge selbst",
        },
        "grenze": [
            "misst nur EINEN Zeitpunkt (2026-08-18) gegen den aktuell laufenden Bestand -- "
            "wachsen Bestand oder Embeddings, ist der Lauf zu wiederholen",
            "35 Faelle sind klein -- ein knapper Unterschied ist kein Ergebnis",
            "Umschrift-Stufe nutzt eine vorbereitete Datei, keinen Live-API-Aufruf -- "
            "Umschreibedauer/Betriebskosten sind hier NICHT gemessen",
            "Rang jenseits max_results=50 wird als Totalausfall gezaehlt, auch wenn das Ziel "
            "z.B. auf Rang 51 gelandet waere -- keine Unterscheidung zwischen 'nicht im Kanal' "
            "und 'knapp ausserhalb des Fensters'",
        ],
        "stufe_0_ausgangslage": aus0,
        "stufe_2_anfrageumschrift": aus2,
        "roh": {"stufe_0": stufe0["raenge"], "stufe_2": stufe2["raenge"]},
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"geschrieben: {OUT}")
    for aus in (aus0, aus2):
        print(f"{aus['name']:20} top5={aus['top5']}/{aus['faelle']}  top50={aus['top50']}  "
              f"median={aus['median_rang']}  totalausfaelle={aus['totalausfaelle']}")


if __name__ == "__main__":
    demo()
    main()
