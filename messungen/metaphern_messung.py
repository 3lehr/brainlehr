#!/usr/bin/env python3
"""Schritt 2 -- Blinder Durchlauf und Auswertung fuer die Metaphern-Messung.

Auftrag: docs/PLAN_METAPHERN_2026-08-13.md, Abschnitt "Schritt 2 - Blinder
Durchlauf und Auswertung". Baut auf messungen/metaphern_regelpaare.py auf
(NUR gelesen -- Faelle/Fassungen sind dort Schritt 1 und bleiben unangetastet;
ein Mangel daran wird gemeldet, nicht hier korrigiert).

BAUFORM-VORBILD: messungen/okkultation.py, insbesondere dessen auswerten()
und der Umgang mit Fehlbestand (fehlende Antwortzellen werden GENANNT, nicht
stillschweigend als "nicht angewandt" gelesen -- fail-closed statt
fail-open). Dreiteilung wie dort, weil ein Python-Skript keinen Subagenten
starten kann (L-a69129):
  1. --aufgaben     blinde Bewertungsitems bauen, KEIN Urteil (dieses Skript)
  2. Hauptfaden     jedes Item blind beantworten ("wird die Regel auf diesen
                     Fall angewandt, ja/nein?") -- aus dem Orchestrator
  3. --auswerten    Antworten mit der Zuordnung zusammenfuehren, Quoten
                     bilden, KEIN Urteil (dieses Skript)

WAS GEMESSEN WIRD, je Regelpaar und Fassung (woertlich/passend/unpassend),
GETRENNT, nie zu einer Zahl verrechnet:
  Reichweite     = Anteil 'ja' unter Menge 'gemeint'
  Fehlanwendung  = Anteil 'ja' unter Menge 'nicht_gemeint'
Menge 'genannt' ist die Gueltigkeitspruefung: werden in DIESEM Lauf nicht
alle genannten Faelle einer Fassung mit 'ja' beantwortet, ist das Paar in
dieser Fassung als ungueltig ausgewiesen, statt in die Quoten einzugehen.

BLIND GEGEN DIE FASSUNG, nachweisbar statt behauptet: Die Items, die dem
Bewerter vorgelegt werden (items_blind), tragen weder ein 'fassung'- noch
ein 'menge'- noch ein Paar-Feld, und die ID ('it-000' ...) ist eine reine
Laufnummer ohne Kodierung. Die Zuordnung Item->Fassung/Menge/Paar liegt in
einem GETRENNTEN Feld ('zuordnung') derselben Aufgabendatei und wird ERST in
auswerten() wieder zusammengefuehrt. Die Reihenfolge der Items ist
deterministisch gemischt -- Hash aus Seed+Item-Inhalt (Muster aus
m1_sample()/m2_sample() in okkultation.py), kein random.shuffle() ohne
Protokoll. Der Seed steht im Ergebnis, ein Lauf ist damit wiederholbar.
tests/test_metaphern_messung.py belegt die Blindheit mechanisch.

Aufruf:
    python3 messungen/metaphern_messung.py --aufgaben runs/metaphern_aufgaben_<datum>.json
    python3 messungen/metaphern_messung.py --auswerten AUFGABEN ANTWORTEN --out runs/metaphern_ergebnis_<datum>.json
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Repo-Wurzel an schema.sql festmachen (Muster aus messungen/okkultation.py).
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern")]

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import codestand  # noqa: E402
import metaphern_regelpaare as mr  # noqa: E402 -- nur gelesen (REGELPAARE/FASSUNGEN/MENGEN)

WURZEL = _w


# --------------------------------------------------------------- Items bauen
def _items_erzeugen(seed: int) -> tuple[list[dict], dict]:
    """Baut alle (paar, fassung, menge, fall)-Kombinationen, mischt sie
    deterministisch ueber seed und vergibt eine blinde Laufnummer. Gibt
    (items_blind, zuordnung) getrennt zurueck -- items_blind enthaelt KEINEN
    Hinweis auf Fassung/Menge/Paar."""
    roh = []
    for paar in mr.REGELPAARE:
        for fassung in mr.FASSUNGEN:
            regel_text = paar["fassungen"][fassung]
            fallmengen = paar["fallmengen"][fassung]
            for menge in mr.MENGEN:
                for fall_text in fallmengen[menge]:
                    roh.append({
                        "paar_id": paar["id"], "fassung": fassung, "menge": menge,
                        "regel_text": regel_text, "fall_text": fall_text,
                    })
    roh.sort(key=lambda r: hashlib.sha256(
        f"{seed}|{r['paar_id']}|{r['fassung']}|{r['menge']}|{r['fall_text']}"
        .encode("utf-8")).hexdigest())

    items_blind, zuordnung = [], {}
    for i, r in enumerate(roh):
        iid = f"it-{i:03d}"
        items_blind.append({
            "id": iid, "regel_text": r["regel_text"], "fall_text": r["fall_text"],
        })
        zuordnung[iid] = {
            "paar_id": r["paar_id"], "fassung": r["fassung"], "menge": r["menge"],
        }
    return items_blind, zuordnung


def aufgaben_erzeugen(seed: int = 0) -> dict:
    items_blind, zuordnung = _items_erzeugen(seed)
    return {
        "erzeugt_am": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": seed,
        "codestand": codestand.ermitteln(WURZEL),
        "n_items": len(items_blind),
        "frage_an_bewerter": ("Wird diese Regel auf diesen Fall angewandt, "
                               "ja oder nein? Je Item-ID mit "
                               "{'angewandt': true/false} beantworten."),
        "items_blind": items_blind,
        "zuordnung": zuordnung,
    }


# -------------------------------------------------------------- auswerten()
def _antwort_ja(eintrag) -> bool | None:
    """True/False/None (unlesbar). Akzeptiert {'angewandt': bool} oder einen
    blossen String 'ja'/'nein' (Gross/Kleinschreibung egal)."""
    if isinstance(eintrag, dict):
        wert = eintrag.get("angewandt")
        if isinstance(wert, bool):
            return wert
        eintrag = eintrag.get("antwort")
    if isinstance(eintrag, str):
        s = eintrag.strip().lower()
        if s in ("ja", "true", "yes"):
            return True
        if s in ("nein", "false", "no"):
            return False
    return None


def _quote(treffer: int, n: int) -> dict:
    return {
        "treffer": treffer, "n": n,
        "anteil": (treffer / n) if n else None,
        "hinweis": None if n else "keine Faelle",
    }


def auswerten(aufgaben: dict, antworten: dict) -> dict:
    """Fuehrt Antworten mit der Zuordnung zusammen. Fehlende oder unlesbare
    Antwortzellen werden GENANNT (fehlbestand/unlesbar), nicht stillschweigend
    als 'nicht angewandt' in die Quote gerechnet -- sonst saehe eine
    unvollstaendige Antwortdatei aus wie Vollstaendigkeit (Auftrag,
    Negativfall 4)."""
    gegeben = antworten.get("antworten", {})
    zuordnung = aufgaben["zuordnung"]

    zellen: dict[tuple[str, str, str], list[bool]] = {}
    fehlbestand: list[str] = []
    unlesbar: list[str] = []

    for iid, meta in zuordnung.items():
        if iid not in gegeben:
            fehlbestand.append(iid)
            continue
        wert = _antwort_ja(gegeben[iid])
        if wert is None:
            unlesbar.append(iid)
            continue
        schluessel = (meta["paar_id"], meta["fassung"], meta["menge"])
        zellen.setdefault(schluessel, []).append(wert)

    paare_ergebnis = []
    for paar in mr.REGELPAARE:
        pid = paar["id"]
        fassungen_out = {}
        for fassung in mr.FASSUNGEN:
            genannt = zellen.get((pid, fassung, "genannt"), [])
            gemeint = zellen.get((pid, fassung, "gemeint"), [])
            nicht_gemeint = zellen.get((pid, fassung, "nicht_gemeint"), [])
            n_genannt_soll = len(paar["fallmengen"][fassung]["genannt"])
            vollstaendig = len(genannt) == n_genannt_soll
            gueltig = vollstaendig and all(genannt)
            fassungen_out[fassung] = {
                "reichweite": _quote(sum(gemeint), len(gemeint)),
                "fehlanwendung": _quote(sum(nicht_gemeint), len(nicht_gemeint)),
                "genannt_getroffen": _quote(sum(genannt), len(genannt)),
                "genannt_soll": n_genannt_soll,
                "genannt_vollstaendig_beantwortet": vollstaendig,
                "gueltig_in_diesem_lauf": gueltig,
            }
        paare_ergebnis.append({
            "paar_id": pid, "quelle": paar["quelle"], "fassungen": fassungen_out,
        })

    return {
        "ausgewertet_am": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": aufgaben.get("seed"),
        "codestand_aufgaben": aufgaben.get("codestand"),
        "codestand_auswertung": codestand.ermitteln(WURZEL),
        "n_items_gesamt": len(zuordnung),
        "n_fehlbestand": len(fehlbestand),
        "fehlbestand": fehlbestand,
        "n_unlesbar": len(unlesbar),
        "unlesbar": unlesbar,
        "paare": paare_ergebnis,
    }


# ---------------------------------------------------------------------- CLI
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--aufgaben", metavar="DATEI",
                     help="Schritt 1: blinde Items bauen, kein Urteil")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--auswerten", nargs=2, metavar=("AUFGABEN", "ANTWORTEN"),
                     help="Schritt 3: Antworten auswerten, kein Urteil")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.aufgaben:
        daten = aufgaben_erzeugen(args.seed)
        ziel = Path(args.aufgaben)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Items: {daten['n_items']}  Seed: {daten['seed']}  Geschrieben: {ziel}")
        return

    if args.auswerten:
        aufg = json.loads(Path(args.auswerten[0]).read_text(encoding="utf-8"))
        antw = json.loads(Path(args.auswerten[1]).read_text(encoding="utf-8"))
        ergebnis = auswerten(aufg, antw)
        out = Path(args.out or (WURZEL / "runs" / "metaphern_ergebnis.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Fehlbestand: {ergebnis['n_fehlbestand']}  Unlesbar: {ergebnis['n_unlesbar']}")
        for p in ergebnis["paare"]:
            for f, werte in p["fassungen"].items():
                r, fa = werte["reichweite"], werte["fehlanwendung"]
                print(f"{p['paar_id']:28s} {f:10s} "
                      f"reichweite={r['treffer']}/{r['n']} "
                      f"fehlanwendung={fa['treffer']}/{fa['n']} "
                      f"gueltig={werte['gueltig_in_diesem_lauf']}")
        print(f"Geschrieben: {out}")
        return

    ap.print_help()


if __name__ == "__main__":
    main()
