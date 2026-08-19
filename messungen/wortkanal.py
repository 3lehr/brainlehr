#!/usr/bin/env python3
"""Die Wortzerlegung, auf der ALLE Kriterien dieser Messreihe beruhen --
eine Stelle, weil zwei Kopien zwangslaeufig auseinanderlaufen.

Herausgeloest 2026-08-19 aus wirkung_llm_probe.py, als kriterium_113.py
dieselbe Funktion brauchte und ein wechselseitiger Import entstand. Nicht
kopiert: die Umlaut-Normalisierung ist der Kern des Befunds aus Aufgabe 99
(die Stoppwortliste war transliteriert, der Modelltext nicht) -- eine zweite
Fassung davon waere genau der Fehler, den sie behebt.
"""
from __future__ import annotations

import re

STOPWORTE = {
    "eine", "einer", "einem", "einen", "eines", "dass", "sich", "sind",
    "wird", "werden", "wurde", "wurden", "haben", "hatte", "hatten", "auch",
    "nicht", "kann", "koennen", "muss", "muessen", "soll", "sollen", "wenn",
    "waehrend", "durch", "ueber", "unter", "nach", "vor", "bei", "aus",
    "dabei", "diese", "dieser", "dieses", "dort", "hier", "dann", "noch",
    "dafuer", "damit", "dadurch", "dessen", "deren",
}


_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def signifikante_woerter(text: str) -> set[str]:
    """AUFGABE 99, 2026-08-18: normalisiert Umlaute (ae/oe/ue/ss) VOR dem
    Stoppwortabgleich. Befund am alten Lauf runs/wirkung_llm_probe_
    2026-08-18T210154.json: STOPWORTE ist in transliterierter Schreibweise
    gepflegt ("ueber", "koennen", "waehrend", ...), der Text aus echten
    Modellantworten aber in echten Umlauten ("über", "können", "während").
    Ohne Normalisierung greift KEIN Stoppwort mit Umlaut je -- ein
    Negativfall (Ordnungsamt-Frage) wurde dadurch allein wegen des Wortes
    "über" als kontaminiert gewertet."""
    text = (text or "").lower().translate(_UMLAUT)
    toks = re.findall(r"[a-z]{4,}", text)
    return {t for t in toks if t not in STOPWORTE}


