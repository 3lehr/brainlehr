#!/usr/bin/env python3
"""Traegt die Yjs-Familie ueber die Sprachgrenze? Gemessen, nicht behauptet.

ANLASS (2026-08-14): Das Dokumentfenster im atelier soll Zeichen fuer Zeichen
mehrbenutzerfaehig sein (Knoten `de9aba1a`, Betreiberentscheid). Damit steht ein
CRDT im Weg, und die Frage ist nicht "welches ist das beste", sondern welches
auf BEIDEN Seiten des Hauses existiert: Python ist Grundsprache (ADR-006), die
Oberflaeche soll nativ bleiben (Betreiber, 2026-08-14: "Ich will das zuerst
schon nativ in der Mac App").

BEFUND, den diese Probe festhaelt: `yswift` schneidet die Teilnehmerkennung
(client id) auf 32 Bit ab. `pycrdt` vergibt sie standardmaessig zufaellig bis
etwa 2^53. Faellt sie darueber, kommt der eigene Beitrag als FREMDER zurueck --
der Text verdoppelt sich still, statt zusammengefuehrt zu werden. Genau die
Fehlerklasse, die ein Nutzer als "meine Aenderung war ploetzlich zweimal da"
meldet und die kein Absturz begleitet. Die Schranke ist scharf gemessen:
2^32-1 traegt, 2^32 nicht.

Voraussetzung:  pip install pycrdt     · Swift-Teil: xcrun swift run
Aufruf:         python3 spikes/crdt_pyswift/probe.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent

# Groesste Teilnehmerkennung, die yswift unbeschaedigt zurueckgibt. Kein
# Schaetzwert -- an der Schwelle, darueber und darunter gemessen (2026-08-14).
KENNUNG_GRENZE = 2**32 - 1


def _swift_runde(quelle) -> str:
    """Schreibt den Stand fuer die Swift-Seite, laesst sie laufen, liest zurueck."""
    (HIER / "py_update.bin").write_bytes(quelle.get_update())
    (HIER / "py_sv.bin").write_bytes(quelle.get_state())
    lauf = subprocess.run(
        ["xcrun", "swift", "run"], cwd=HIER, capture_output=True, text=True
    )
    if lauf.returncode != 0:
        raise RuntimeError(f"Swift-Teil lief nicht: {lauf.stderr.strip()[-400:]}")
    quelle.apply_update((HIER / "swift_update.bin").read_bytes())
    return lauf.stdout


def lauf() -> int:
    from pycrdt import Array, Doc, Map, Text

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
    #        derselben Struktur (Knoten `de9aba1a`, "Felder mitdenken").
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

    # --- 3. Ueber die Sprachgrenze, in beide Richtungen, mit tragbarer Kennung.
    erwartet = "[Swift] Hallo aus Python"
    quelle = Doc(client_id=KENNUNG_GRENZE)
    quelle["t"] = Text("Hallo aus Python")
    ausgabe = _swift_runde(quelle)
    print(ausgabe.strip())
    if "Swift liest aus Python-Update: Hallo aus Python" not in ausgabe:
        print("FEHLT: Swift hat den Python-Stand nicht gelesen")
        fehler += 1
    if str(quelle["t"]) != erwartet:
        print(f"FEHLT: Rueckrichtung -- {str(quelle['t'])!r} statt {erwartet!r}")
        fehler += 1
    else:
        print(f"ok  Rueckrichtung sauber: {str(quelle['t'])!r}")

    # --- 4. Der Negativfall, und er ist der eigentliche Ertrag dieser Datei:
    #        EINE Kennung ueber der Schranke muss verdoppeln. Bleibt das aus,
    #        ist entweder yswift repariert (dann faellt KENNUNG_GRENZE weg) oder
    #        die Probe misst nichts mehr.
    darueber = Doc(client_id=KENNUNG_GRENZE + 1)
    darueber["t"] = Text("Hallo aus Python")
    _swift_runde(darueber)
    if str(darueber["t"]) == erwartet:
        print(
            "FEHLT: Kennung ueber 2^32-1 verdoppelt NICHT mehr -- yswift repariert? "
            "Dann KENNUNG_GRENZE und die Auflage in ADR-010 pruefen"
        )
        fehler += 1
    else:
        print(f"ok  Negativfall haelt: ueber der Schranke verdoppelt es ({str(darueber['t'])!r})")

    return fehler


if __name__ == "__main__":
    sys.exit(1 if lauf() else 0)
