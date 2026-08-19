#!/usr/bin/env python3
"""Datengrundlage fuer eine Enthaltungsschwelle auf `bedeutungs_kosinus`
(seit Commit 4c88915b Teil jedes Treffers aus knowledge_mcp_server.
knowledge_search(), roher Kosinus des Bedeutungskanals, None ohne Vektor).

Vorlaufmessung runs/enthaltung_114_2026-08-19.json hatte n=20 (10/10) und war
zu duenn (Auftrag, woertlich). Diese Datei erweitert beide Seiten:

  EINSCHLAEGIG: alle 35 Faelle aus runs/pruefkorpus.jsonl mit target_kind
  gesetzt (category in lesson/fact/norm, accepted=true) -- dieselbe Menge wie
  messungen/vier_gatearten.py::lade_faelle liefert, hier NICHT neu erfunden,
  sondern importiert. Keine Auswahl, alle verfuegbaren Faelle.

  FACHFREMD: 40 Fragen aus Sachgebieten, zu denen dieser Bestand (Code/
  Rechtslage WEG+Steuer/Lehre) nichts fuehrt. Die ersten 10 sind woertlich
  die category=negative-Faelle aus runs/pruefkorpus.jsonl (lagen vor diesem
  Auftrag schon dort, nicht neu angelegt) -- darunter die zwei belegten
  Schadensfaelle aus runs/wirkung_llm_probe_2026-08-19T084859.json:
  "schadensfall_plane" (Seemannsknoten, System sagte "Kaliblerbremse" statt
  "Mastwurf") und "schadensfall_macos" (Bildschirmaufloesung, System sagte
  "displaychanger" statt "displayplacer"). 30 weitere neu ergaenzt, um
  Kochen/Garten/Seefahrt/Astronomie/Medizin/Sport/Musik/Recht-ausserhalb-WEG-
  Steuer/Alltagstechnik auf mindestens 40 zu bringen.

WEG: knowledge_mcp_server.knowledge_search() -- kein Nachbau. Bester Kosinus
je Frage = max(bedeutungs_kosinus) ueber alle Treffer, None gefiltert (kein
Vektor). Eine Frage ganz ohne Treffer bzw. ganz ohne Vektor-Treffer liefert
None -- das ist unten als eigener Fall behandelt (zaehlt fuer Enthaltung
IMMER richtig, weil unterhalb jeder Schwelle).

SCHNAPPSCHUSS: genau einer je Lauf (kern/schnappschuss.py::festhalten()),
kms.DB_PATH danach umgebogen -- wie in messungen/wirkung_llm_probe.py.

Auftrag ausdruecklich: KEINE Empfehlung fuer eine Schwelle. Nur die
Zahlen, beide Fehlerarten nebeneinander, und die Ueberlappung benannt.

Aufruf:
    python3 messungen/enthaltungsschwelle_kosinus.py --selbsttest
    python3 messungen/enthaltungsschwelle_kosinus.py --out runs/<datei>.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "messungen")]

import knowledge_mcp_server as kms  # noqa: E402 -- Produktivweg, kein Nachbau
from vier_gatearten import KORPUS, lade_faelle  # noqa: E402 -- 35 Zielfaelle, nicht neu erfunden
from schnappschuss import festhalten  # noqa: E402

MAX_RESULTS = 50

# Die ersten 10 sind woertlich runs/pruefkorpus.jsonl, category=negative
# (vor diesem Auftrag schon dort). "name" nur bei den zwei belegten
# Schadensfaellen gesetzt -- fuer die Abnahme muessen sie als Einzelfall
# auffindbar sein.
FACHFREMD: list[dict] = [
    {"domain": "alltagstechnik", "name": "schadensfall_macos",
     "frage": "Wie stellt man in macOS die Bildschirmaufloesung per Terminal-Befehl ein?"},
    {"domain": "seefahrt", "name": "schadensfall_plane",
     "frage": "Welcher Knoten eignet sich zum schnellen, loesbaren Verzurren einer Plane?"},
    {"domain": "alltagstechnik", "frage": "Nenne den kubectl-Befehl, um alle Pods im Namespace default aufzulisten."},
    {"domain": "recht_sonstig", "frage": "Welches Papier braucht ein Restaurant fuer die Anmeldung beim Ordnungsamt?"},
    {"domain": "kochen", "frage": "Beschreibe in 2 Saetzen, wie man einen Hefeteig fuer Pizza ansetzt."},
    {"domain": "astronomie", "frage": "Wie berechnet man die Umlaufbahnperiode eines Satelliten aus der Bahnhoehe?"},
    {"domain": "kochen", "frage": "Nenne die Zutaten fuer einen klassischen Bechamel."},
    {"domain": "garten", "frage": "Nenne drei Faustregeln fuer Rosenschnitt im Fruehjahr."},
    {"domain": "alltagstechnik", "frage": "Erklaere kurz den Unterschied zwischen TCP und UDP."},
    {"domain": "alltagstechnik", "frage": "Wie lautet der Befehl, um in git einen Branch umzubenennen (lokal + remote)?"},
    # 30 neu ergaenzt
    {"domain": "kochen", "frage": "Wie lange muss ein Steak vor dem Braten Zimmertemperatur annehmen?"},
    {"domain": "kochen", "frage": "Welches Gewuerz gehoert klassisch in ein Gulasch?"},
    {"domain": "kochen", "frage": "Wie erkennt man am Klang, ob ein Brot fertig gebacken ist?"},
    {"domain": "garten", "frage": "Wann ist die beste Pflanzzeit fuer Tulpenzwiebeln?"},
    {"domain": "garten", "frage": "Wie schuetzt man Kuebelpflanzen vor Frost auf dem Balkon?"},
    {"domain": "garten", "frage": "Welcher Boden-pH-Wert eignet sich fuer Hortensien mit blauen Blueten?"},
    {"domain": "seefahrt", "frage": "Was bedeutet die Abkuerzung 'Lee' beim Segeln?"},
    {"domain": "seefahrt", "frage": "Wie wird ein Palstek geknuepft und wofuer wird er verwendet?"},
    {"domain": "seefahrt", "frage": "Was zeigt ein gruenes Backbord-Licht bei einem entgegenkommenden Schiff an?"},
    {"domain": "astronomie", "frage": "Warum ist der Mond bei Vollmond manchmal roetlich gefaerbt?"},
    {"domain": "astronomie", "frage": "Was unterscheidet einen Zwergplaneten von einem Planeten?"},
    {"domain": "astronomie", "frage": "Wie weit ist der naechste Stern ausserhalb unseres Sonnensystems entfernt?"},
    {"domain": "medizin", "frage": "Welche Erste-Hilfe-Schritte gelten bei einer Verbrennung ersten Grades?"},
    {"domain": "medizin", "frage": "Was ist der Unterschied zwischen einer Virus- und einer Bakterieninfektion?"},
    {"domain": "medizin", "frage": "Wie lange sollte man nach einer Gehirnerschuetterung auf Sport verzichten?"},
    {"domain": "sport", "frage": "Wie viele Spieler stehen bei einem Volleyballteam gleichzeitig auf dem Feld?"},
    {"domain": "sport", "frage": "Was ist ein Abseits im Fussball?"},
    {"domain": "sport", "frage": "Welche Muskelgruppen trainiert eine klassische Kniebeuge vorrangig?"},
    {"domain": "musik", "frage": "Wie viele Halbtoene hat eine Oktave in der westlichen Musiktheorie?"},
    {"domain": "musik", "frage": "Was unterscheidet eine Dur- von einer Molltonleiter?"},
    {"domain": "musik", "frage": "Welches Instrument hat typischerweise 88 Tasten?"},
    {"domain": "recht_sonstig", "frage": "Wie lange ist ein Fuehrerschein der Klasse B in Deutschland gueltig, bevor er erneuert werden muss?"},
    {"domain": "recht_sonstig", "frage": "Welche Frist gilt fuer den Widerruf eines Onlinekaufs nach dem Fernabsatzrecht?"},
    {"domain": "recht_sonstig", "frage": "Ab welchem Alter duerfen Jugendliche in Deutschland allein ins Kino, wenn der Film ab 12 freigegeben ist?"},
    {"domain": "alltagstechnik", "frage": "Wie setzt man einen WLAN-Router auf die Werkseinstellungen zurueck?"},
    {"domain": "alltagstechnik", "frage": "Was bedeutet die IP-Schutzklasse IP67 bei einem Smartphone?"},
    {"domain": "alltagstechnik", "frage": "Wie wechselt man den Toner in einem Laserdrucker aus?"},
    {"domain": "kochen", "frage": "Wie stellt man eine einfache Vinaigrette fuer Salat her?"},
    {"domain": "garten", "frage": "Wie oft sollte Rasen im Sommer gemaeht werden?"},
    {"domain": "medizin", "frage": "Was hilft am ehesten gegen einen leichten Sonnenbrand?"},
    {"domain": "sport", "frage": "Wie lang ist eine olympische Schwimmbahn?"},
]


def bester_kosinus(frage: str) -> float | None:
    """Hoechster bedeutungs_kosinus ueber alle Treffer der Anfrage, None
    filtert Nicht-Vektor-Treffer heraus. Kein Treffer bzw. kein einziger mit
    Vektor -> None (unterhalb jeder Schwelle, siehe Auswertung)."""
    out = kms.knowledge_search(frage, scope="all", max_results=MAX_RESULTS)
    werte = [r["bedeutungs_kosinus"] for r in out["results"] if r.get("bedeutungs_kosinus") is not None]
    return round(max(werte), 4) if werte else None


def auswerten(einschlaegig: list[float | None], fachfremd: list[float | None],
               schritt: float = 0.01) -> list[dict]:
    """Schwellentabelle ueber den beobachteten Bereich (min bis max aller
    NICHT-None-Werte beider Seiten), in `schritt`-Stufen. Je Schwelle S:
      faelschlich_enthalten = einschlaegige Frage mit bestem Kosinus < S
                               ODER ohne Wert (None), weil dann der Speicher
                               unter jeder Schwelle schweigt.
      faelschlich_geliefert = fachfremde Frage mit bestem Kosinus >= S.
    Leere Eingabelisten -> leere Tabelle (kein Bereich definiert)."""
    alle_werte = [w for w in einschlaegig + fachfremd if w is not None]
    if not alle_werte:
        return []
    lo = round(min(alle_werte), 2)
    hi = round(max(alle_werte), 2)
    zeilen = []
    s = lo
    # ueber ganze Cents iterieren, keine Gleitkomma-Drift
    n_stufen = round((hi - lo) / schritt) + 1
    for k in range(n_stufen):
        s = round(lo + k * schritt, 2)
        fe = sum(1 for w in einschlaegig if w is None or w < s)
        fg = sum(1 for w in fachfremd if w is not None and w >= s)
        zeilen.append({
            "schwelle": s,
            "faelschlich_enthalten": fe,
            "faelschlich_enthalten_quote": round(fe / len(einschlaegig), 4) if einschlaegig else None,
            "faelschlich_geliefert": fg,
            "faelschlich_geliefert_quote": round(fg / len(fachfremd), 4) if fachfremd else None,
        })
    return zeilen


def _selbsttest() -> None:
    # zwei erfundene Seiten, disjunkt bis auf einen Ueberlappungspunkt bei 0.5
    einschlaegig = [0.6, 0.55, 0.5, None]
    fachfremd = [0.3, 0.4, 0.5]
    tab = auswerten(einschlaegig, fachfremd, schritt=0.1)
    by_s = {z["schwelle"]: z for z in tab}

    # Schwelle 0.3: alles fachfremd >= 0.3 liegt drueber (3 von 3) -- faelschlich_geliefert.
    assert by_s[0.3]["faelschlich_geliefert"] == 3, by_s[0.3]
    # bei 0.3 ist kein einschlaegiger Wert < 0.3 (und der None zaehlt IMMER) -> 1.
    assert by_s[0.3]["faelschlich_enthalten"] == 1, by_s[0.3]

    # Schwelle 0.6: nur der 0.6-Wert liegt >=, die drei anderen (0.55, 0.5, None)
    # liegen darunter bzw. sind None -> 3 faelschlich_enthalten.
    assert by_s[0.6]["faelschlich_enthalten"] == 3, by_s[0.6]
    # kein fachfremder Wert erreicht 0.6 -> 0 faelschlich_geliefert.
    assert by_s[0.6]["faelschlich_geliefert"] == 0, by_s[0.6]

    # Grenzfall: Schwelle GENAU auf einem beobachteten Wert (0.5, kommt auf
    # beiden Seiten vor). Bei S=0.5: einschlaegig 0.5 zaehlt NICHT als
    # faelschlich_enthalten (0.5 < 0.5 ist falsch) -- nur 0.5 selbst faellt
    # raus, None bleibt immer drin -> 1 (der None-Fall). fachfremd 0.5 IST
    # >= 0.5 -> zaehlt als faelschlich_geliefert (1 von 3, die anderen zwei
    # liegen darunter).
    assert by_s[0.5]["faelschlich_enthalten"] == 1, by_s[0.5]
    assert by_s[0.5]["faelschlich_geliefert"] == 1, by_s[0.5]

    # leere Eingabe -> leere Tabelle, kein Crash
    assert auswerten([], []) == []

    print("selbsttest: ok", file=sys.stderr)


def messstand() -> str:
    """Genau ein Schnappschuss je Lauf, kms.DB_PATH wird zur Aufrufzeit in
    get_db() gelesen -- siehe messungen/wirkung_llm_probe.py::messstand()."""
    stand = festhalten()
    kms.DB_PATH = stand.pfad
    print(f"messstand: {stand.kennung} ({stand.pfad})", file=sys.stderr)
    return stand.kennung


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selbsttest", action="store_true")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    if args.selbsttest:
        _selbsttest()
        return

    if not KORPUS.exists():
        print(f"ABBRUCH: Pruefkorpus fehlt: {KORPUS}", file=sys.stderr)
        sys.exit(1)

    stand_kennung = messstand()

    faelle_mit_ziel, _ = lade_faelle(KORPUS)

    einschlaegig_zeilen = []
    for f in faelle_mit_ziel:
        wert = bester_kosinus(f["task"])
        einschlaegig_zeilen.append({"art": "einschlaegig", "ziel": f["target_id"],
                                     "frage": f["task"], "bester_kosinus": wert})

    fachfremd_zeilen = []
    for f in FACHFREMD:
        wert = bester_kosinus(f["frage"])
        eintrag = {"art": "fachfremd", "domain": f["domain"], "frage": f["frage"],
                   "bester_kosinus": wert}
        if "name" in f:
            eintrag["name"] = f["name"]
        fachfremd_zeilen.append(eintrag)

    e_werte = [z["bester_kosinus"] for z in einschlaegig_zeilen]
    f_werte = [z["bester_kosinus"] for z in fachfremd_zeilen]
    e_werte_num = [w for w in e_werte if w is not None]
    f_werte_num = [w for w in f_werte if w is not None]

    # Abnahme 1: mindestens eine fachfremde Frage klar niedriger als
    # mindestens eine einschlaegige.
    positivkontrolle_bestanden = bool(e_werte_num) and bool(f_werte_num) and \
        min(f_werte_num) < max(e_werte_num)

    # Ueberlappung: Bereich [min(einschlaegig), max(einschlaegig)] gegen
    # [min(fachfremd), max(fachfremd)] -- ueberlappen sich die Intervalle?
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

    schadensfaelle = {z["name"]: z for z in fachfremd_zeilen if "name" in z}

    ergebnis = {
        "schnappschuss": stand_kennung,
        "weg": "knowledge_mcp_server.knowledge_search() -- echter Produktivweg, kein Nachbau",
        "n": {"einschlaegig": len(einschlaegig_zeilen), "fachfremd": len(fachfremd_zeilen)},
        "quelle_einschlaegig": "runs/pruefkorpus.jsonl ueber vier_gatearten.lade_faelle() -- "
                                "alle 35 Faelle mit target_kind, category in (lesson,fact,norm), "
                                "accepted=true, keine Auswahl",
        "quelle_fachfremd": "10 woertlich aus runs/pruefkorpus.jsonl (category=negative, vor "
                             "diesem Auftrag vorhanden) + 30 neu ergaenzt (Kochen, Garten, "
                             "Seefahrt, Astronomie, Medizin, Sport, Musik, Recht ausserhalb "
                             "WEG/Steuer, Alltagstechnik)",
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
        "hinweis": "Keine Schwelle wird hier empfohlen oder als richtig bezeichnet -- "
                   "'faelschlich_enthalten' (Speicher schweigt trotz Ziel) und "
                   "'faelschlich_geliefert' (Speicher liefert bei fachfremder Frage) stehen "
                   "nebeneinander, die Wahl faellt woanders.",
    }

    if not positivkontrolle_bestanden:
        print("BEFUND: Positivkontrolle nicht bestanden -- Aufbau verdaechtig, siehe Ergebnis.",
              file=sys.stderr)

    out_pfad = Path(args.out) if args.out else _w / "runs" / "enthaltungsschwelle_kosinus.json"
    out_pfad.parent.mkdir(parents=True, exist_ok=True)
    out_pfad.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"geschrieben: {out_pfad}", file=sys.stderr)


if __name__ == "__main__":
    main()
