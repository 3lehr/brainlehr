"""Einmal-Arbeitsskript, Auftrag 2026-08-20: NOISE_FLOOR_MAD_MULT (Radar-
Schwelle, haken/knowledge_recall_hook.py Zeile ~422) war seit Einfuehrung
GEWAEHLT statt GEMESSEN (Kommentar dort woertlich: "kein Pruefkorpus fuer
diese Schwelle"). Fegt 1.0..4.0 (der dort dokumentierte zulaessige Bereich)
in Zustand B (B_2Kanal_an_Pflicht_aus) und C (C_beide_an, Auslieferungszustand).

Nutzt DENSELBEN Weg wie kern/messlauf_abrufguete.py: load_cases()/messe()/
STATES/_with_state()/_gegen_schnappschuss() importiert, kein zweiter
Messweg. Die einzige Aenderung je Lauf ist hook.NOISE_FLOOR_MAD_MULT selbst,
zur Laufzeit umgebogen wie MAX_NODES/MAX_LESSONS in messungen/abrufeinbruch.py
-- die Konstante im Produktivcode bleibt unveraendert (Auftrag: NUR MESSEN).

NOISE_FLOOR_MAD_MULT wird als lokale Variable `mad_mult = NOISE_FLOOR_MAD_MULT`
zu BEGINN jedes query()-Aufrufs (haken/knowledge_recall_hook.py Zeile ~1283)
aus dem Modul gelesen, nicht als gebundener Default-Parameter -- ein Ueber-
schreiben von hook.NOISE_FLOOR_MAD_MULT VOR dem Aufruf wirkt darum zuverlaessig
auf den naechsten Aufruf, ganz wie beim MAX_NODES/MAX_LESSONS-Muster.

Nur lesend gegen die DB (ueber den gepinnten Schnappschuss aus
_gegen_schnappschuss(), s. kern/messlauf_abrufguete.py).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "melder", "migrationen")]

import messlauf_abrufguete as ml  # noqa: E402
import knowledge_recall_hook as hook  # noqa: E402

MAD_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
STATE_NAMES = ["B_2Kanal_an_Pflicht_aus", "C_beide_an"]
RESULT = _w / "runs/rauschteppich_sweep_2026-08-20.json"
PROD_MAD_MULT = hook.NOISE_FLOOR_MAD_MULT


def sweep(cases: list) -> dict:
    laeufe = {}
    for mad_mult in MAD_VALUES:
        hook.NOISE_FLOOR_MAD_MULT = mad_mult
        for state_name in STATE_NAMES:
            with ml._with_state(ml.STATES[state_name]):
                r = ml.messe(cases)
            key = f"{mad_mult}/{state_name}"
            laeufe[key] = {"mad_mult": mad_mult, "zustand": state_name, **r}
            print(f"{key}: trefferguete {r['trefferguete']} "
                  f"je_klasse={r['trefferguete_je_klasse']} "
                  f"richtiges_schweigen={r['richtiges_schweigen']} "
                  f"falsches_sprechen={r['falsches_sprechen']}")
    hook.NOISE_FLOOR_MAD_MULT = PROD_MAD_MULT
    return laeufe


def pareto_front(laeufe: dict, state_name: str) -> list[float]:
    """Dominanz in ZWEI Groessen zugleich (Auftrag): Trefferguote (mehr
    besser) und richtiges Schweigen (mehr besser). x dominiert y, wenn x in
    beiden >= y ist und in mindestens einer echt groesser. Kein anderer Wert
    darf einen Frontwert in beiden Groessen gleichzeitig schlagen."""
    punkte = {}
    for mad_mult in MAD_VALUES:
        r = laeufe[f"{mad_mult}/{state_name}"]
        punkte[mad_mult] = (r["trefferguete"][0], r["richtiges_schweigen"][0])
    front = []
    for x, px in punkte.items():
        dominiert = False
        for y, py in punkte.items():
            if y == x:
                continue
            if py[0] >= px[0] and py[1] >= px[1] and (py[0] > px[0] or py[1] > px[1]):
                dominiert = True
                break
        if not dominiert:
            front.append(x)
    return sorted(front)


def eichung(laeufe: dict) -> dict:
    """Positivkontrolle laut Auftrag: mad_mult=2.0 MUSS in B 15/35 und in C
    1/35 treffen (die heute mit der Produktivkonstante gemessenen Werte,
    runs/messlauf_abrufguete.json). Weicht das ab, ist der Aufbau hier
    verdaechtig, nicht die Abrufguete -- Auftrag ausdruecklich."""
    b = laeufe["2.0/B_2Kanal_an_Pflicht_aus"]["trefferguete"]
    c = laeufe["2.0/C_beide_an"]["trefferguete"]
    ok = b == [15, 35] and c == [1, 35]
    return {"ok": ok, "erwartet": {"B": [15, 35], "C": [1, 35]},
            "gemessen": {"B": b, "C": c}}


if __name__ == "__main__":
    cases = ml.load_cases()
    with ml._gegen_schnappschuss() as stand:
        laeufe = sweep(cases)
    eich = eichung(laeufe)
    print(f"\nEichung (mad_mult=2.0 gegen Produktivmessung): {eich}")
    if not eich["ok"]:
        print("\nABWEICHUNG: der Aufbau hier reproduziert die Produktivmessung "
              "bei mad_mult=2.0 nicht -- als Befund im Ergebnis vermerkt, "
              "Rechnung trotzdem vollstaendig ausgegeben.")

    fronten = {s: pareto_front(laeufe, s) for s in STATE_NAMES}
    print("\nPareto-Front je Zustand (Trefferguete UND richtiges Schweigen, "
          "beide 'mehr ist besser'):")
    for s, f in fronten.items():
        print(f"  {s}: {f}")

    ergebnis = {
        "laeufe": laeufe,
        "pareto_front": fronten,
        "eichung_2_0": eich,
        "mad_werte": MAD_VALUES,
        "zustaende": STATE_NAMES,
        "stand": {"kennung": stand.kennung, "aufgenommen": stand.aufgenommen},
        "laufmetadaten": ml.laufmetadaten(cases, ml.CORPUS),
    }
    RESULT.parent.mkdir(exist_ok=True)
    RESULT.write_text(json.dumps(ergebnis, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\ngeschrieben: {RESULT}")
