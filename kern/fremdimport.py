#!/usr/bin/env python3
"""Fremdbestände holen — mit einer Whitelist, nicht mit einer Säuberung.

ANLASS: Die Lizenzprüfung vom 2026-08-11 (Prüfspruch #7) ergab für FDA MAUDE
CC0 1.0 — urheberrechtlich frei — und trotzdem einen bestätigten Art.-9-Gehalt.
Der Betreiber schlug vor, den Bestand zu nehmen und hinterher zu
anonymisieren. Dagegen sprechen zwei Dinge, und beide sind hier eingebaut
statt bloß aufgeschrieben:

1. Nachträglich entfernen ändert nichts daran, dass es da war. Die
   Verarbeitung beginnt beim Abruf, nicht bei der Auswertung. Und
   pseudonymisierte Daten bleiben personenbezogen (Erwägungsgrund 26,
   Knoten 3e955504 sagt das für den eigenen Enigma-Proxy ausdrücklich).
2. Jede Blacklist hat ein Loch, und bei personenbezogenen Daten ist das Loch
   genau dort (Hausknoten zur Extraktion aus Dokumenten). Eine Whitelist hat
   diese Eigenschaft nicht: was nicht genannt ist, kommt nicht mit.

DER VORBILDFALL AUS DEM EIGENEN HAUS: wohlair hält vier Gesundheitsfelder aus
dem LAN-Abgleich heraus, und zwar nicht per Vorsatz, sondern per
test/privacy/health_fields_stay_local_test.dart — ein Test, der die Feldnamen
im Quelltext SUCHT und fehlschlägt, wenn sie auftauchen (L-e9aa47: ein
Entwurf hätte sie beinahe aufgenommen, ohne dass Compiler oder Analyzer
gemeckert hätten). Dieselbe Bauform hier, eine Ebene früher: die Felder
kommen gar nicht erst herein.

DREI STUFEN, die nacheinander greifen -- Verteidigung in der Tiefe, weil eine
einzelne Bedingung genau einmal falsch sein muss:

  1. PROJEKTION   Aus jedem Datensatz wird NUR gebaut, was in `erlaubt` steht.
                  Kein Filtern, kein Entfernen -- ein neuer Satz aus alten
                  Teilen. Fügt die Quelle morgen ein Feld hinzu, ist es
                  automatisch draußen.
  2. GEGENPROBE   Der gebaute Satz wird danach nach den verbotenen Namen
                  DURCHSUCHT, rekursiv. Findet sich einer, bricht der Import
                  ab -- das fängt den Fall, dass ein erlaubtes Feld ein
                  verbotenes verschachtelt enthält.
  3. GATTUNG      Alles landet als `nachschlagewerk`, nimmt also am
                  automatischen Abruf nicht teil (wie NASA LLIS). Ein
                  Fremdbestand drängt sich nicht auf, man schlägt darin nach.

WAS DAS NICHT LEISTET: Es macht keine Rechtsaussage. Ob der projizierte
Datensatz personenbezogen ist, entscheidet nicht dieses Programm --
kanonymitaet.py sagt aus gutem Grund denselben Satz über sich selbst. Es
stellt nur sicher, dass die Felder, die den Personenbezug tragen, den Rechner
nie erreichen.

Aufruf:
    python3 fremdimport.py --probe maude
    python3 fremdimport.py --lage
    python3 fremdimport.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))

# Je Quelle: was hereindarf, was nie hereindarf, und wie es zu holen ist.
# Die verbotenen Namen stehen ausdrücklich DA, obwohl die Projektion sie schon
# ausschließt -- sie sind die Gegenprobe und zugleich die Dokumentation, wovor
# hier geschützt wird. Wer sie streicht, streicht sie sichtbar.
QUELLEN: dict[str, dict] = {
    "maude": {
        "titel": "FDA MAUDE (openFDA)",
        "lizenz": "CC0 1.0 — Weitergabe frei, Personenbezug bestätigt",
        "abruf": "https://api.fda.gov/device/event.json?limit={n}",
        "wurzel": "results",
        "erlaubt": ["report_number", "event_type", "date_of_event",
                     "date_received", "source_type", "product_problems",
                     "device"],
        # device ist eine Liste von Geräteangaben -- daraus wieder nur dieses:
        "erlaubt_tief": {"device": ["brand_name", "generic_name",
                                     "manufacturer_d_name", "device_report_product_code",
                                     "device_operator", "model_number"]},
        "verboten": ["patient", "patient_age", "patient_sex", "patient_weight",
                      "patient_race", "patient_ethnicity", "mdr_text",
                      "reporter_occupation_code", "sequence_number_outcome",
                      "sequence_number_treatment"],
    },
    "asrs": {
        "titel": "ASRS (NASA/FAA)",
        "lizenz": "de-identifiziert laut Betreiber, Weitergabe frei",
        "abruf": None,   # siehe --lage
        "wurzel": None,
        "erlaubt": [],
        "erlaubt_tief": {},
        "verboten": [],
    },
    "nist": {
        "titel": "NIST",
        "lizenz": "öffentlich, Auflage: Byline + Änderungshinweis",
        "abruf": None,
        "wurzel": None,
        "erlaubt": [],
        "erlaubt_tief": {},
        "verboten": [],
    },
}


def projizieren(satz: dict, quelle: dict) -> dict:
    """Baut einen NEUEN Satz aus den erlaubten Teilen. Kein Entfernen: was
    nicht genannt ist, entsteht gar nicht erst."""
    tief = quelle.get("erlaubt_tief", {})
    neu: dict = {}
    for feld in quelle["erlaubt"]:
        if feld not in satz:
            continue
        wert = satz[feld]
        if feld in tief and isinstance(wert, list):
            neu[feld] = [{k: e[k] for k in tief[feld] if k in e}
                          for e in wert if isinstance(e, dict)]
        elif feld in tief and isinstance(wert, dict):
            neu[feld] = {k: wert[k] for k in tief[feld] if k in wert}
        else:
            neu[feld] = wert
    return neu


def _namen(gebilde) -> set[str]:
    """Alle Schlüsselnamen, rekursiv -- auch aus Listen und tiefen Ebenen."""
    raus: set[str] = set()
    if isinstance(gebilde, dict):
        for k, v in gebilde.items():
            raus.add(k)
            raus |= _namen(v)
    elif isinstance(gebilde, list):
        for e in gebilde:
            raus |= _namen(e)
    return raus


def gegenprobe(satz: dict, quelle: dict) -> None:
    """Zweite Stufe: der gebaute Satz darf keinen verbotenen Namen tragen,
    auf keiner Ebene. Bricht ab statt zu bereinigen -- eine Bereinigung an
    dieser Stelle wäre wieder die Blacklist, gegen die die Projektion steht."""
    gefunden = _namen(satz) & set(quelle["verboten"])
    if gefunden:
        raise RuntimeError(
            f"Import abgebrochen: der projizierte Satz traegt verbotene Felder "
            f"{sorted(gefunden)}. Das heisst, ein erlaubtes Feld enthaelt sie "
            "verschachtelt -- die Whitelist gehoert praezisiert, NICHT der Satz "
            "bereinigt.")


def holen(name: str, n: int = 3) -> list[dict]:
    quelle = QUELLEN[name]
    if not quelle["abruf"]:
        raise RuntimeError(f"{quelle['titel']}: kein maschineller Abrufweg hinterlegt "
                            "-- siehe --lage")
    with urllib.request.urlopen(quelle["abruf"].format(n=n), timeout=30) as antwort:
        daten = json.loads(antwort.read().decode("utf-8"))
    saetze = daten[quelle["wurzel"]] if quelle["wurzel"] else daten
    raus = []
    for satz in saetze:
        neu = projizieren(satz, quelle)
        gegenprobe(neu, quelle)
        raus.append(neu)
    return raus


def _selftest() -> None:
    quelle = QUELLEN["maude"]

    roh = {"report_number": "1", "event_type": "Injury",
           "patient": [{"patient_age": "72", "patient_sex": "F"}],
           "mdr_text": [{"text": "Patient verstarb ..."}],
           "device": [{"brand_name": "X", "manufacturer_d_name": "Y",
                        "openfda": {"device_name": "Z"}}]}

    # 1) Projektion: personenbezogene Zweige entstehen gar nicht erst.
    neu = projizieren(roh, quelle)
    assert "patient" not in neu and "mdr_text" not in neu, neu
    assert neu["report_number"] == "1" and neu["event_type"] == "Injury"

    # 2) Auch TIEF wird projiziert: openfda war nicht genannt, also weg.
    assert neu["device"] == [{"brand_name": "X", "manufacturer_d_name": "Y"}], neu["device"]

    # 3) Ein neues Feld der Quelle ist automatisch draussen -- das ist der
    #    ganze Unterschied zur Blacklist.
    neu2 = projizieren({**roh, "neues_feld_von_morgen": "irgendwas"}, quelle)
    assert "neues_feld_von_morgen" not in neu2

    # 4) Gegenprobe schlaegt an, wenn ein verbotener Name doch auftaucht --
    #    hier kuenstlich herbeigefuehrt, weil die Projektion ihn sonst nie
    #    durchliesse. Ohne diesen Fall waere Stufe 2 unbelegt.
    try:
        gegenprobe({"device": [{"brand_name": "X", "patient_age": "72"}]}, quelle)
        raise AssertionError("Gegenprobe liess ein verbotenes Feld durch")
    except RuntimeError as e:
        assert "patient_age" in str(e)

    # 5) Negativfall: ein sauberer Satz darf NICHT anschlagen.
    gegenprobe(neu, quelle)

    print("selftest ok (5 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def _lage() -> None:
    print("Fremdbestaende -- Stand nach der Lizenzpruefung 2026-08-11:\n")
    for name, q in QUELLEN.items():
        weg = "maschinell abrufbar" if q["abruf"] else "KEIN maschineller Weg hinterlegt"
        print(f"  {name:6s} {q['titel']:22s} {weg}")
        print(f"         Lizenz: {q['lizenz']}")
        if q["verboten"]:
            print(f"         nie importiert: {', '.join(q['verboten'][:5])} ...")
    print("""
ASRS: die Datenbank hat nur eine Suchoberflaeche, keine Programmierschnittstelle
      und keine Massendatei. Der Weg fuehrt ueber einen Ausfuhrlauf der
      Oberflaeche -- eine Handlung, keine Automatik. Genau wie bei NASA LLIS,
      das nur ueber ein fremdes MIT-Repository zu bekommen war.
NIST: der Teilbestand ist im Register unbenannt. Ohne die Entscheidung, WELCHER
      Bestand gemeint ist, gibt es nichts zu holen -- das ist keine technische
      Luecke, sondern eine offene Frage an den Betreiber.""")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--probe", choices=sorted(QUELLEN))
    p.add_argument("--anzahl", type=int, default=3)
    p.add_argument("--lage", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return
    if a.lage:
        _lage()
        return
    if a.probe:
        saetze = holen(a.probe, a.anzahl)
        print(f"{len(saetze)} Satz/Saetze projiziert, Gegenprobe bestanden:\n")
        print(json.dumps(saetze[0], ensure_ascii=False, indent=2)[:900])
        return
    p.print_help()


if __name__ == "__main__":
    main()
