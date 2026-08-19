#!/usr/bin/env python3
"""Zweite Erhebung derselben Schwellentabelle wie
messungen/enthaltungsschwelle_kosinus_abrufweg.py, gegen den HEUTIGEN Bestand
(nach dem Neuberechnen von 478 Einbettungszeilen, s. Auftrag 2026-08-19,
Knoten 79487bf9). Fragen, Weg (haken/suchpfad_abruf.py::kandidaten()) und
Auswertungsfunktion (messungen.enthaltungsschwelle_kosinus.auswerten) sind
UNVERAENDERT gegenueber dem alten Lauf -- nur der Datenbestand ist neu.

ALT: runs/enthaltungsschwelle_kosinus_abrufweg.json (Schnappschuss
20260819T094703-31bcb647). Von dort wird 'je_frage_einschlaegig' /
'je_frage_fachfremd' als FRAGENQUELLE woertlich uebernommen (Frage + ziel/
name), NICHT die alten Kosinuswerte neu erfunden -- die alten Werte kommen
aus derselben Datei.

WEG: identisch zum Vorlauf (s. dortiger Docstring) -- kein Nachbau.

SCHNAPPSCHUSS: genau einer (kern/schnappschuss.py::festhalten()), beide
Modul-Attribute gepinnt (knowledge_recall_hook.DB, knowledge_mcp_server.
DB_PATH, L-dadfac), am Ende weggeraeumt.

Auftrag ausdruecklich: KEINE Empfehlung fuer eine Schwelle.

Aufruf:
    python3 messungen/schwelle_nachlauf_abrufweg_2026-08-19.py --selbsttest
    python3 messungen/schwelle_nachlauf_abrufweg_2026-08-19.py --out runs/<datei>.json
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
import knowledge_mcp_server as kms  # noqa: E402 -- nur fuer den Pin
import knowledge_recall_hook as hook  # noqa: E402 -- nur fuer den Pin
import speicher  # noqa: E402
import suchpfad_abruf  # noqa: E402 -- der Produktivweg selbst
from schnappschuss import festhalten  # noqa: E402
from enthaltungsschwelle_kosinus import auswerten  # noqa: E402 -- unveraendert wiederverwendet

ALT_DATEI = _w / "runs" / "enthaltungsschwelle_kosinus_abrufweg.json"
MAX_RESULTS = hook.MAX_NODES + hook.MAX_LESSONS

# Die drei Grenzfaelle, im Auftrag namentlich benannt (alter Wert, s. Auftrag).
GRENZFAELLE_ZIELE = {"/ops/buckeberg-konsil-2026-07-22-governance",
                      "/apps/metahuman-podcast-one-command-pipeline",
                      "/stadtwerke"}

FESTE_SCHWELLE = 0.55


def bester_kosinus(conn, frage: str) -> float | None:
    """Hoechster bedeutungs_kosinus ueber alle vom Abrufweg gelieferten
    Kandidaten (Nodes + Lehren). Kein Treffer bzw. keiner mit Vektor -> None."""
    query_vec = embeddings.embed_text(frage)
    nodes, lessons = suchpfad_abruf.kandidaten(conn, frage, query_vec, MAX_RESULTS)
    werte = [r["bedeutungs_kosinus"] for r in nodes + lessons if r.get("bedeutungs_kosinus") is not None]
    return round(max(werte), 4) if werte else None


def _vergleich_je_frage(alt_zeilen: list[dict], neu_zeilen: list[dict], schluessel: str) -> tuple[list[dict], int, int, int]:
    """Alter/neuer bester Kosinus nebeneinander, je Frage identifiziert ueber
    `schluessel` ('ziel' bei einschlaegig, 'frage' bei fachfremd -- fachfremd
    traegt 'name' nur bei den zwei Schadensfaellen). Liefert (Zeilen,
    bewegt_hoch, bewegt_runter, unveraendert) mit Schwelle > 0.01 Betrag."""
    alt_by_key = {z[schluessel]: z["bester_kosinus"] for z in alt_zeilen}
    zeilen = []
    hoch = runter = gleich = 0
    for z in neu_zeilen:
        key = z[schluessel]
        alt_wert = alt_by_key.get(key)
        neu_wert = z["bester_kosinus"]
        delta = None
        bewegung = "unbestimmt"  # falls einer der beiden Werte None ist
        if alt_wert is not None and neu_wert is not None:
            delta = round(neu_wert - alt_wert, 4)
            if delta > 0.01:
                bewegung = "hoch"
                hoch += 1
            elif delta < -0.01:
                bewegung = "runter"
                runter += 1
            else:
                bewegung = "unveraendert"
                gleich += 1
        zeilen.append({
            schluessel: key,
            "frage": z["frage"],
            "alt": alt_wert,
            "neu": neu_wert,
            "delta": delta,
            "bewegung": bewegung,
        })
    return zeilen, hoch, runter, gleich


def _selbsttest() -> None:
    """Selbsttest von _vergleich_je_frage mit erfundenen Zahlen: eine Frage
    steigt (>0.01), eine faellt (<-0.01), eine bleibt (<=0.01 Betrag).
    Keine DB, kein Netz."""
    alt = [
        {"ziel": "a", "frage": "fa", "bester_kosinus": 0.50},
        {"ziel": "b", "frage": "fb", "bester_kosinus": 0.60},
        {"ziel": "c", "frage": "fc", "bester_kosinus": 0.55},
    ]
    neu = [
        {"ziel": "a", "frage": "fa", "bester_kosinus": 0.53},   # steigt, +0.03
        {"ziel": "b", "frage": "fb", "bester_kosinus": 0.58},   # faellt, -0.02
        {"ziel": "c", "frage": "fc", "bester_kosinus": 0.552},  # bleibt, +0.002
    ]
    zeilen, hoch, runter, gleich = _vergleich_je_frage(alt, neu, "ziel")
    assert hoch == 1, (hoch, zeilen)
    assert runter == 1, (runter, zeilen)
    assert gleich == 1, (gleich, zeilen)
    by_ziel = {z["ziel"]: z for z in zeilen}
    assert by_ziel["a"]["bewegung"] == "hoch"
    assert by_ziel["b"]["bewegung"] == "runter"
    assert by_ziel["c"]["bewegung"] == "unveraendert"
    # None auf einer Seite -> 'unbestimmt', zaehlt in keine Richtung
    zeilen2, h2, r2, g2 = _vergleich_je_frage(
        [{"ziel": "d", "frage": "fd", "bester_kosinus": None}],
        [{"ziel": "d", "frage": "fd", "bester_kosinus": 0.5}],
        "ziel")
    assert h2 == 0 and r2 == 0 and g2 == 0
    assert zeilen2[0]["bewegung"] == "unbestimmt"
    print("selbsttest: ok", file=sys.stderr)


def _lade_alt() -> dict:
    if not ALT_DATEI.exists():
        print(f"ABBRUCH: Vorlauf-Datei fehlt: {ALT_DATEI}", file=sys.stderr)
        sys.exit(1)
    return json.loads(ALT_DATEI.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.selbsttest:
        _selbsttest()
        return

    alt = _lade_alt()
    einschlaegig_quelle = alt["je_frage_einschlaegig"]
    fachfremd_quelle = alt["je_frage_fachfremd"]

    stand = festhalten()
    orig_hook_db, orig_kms_db = hook.DB, kms.DB_PATH
    hook.DB = str(stand.pfad)
    kms.DB_PATH = stand.pfad
    print(f"messstand (neu): {stand.kennung} ({stand.pfad})", file=sys.stderr)
    try:
        with speicher.lesen(stand.pfad) as conn:
            einschlaegig_zeilen = []
            for f in einschlaegig_quelle:
                wert = bester_kosinus(conn, f["frage"])
                einschlaegig_zeilen.append({"art": "einschlaegig", "ziel": f["ziel"],
                                             "frage": f["frage"], "bester_kosinus": wert})

            fachfremd_zeilen = []
            for f in fachfremd_quelle:
                wert = bester_kosinus(conn, f["frage"])
                eintrag = {"art": "fachfremd", "domain": f["domain"], "frage": f["frage"],
                           "bester_kosinus": wert}
                if "name" in f:
                    eintrag["name"] = f["name"]
                fachfremd_zeilen.append(eintrag)
    finally:
        hook.DB = orig_hook_db
        kms.DB_PATH = orig_kms_db
        shutil.rmtree(stand.pfad.parent, ignore_errors=True)

    e_werte = [z["bester_kosinus"] for z in einschlaegig_zeilen]
    f_werte = [z["bester_kosinus"] for z in fachfremd_zeilen]
    e_werte_num = [w for w in e_werte if w is not None]
    f_werte_num = [w for w in f_werte if w is not None]

    positivkontrolle_bestanden = bool(e_werte_num) and bool(f_werte_num) and \
        min(f_werte_num) < max(e_werte_num)

    ueberlappung_neu = None
    if e_werte_num and f_werte_num:
        lo = max(min(e_werte_num), min(f_werte_num))
        hi = min(max(e_werte_num), max(f_werte_num))
        breite = round(hi - lo, 4) if hi > lo else 0.0
        ueberlappung_neu = {
            "ueberlappen": hi > lo,
            "breite": breite,
            "einschlaegig_bereich": [round(min(e_werte_num), 4), round(max(e_werte_num), 4)],
            "fachfremd_bereich": [round(min(f_werte_num), 4), round(max(f_werte_num), 4)],
        }
    ueberlappung_alt = alt["ueberlappung"]

    schwellentabelle_neu = auswerten(e_werte, f_werte)
    schwellentabelle_alt = alt["schwellentabelle"]

    # Gegenueberstellung beider Schwellentabellen, je Schwelle die dieser
    # Tabelle -- None, wenn die Schwelle ausserhalb des jeweils anderen
    # beobachteten Bereichs liegt (keine Interpolation, keine Erfindung).
    alt_by_s = {z["schwelle"]: z for z in schwellentabelle_alt}
    neu_by_s = {z["schwelle"]: z for z in schwellentabelle_neu}
    alle_schwellen = sorted(set(alt_by_s) | set(neu_by_s))
    schwellen_gegenueberstellung = []
    for s in alle_schwellen:
        a = alt_by_s.get(s)
        n = neu_by_s.get(s)
        schwellen_gegenueberstellung.append({
            "schwelle": s,
            "faelschlich_enthalten_alt": a["faelschlich_enthalten"] if a else None,
            "faelschlich_geliefert_alt": a["faelschlich_geliefert"] if a else None,
            "faelschlich_enthalten_neu": n["faelschlich_enthalten"] if n else None,
            "faelschlich_geliefert_neu": n["faelschlich_geliefert"] if n else None,
        })

    zeile_055_alt = alt_by_s.get(FESTE_SCHWELLE)
    zeile_055_neu = neu_by_s.get(FESTE_SCHWELLE)
    schwelle_055 = {
        "schwelle": FESTE_SCHWELLE,
        "alt": {"faelschlich_enthalten": zeile_055_alt["faelschlich_enthalten"],
                "faelschlich_geliefert": zeile_055_alt["faelschlich_geliefert"]} if zeile_055_alt else None,
        "neu": {"faelschlich_enthalten": zeile_055_neu["faelschlich_enthalten"],
                "faelschlich_geliefert": zeile_055_neu["faelschlich_geliefert"]} if zeile_055_neu else None,
        "unveraendert": bool(zeile_055_alt and zeile_055_neu
                             and zeile_055_alt["faelschlich_enthalten"] == zeile_055_neu["faelschlich_enthalten"]
                             and zeile_055_alt["faelschlich_geliefert"] == zeile_055_neu["faelschlich_geliefert"]),
    }

    e_vergleich, e_hoch, e_runter, e_gleich = _vergleich_je_frage(
        einschlaegig_quelle, einschlaegig_zeilen, "ziel")
    f_vergleich, f_hoch, f_runter, f_gleich = _vergleich_je_frage(
        fachfremd_quelle, fachfremd_zeilen, "frage")

    grenzfaelle = {z["ziel"]: {"alt": next(a["bester_kosinus"] for a in einschlaegig_quelle if a["ziel"] == z["ziel"]),
                                "neu": z["bester_kosinus"]}
                   for z in einschlaegig_zeilen if z["ziel"] in GRENZFAELLE_ZIELE}

    ergebnis = {
        "schnappschuss_alt": alt["schnappschuss"],
        "schnappschuss_neu": stand.kennung,
        "weg": "haken/suchpfad_abruf.py::kandidaten() -- identisch zum Vorlauf, kein Nachbau",
        "fragenquelle": f"{ALT_DATEI.relative_to(_w)} (je_frage_einschlaegig/je_frage_fachfremd, "
                        "woertlich uebernommen -- gleiche Fragen wie im Vorlauf)",
        "max_results": MAX_RESULTS,
        "n": {"einschlaegig": len(einschlaegig_zeilen), "fachfremd": len(fachfremd_zeilen)},
        "positivkontrolle": {
            "bestanden": positivkontrolle_bestanden,
            "min_fachfremd": min(f_werte_num) if f_werte_num else None,
            "max_einschlaegig": max(e_werte_num) if e_werte_num else None,
        },
        "drei_grenzfaelle": grenzfaelle,
        "ueberlappung_alt": ueberlappung_alt,
        "ueberlappung_neu": ueberlappung_neu,
        "schwelle_0_55": schwelle_055,
        "bewegte_fragen": {
            "einschlaegig_hoch": e_hoch, "einschlaegig_runter": e_runter, "einschlaegig_unveraendert": e_gleich,
            "fachfremd_hoch": f_hoch, "fachfremd_runter": f_runter, "fachfremd_unveraendert": f_gleich,
        },
        "je_frage_einschlaegig_vergleich": e_vergleich,
        "je_frage_fachfremd_vergleich": f_vergleich,
        "je_frage_einschlaegig_neu": einschlaegig_zeilen,
        "je_frage_fachfremd_neu": fachfremd_zeilen,
        "schwellentabelle_gegenueberstellung": schwellen_gegenueberstellung,
        "hinweis": "Keine Schwelle wird hier empfohlen oder als richtig bezeichnet -- "
                   "'faelschlich_enthalten' (Speicher schweigt trotz Ziel) und "
                   "'faelschlich_geliefert' (Speicher liefert bei fachfremder Frage) stehen "
                   "nebeneinander, die Wahl faellt woanders.",
    }

    if not positivkontrolle_bestanden:
        print("BEFUND: Positivkontrolle nicht bestanden -- Aufbau verdaechtig, siehe Ergebnis.",
              file=sys.stderr)

    out_pfad = Path(args.out) if args.out else _w / "runs" / "schwelle_nachlauf_abrufweg_2026-08-19.json"
    out_pfad.parent.mkdir(parents=True, exist_ok=True)
    out_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
