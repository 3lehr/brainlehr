#!/usr/bin/env python3
"""Findet Widersprueche zwischen gleichrangigen Normen -- als Verdacht.

DER ANLASS: Der Wettbewerbsvergleich vom 2026-08-20 fand bei `holographic`
(dem einzigen rein lokalen der acht Speicher-Anbieter in Hermes) ein
`contradict()`, das brainlehr fehlt. Normkonflikte fallen hier bisher nur
auf, wenn ein Mensch stolpert -- L-2bba13 haelt einen seit dem 2026-08-08 als
"ungeloest" fest, und niemand hat ihn seither gesucht.

DER NULLBEFUND, DER DEN ENTWURF BESTIMMT HAT:
Der naheliegende Ansatz -- hohe BEDEUTUNGSAEHNLICHKEIT bei gleichem Rang --
findet Widersprueche NICHT. Gemessen am 2026-08-20 ueber 47 Rang-1-Normen
(1 081 Paare): Der bekannte Konflikt landete auf Rang 266, und die acht
aehnlichsten Paare waren durchweg VERWANDTE Regeln (Agentenauftrag neben
Auftraege-sind-Schnappschuesse, Caveman neben Abwesenheitsmodus), kein
einziger Widerspruch.

Der Grund ist eine Eigenschaft von Einbettungen, die man kennen muss, bevor
man sie fuer so etwas benutzt: "X ist erlaubt" und "X ist verboten" liegen
dicht beieinander. Sie erfassen Themennaehe, nicht Wahrheitswert.

WAS TRAEGT, ist holographics Umkehrung (plugins/memory/holographic/
retrieval.py:355-430): hohe WORTUEBERLAPPUNG bei NIEDRIGER Bedeutungsnaehe --
zwei Texte, die dieselben Begriffe nennen und trotzdem semantisch
auseinanderliegen. Derselbe Konflikt landete damit auf Rang 3 von 12.

WARUM NUR GLEICHER RANG: Zwei Normen verschiedenen Rangs koennen einander
stechen (lex superior). Zwei gleichrangige koennen es nicht -- dort bleibt
ein Widerspruch ungeloest, bis ein Mensch entscheidet. Genau das sagt
L-2bba13: "weder lex superior noch lex specialis noch lex posterior
entscheidet".

WAS DIESER MELDER NICHT IST: ein Beweis. Er liefert einen VERDACHT mit beiden
Eingangsgroessen, damit ein Mensch in Sekunden sieht, woran es lag. Ein
Widerspruch ist eine Aussage ueber BEDEUTUNG, und die trifft kein Zaehlwerk.

Aufruf:
    python3 melder/normwiderspruch.py            # Rang 1
    python3 melder/normwiderspruch.py --rang 2
"""
from __future__ import annotations

import argparse
import itertools
import re
import sqlite3
import struct
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

# Beide Schwellen sind GERATEN, nicht kalibriert -- sie stammen aus EINEM Lauf
# gegen EINEN bekannten Konflikt (L-2bba13). Es gibt im Bestand keinen zweiten
# belegten Fall, gegen den sich messen liesse. Wer sie aendert, sollte das
# wissen: hier ist nichts gemessen, was Genauigkeit verspraeche.
WORTSCHWELLE = 0.10          # ungemessen
MELDEGRENZE = 8              # ungemessen -- wie viele Verdachtsfaelle gezeigt werden

STOPP = set(
    "der die das und nicht wird ist eine mit von fuer für auf dem den sich "
    "werden kann als bei ein einer dass nur wenn wie war sind haben hat aus "
    "dazu oder zum zur des dies dieser diese jede jeder alle also aber".split())


def worte(text: str) -> set:
    return {w for w in re.findall(r"\w{4,}", (text or "").lower()) if w not in STOPP}


def ueberlappung(a: str, b: str) -> float:
    """Jaccard ueber Inhaltswoerter -- Fuellwoerter zaehlen nicht mit.

    Ohne Stoppwortliste misst man die deutsche Grammatik statt des
    Gegenstands: Zwei beliebige Regeltexte teilen "der die das und"."""
    wa, wb = worte(a), worte(b)
    return len(wa & wb) / max(len(wa | wb), 1)


def bedeutung(va, vb) -> float:
    sp = sum(x * y for x, y in zip(va, vb))
    na = sum(x * x for x in va) ** 0.5
    nb = sum(y * y for y in vb) ** 0.5
    return sp / (na * nb) if na and nb else 0.0


def verdacht(ueberlappung: float, bedeutung: float) -> float:
    """Gemeinsame Begriffe MINUS Bedeutungsnaehe.

    Positiv heisst: Sie reden ueber dasselbe und sagen Verschiedenes. Negativ
    heisst: Sie sagen dasselbe -- eine Dublette, kein Konflikt. Deshalb ist
    die Differenz richtig und nicht etwa das Verhaeltnis: Bei zwei identischen
    Texten (1,0 und 1,0) muss null herauskommen, nicht eins."""
    return ueberlappung - bedeutung


def finde(eintraege: list, wortschwelle: float = WORTSCHWELLE) -> list:
    """[(id, pfad, text, vektor), ...] -> sortierte Verdachtsliste."""
    raus = []
    for (ia, pa, ta, va), (ib, pb, tb, vb) in itertools.combinations(eintraege, 2):
        u = ueberlappung(ta, tb)
        if u < wortschwelle:
            continue
        b = bedeutung(va, vb)
        raus.append({"a": pa, "b": pb, "ueberlappung": round(u, 3),
                     "bedeutung": round(b, 3), "verdacht": round(verdacht(u, b), 3)})
    return sorted(raus, key=lambda p: -p["verdacht"])


def _lade(rang: int) -> list:
    import ort
    c = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    try:
        rows = c.execute(
            """select n.id, n.path, coalesce(n.title,'')||' '||coalesce(n.summary,''),
                      e.vector
               from knowledge_nodes n
               join knowledge_embeddings e on e.ref_id = n.id and e.kind = 'node'
               where n.norm_rang = ? and n.zurueckgezogen = 0""", (rang,)).fetchall()
    finally:
        c.close()
    return [(r[0], r[1], r[2], struct.unpack(f"{len(r[3])//4}f", r[3])) for r in rows]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rang", type=int, default=1)
    p.add_argument("--alle", action="store_true", help="alle Verdachtsfaelle statt der ersten")
    args = p.parse_args()

    eintraege = _lade(args.rang)
    if len(eintraege) < 2:
        print(f"Rang {args.rang}: weniger als zwei Normen mit Vektor -- nichts zu vergleichen")
        return 0
    treffer = finde(eintraege)
    paare = len(eintraege) * (len(eintraege) - 1) // 2
    print(f"Rang {args.rang}: {len(eintraege)} Normen, {paare} Paare, "
          f"{len(treffer)} mit gemeinsamen Begriffen (Schwelle {WORTSCHWELLE}, ungemessen)\n")
    if not treffer:
        return 0
    print("Verdacht auf Widerspruch -- gemeinsame Begriffe, ferne Bedeutung:")
    for t in (treffer if args.alle else treffer[:MELDEGRENZE]):
        print(f"  {t['verdacht']:+.3f}  (Woerter {t['ueberlappung']:.2f}, "
              f"Bedeutung {t['bedeutung']:.2f})")
        print(f"          {t['a']}")
        print(f"          {t['b']}")
    print("\nDas ist ein VERDACHT, kein Befund: Ob zwei Normen einander wirklich"
          "\nwidersprechen, ist eine Aussage ueber Bedeutung -- die trifft kein"
          "\nZaehlwerk. Beide Eingangswerte stehen daneben, damit sich in Sekunden"
          "\nsehen laesst, woran es lag.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
