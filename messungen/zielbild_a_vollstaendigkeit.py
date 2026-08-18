#!/usr/bin/env python3
"""BDW-P05-AC1: „Der Kern reproduziert in mindestens 95 % des festgelegten
Prüfkorpus Aussage, Quelle, Status und Gültigkeit innerhalb eines Abrufs."

Misst nicht eine Zahl, sondern VIER je Fall -- und dann, wie oft alle vier
zugleich vorliegen. Das ist der Unterschied zur Trefferquote: Ein Abruf, der
das richtige Ziel findet, aber nicht sagt, woher es stammt und ob es noch
gilt, erfuellt dieses Kriterium nicht.

ANLASS, 2026-08-18: `BDW-P05` steht seit dem Katalogschnitt auf NOT RUN.
Zwei Messungen desselben Tages legen nahe, dass es nicht erfuellt ist --
die Trefferquote liegt bei 20 %, und `BDW-R05` ist FAIL, weil die Antwort
weder `norm_rang` noch `gilt_ab` noch `source` mitfuehrt. Nahelegen ist
aber nicht messen: dieses Werkzeug rechnet es aus, statt es abzuleiten.

WEG: `knowledge_mcp_server.knowledge_search()`, derselbe Produktivweg wie
`messungen/vier_gatearten.py`. Kein Nachbau.

Aufruf:
    python3 zielbild_a_vollstaendigkeit.py [--out DATEI]
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "kern")]

KORPUS = WURZEL / "runs" / "pruefkorpus.jsonl"
SCHWELLE = 0.95  # steht so im AC, nicht von hier gewaehlt
K = 5


def _faelle() -> list[dict]:
    zeilen = [json.loads(z) for z in KORPUS.read_text(encoding="utf-8").splitlines() if z.strip()]
    return [f for f in zeilen if f.get("category") != "negative"]


def _treffer(srv, aufgabe: str) -> dict:
    antwort = srv.knowledge_search(query=aufgabe, scope="all", max_results=50)
    if isinstance(antwort, str):
        try:
            antwort = json.loads(antwort)
        except ValueError:
            return {"results": []}
    return antwort or {"results": []}


def _bestandteile(ergebnis: dict, ziel_id: str) -> dict:
    """Die vier Bestandteile des AC, je einzeln geprueft.

    AUSSAGE  -- steht das Ziel unter den ersten K?
    QUELLE   -- traegt der Treffer ein Herkunftsfeld?
    STATUS   -- traegt er eine Normentscheidung oder einen Rang?
    GELTUNG  -- traegt er gilt_ab/gilt_bis?

    Geprueft wird der TREFFER, nicht die Datenbank: Die Frage des AC ist,
    was innerhalb eines Abrufs beim Fragenden ankommt."""
    treffer = (ergebnis.get("results") or [])[:K]
    ziel = next((t for t in treffer if t.get("id") == ziel_id or t.get("path") == ziel_id), None)
    if ziel is None:
        return {"aussage": False, "quelle": False, "status": False, "geltung": False}
    return {
        "aussage": True,
        "quelle": bool(ziel.get("source") or ziel.get("quelle")),
        "status": ziel.get("norm_rang") is not None or bool(ziel.get("norm_entscheidung")),
        "geltung": bool(ziel.get("gilt_ab") or ziel.get("gilt_bis")),
    }


def messe(out: Path | None = None) -> dict:
    import knowledge_mcp_server as srv

    faelle = _faelle()
    je_bestandteil = {"aussage": 0, "quelle": 0, "status": 0, "geltung": 0}
    vollstaendig = 0
    einzeln = []

    for fall in faelle:
        ziel = fall.get("target_id") or fall.get("target_label")
        b = _bestandteile(_treffer(srv, fall.get("task", "")), ziel)
        for name, wert in b.items():
            je_bestandteil[name] += int(wert)
        if all(b.values()):
            vollstaendig += 1
        einzeln.append({"ziel": ziel, **b})

    n = len(faelle)
    ergebnis = {
        "zeit": datetime.now(timezone.utc).isoformat(),
        "weg": "knowledge_mcp_server.knowledge_search() -- Produktivweg, kein Nachbau",
        "korpus": {"datei": str(KORPUS.relative_to(WURZEL)), "n": n,
                   "hinweis": "nur Positivfaelle; category=negative ausgeschlossen"},
        "kriterium": ("BDW-P05-AC1 woertlich: Aussage, Quelle, Status UND Gueltigkeit "
                      "innerhalb EINES Abrufs, in mindestens 95 % der Faelle. Geprueft wird, "
                      "was beim Fragenden ankommt, nicht was in der Datenbank steht."),
        "schwelle": SCHWELLE,
        "je_bestandteil": {k: {"treffer": v, "quote": round(v / n, 4)} for k, v in je_bestandteil.items()},
        "vollstaendig": {"treffer": vollstaendig, "quote": round(vollstaendig / n, 4)},
        "bestanden": vollstaendig / n >= SCHWELLE,
        "grenze": [
            "K=5 -- ein Ziel auf Rang 6 zaehlt als nicht reproduziert.",
            "Geprueft wird die Trefferstruktur, nicht der Datenbankinhalt: die Felder "
            "koennen vorhanden sein und trotzdem nicht ausgeliefert werden (BDW-R05, FAIL).",
            "Momentaufnahme eines wachsenden Bestands.",
        ],
        "einzeln": einzeln,
    }

    ziel = out or (WURZEL / "runs" /
                   f"zielbild_a_vollstaendigkeit_{datetime.now().strftime('%Y-%m-%dT%H%M%S')}.json")
    ziel.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    ergebnis["datei"] = str(ziel)
    return ergebnis


def main() -> int:
    out = None
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    e = messe(out)
    print(f"BDW-P05 ueber {e['korpus']['n']} Faelle, Weg: Produktivweg")
    for name, w in e["je_bestandteil"].items():
        print(f"  {name:9} {w['treffer']:2}/{e['korpus']['n']}  = {w['quote']:.1%}")
    print(f"  ALLE VIER {e['vollstaendig']['treffer']:2}/{e['korpus']['n']}  = "
          f"{e['vollstaendig']['quote']:.1%}  (Schwelle {SCHWELLE:.0%}) -> "
          f"{'bestanden' if e['bestanden'] else 'NICHT bestanden'}")
    print(f"  {e['datei']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
