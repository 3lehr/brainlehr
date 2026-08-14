#!/usr/bin/env python3
"""Traegt die Yjs-Familie ueber die Sprachgrenze? Gemessen, nicht behauptet.

ANLASS (2026-08-14): Das Dokumentfenster im atelier soll Zeichen fuer Zeichen
mehrbenutzerfaehig sein (Knoten `de9aba1a`, Betreiberentscheid). Damit steht ein
CRDT im Weg, und die Frage ist nicht "welches ist das beste", sondern welches
auf BEIDEN Seiten des Hauses existiert: Python ist Grundsprache (ADR-006), die
Oberflaeche soll nativ bleiben (Betreiber, 2026-08-14: "Ich will das zuerst
schon nativ in der Mac App").

Diese Datei ist die Rot-Probe zu ADR-010. Sie laeuft in beide Richtungen und
prueft ausdruecklich auch den Negativfall (zweimal anwenden darf nichts
verdoppeln).

Voraussetzung:  pip install pycrdt     · Swift-Teil: xcrun swift run
Aufruf:         python3 spikes/crdt_pyswift/probe.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent


def lauf() -> int:
    from pycrdt import Doc, Text

    fehler = 0

    # --- 1. Python allein: laufen zwei gleichzeitige Aenderungen zusammen?
    a = Doc()
    a["t"] = ta = Text("Hallo Welt")
    b = Doc()
    b.apply_update(a.get_update())
    tb = b.get("t", type=Text)
    ta.insert(6, "schoene ")                 # Mensch
    tb.insert(len(str(tb)), ", heute")       # Modell, gleichzeitig
    ua, ub = a.get_update(), b.get_update()
    a.apply_update(ub)
    b.apply_update(ua)
    if str(a["t"]) != str(b["t"]):
        print(f"FEHLT: divergent -- A={str(a['t'])!r} B={str(b['t'])!r}")
        fehler += 1
    else:
        print(f"ok  gleichzeitig, konvergent: {str(a['t'])!r}")

    # --- 2. Baustein-Baum mit stabiler Kennung -- Schriftsatz und Formular in
    #        derselben Struktur (Knoten `de9aba1a`, Punkt "Felder mitdenken").
    from pycrdt import Array, Map

    d = Doc()
    d["bausteine"] = arr = Array()
    arr.append(Map({"kennung": "b1", "typ": "absatz", "text": Text("Erster Satz.")}))
    arr.append(Map({"kennung": "f1", "typ": "feld", "text": Text("Rechnungsnummer")}))
    typen = [m["typ"] for m in d["bausteine"].to_py()]
    if typen != ["absatz", "feld"]:
        print(f"FEHLT: Baum traegt die Typen nicht -- {typen}")
        fehler += 1
    else:
        print("ok  Baum traegt Absatz und Feld nebeneinander")

    # --- 3. Ueber die Sprachgrenze: Python schreibt, Swift liest.
    quelle = Doc()
    quelle["t"] = Text("Hallo aus Python")
    (HIER / "py_update.bin").write_bytes(quelle.get_update())
    (HIER / "py_sv.bin").write_bytes(quelle.get_state())

    swift = subprocess.run(
        ["xcrun", "swift", "run"], cwd=HIER, capture_output=True, text=True
    )
    if swift.returncode != 0:
        print("FEHLT: Swift-Teil lief nicht --", swift.stderr.strip()[-400:])
        return fehler + 1
    print(swift.stdout.strip())
    if "Swift liest aus Python-Update: Hallo aus Python" not in swift.stdout:
        print("FEHLT: Swift hat den Python-Stand nicht gelesen")
        fehler += 1

    # --- 4. Rueckrichtung. OFFEN, und darum steht hier der gemessene Stand,
    #        nicht eine Zusicherung: Am 2026-08-14 kam der Python-Stand als
    #        ZWEITE Fassung zurueck statt zusammengefuehrt, und der
    #        Zustandsvektor filterte nichts (30 Byte gegen den Vektor, 30 Byte
    #        gegen leer). Solange das so ist, ist die Rueckrichtung ungeklaert.
    zurueck = HIER / "swift_update.bin"
    if zurueck.exists():
        quelle.apply_update(zurueck.read_bytes())
        stand = str(quelle["t"])
        erwartet = "[Swift] Hallo aus Python"
        if stand == erwartet:
            print(f"ok  Rueckrichtung sauber: {stand!r}")
        else:
            print(f"OFFEN Rueckrichtung: {stand!r} statt {erwartet!r} -- Spike 1 in ADR-010")

    return fehler


if __name__ == "__main__":
    sys.exit(1 if lauf() else 0)
