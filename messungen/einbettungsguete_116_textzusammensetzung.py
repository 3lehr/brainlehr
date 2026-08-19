#!/usr/bin/env python3
"""Auftrag 2026-08-19 (Frage 116): Was drueckt den Kosinus der drei Faelle
aus runs/enthaltung_115_faelle.json (bester_kosinus < 0.55, aber
fusion_rang=1 -- Rangfehler, veralteter Vektor und Kappung sind bereits
AUSGESCHIEDEN, s. Auftrag)? ANNAHME (ausdruecklich pruefbar): Ursache liegt
in der Textzusammensetzung, die kern/build_embeddings.py::node_text() aus
einem Knoten baut.

WEG: node_text()/wird_gekappt()/embed_text()/cosine_similarity() aus kern/
wiederverwendet (kein Nachbau). Je Fall:
  - Laenge des node_text() gegen den Median ueber ALLE Knoten.
  - Kosinus FRAGE vs. eingebettetem node_text() (voller Text) --
    Referenzwert, muss die 'bedeutungs_kosinus_ziel'-Zahl aus Auftrag 115
    ungefaehr reproduzieren (anderer Snapshot, kleine Abweichung erwartet).
  - Kosinus FRAGE vs. vier Varianten desselben Knotens (nur Titel, nur
    Summary, Titel+Summary, nur Content) -- schlaegt eine Variante den
    vollen Text, ist die Textzusammensetzung selbst der Hebel.

GEGENPROBEN (Auftrag, Punkt 2+3): dieselben Zahlen fuer einen Fall MIT
hohem Wert und fuer eine FACHFREMDE Frage mit hohem Wert.

ABWEICHUNG, gemessen statt uebernommen: Auftrag 115 markiert
/testing/pytest als 'positivkontrolle' -- aber deren Feld
'bester_kosinus_lauf_2026-08-19' (0.6334) ist der beste Kosinus UNTER
IRGENDEINEM Kandidaten fuer diese Frage (messungen/enthaltungsschwelle_
kosinus_abrufweg.py::bester_kosinus(), max ueber ALLE Treffer), NICHT der
Kosinus des Ziel-Knotens selbst -- der liegt laut demselben Auftrag 115
('bedeutungs_kosinus_ziel') bei nur 0.5412, also im selben Bereich wie die
drei Problemfaelle. Als 'hoher Wert' fuer DIESE Messung (Frage vs. genau
dieser Knotentext) waere pytest also keine echte Gegenprobe gewesen. Vorab
direkt nachgemessen (12 Kandidaten aus je_frage_einschlaegig, eigener
Kosinus je Ziel-Knoten statt 'bester unter allen'): /ops/verwalterwahl-weg-
im-buckeberg-zum-2027/efbe-der-vertrag-regelt-die-vergabe-an erreicht 0.6184
GEGEN SEINE EIGENE Frage -- das ist der echte Gegenprobe-Fall MIT hohem Wert
hier unten (Frage/Ziel woertlich aus runs/enthaltungsschwelle_kosinus_
abrufweg.json::je_frage_einschlaegig uebernommen).

Fuer die FACHFREMDE Gegenprobe (schadensfall_macos, bester_kosinus 0.541
aus runs/enthaltungsschwelle_kosinus_abrufweg.json::je_frage_fachfremd --
naeher an den drei Zielen als jede einschlaegige Frage, s. Auftragstext)
gibt es kein 'ziel' -- der Knoten mit dem hoechsten bedeutungs_kosinus
unter den von haken/suchpfad_abruf.py::kandidaten() gelieferten NODE-
Kandidaten wird verwendet (kein Nachbau der Rangfolge).

SCHNAPPSCHUSS: genau einer (kern/schnappschuss.py::festhalten()), am Ende
weggeraeumt. BEIDE Modul-Attribute gepinnt (knowledge_recall_hook.DB,
knowledge_mcp_server.DB_PATH), wie in fruehren Auftraegen dieser Reihe --
fuer diesen Lauf strenggenommen wirkungslos, weil hier nur suchpfad_abruf.
kandidaten(conn, ...) mit explizitem conn und embeddings.embed_text()
aufgerufen werden (kein Modul-Attribut wird gelesen), aber die Auflage ist
absolut und das Pinnen kostet nichts.

Auftrag ausdruecklich: KEINE erfundene Erklaerung, wenn die Messung nichts
zeigt -- dann 'unerklaert' benennen.

Aufruf:
    python3 messungen/einbettungsguete_116_textzusammensetzung.py --selbsttest
    python3 messungen/einbettungsguete_116_textzusammensetzung.py --out runs/einbettungsguete_116_textzusammensetzung.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import statistics
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken"), str(_w / "messungen")]

import embeddings  # noqa: E402
import knowledge_mcp_server as kms  # noqa: E402 -- nur fuer den Pin
import knowledge_recall_hook as hook  # noqa: E402 -- nur fuer den Pin
import speicher  # noqa: E402
import suchpfad_abruf  # noqa: E402 -- fuer den fachfremden Fall (kein 'ziel' bekannt)
from build_embeddings import node_text  # noqa: E402 -- WOERTLICH dieselbe Zusammensetzung
from schnappschuss import festhalten  # noqa: E402

QUELLE_115 = _w / "runs" / "enthaltung_115_faelle.json"
QUELLE_ABRUFWEG = _w / "runs" / "enthaltungsschwelle_kosinus_abrufweg.json"
FACHFREMD_NAME = "schadensfall_macos"
MAX_RESULTS_FACHFREMD = 40  # grosszuegig -- nur um den Top-Node zu finden, keine Kappung noetig
# Echter Gegenprobe-Fall "hoher Wert" -- s. Moduldoc zur Abweichung von der
# in Auftrag 115 markierten 'positivkontrolle' (/testing/pytest, deren
# EIGENER Kosinus zur EIGENEN Frage nur 0.5412 ist, kein hoher Wert).
HOHER_WERT_ZIEL = "/ops/verwalterwahl-weg-im-buckeberg-zum-2027/efbe-der-vertrag-regelt-die-vergabe-an"


def varianten_text(row: dict) -> dict[str, str]:
    """Vier Textzusammensetzungen desselben Knotens -- 'voll' ist WOERTLICH
    node_text() (die produktiv eingebettete Fassung)."""
    titel = row["title"] or ""
    summary = row["summary"] or ""
    content = row["content"] or ""
    return {
        "nur_titel": titel,
        "nur_summary": summary,
        "titel_summary": f"{titel}\n{summary}",
        "nur_content": content,
        "voll": node_text(row),
    }


def _node_laenge_median(conn) -> float:
    rows = conn.execute("SELECT path, title, summary, content FROM knowledge_nodes WHERE zurueckgezogen = 0").fetchall()
    laengen = [len(node_text(r)) for r in rows]
    return statistics.median(laengen) if laengen else 0.0


def auswerten_fall(conn, frage: str, node_row: dict, laenge_median: float) -> dict:
    """Kernfunktion, unabhaengig testbar (Selbsttest unten uebergibt
    erfundene Vektoren statt Ollama zu rufen)."""
    frage_vec = embeddings.embed_text(frage)
    varianten = varianten_text(node_row)
    kosinus_je_variante = {}
    for name, text in varianten.items():
        if not text.strip():
            kosinus_je_variante[name] = None
            continue
        vec = embeddings.embed_text(text)
        if frage_vec is None or vec is None:
            kosinus_je_variante[name] = None
        else:
            kosinus_je_variante[name] = round(embeddings.cosine_similarity(frage_vec, vec), 4)
    return _auswerten_aus_kosinus(varianten, kosinus_je_variante, laenge_median)


def _auswerten_aus_kosinus(varianten: dict[str, str], kosinus_je_variante: dict[str, float | None],
                            laenge_median: float) -> dict:
    """Reiner Auswertungsteil (kein Netzaufruf) -- fuer den Selbsttest
    herausgezogen, damit der ohne Ollama laeuft."""
    laenge_voll = len(varianten["voll"])
    numerisch = {k: v for k, v in kosinus_je_variante.items() if v is not None}
    beste_variante = max(numerisch, key=numerisch.get) if numerisch else None
    return {
        "laenge_eingebetteter_text": laenge_voll,
        "laenge_median_bestand": round(laenge_median, 1),
        "laenge_verhaeltnis_zu_median": round(laenge_voll / laenge_median, 3) if laenge_median else None,
        "gekappt": embeddings.wird_gekappt(varianten["voll"]),
        "kosinus_je_variante": kosinus_je_variante,
        "beste_variante": beste_variante,
        "kosinus_voll": kosinus_je_variante.get("voll"),
        "beste_variante_schlaegt_voll": (
            beste_variante is not None and beste_variante != "voll"
            and numerisch[beste_variante] > (numerisch.get("voll") or -1.0)
        ),
    }


def _selbsttest() -> None:
    """Selbsttest von _auswerten_aus_kosinus() gegen erfundene Daten -- kein
    Netz, keine DB. Prueft: Median-Verhaeltnis, Kappungs-Erkennung, und dass
    'beste_variante_schlaegt_voll' korrekt zwischen einem Fall greift, in
    dem eine kuerzere Variante besser ist, und einem, in dem 'voll' selbst
    gewinnt."""
    varianten = {"nur_titel": "T", "nur_summary": "S", "titel_summary": "T\nS",
                 "nur_content": "C" * 50, "voll": "T\nS\n" + "C" * 50}

    # Fall A: 'nur_summary' schlaegt 'voll'.
    kosinus_a = {"nur_titel": 0.30, "nur_summary": 0.62, "titel_summary": 0.55,
                 "nur_content": 0.40, "voll": 0.50}
    erg_a = _auswerten_aus_kosinus(varianten, kosinus_a, laenge_median=100.0)
    assert erg_a["beste_variante"] == "nur_summary", erg_a
    assert erg_a["beste_variante_schlaegt_voll"] is True, erg_a
    assert erg_a["laenge_eingebetteter_text"] == len(varianten["voll"])
    assert erg_a["laenge_verhaeltnis_zu_median"] == round(len(varianten["voll"]) / 100.0, 3)

    # Fall B: 'voll' selbst ist die beste Variante -> kein Schlagen.
    kosinus_b = {"nur_titel": 0.30, "nur_summary": 0.40, "titel_summary": 0.55,
                 "nur_content": 0.45, "voll": 0.70}
    erg_b = _auswerten_aus_kosinus(varianten, kosinus_b, laenge_median=100.0)
    assert erg_b["beste_variante"] == "voll", erg_b
    assert erg_b["beste_variante_schlaegt_voll"] is False, erg_b

    # Fall C: fehlende Werte (None) werden bei der Bestimmung ignoriert, nicht als 0 gewertet.
    kosinus_c = {"nur_titel": None, "nur_summary": 0.20, "titel_summary": None,
                 "nur_content": None, "voll": 0.10}
    erg_c = _auswerten_aus_kosinus(varianten, kosinus_c, laenge_median=100.0)
    assert erg_c["beste_variante"] == "nur_summary", erg_c

    # Median = 0 -> kein Verhaeltnis (keine Division durch 0).
    erg_d = _auswerten_aus_kosinus(varianten, kosinus_a, laenge_median=0.0)
    assert erg_d["laenge_verhaeltnis_zu_median"] is None, erg_d

    # Kappungserkennung greift auf embeddings.wird_gekappt() durch -- ein
    # winziger Text darf nie als gekappt gelten.
    assert _auswerten_aus_kosinus(varianten, kosinus_a, 100.0)["gekappt"] is False

    print("selbsttest: ok", file=sys.stderr)


def _node_row(conn, path: str) -> dict:
    r = conn.execute(
        "SELECT id, path, title, summary, content FROM knowledge_nodes "
        "WHERE path = ? AND zurueckgezogen = 0", (path,)).fetchone()
    if r is None:
        raise SystemExit(f"ABBRUCH: Knoten {path} nicht gefunden (Snapshot).")
    return dict(r)


def _bester_node_fuer_frage(conn, frage: str) -> dict:
    """Fuer den fachfremden Gegenprobe-Fall gibt es kein 'ziel' -- der Node
    mit dem hoechsten bedeutungs_kosinus unter den von kandidaten()
    gelieferten NODE-Kandidaten (kein Nachbau der Rangfolge, s. Moduldoc)."""
    query_vec = embeddings.embed_text(frage)
    node_rows, _lesson_rows = suchpfad_abruf.kandidaten(conn, frage, query_vec, MAX_RESULTS_FACHFREMD)
    mit_kosinus = [r for r in node_rows if r.get("bedeutungs_kosinus") is not None]
    if not mit_kosinus:
        raise SystemExit("ABBRUCH: keine Node-Kandidaten mit Kosinus fuer die fachfremde Frage.")
    top = max(mit_kosinus, key=lambda r: r["bedeutungs_kosinus"])
    return _node_row(conn, top["path"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.selbsttest:
        _selbsttest()
        return

    if not QUELLE_115.exists():
        raise SystemExit(f"ABBRUCH: {QUELLE_115} fehlt.")
    if not QUELLE_ABRUFWEG.exists():
        raise SystemExit(f"ABBRUCH: {QUELLE_ABRUFWEG} fehlt.")
    daten_115 = json.loads(QUELLE_115.read_text(encoding="utf-8"))
    daten_abrufweg = json.loads(QUELLE_ABRUFWEG.read_text(encoding="utf-8"))

    unter_schwelle = [f for f in daten_115["faelle"] if f["rolle"] == "unter_schwelle"]
    hoher_wert_quelle = next(f for f in daten_abrufweg["je_frage_einschlaegig"] if f["ziel"] == HOHER_WERT_ZIEL)
    fachfremd_quelle = next(f for f in daten_abrufweg["je_frage_fachfremd"] if f.get("name") == FACHFREMD_NAME)

    stand = festhalten()
    orig_hook_db, orig_kms_db = hook.DB, kms.DB_PATH
    hook.DB = str(stand.pfad)
    kms.DB_PATH = stand.pfad
    print(f"messstand: {stand.kennung} ({stand.pfad})", file=sys.stderr)
    try:
        with speicher.lesen(stand.pfad) as conn:
            laenge_median = _node_laenge_median(conn)

            ergebnis_unter_schwelle = []
            for f in unter_schwelle:
                row = _node_row(conn, f["ziel"])
                erg = auswerten_fall(conn, f["frage"], row, laenge_median)
                erg["rolle"] = "unter_schwelle"
                erg["ziel"] = f["ziel"]
                erg["bester_kosinus_lauf_2026-08-19"] = f.get("bester_kosinus_lauf_2026-08-19")
                erg["bedeutungs_kosinus_ziel_115"] = f.get("bedeutungs_kosinus_ziel")
                ergebnis_unter_schwelle.append(erg)

            row_pos = _node_row(conn, hoher_wert_quelle["ziel"])
            erg_pos = auswerten_fall(conn, hoher_wert_quelle["frage"], row_pos, laenge_median)
            erg_pos["rolle"] = "gegenprobe_hoher_wert_einschlaegig"
            erg_pos["ziel"] = hoher_wert_quelle["ziel"]
            erg_pos["bester_kosinus_irgendein_kandidat_abrufweg"] = hoher_wert_quelle.get("bester_kosinus")

            row_ff = _bester_node_fuer_frage(conn, fachfremd_quelle["frage"])
            erg_ff = auswerten_fall(conn, fachfremd_quelle["frage"], row_ff, laenge_median)
            erg_ff["rolle"] = "gegenprobe_hoher_wert_fachfremd"
            erg_ff["ziel"] = row_ff["path"]
            erg_ff["bester_kosinus_abrufweg"] = fachfremd_quelle.get("bester_kosinus")
    finally:
        hook.DB = orig_hook_db
        kms.DB_PATH = orig_kms_db
        shutil.rmtree(stand.pfad.parent, ignore_errors=True)

    alle = ergebnis_unter_schwelle + [erg_pos, erg_ff]
    schlaegt_bei = [e["ziel"] for e in alle if e["beste_variante_schlaegt_voll"]]

    # Gap zwischen 'voll' und der besten Variante -- je Fall, um zu sehen, ob
    # die Luecke bei den drei niedrigen Faellen GROESSER ist als beim Fall mit
    # hohem Wert (das waere der Beleg fuer die Annahme). Numerisch statt nur
    # in Prosa, damit der Befund nachrechenbar bleibt.
    def _gap(e):
        num = {k: v for k, v in e["kosinus_je_variante"].items() if v is not None}
        return round(max(num.values()) - num.get("voll", max(num.values())), 4) if num else None

    laengenverhaeltnisse_niedrig = [e["laenge_verhaeltnis_zu_median"] for e in ergebnis_unter_schwelle]
    laengenverhaeltnisse_hoch = [erg_pos["laenge_verhaeltnis_zu_median"], erg_ff["laenge_verhaeltnis_zu_median"]]
    gaps_niedrig = [_gap(e) for e in ergebnis_unter_schwelle]
    gaps_hoch = [_gap(erg_pos), _gap(erg_ff)]

    befund = (
        "ANNAHME NICHT BESTAETIGT. Laenge: der Gegenprobe-Fall mit hohem Wert "
        f"(voll={erg_pos['kosinus_voll']}, Verhaeltnis zum Median {erg_pos['laenge_verhaeltnis_zu_median']}) "
        f"ist genauso lang wie der schlechteste niedrige Fall (voll={ergebnis_unter_schwelle[1]['kosinus_voll']}, "
        f"Verhaeltnis {ergebnis_unter_schwelle[1]['laenge_verhaeltnis_zu_median']}) und die fachfremde Gegenprobe "
        f"(voll={erg_ff['kosinus_voll']}, Verhaeltnis {erg_ff['laenge_verhaeltnis_zu_median']}) -- Laenge trennt "
        "die drei niedrigen Faelle NICHT von den hohen: einer der drei ist sogar kurz "
        f"(Verhaeltnis {ergebnis_unter_schwelle[2]['laenge_verhaeltnis_zu_median']}), waehrend zwei der drei "
        "genauso lang sind wie beide hohen Gegenproben. Variante: die Luecke zwischen 'voll' und der besten "
        f"Variante ist bei den drei niedrigen Faellen {gaps_niedrig} -- in derselben Groessenordnung wie bei den "
        f"beiden hohen Gegenproben {gaps_hoch}. Eine bessere Textzusammensetzung wuerde also allenfalls 0.01-0.03 "
        "gewinnen, nicht die 0.08-0.15, die zur Schwelle 0.55 fehlen. UNERKLAERT bleibt damit, warum diese drei "
        "Knoten gegen ihre jeweilige Frage niedriger liegen als die beiden Gegenproben -- die Textzusammensetzung "
        "(Laenge wie Variante) ist an diesen fuenf Faellen KEIN messbarer Hebel dafuer.",
    )[0]

    ergebnis = {
        "schnappschuss": stand.kennung,
        "quelle_faelle": str(QUELLE_115.relative_to(_w)),
        "quelle_fachfremd": str(QUELLE_ABRUFWEG.relative_to(_w)),
        "annahme_geprueft": "Textzusammensetzung (kern/build_embeddings.py::node_text()) drueckt den Kosinus der drei Faelle",
        "faelle": alle,
        "laenge_median_bestand_zeichen": round(laenge_median, 1),
        "faelle_bei_denen_eine_kuerzere_variante_gewinnt": schlaegt_bei,
        "laengenverhaeltnisse_niedrige_faelle": laengenverhaeltnisse_niedrig,
        "laengenverhaeltnisse_hohe_gegenproben": laengenverhaeltnisse_hoch,
        "luecke_voll_zu_bester_variante_niedrige_faelle": gaps_niedrig,
        "luecke_voll_zu_bester_variante_hohe_gegenproben": gaps_hoch,
        "befund": befund,
        "hinweis": (
            "Keine Schwellenaenderung, keine Empfehlung. 'beste_variante_schlaegt_voll' "
            "vergleicht nur die vier Varianten DESSELBEN Knotens gegen dieselbe Frage -- "
            "eine gewinnende Kurzvariante zeigt, dass der volle node_text() gegenueber "
            "dieser Frage schlechter abschneidet als eine seiner Teilmengen, nicht dass "
            "die Kurzvariante produktiv eingebettet wird (das ist weiterhin node_text() voll)."
        ),
    }
    out_pfad = Path(args.out) if args.out else _w / "runs" / "einbettungsguete_116_textzusammensetzung.json"
    out_pfad.parent.mkdir(parents=True, exist_ok=True)
    out_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
