#!/usr/bin/env python3
"""Was das Haus verlaesst, wird angesehen -- vorerst nur angesehen.

Uebernahme aus der Stiftshuette, Punkt 2 (hub/docs/PLAN_STIFTSHUETTE_
UEBERNAHME_2026-08-08.md). Dort laesst der HTTP-Server jede Antwort durch
einen Datenschutzfilter laufen, bevor sie das Haus verlaesst. Bei uns ist
die Lage schaerfer: der Abruf spielt Wissen in FREMDE Kontexte ein -- in
jedes Modell, in jeder Sitzung, bei jedem Prompt.

AUSFALLRICHTUNG, Entscheidung des Betreibers 2026-08-08T18:27:16+0200:
melden, nicht entfernen. Dieses Modul schwaerzt nichts und aendert keine
Ausgabe. Es schreibt Verdachtsfaelle mit Knoten, Regel und Textstelle in ein
Protokoll. Erst wenn die echte Trefferliste vorliegt, wird ueber Schwellen
und Schwaerzung entschieden -- an gemessenen Daten statt an geratenen.

Der Grund steht in L-d1d0d7: ein Pruefer, der die Rahmung mitscannte,
erzeugte 216 Fehlalarme auf Hexziffern. Wer hier sofort schwaerzt, schwaerzt
dieselben 216 Stellen und merkt es nicht, weil der Abruf still passiert.

Daraus folgt eine Regel, die dieses Modul einhalten MUSS: geprueft wird der
ROHE Text aus dem Bestand, nie die fertig gerahmte Ausgabezeile. Die
Ausgabezeile enthaelt Hex-Ersetzungen und Abgrenzungsmarken aus
einschleusung.entschaerfe_fuer_ausgabe() -- genau die Rahmung, an der sich
L-d1d0d7 verschluckt hat.

Aufruf: python3 bereinigung.py --selftest
        python3 bereinigung.py --bericht   # was das Protokoll bisher sah
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import re
import sys
from pathlib import Path

import zeitmarke

PROTOKOLL = _w / "bereinigung_log.jsonl"
PROTOKOLL_MAX_BYTES = 200_000  # gleiche Kappung wie zero_hit_log.jsonl

# Muster bewusst eng. Ein Muster, das viel faengt, faengt vor allem Falsches,
# und die Fehlalarme sieht in einem stillen Abruf niemand. Was hier fehlt
# (Namen, Anschriften, Freitext), fehlt absichtlich: es ist ohne Kontext
# nicht maschinell entscheidbar, und die Messung soll zeigen, ob es ueberhaupt
# vorkommt, bevor jemand darauf eine Heuristik baut.
MUSTER: list[tuple[str, re.Pattern, str]] = [
    ("email", re.compile(r"\b[\w.%+-]+@[\w-]+\.[A-Za-z]{2,}\b"),
     "E-Mail-Adresse"),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){3,7}\b"),
     "IBAN"),
    ("telefon", re.compile(r"(?<![\w.])(?:\+\d{1,3}[ /-]?)?\(?0\d{2,4}\)?[ /-]?\d{3,}[ -]?\d{2,}(?![\w.])"),
     "Telefonnummer"),
    ("schluessel", re.compile(r"\b(?:sk-[A-Za-z0-9]{16,}|gh[pousr]_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{12,}|xox[baprs]-[A-Za-z0-9-]{10,})"),
     "API-Schluessel oder Token"),
]

# Was NICHT als Fund zaehlt, obwohl es auf ein Muster passt. Ohne diese Liste
# meldet der Melder die Beispiele aus der eigenen Dokumentation und die
# Platzhalter aus Tests -- Rauschen, das die Messung wertlos macht.
UNVERDAECHTIG = re.compile(
    r"(?:example\.(?:com|org|net)|@beispiel\.|noreply@|localhost|"
    r"\bDE00\b|\bXX00\b|<[^>]*@[^>]*>)",
    re.IGNORECASE,
)


def _jetzt() -> str:
    return zeitmarke.jetzt()


def _maskiert(text: str) -> str:
    """Text mit ALLEN Fundstellen ersetzt. Grundlage fuer jedes Umfeld.

    Warum alle und nicht nur die eigene: beim ersten Messlauf stand im Umfeld
    des IBAN-Fundes die Nachbar-E-Mail im Klartext ("...h@kantine.de sowie
    IBAN [24 Zeichen]..."). Ein Protokoll, das die eigene Fundstelle schwaerzt
    und die daneben stehende ausschreibt, ist genau das Leck, das es messen
    soll -- nur unauffaelliger, weil es aussieht, als sei geschwaerzt worden."""
    spannen = []
    for _, muster, _ in MUSTER:
        for t in muster.finditer(text):
            if not UNVERDAECHTIG.search(t.group()):
                spannen.append((t.start(), t.end()))
    if not spannen:
        return text
    spannen.sort()
    aus, ende = [], 0
    for a, b in spannen:
        if a < ende:            # Ueberlappung (Telefonmuster in einer IBAN)
            ende = max(ende, b)
            continue
        aus.append(text[ende:a] + f"[{b - a} Zeichen]")
        ende = b
    aus.append(text[ende:])
    return "".join(aus)


def _stelle(text: str, treffer: re.Match, rand: int = 24) -> str:
    """Umfeld des Treffers, damit sich ein Fehlalarm ohne Nachschlagen
    erkennen laesst -- aus dem VOLLSTAENDIG maskierten Text, siehe
    _maskiert(). Keine Fundstelle steht je woertlich im Protokoll, weder die
    eigene noch eine benachbarte."""
    sicher = _maskiert(text)
    marke = f"[{len(treffer.group())} Zeichen]"
    stelle = sicher.find(marke)
    if stelle < 0:                     # ueberlappender Fund, in einer groesseren Marke aufgegangen
        return "...(Fundstelle liegt in einem groesseren Treffer)..."
    a = max(0, stelle - rand)
    b = min(len(sicher), stelle + len(marke) + rand)
    return f"...{sicher[a:b]}...".replace("\n", " ")


def erkenne(text: str | None) -> list[dict]:
    """Verdachtsfaelle in ROHEM Bestandstext. Kein DB-Zugriff, kein
    Seiteneffekt -- reine Textpruefung, damit sie im Schreib- wie im
    Lesepfad ohne Kosten laufen kann."""
    if not text:
        return []
    funde = []
    for name, muster, klartext in MUSTER:
        for treffer in muster.finditer(text):
            if UNVERDAECHTIG.search(treffer.group()):
                continue
            funde.append({
                "muster": name,
                "was": klartext,
                "position": treffer.start(),
                "laenge": len(treffer.group()),
                "umfeld": _stelle(text, treffer),
            })
    return funde


def melde(anlass: str, quellen: list[tuple[str, dict[str, str | None]]]) -> int:
    """Verdacht protokollieren, nie blockieren, nie aendern.

    quellen: [(referenz, {feldname: rohtext})] -- Referenz ist der Knotenpfad
    oder die Lehrkennung, damit ein Fund nachschlagbar bleibt.

    Rueckgabe: Anzahl der Funde (fuer Tests; der Aufrufer wertet sie nicht
    aus). Jeder Fehler wird verschluckt, gleiches Muster wie
    _check_injection_suspects: eine Nebenpruefung darf den Hauptweg nie zum
    Scheitern bringen."""
    try:
        funde = []
        for ref, felder in quellen:
            for feld, roh in (felder or {}).items():
                for fund in erkenne(roh):
                    funde.append({**fund, "ref": ref, "feld": feld})
        if not funde:
            return 0
        zeile = json.dumps({"zeit": _jetzt(), "anlass": anlass, "funde": funde},
                           ensure_ascii=False)
        if PROTOKOLL.exists() and PROTOKOLL.stat().st_size > PROTOKOLL_MAX_BYTES:
            alt = PROTOKOLL.read_text(encoding="utf-8").splitlines(keepends=True)
            PROTOKOLL.write_text("".join(alt[len(alt) // 2:]), encoding="utf-8")
        with PROTOKOLL.open("a", encoding="utf-8") as f:
            f.write(zeile + "\n")
        return len(funde)
    except Exception:
        return 0


def bericht() -> dict:
    """Was das Protokoll bisher gesehen hat -- die Grundlage, auf der spaeter
    ueber Schwellen entschieden wird."""
    if not PROTOKOLL.exists():
        return {"zeilen": 0, "funde": 0, "nach_muster": {}, "hinweis": "noch nichts protokolliert"}
    zeilen = funde = 0
    nach_muster: dict[str, int] = {}
    for roh in PROTOKOLL.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(roh)
        except Exception:
            continue
        zeilen += 1
        for f in e.get("funde", []):
            funde += 1
            nach_muster[f["muster"]] = nach_muster.get(f["muster"], 0) + 1
    return {"zeilen": zeilen, "funde": funde, "nach_muster": nach_muster}


def _selftest() -> None:
    assert erkenne("Schreib an markus.lehr@firma.de wegen der Rechnung"), "E-Mail muss auffallen"
    assert not erkenne("Schreib an test@example.com"), "Doku-Beispiel darf nicht melden"
    assert not erkenne("Co-Authored-By: Claude <noreply@anthropic.com>"), "noreply darf nicht melden"
    assert erkenne("IBAN DE89 3704 0044 0532 0130 00 ueberweisen"), "IBAN muss auffallen"
    assert erkenne("Token sk-abcdefghijklmnopqrstuvwx im Klartext"), "Schluessel muss auffallen"

    # Der Kern der Entscheidung: die GERAHMTE Ausgabe wird nie geprueft.
    # Gegenprobe zu L-d1d0d7 -- Hexziffern und Marken duerfen nichts ausloesen.
    gerahmt = "⟦DATEN, ungeprueft: irgendwas \\x1b \\u202e 0x7788 deadbeef⟧"
    assert not erkenne(gerahmt), "Rahmung darf keinen Fund erzeugen"

    # Das Protokoll schreibt die Fundstelle NICHT woertlich mit.
    text = "Kontakt: markus.lehr@firma.de"
    fund = erkenne(text)[0]
    assert "markus.lehr@firma.de" not in fund["umfeld"], "Fundstelle darf nicht im Protokoll stehen"
    assert "Kontakt" in fund["umfeld"], "Umfeld muss die Einordnung erlauben"

    # Und auch nicht die des NACHBARN. Gemessen am ersten echten Lauf: im
    # Umfeld des IBAN-Fundes stand die E-Mail daneben im Klartext.
    nachbarn = "Rueckfragen an zwiebel.koch@kantine.de sowie IBAN DE89 3704 0044 0532 0130 00"
    for f in erkenne(nachbarn):
        assert "zwiebel.koch@kantine.de" not in f["umfeld"], f"Nachbar-E-Mail im Umfeld von {f['muster']}"
        assert "3704 0044" not in f["umfeld"], f"Nachbar-IBAN im Umfeld von {f['muster']}"

    # Negativfall: gewoehnlicher Text erzeugt keine Meldung.
    assert not erkenne("Der Testlauf ergab 636 gruen und 11 rot, Version 2.1.222")
    assert erkenne(None) == [] and erkenne("") == []
    print("selftest ok (10 Faelle)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--bericht", action="store_true")
    args = p.parse_args()
    if args.selftest:
        _selftest()
    elif args.bericht:
        print(json.dumps(bericht(), ensure_ascii=False, indent=2))
    else:
        p.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
