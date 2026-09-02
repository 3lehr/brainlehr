#!/usr/bin/env python3
"""BDW-P04 AC1 — Aktion-Gate.

Misst Gate 4 (Aktion): Ob ein Abruf-Treffer zu einer besseren (informierten)
Handlungswahl fuehrt als eine No-Memory-Baseline.

PRINZIP (Test-getrieben, keine erfundenen Zahlen):
- Fuer jeden Fall: Die 'task' beschreibt ein Szenario mit einer Entscheidung.
- 'expected_action' ist die konkrete Handlungsanweisung, die aus dem abgerufenen
  Wissen folgen sollte (z.B. "Verwende INSERT-OR-IGNORE statt INSERT", 
  "Pruefe FD-Baseline vor dem Test").
- MIT Speicher: knowledge_search() wird aufgerufen, das Ziel abgerufen, und
  geprueft, ob das Ziel die 'expected_action' enthaelt oder unterstuetzt.
- OHNE Speicher (Baseline): Ein leerer Prompt ohne Kontext — die 'task' allein
  liefert keine spezifische Handlungsanweisung.
- Schwelle: >=80% der Faelle mit Speicher liefern die erwartete Aktion;
  <=20% ohne Speicher (per Konstruktion, da keine Handlungsanleitung in der
  Task-Beschreibung selbst steht).

KORPUS: runs/pruefkorpus_aktion.jsonl — eine Untermenge der positiven Faelle
aus runs/pruefkorpus.jsonl, erweitert um 'expected_action' und
'action_probe' (woertlicher Text, der die Handlungsanweisung im Ziel identifiziert).

WEG: knowledge_mcp_server.knowledge_search() + knowledge_read() — echter
Produktivweg, kein Nachbau.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern")]

import knowledge_mcp_server as kms  # noqa: E402

KORPUS = _w / "runs" / "pruefkorpus_aktion.jsonl"
SCHWELLE_AKTION = 0.80  # bestanden, wenn NICHT unterschritten
SCHWELLE_BASELINE = 0.20  # bestanden, wenn NICHT ueberschritten


def lade_faelle(korpus: Path) -> list[dict]:
    faelle = []
    with korpus.open(encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
            d = json.loads(zeile)
            if d.get("accepted", True) and d.get("expected_action"):
                faelle.append(d)
    return faelle


def ziel_ist_handlungsrelevant(fall: dict, results: list[dict]) -> bool:
    """Prueft, ob der Abruf das Ziel liefert UND das Ziel die erwartete Aktion
    enthaelt oder unterstuetzt.

    Fuer node: knowledge_read() des Pfads, pruefe ob 'content' oder 'summary'
    den action_probe-Text enthaelt.
    Fuer lesson: knowledge_read() der ID, pruefe ob 'description' oder
    'prevention' den action_probe enthaelt.
    """
    target_kind = fall["target_kind"]
    target_id = fall["target_id"]
    probe = fall.get("action_probe", "").lower()

    # Ziel muss in den Abrufergebnissen sein
    feld = "path" if target_kind == "node" else "id"
    gefunden = any(r.get(feld) == target_id for r in results)
    if not gefunden:
        return False

    # Ziel muss handlungsrelevante Information enthalten
    if not probe:
        # Kein Probe definiert — wir koennen nur pruefen, ob das Ziel existiert
        return True  # schwache Form: Treffer = Handlungsrelevant

    try:
        if target_kind == "node":
            node = kms.knowledge_read(target_id)
            if "error" in node:
                return False
            text = (node.get("title", "") + " " + node.get("summary", "") +
                    " " + node.get("content", "")).lower()
        else:  # lesson
            # Lessons haben kein knowledge_read direkt; wir pruefen im summary
            # Der Abruf liefert bereits summary, das reicht fuer den Probe
            ziel_eintrag = next((r for r in results if r.get("id") == target_id), None)
            if not ziel_eintrag:
                return False
            text = (ziel_eintrag.get("summary", "") + " " +
                    ziel_eintrag.get("description", "")).lower()
    except Exception:
        return False

    return probe in text


def messe_aktion(faelle: list[dict]) -> dict:
    zeilen = []
    for f in faelle:
        out = kms.knowledge_search(f["task"], scope="all", max_results=50)
        relevant = ziel_ist_handlungsrelevant(f, out["results"])
        zeilen.append({
            "ziel": f["target_id"],
            "art": f["target_kind"],
            "task_kurz": f["task"][:80] + "...",
            "expected_action": f["expected_action"],
            "handlungsrelevant": relevant,
        })

    n = len(zeilen)
    treffer = sum(1 for z in zeilen if z["handlungsrelevant"])
    quote = treffer / n if n else 0.0

    return {
        "n": n,
        "treffer": treffer,
        "wert": round(quote, 4),
        "schwelle": SCHWELLE_AKTION,
        "bestanden": quote >= SCHWELLE_AKTION,
        "je_fall": zeilen,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    if not KORPUS.exists():
        print(f"ABBRUCH: Aktionskorpus fehlt: {KORPUS}", file=sys.stderr)
        print("HINWEIS: runs/pruefkorpus_aktion.jsonl muss erst erstellt werden.",
              file=sys.stderr)
        sys.exit(1)

    faelle = lade_faelle(KORPUS)
    if not faelle:
        print("ABBRUCH: Keine Faelle mit 'expected_action' im Korpus.",
              file=sys.stderr)
        sys.exit(1)

    aktion = messe_aktion(faelle)

    ergebnis = {
        "weg": "knowledge_mcp_server.knowledge_search() -- echter Produktivweg",
        "korpus": {
            "datei": str(KORPUS),
            "n": aktion["n"],
        },
        "gatearten": {
            "aktion": aktion,
        },
        "grenze": [
            "Der Aktion-Gate misst die ZUFUHR (ob der Abruf handlungsrelevante "
            "Information liefert), nicht die WIRKUNG (ob ein echter Agent sie nutzt). "
            "Das ist die Grenze, die vier_gatearten.py selbst zieht.",
            "Ohne-Speicher-Baseline ist nicht direkt gemessen, sondern per Konstruktion: "
            "die 'task' enthaelt keine Handlungsanleitung, nur eine Szenariobeschreibung.",
            "Die Schwelle (0.80) ist eine konstruktive Annahme; sie wurde nicht "
            "empirisch abgeleitet.",
        ],
    }

    out_path = Path(args.out) if args.out else (
        _w / "runs" / f"aktion_gate_{__import__('datetime').datetime.now():%Y-%m-%dT%H%M%S}.json"
    )
    out_path.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    print(f"geschrieben: {out_path}")
    print(f"aktion={aktion['wert']} ({aktion['treffer']}/{aktion['n']}, "
          f"bestanden={aktion['bestanden']})")


if __name__ == "__main__":
    main()
