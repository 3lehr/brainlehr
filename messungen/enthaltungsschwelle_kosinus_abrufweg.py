#!/usr/bin/env python3
"""Dieselbe Schwellentabelle wie messungen/enthaltungsschwelle_kosinus.py,
aber ueber den ABRUFWEG (haken/suchpfad_abruf.py::kandidaten()) statt ueber
knowledge_search() (Auftrag 2026-08-19).

FAKTEN, die diesen Lauf begruenden: suchpfad_abruf.kandidaten() traegt seit
Commit 1e2b40ee je Kandidat 'bedeutungs_kosinus' (roher Kosinus, None ohne
Vektor) -- dieselbe Bauform wie knowledge_search(), aber ein anderer Pfad
(kein _fuse_with_keyword_floor-Sockel, reine RRF-Fusion, s. Moduldoc dort).
Eine Schwelle 0.55 existiert bereits, aber NUR ueber knowledge_search
erhoben (runs/enthaltungsschwelle_kosinus_2026-08-19.json) -- die beiden
Wege liefern nachweislich verschiedene Ergebnisse (knowledge_search top5
7/35, Abrufweg 11/35, runs/abrufweg_produktiv_2026-08-19T111150.json).

WEG: haken/suchpfad_abruf.py::kandidaten(conn, text, query_vec, max_results)
-- kein Nachbau. query_vec = embeddings.embed_text(text), genau wie
knowledge_recall_hook.query() ihn beschafft. max_results = MAX_NODES +
MAX_LESSONS (17) -- der Wert, mit dem der Haken kandidaten() tatsaechlich
aufruft (Zeile 'node_rows, lesson_rows = mehrstufiger_abruf.kandidaten_
geschaltet(conn, ..., MAX_NODES + MAX_LESSONS)', faellt bei
KNOWLEDGE_MEHRSTUFIGER_ABRUF=AUS (Vorgabe) auf suchpfad_abruf.kandidaten()
1:1 zurueck). Bester Kosinus je Frage = max(bedeutungs_kosinus) ueber ALLE
gelieferten Kandidaten (Nodes + Lehren), None gefiltert.

FRAGEN: NICHT neu erfunden -- woertlich aus
runs/enthaltungsschwelle_kosinus_2026-08-19.json (je_frage_einschlaegig /
je_frage_fachfremd), damit die beiden Wege an denselben Fragen gemessen
sind.

AUSWERTUNG: importiert messungen.enthaltungsschwelle_kosinus.auswerten()
unveraendert -- dieselbe Funktion, kein Nachbau, keine zweite Fehlerquelle.

SCHNAPPSCHUSS: genau einer (kern/schnappschuss.py::festhalten()). Die
eigentliche Isolierung ist der explizite conn ueber speicher.lesen(stand.pfad)
-- kandidaten() liest ausschliesslich aus diesem conn (kein Modul-Attribut).
Zusaetzlich, wie im Auftrag verlangt, BEIDE Modul-Attribute gepinnt
(knowledge_recall_hook.DB, knowledge_mcp_server.DB_PATH) -- fuer DIESEN Pfad
strenggenommen wirkungslos (kandidaten() und die drei aus knowledge_
mcp_server importierten Bausteine _embedding_ranking/_or_query/
_stichwortkanal_blind nehmen conn als Parameter, kein Modul-Attribut wird
gelesen -- gemessen am Code, nicht vermutet), aber die Auflage ist absolut
("BEIDE Attribute") und das Pinnen kostet nichts.

Auftrag ausdruecklich: KEINE Empfehlung fuer eine Schwelle.

Aufruf:
    python3 messungen/enthaltungsschwelle_kosinus_abrufweg.py --selbsttest
    python3 messungen/enthaltungsschwelle_kosinus_abrufweg.py --out runs/<datei>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken"), str(_w / "messungen")]

import embeddings  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402 -- nur fuer den Pin, s. Docstring
import knowledge_recall_hook as hook  # noqa: E402 -- nur fuer den Pin, s. Docstring
import speicher  # noqa: E402
import suchpfad_abruf  # noqa: E402 -- der Produktivweg selbst
from schnappschuss import festhalten  # noqa: E402
from enthaltungsschwelle_kosinus import auswerten  # noqa: E402 -- unveraendert wiederverwendet

QUELLE_FRAGEN = _w / "runs" / "enthaltungsschwelle_kosinus_2026-08-19.json"
MAX_RESULTS = hook.MAX_NODES + hook.MAX_LESSONS  # 17, s. Docstring


def bester_kosinus(conn, frage: str) -> float | None:
    """Hoechster bedeutungs_kosinus ueber alle vom Abrufweg gelieferten
    Kandidaten (Nodes + Lehren). Kein Treffer bzw. keiner mit Vektor -> None."""
    query_vec = embeddings.embed_text(frage)
    nodes, lessons = suchpfad_abruf.kandidaten(conn, frage, query_vec, MAX_RESULTS)
    werte = [r["bedeutungs_kosinus"] for r in nodes + lessons if r.get("bedeutungs_kosinus") is not None]
    return round(max(werte), 4) if werte else None


def _selbsttest() -> None:
    """Selbsttest der (importierten, unveraendert wiederverwendeten)
    Auswertungsfunktion -- beide Fehlerarten je einmal plus der Grenzfall
    'Schwelle exakt auf einem beobachteten Wert'. Keine DB, kein Netz."""
    einschlaegig = [0.7, 0.6, None]   # None = faelschlich_enthalten IMMER
    fachfremd = [0.45, 0.6, 0.3]      # 0.6 kommt auf BEIDEN Seiten vor
    tab = auswerten(einschlaegig, fachfremd, schritt=0.1)
    by_s = {z["schwelle"]: z for z in tab}

    # faelschlich_enthalten: bei S=0.7 faellt 0.6 UND None darunter -> 2.
    assert by_s[0.7]["faelschlich_enthalten"] == 2, by_s[0.7]
    # faelschlich_geliefert: bei S=0.3 liegen alle 3 fachfremden Werte >= 0.3.
    assert by_s[0.3]["faelschlich_geliefert"] == 3, by_s[0.3]

    # Grenzfall: Schwelle GENAU auf 0.6 (beobachtet auf beiden Seiten).
    # einschlaegig 0.6 < 0.6 ist falsch -> zaehlt NICHT als faelschlich_enthalten
    # (nur None zaehlt) -> 1. fachfremd 0.6 >= 0.6 ist wahr -> zaehlt als
    # faelschlich_geliefert -> 1. Die Gleichheit gewinnt fuer die GELIEFERT-
    # Seite (>=), NICHT fuer die ENTHALTEN-Seite (<) -- das ist dieselbe
    # Asymmetrie wie im Original (messungen/enthaltungsschwelle_kosinus.py).
    assert by_s[0.6]["faelschlich_enthalten"] == 1, by_s[0.6]
    assert by_s[0.6]["faelschlich_geliefert"] == 1, by_s[0.6]

    assert auswerten([], []) == []
    print("selbsttest: ok", file=sys.stderr)


def _lade_fragen() -> tuple[list[dict], list[dict]]:
    if not QUELLE_FRAGEN.exists():
        print(f"ABBRUCH: Fragenquelle fehlt: {QUELLE_FRAGEN}", file=sys.stderr)
        sys.exit(1)
    d = json.loads(QUELLE_FRAGEN.read_text(encoding="utf-8"))
    return d["je_frage_einschlaegig"], d["je_frage_fachfremd"]


def _gegenueberstellung(unsere_tabelle: list[dict], ks_tabelle: list[dict]) -> tuple[list[dict], list[float]]:
    """Fuegt je Schwelle dieser Tabelle die Werte der knowledge_search-
    Tabelle daneben -- None, wenn die Schwelle ausserhalb von deren
    beobachtetem Bereich liegt (keine Interpolation, keine Erfindung).
    Liefert zusaetzlich die Liste der Schwellen, an denen sich mindestens
    eine der beiden Fehlerarten unterscheidet (nur benannt, nicht erklaert)."""
    ks_by_s = {z["schwelle"]: z for z in ks_tabelle}
    zusammen = []
    abweichende_schwellen = []
    for z in unsere_tabelle:
        s = z["schwelle"]
        ks = ks_by_s.get(s)
        zeile = {
            "schwelle": s,
            "faelschlich_enthalten_abrufweg": z["faelschlich_enthalten"],
            "faelschlich_geliefert_abrufweg": z["faelschlich_geliefert"],
            "faelschlich_enthalten_knowledge_search": ks["faelschlich_enthalten"] if ks else None,
            "faelschlich_geliefert_knowledge_search": ks["faelschlich_geliefert"] if ks else None,
        }
        zusammen.append(zeile)
        if ks is not None and (ks["faelschlich_enthalten"] != z["faelschlich_enthalten"]
                                or ks["faelschlich_geliefert"] != z["faelschlich_geliefert"]):
            abweichende_schwellen.append(s)
    return zusammen, abweichende_schwellen


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.selbsttest:
        _selbsttest()
        return

    einschlaegig_quelle, fachfremd_quelle = _lade_fragen()
    ks_daten = json.loads(QUELLE_FRAGEN.read_text(encoding="utf-8"))

    stand = festhalten()
    orig_hook_db, orig_kms_db = hook.DB, kms.DB_PATH
    hook.DB = str(stand.pfad)
    kms.DB_PATH = stand.pfad
    print(f"messstand: {stand.kennung} ({stand.pfad})", file=sys.stderr)
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
        import shutil
        shutil.rmtree(stand.pfad.parent, ignore_errors=True)

    e_werte = [z["bester_kosinus"] for z in einschlaegig_zeilen]
    f_werte = [z["bester_kosinus"] for z in fachfremd_zeilen]
    e_werte_num = [w for w in e_werte if w is not None]
    f_werte_num = [w for w in f_werte if w is not None]

    positivkontrolle_bestanden = bool(e_werte_num) and bool(f_werte_num) and \
        min(f_werte_num) < max(e_werte_num)

    ueberlappung = None
    if e_werte_num and f_werte_num:
        lo = max(min(e_werte_num), min(f_werte_num))
        hi = min(max(e_werte_num), max(f_werte_num))
        breite = round(hi - lo, 4) if hi > lo else 0.0
        ueberlappung = {
            "ueberlappen": hi > lo,
            "breite": breite,
            "einschlaegig_bereich": [round(min(e_werte_num), 4), round(max(e_werte_num), 4)],
            "fachfremd_bereich": [round(min(f_werte_num), 4), round(max(f_werte_num), 4)],
            "satz": (
                f"Die Bereiche ueberlappen um {breite}: einschlaegig "
                f"[{round(min(e_werte_num), 4)}, {round(max(e_werte_num), 4)}], "
                f"fachfremd [{round(min(f_werte_num), 4)}, {round(max(f_werte_num), 4)}]."
                if hi > lo else
                f"Die Bereiche ueberlappen NICHT: einschlaegig "
                f"[{round(min(e_werte_num), 4)}, {round(max(e_werte_num), 4)}], "
                f"fachfremd [{round(min(f_werte_num), 4)}, {round(max(f_werte_num), 4)}]."
            ),
        }

    schwellentabelle = auswerten(e_werte, f_werte)
    gegenueberstellung, abweichende_schwellen = _gegenueberstellung(
        schwellentabelle, ks_daten["schwellentabelle"])

    schadensfaelle = {z["name"]: z for z in fachfremd_zeilen if "name" in z}

    ergebnis = {
        "schnappschuss": stand.kennung,
        "weg": "haken/suchpfad_abruf.py::kandidaten() -- echter Abrufweg-Baustein, kein Nachbau",
        "max_results": MAX_RESULTS,
        "n": {"einschlaegig": len(einschlaegig_zeilen), "fachfremd": len(fachfremd_zeilen)},
        "quelle_fragen": f"{QUELLE_FRAGEN.relative_to(_w)} (je_frage_einschlaegig/je_frage_fachfremd, "
                          "woertlich uebernommen, damit beide Wege an denselben Fragen gemessen sind)",
        "positivkontrolle": {
            "bestanden": positivkontrolle_bestanden,
            "min_fachfremd": min(f_werte_num) if f_werte_num else None,
            "max_einschlaegig": max(e_werte_num) if e_werte_num else None,
        },
        "schadensfaelle": schadensfaelle,
        "ueberlappung": ueberlappung,
        "je_frage_einschlaegig": einschlaegig_zeilen,
        "je_frage_fachfremd": fachfremd_zeilen,
        "schwellentabelle": schwellentabelle,
        "gegenueberstellung_knowledge_search": gegenueberstellung,
        "abweichende_schwellen_ggue_knowledge_search": abweichende_schwellen,
        "hinweis": "Keine Schwelle wird hier empfohlen oder als richtig bezeichnet -- "
                   "'faelschlich_enthalten' (Speicher schweigt trotz Ziel) und "
                   "'faelschlich_geliefert' (Speicher liefert bei fachfremder Frage) stehen "
                   "nebeneinander, die Wahl faellt woanders. Diese Tabelle unterscheidet sich "
                   "von der ueber knowledge_search erhobenen (runs/enthaltungsschwelle_kosinus_"
                   "2026-08-19.json) an den in 'abweichende_schwellen_ggue_knowledge_search' "
                   "genannten Schwellen -- nur benannt, nicht erklaert.",
    }

    if not positivkontrolle_bestanden:
        print("BEFUND: Positivkontrolle nicht bestanden -- Aufbau verdaechtig, siehe Ergebnis.",
              file=sys.stderr)

    out_pfad = Path(args.out) if args.out else _w / "runs" / "enthaltungsschwelle_kosinus_abrufweg.json"
    out_pfad.parent.mkdir(parents=True, exist_ok=True)
    out_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
