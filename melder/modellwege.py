#!/usr/bin/env python3
"""Sind die Modell-Endpunkte erreichbar, auf die brainlehr zeigt?

ZWEIMAL AM 2026-08-20 lief etwas ins Leere, beide Male unbemerkt:

1. `kern/nachrangung.modell()` zeigte fest auf Ollama (Port 11434). Dort
   lauschte niemand -- der Betreiber arbeitet mit LM Studio (1234). Jeder
   Aufruf fiel in den Rueckfall "urspruengliche Reihenfolge". Kein Fehler,
   kein Log; der Aufrufer sieht es allein daran, dass sich nichts aendert.
2. `knowledge_add` schrieb 13 Eintraege ohne Vektor, weil der
   Einbettungsdienst nicht antwortete. Die Eintraege sind gueltig und ueber
   die Bedeutungssuche unauffindbar -- also genau die Haelfte des Abrufs,
   um den es geht.

Beide Zustaende waren ueber einen einzigen HTTP-Aufruf feststellbar. Es
fragte nur niemand.

WAS DIESER MELDER ANDERS MACHT als ein blosses "Dienst weg": Er nennt die
FOLGE. Ein Port in einer Warnung laesst den Leser raten, was ihn das kostet;
beide Faelle von heute waren still, und still heisst: die Folge ist die
eigentliche Information.

Er schweigt, wenn alles laeuft. Ein Melder, der immer etwas sagt, wird
ueberlesen.
"""
from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request
from typing import Callable, Optional

ZEITGRENZE = 3.0


def _lebt(url: str) -> bool:
    """Ein HEAD/GET auf die Wurzel des Dienstes -- kein Modellaufruf.

    Absichtlich anspruchslos: Gefragt ist, ob ueberhaupt jemand lauscht, nicht
    ob das richtige Modell geladen ist. Ein Melder, der ein Modell laedt, um
    zu pruefen, ob er es laden kann, kostet mehr als der Fehler, den er sucht."""
    wurzel = url.split("/api/")[0].split("/v1/")[0]
    for pfad in ("/api/tags", "/v1/models", "/"):
        try:
            with urllib.request.urlopen(wurzel + pfad, timeout=ZEITGRENZE) as a:
                if a.status < 500:
                    return True
        except urllib.error.HTTPError:
            return True   # antwortet, wenn auch ablehnend -- jemand lauscht
        except Exception:
            continue
    return False


def wege() -> list:
    """Die Endpunkte, auf die brainlehr zeigt -- aus der Umgebung gelesen.

    Fest verdrahtet waeren sie genau der Fehler aus Fall 1."""
    return [
        {
            "aufgabe": "Einbettungen",
            "url": os.environ.get("KNOWLEDGE_OLLAMA_URL", "http://127.0.0.1:11434"),
            "schalter": "KNOWLEDGE_OLLAMA_URL",
            "folge": ("neue Eintraege bekommen keinen Vektor und bleiben ueber "
                      "die Bedeutungssuche unauffindbar -- der Eintrag selbst "
                      "entsteht trotzdem, ohne Fehlermeldung"),
        },
        {
            "aufgabe": "Nachrangung",
            "url": os.environ.get("BRAINLEHR_MODELL_ENDPUNKT",
                                  "http://127.0.0.1:11434/api/generate"),
            "schalter": "BRAINLEHR_MODELL_ENDPUNKT",
            "folge": ("die Reihenfolge der Treffer bleibt unveraendert -- ein "
                      "stiller Rueckfall, von einem wirkungslosen Nachranger "
                      "nicht zu unterscheiden"),
        },
    ]


def pruefe(pruefer: Optional[Callable[[str], bool]] = None) -> dict:
    p = pruefer or _lebt
    raus = []
    for w in wege():
        raus.append({**w, "erreichbar": bool(p(w["url"]))})
    return {"wege": raus, "tote": sum(1 for w in raus if not w["erreichbar"])}


def als_text(lage: dict) -> str:
    tot = [w for w in lage["wege"] if not w["erreichbar"]]
    if not tot:
        return ""
    z = [f"⚠ {len(tot)} Modell-Endpunkt(e) nicht erreichbar -- "
         f"das faellt sonst NICHT auf, es gibt keinen Fehler:"]
    for w in tot:
        z.append(f"  {w['aufgabe']}: {w['url']}")
        z.append(f"     Folge: {w['folge']}")
        z.append(f"     Umstellen mit {w['schalter']}=<url>")
    return "\n".join(z)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--immer", action="store_true",
                   help="auch melden, wenn alles laeuft")
    args = p.parse_args()
    lage = pruefe()
    text = als_text(lage)
    if text:
        print(text)
    elif args.immer:
        for w in lage["wege"]:
            print(f"  {w['aufgabe']:<14} {w['url']}  erreichbar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
