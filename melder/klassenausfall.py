#!/usr/bin/env python3
"""Eine ganze Zielklasse trifft nie -- das ist ein Defekt, kein Ergebnis.

ANLASS: `L-0e0ab6`, elf Vorkommen, die haeufigste Lehre des Bestands und bis
heute ohne Mechanismus (gefunden von melder/ohne_mechanismus.py). Zwei der elf
Vorkommen sind exakt derselbe Griff:

  2026-08-18, Vorkommen 10: Die Rangfunktion verglich bei Knoten `id` gegen
  ein Ziel, das den PFAD traegt. Alle 20 Knotenfaelle konnten NIE treffen.
  Ergebnis 39 von 45 Totalausfaellen, waehrend eine andere Messung derselben
  Sache am selben Tag 7 von 35 meldete.

  2026-08-18, Vorkommen 11: Dasselbe beim BDW-P04-Gate. 2 von 35 gemessen,
  beinahe als Leistungseinbruch gemeldet -- 0 von 20 Knotenzielen waren
  strukturell unerreichbar, die 15 Lehren trugen die Zahl allein.

DER SATZ, DER BEIDE FAELLE BESCHREIBT: "Die Zahl sah nicht kaputt aus, sondern
nur schlecht -- und schlechte Abrufzahlen waren an diesem Tag die Erwartung."
Genau deshalb faellt es niemandem auf: Ein Totalausfall EINER Klasse sieht aus
wie ein schwaches Gesamtergebnis.

GEMESSEN am Pruefkorpus (runs/pruefkorpus.jsonl, 2026-08-20):
  lesson  15 Faelle, Ziel als `L-xxxxxx`
  node    20 Faelle, Ziel als `/pfad`
  (ohne)  10 Faelle ohne Ziel -- Negativfaelle, gehoeren NICHT in den Nenner
Zwei Klassen, zwei Zielformen, ein Vergleichsfeld. Die Falle ist eingebaut.

WAS DIESES MODUL TUT: Es nimmt die Treffer JE KLASSE und meldet eine Klasse,
die bei hinreichend vielen Faellen NULL trifft. Es beurteilt die Guete nicht --
es unterscheidet "schlecht" von "unerreichbar".

    python3 melder/klassenausfall.py --selftest
    python3 melder/klassenausfall.py --korpus            # Klassen im Korpus
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

# Ab wie vielen Faellen ein Nullergebnis nicht mehr Zufall sein kann. Bei drei
# Faellen ist null Treffer eine schlechte Quote, bei zwanzig ist es ein Defekt.
AB_FAELLEN = 5


def pruefe(treffer_je_klasse: dict[str, tuple[int, int]]) -> str | None:
    """{'node': (treffer, faelle), ...} -> Meldung oder None.

    Der Nenner sind die Faelle MIT Ziel. Negativfaelle (kein Ziel, richtiges
    Schweigen erwartet) gehoeren nicht hinein -- sie koennen per Bauart nicht
    'treffen', und sie mitzuzaehlen wuerde einen Ausfall verdecken."""
    tot = [(k, t, n) for k, (t, n) in sorted(treffer_je_klasse.items())
           if n >= AB_FAELLEN and t == 0]
    if not tot:
        return None
    zeilen = [f"{k}: 0 von {n}" for k, _, n in tot]
    andere = [f"{k}: {t} von {n}" for k, (t, n) in sorted(treffer_je_klasse.items())
              if not any(k == x[0] for x in tot)]
    return (
        "KLASSENAUSFALL: " + " · ".join(zeilen) + ".\n\n"
        "Eine Zielklasse, die bei " + str(AB_FAELLEN) + "+ Faellen NULL trifft, "
        "ist strukturell unerreichbar -- das ist ein Defekt des Messaufbaus, "
        "kein schwaches Ergebnis. Zweimal belegt (L-0e0ab6, Vorkommen 10 und "
        "11): beide Male wurde die Kennung gegen ein Ziel gehalten, das den "
        "PFAD traegt.\n\n"
        + ("Zum Vergleich, die uebrigen Klassen: " + " · ".join(andere) + "\n\n"
           if andere else "")
        + "Zuerst pruefen: Vergleicht die Rangfunktion dasselbe Feld, das der "
          "Korpus als Ziel fuehrt? `target_kind` sagt, welche Form erwartet "
          "wird."
    )


def korpusklassen(pfad: Path | None = None) -> dict[str, int]:
    """Welche Zielklassen fuehrt der Pruefkorpus, und wie viele Faelle je Klasse?"""
    p = pfad or (_w / "runs" / "pruefkorpus.jsonl")
    zaehler: dict[str, int] = {}
    try:
        roh = p.read_text(encoding="utf-8")
    except OSError:
        return {}
    for zeile in roh.splitlines():
        if not zeile.strip():
            continue
        try:
            d = json.loads(zeile)
        except ValueError:
            continue
        if not d.get("target_id"):
            continue          # Negativfall, kein Ziel
        art = str(d.get("target_kind") or "unbekannt")
        zaehler[art] = zaehler.get(art, 0) + 1
    return zaehler


def _selftest() -> int:
    # a) Ein Totalausfall wird gemeldet, und die uebrigen Klassen stehen daneben.
    grund = pruefe({"node": (0, 20), "lesson": (7, 15)})
    assert grund and "node: 0 von 20" in grund, grund
    assert "lesson: 7 von 15" in grund, "die gesunde Klasse gehoert zum Vergleich daneben"

    # b) NEGATIVFALL: schlechte, aber nicht tote Quote schlaegt NICHT an. Das
    #    ist die Haelfte, die das Modul brauchbar macht -- 1 von 20 ist ein
    #    Ergebnis, 0 von 20 ist ein Defekt.
    assert pruefe({"node": (1, 20), "lesson": (7, 15)}) is None

    # c) NEGATIVFALL: wenige Faelle -> null Treffer ist Zufall, kein Defekt.
    assert pruefe({"node": (0, 3)}) is None

    # d) Beide Klassen tot -> beide werden genannt.
    g = pruefe({"node": (0, 20), "lesson": (0, 15)})
    assert "node: 0 von 20" in g and "lesson: 0 von 15" in g

    # e) Leere Eingabe schlaegt nicht an.
    assert pruefe({}) is None

    # f) Der echte Korpus fuehrt genau die zwei Klassen, die die Falle bilden.
    klassen = korpusklassen()
    if klassen:
        assert set(klassen) >= {"lesson", "node"}, klassen
        assert klassen["node"] >= AB_FAELLEN and klassen["lesson"] >= AB_FAELLEN, klassen

    print("klassenausfall: Selbsttest gruen (6 Faelle: Ausfall gemeldet mit "
          "Vergleichsklasse, schlechte Quote geht durch, wenige Faelle gehen "
          "durch, beide Klassen tot, leere Eingabe still, echter Korpus "
          "traegt beide Klassen)")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    k = korpusklassen()
    print("Zielklassen im Pruefkorpus (nur Faelle MIT Ziel):", k or "keiner gefunden")
    print(f"Schwelle fuer 'Ausfall': {AB_FAELLEN} Faelle bei null Treffern")
