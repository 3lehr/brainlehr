#!/usr/bin/env python3
"""Rechnet die S12-Messung ueber die TATSAECHLICH behandelten Ziele.

Aufgabe 108. Kein neuer Messlauf: beide vorhandenen Laeufe tragen ihre
Einzelinstanzen (`einzel`, je 205), die Zuordnung fehlte nur.

DAS PROBLEM WAR DER NENNER, nicht das Ergebnis. Die Auswertung vom
2026-08-13T21:28 zaehlte ALLE Zielinstanzen einer Haelfte -- 101 und 104.
Behandelt wurden aber nur 225 von 1101 gesicherten Knoten; der Rest sind
Normen und Fremdbestand, beide ausgenommen. Ein Effekt an den behandelten
Knoten wird so mit unberuehrten Zielen verduennt.

BEHANDELT HEISST HIER: der heutige Text weicht von der gesicherten Urfassung
ab (s12_urfassungen). Das ist eine Mengenoperation gegen die Datenbank, keine
Annahme darueber, was das Umschriftwerkzeug getan haben SOLLTE -- gemessen
2026-08-14: 225 von 1101.

SYMMETRIE IST PFLICHT, sonst misst der Vergleich die Auswahl statt die
Wirkung: In der unbehandelten Haelfte gibt es per Definition keine
behandelten Knoten. Verglichen wird deshalb nicht "behandelt gegen
unbehandelt", sondern die Teilmenge der VERGLEICHBAREN Knoten -- solche, die
in ihrer jeweiligen Haelfte fuer die Behandlung in Frage gekommen waeren
(arbeitsbestand, keine Norm). In der behandelten Haelfte sind das die 225
angefassten, in der unbehandelten ihre Entsprechung.

EHRLICHE GRENZE, im Auftrag ausdruecklich verlangt: Ist die Teilmenge zu
klein, ist auch sie nicht aussagekraeftig. Dann lautet das Ergebnis "mit
diesem Korpus nicht entscheidbar" -- und der naechste Schritt ist ein
groesserer Korpus, keine feinere Rechnung. Eine Zahl mit n=6 ist keine
Antwort, sie sieht nur wie eine aus.
"""
from __future__ import annotations

import argparse
import json
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder", "messungen")]

import speicher  # noqa: E402
import teilung_s12  # noqa: E402

# Unter dieser Zahl je Zelle wird nicht gerechnet, sondern gemeldet. 20 ist
# gewaehlt, nicht gemessen: bei n=20 liegt der Standardfehler einer Quote um
# 20 Prozent bereits bei rund 9 Prozentpunkten -- ein Unterschied muesste
# groesser sein als der ganze gemessene Effektbereich, um sichtbar zu werden.
MINDESTZAHL = 20


def behandelte_knoten(conn) -> set[str]:
    """Knoten-IDs, deren heutiger Text von der Urfassung abweicht."""
    return {r[0] for r in conn.execute(
        "SELECT u.node_id FROM s12_urfassungen u JOIN knowledge_nodes k ON k.id = u.node_id "
        "WHERE k.title <> u.title "
        "   OR COALESCE(k.summary,'') <> COALESCE(u.summary,'') "
        "   OR COALESCE(k.content,'') <> COALESCE(u.content,'')")}


def vergleichbare_knoten(conn) -> set[str]:
    """Knoten, die fuer eine Behandlung ueberhaupt in Frage kamen.

    Dieselben Schranken wie kern/umschrift_s12.py: Arbeitsbestand, keine
    Norm. Ohne diese Menge waere der Vergleich schief -- die unbehandelte
    Haelfte enthaelt Normen und Fremdbestand, die dort NIE angefasst worden
    waeren, und ihre Treffer wuerden gegen behandelte Knoten gerechnet.
    """
    return {r[0] for r in conn.execute(
        "SELECT id FROM knowledge_nodes WHERE COALESCE(gattung,'arbeitsbestand') = 'arbeitsbestand' "
        "AND norm_rang IS NULL AND zurueckgezogen = 0")}


def auswerten(lauf: dict, conn) -> dict:
    behandelt = behandelte_knoten(conn)
    vergleichbar = vergleichbare_knoten(conn)
    pfade = {e["id"] for e in lauf["einzel"] if e["art"] == "knoten"}
    id_je_pfad = teilung_s12.id_je_pfad(conn, pfade)

    zellen = {h: {"treffer": 0, "gesamt": 0} for h in ("behandelt", "unbehandelt")}
    ausserhalb = 0
    for e in lauf["einzel"]:
        if e["art"] != "knoten":
            # Lehren sind vom Umschriftverfahren nie angefasst worden -- sie
            # gehoeren nicht in eine Messung seiner Wirkung.
            ausserhalb += 1
            continue
        knoten_id = id_je_pfad.get(e["id"])
        if knoten_id is None or knoten_id not in vergleichbar:
            ausserhalb += 1
            continue
        if e["haelfte"] == "behandelt" and knoten_id not in behandelt:
            # In der behandelten Haelfte, aber nicht angefasst (Norm,
            # Fremdbestand, oder das Werkzeug hat den Knoten verworfen).
            ausserhalb += 1
            continue
        zelle = zellen[e["haelfte"]]
        zelle["gesamt"] += 1
        if e["treffer"]:
            zelle["treffer"] += 1

    for z in zellen.values():
        z["quote"] = round(z["treffer"] / z["gesamt"], 4) if z["gesamt"] else None

    zu_klein = [h for h, z in zellen.items() if z["gesamt"] < MINDESTZAHL]
    return {
        "zellen": zellen,
        "ausserhalb_der_teilmenge": ausserhalb,
        "behandelte_knoten_im_bestand": len(behandelt),
        "mindestzahl": MINDESTZAHL,
        "belastbar": not zu_klein,
        "zu_kleine_zellen": zu_klein,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vorher", type=_Path, required=True)
    p.add_argument("--nachher", type=_Path, required=True)
    p.add_argument("--out", type=_Path)
    args = p.parse_args()

    with speicher.lesen() as conn:
        vorher = auswerten(json.loads(args.vorher.read_text(encoding="utf-8")), conn)
        nachher = auswerten(json.loads(args.nachher.read_text(encoding="utf-8")), conn)

    ergebnis = {
        "zweck": "S12-Wirkung ueber die TATSAECHLICH behandelten Ziele (Aufgabe 108)",
        "quelle_vorher": str(args.vorher),
        "quelle_nachher": str(args.nachher),
        "vorher": vorher,
        "nachher": nachher,
    }

    if vorher["belastbar"] and nachher["belastbar"]:
        d_b = (nachher["zellen"]["behandelt"]["quote"] - vorher["zellen"]["behandelt"]["quote"])
        d_u = (nachher["zellen"]["unbehandelt"]["quote"] - vorher["zellen"]["unbehandelt"]["quote"])
        ergebnis["differenz_der_differenzen_pp"] = round((d_b - d_u) * 100, 2)
        ergebnis["urteil"] = "gerechnet"
    else:
        ergebnis["differenz_der_differenzen_pp"] = None
        ergebnis["urteil"] = (
            "MIT DIESEM KORPUS NICHT ENTSCHEIDBAR -- die Teilmenge der behandelten "
            f"Ziele ist zu klein (unter {MINDESTZAHL} je Zelle). Das ist kein "
            "Nullergebnis: eine Quote aus so wenigen Faellen sieht nur wie eine "
            "Antwort aus. Der naechste Schritt ist ein groesserer Korpus, keine "
            "feinere Rechnung.")

    text = json.dumps(ergebnis, ensure_ascii=False, indent=1)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
