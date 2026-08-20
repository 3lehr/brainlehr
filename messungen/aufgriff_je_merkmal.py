"""Welche VORHANDENEN Merkmale trennen aufgegriffene von nie aufgegriffenen
Eintraegen?

FRAGE DES BETREIBERS (2026-08-20): "welche faktoren bleiben uns dann uebrig?
welche faktoren haben wir noch nicht bedacht lassen sich aber aus unseren
daten und oder unsere daten plus weiteren knoten und oder weiteren
metadatenknotenpunkt bilden?"

Geprueft werden ausschliesslich Merkmale, die HEUTE SCHON im Bestand stehen
und die bisher in keiner Rangfunktion vorkommen:

  anlass         selbst | betreiber | hook | skript | unbekannt   (100 % gefuellt)
  severity       critical | high | medium | low, nur Lehren        (100 % gefuellt)
  occurrences    Wiederholungszahl einer Lehre                     (100 % gefuellt)
  beinahefehler  0/1, nur Lehren                                   (100 % gefuellt)
  type           error | insight | pattern | antipattern           (100 % gefuellt)
  norm_rang      1/2/3, nur Knoten                                 (3 % gefuellt)
  kanten_ausser_aehnlichkeit  abgeleitet_von/loest_ab/supersedes/...

WAS DAS NICHT IST: keine Rangfunktion und kein Vorschlag fuer eine. Der
Aufgriff bleibt eine Eigenschaft des PAARES aus Frage und Eintrag
(Betreiber, 2026-08-20: "koennte aber beim 21. Mal nuetzlich sein wenn die
fragestellung anderst ist ... oder von jemand anderen gefragt wuerde, oder zu
einem anderen zeitpunkt"). Diese Messung fragt nur, ob ein Merkmal ueberhaupt
mit dem Aufgriff zusammenhaengt -- eine Bestandsaussage, kein Gewicht.

Nur lesend. Nutzt hauptlauf() aus messungen/aufgriffsquote_2026-08-20.py.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "kern")]
import rueckwirkung as _rw  # noqa: E402
import speicher  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "aq", _w / "messungen" / "aufgriffsquote_2026-08-20.py")
aq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aq)

MINDESTZAHL = 20


def merkmale_holen(kennungen: set) -> dict:
    """Alle geprueften Merkmale in EINEM Lesezugriff je Tabelle."""
    out = defaultdict(dict)
    with speicher.lesen() as c:
        for r in c.execute("SELECT path, id, anlass, norm_rang, gattung FROM knowledge_nodes"):
            for schluessel in (r["path"], r["id"]):
                if schluessel in kennungen:
                    out[schluessel] = {"art": "knoten", "anlass": r["anlass"],
                                       "norm_rang": r["norm_rang"], "gattung": r["gattung"]}
        for r in c.execute("SELECT id, anlass, severity, occurrences, beinahefehler, type "
                           "FROM lessons_learned"):
            if r["id"] in kennungen:
                out[r["id"]] = {"art": "lehre", "anlass": r["anlass"],
                                "severity": r["severity"], "occurrences": r["occurrences"],
                                "beinahefehler": r["beinahefehler"], "type": r["type"]}
        # Kanten AUSSER Bedeutungsaehnlichkeit -- die 10117 aehnlich_bedeutung
        # sind der Dublettengraph und sagen nichts ueber Bewaehrung.
        grade = defaultdict(int)
        for r in c.execute("SELECT source_path, target_path FROM knowledge_relations "
                           "WHERE relation_type != 'aehnlich_bedeutung'"):
            grade[r["source_path"]] += 1
            grade[r["target_path"]] += 1
    for k in out:
        out[k]["kanten_ausser_aehnlichkeit"] = grade.get(k, 0)
    return out


def auswerten(je_kennung: dict, merkmale: dict) -> dict:
    tabelle = {}
    felder = ["anlass", "severity", "type", "norm_rang", "gattung", "beinahefehler"]
    for feld in felder:
        gruppen = defaultdict(list)
        for kennung, satz in je_kennung.items():
            m = merkmale.get(kennung)
            if not m or feld not in m:
                continue
            gruppen[str(m[feld])].append(satz)
        zeilen = {}
        for wert, saetze in sorted(gruppen.items(), key=lambda x: -len(x[1])):
            b = _rw.zaehle(saetze, lambda s: bool(s.get("benutzt")))
            zeilen[wert] = {"nenner": b.nenner, "treffer": b.treffer,
                            "quote_prozent": round(100 * b.quote, 1),
                            "deutbar": b.nenner >= MINDESTZAHL}
        if zeilen:
            tabelle[feld] = zeilen

    # Zahlwerte gebaendert statt roh -- eine Quote je Einzelwert waere Rauschen.
    for feld, baender in (("occurrences", [(1, 1), (2, 3), (4, 99)]),
                          ("kanten_ausser_aehnlichkeit", [(0, 0), (1, 2), (3, 999)])):
        zeilen = {}
        for lo, hi in baender:
            saetze = [s for k, s in je_kennung.items()
                      if merkmale.get(k) and isinstance(merkmale[k].get(feld), int)
                      and lo <= merkmale[k][feld] <= hi]
            if not saetze:
                continue
            b = _rw.zaehle(saetze, lambda s: bool(s.get("benutzt")))
            zeilen[f"{lo}-{hi}"] = {"nenner": b.nenner, "treffer": b.treffer,
                                    "quote_prozent": round(100 * b.quote, 1),
                                    "deutbar": b.nenner >= MINDESTZAHL}
        if zeilen:
            tabelle[feld] = zeilen
    return tabelle


def main() -> int:
    roh = aq.hauptlauf()
    je_kennung = roh.get("je_kennung") or {}
    if not je_kennung:
        print("ABBRUCH: hauptlauf() liefert keine Einzelkennungen.")
        return 2
    merkmale = merkmale_holen(set(je_kennung))
    tabelle = auswerten(je_kennung, merkmale)

    for feld, zeilen in tabelle.items():
        print(f"\n== {feld} ==")
        for wert, v in sorted(zeilen.items(), key=lambda x: -x[1]["nenner"]):
            marke = "" if v["deutbar"] else f"   (unter {MINDESTZAHL}, nicht deutbar)"
            print(f"   {wert:<14} {v['treffer']:>4} von {v['nenner']:>4} = {v['quote_prozent']:>5}%{marke}")

    ziel = _w / "runs" / "aufgriff_je_merkmal_2026-08-20.json"
    ziel.write_text(json.dumps({
        "messung": "Aufgriffsquote je vorhandenem Merkmal",
        "vorbehalt": ("Bestandsaussage, KEIN Rangvorschlag. Der Aufgriff ist eine "
                      "Eigenschaft des Paares aus Frage und Eintrag und haengt an "
                      "Zeitraum und Fragendem (zehn Tage, im Wesentlichen ein Fragender)."),
        "mindestzahl_zum_deuten": MINDESTZAHL,
        "je_merkmal": tabelle,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngeschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
