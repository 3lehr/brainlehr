"""Gegenprobe zu S4: War der Befund "Korpus urteilt zu mild" ein Artefakt des
BEURTEILUNGSFENSTERS?

BEFUND AUS S4 (runs/beurteilung_blind_2026-08-20.json): Die blinde
Wiederholung urteilte bei 7 von 15 gezaehlten Treffern DANEBEN oder
TEILWEISE -- gelesen als "der Pruefkorpus urteilt zu mild".

DER VERDACHT: Beide Beurteilungen sahen nur die TOP 3 der ausgelieferten
Zeilen. Der Messlauf zaehlt einen Treffer aber, wenn das Ziel innerhalb der
tatsaechlich ausgelieferten Menge steht -- MAX_NODES = 10 bei Knoten,
MAX_LESSONS = 7 bei Lehren. Ein Ziel auf Rang 4 bis 10 ist ausgeliefert und
war fuer die Beurteilung unsichtbar.

GEMESSEN, 2026-08-20: 6 von 7. Nur L-0392e4 lag auf Rang 1 und ist damit ein
echter Widerspruch zwischen Korpus und Urteil.

  /apps/metahuman-podcast-one-command-pipeline          Rang 8
  /ops/verwalterwahl-weg-im-buckeberg.../vor-der-wahl   Rang 7
  /ops/buckeberg-konsil-2026-07-22-governance           Rang 5
  /methodik/adr-bestand.../adr-007-trust-zones          Rang 4
  L-a9ccd0                                              Rang 4
  L-e7bc5e                                              Rang 4
  L-0392e4                                              Rang 1   <- echter Widerspruch

FOLGE: Der Satz "der Pruefkorpus urteilt zu mild" traegt in dieser Form
NICHT. Er beschreibt zu 6 von 7 Teilen das Fenster der Beurteilung, nicht den
Korpus. Die Aussage der Gegenrichtung ("zu streng", 4 von 20) bleibt davon
unberuehrt -- dort wurde etwas als Fehlgriff gezaehlt, das die Beurteilung
als beantwortet ansah, und ein zu kleines Fenster kann das nicht erzeugen.

DIESELBE FEHLERKLASSE WIE DREIMAL AN DIESEM TAG: gemessen wurde ueber einen
GEDECKELTEN Kanal, und die Deckelung wurde als Eigenschaft des Gegenstands
gelesen (vgl. L-c2f6ee: "Ist dieser Kanal VOLLSTAENDIG oder ein Fenster?").
Hier war das Fenster die Zahl 3 in der Aufbereitung fuer die Beurteilung.

Nur lesend. Nutzt kreuztabelle_bc.instrumented_run() und messlauf_abrufguete
unveraendert -- kein zweiter Messweg.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken"), str(_w / "messungen")]

import kreuztabelle_bc as kb  # noqa: E402
import messlauf_abrufguete as ml  # noqa: E402
import rueckwirkung as _rw  # noqa: E402

BEURTEILTES_FENSTER = 3


def main() -> int:
    quelle = _w / "runs" / "beurteilung_blind_2026-08-20.json"
    d = json.loads(quelle.read_text())
    mild = list(d["aufloesung_vergleich"]["korpus_zu_mild"]["faelle"])
    cases = {c["target_id"]: c for c in ml.load_cases() if c.get("target_id")}

    je_fall = []
    with ml._gegen_schnappschuss():
        with ml._with_state(ml.STATES["B_2Kanal_an_Pflicht_aus"]):
            for ziel in sorted(mild):
                c = cases.get(ziel)
                if not c:
                    je_fall.append({"ziel": ziel, "rang": None, "grund": "kein Korpusfall"})
                    continue
                roh = kb.instrumented_run(c)
                geliefert = ([n["path"] for n in roh["nodes"]] if c["target_kind"] == "node"
                             else [l["id"] for l in roh["lessons"]])
                rang = geliefert.index(ziel) + 1 if ziel in geliefert else None
                je_fall.append({"ziel": ziel, "target_kind": c["target_kind"], "rang": rang,
                                "artefakt_des_fensters": bool(rang and rang > BEURTEILTES_FENSTER)})

    b = _rw.zaehle(je_fall, lambda f: bool(f.get("artefakt_des_fensters")),
                   lambda f: f"{f['ziel']} (Rang {f['rang']})")
    zeile = b.zeile("'Korpus zu mild'-Faelle, die ein Artefakt des Beurteilungsfensters sind",
                    f"ueber die {len(je_fall)} von S4 so eingestuften Faelle, Fenster = {BEURTEILTES_FENSTER}")
    print(zeile)
    for f in je_fall:
        marke = "  <- Artefakt" if f.get("artefakt_des_fensters") else ""
        print(f"    {f['ziel'][:56]:<58} Rang {f['rang']}{marke}")

    ziel_datei = _w / "runs" / "beurteilungsfenster_2026-08-20.json"
    ziel_datei.write_text(json.dumps({
        "messung": "Gegenprobe zu S4: Beurteilungsfenster gegen Auslieferungsfenster",
        "beurteiltes_fenster": BEURTEILTES_FENSTER,
        "auslieferung": {"MAX_NODES": 10, "MAX_LESSONS": 7},
        "zeile": zeile,
        "artefakt": b.treffer, "nenner": b.nenner,
        "je_fall": je_fall,
        "folge": ("Der Satz 'der Pruefkorpus urteilt zu mild' traegt in dieser Form nicht -- "
                  "er beschreibt zu " + f"{b.treffer} von {b.nenner}" + " Teilen das Fenster der "
                  "Beurteilung. Die Gegenrichtung ('zu streng', 4 von 20) bleibt unberuehrt: "
                  "ein zu kleines Fenster kann sie nicht erzeugen."),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngeschrieben: {ziel_datei}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
