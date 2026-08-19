#!/usr/bin/env python3
"""Meldet, wenn eine fremde Software oder ein Gesetzestext seit dem letzten
Lauf einen anderen Stand zeigt -- und welche Lehren dieses Produkt nennen.

ANLASS (Knoten 79487bf9, 2026-08-19): 252 von 1112 Lehren haengen an
fremder Software. Wer sich aendert, bemerken wir heute nur zufaellig --
bei einem Gesetz ist genau das schon passiert (unquittierte Eilmeldung zu
GEG). Dieser Melder haelt je Quelle den zuletzt gesehenen Stand fest und
meldet beim naechsten Lauf NUR die Differenz.

HINWEISRECHT, KEIN VETO, wie jeder Melder in diesem Verzeichnis: er endet
IMMER mit Code 0. Und -- das ist der Satz, der im Modulkopf stehen soll,
wortwoertlich als Grenze der Aussage:

    DIESER MELDER MELDET EINEN ANLASS, NIEMALS EINE ABLOESUNG. Eine neue
    Versionsnummer heisst nicht, dass eine Lehre ueberholt ist -- nur, dass
    jemand nachsehen sollte. Die Bewertung bleibt beim Menschen.

WARUM DER STAND IN runs/ LIEGT UND NICHT IN DER WISSENSDATENBANK: er ist
Betriebszustand (zuletzt gesehene Versionsnummer je Quelle), kein Wissen --
niemand fragt "was war die vorletzte Ollama-Version", er dient nur dem
naechsten Lauf dieses Skripts als Vergleichsbasis.

KEIN MODELL, PURER VERGLEICH: `vergleiche()` ist eine reine Funktion ohne
Netz, ohne LLM -- gespeicherter Stand gegen abgerufenen Stand, Text gegen
Text. Stimmt die Annahme aus dem Auftrag nicht, zeigt sich das hier zuerst.

MOCKBARE AUSSENWELT (Walkthrough-Doktrin Punkt 2): der Netzabruf laeuft
ausschliesslich durch den injizierbaren Parameter `holer`. Der Test ruft
NIE das echte Netz, sondern stellt gecannte Antworten.

Aufruf:
    python3 melder/fremdstandsvergleich.py            # Lauf + Bericht
    python3 melder/fremdstandsvergleich.py --selftest  # nur Selbsttest
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

STAND_PFAD = Path(__file__).resolve().parent.parent / "runs" / "fremdstand_letzter_lauf.json"
TIMEOUT_SEK = 5

# Quelle -> (URL, Parser-Kennung). Parser "github" liest tag_name/published_at
# aus der GitHub-Release-API, Parser "hash" bildet einen Inhalts-Hash (fuer
# Feeds ohne eigene Versionsnummer, z.B. die Gesetzestexte).
QUELLEN: dict[str, tuple[str, str]] = {
    "flutter": ("https://api.github.com/repos/flutter/flutter/releases/latest", "github"),
    "ollama": ("https://api.github.com/repos/ollama/ollama/releases/latest", "github"),
    "swift": ("https://api.github.com/repos/swiftlang/swift/releases/latest", "github"),
    "gesetze-toc": ("https://www.gesetze-im-internet.de/gii-toc.xml", "hash"),
    "geg": ("https://www.gesetze-im-internet.de/geg/xml.zip", "hash"),
}

# Produkt -> Begriffe, nach denen in lessons_learned gesucht wird. Namensliste
# stammt aus der Vormessung des Auftrags (2026-08-19, 252 Treffer). Fuer
# gesetze-toc gibt es keine sinnvolle Eingrenzung (Gesamtverzeichnis, kein
# Einzelprodukt) -- absichtlich leer, dann werden keine Lehren gemeldet.
PRODUKT_BEGRIFFE: dict[str, list[str]] = {
    "flutter": ["Flutter", "Dart"],
    "ollama": ["Ollama"],
    "swift": ["Swift", "SwiftUI", "Xcode"],
    "geg": ["GEG", "§ 71"],
    "gesetze-toc": [],
}

Holer = Callable[[str, int], tuple[bytes, dict]]


def _echter_abruf(url: str, timeout: int) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "brainlehr-fremdstandsvergleich"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 -- feste, gelesene Feeds
        return resp.read(), dict(resp.headers)


def _parse_github(inhalt: bytes, header: dict) -> tuple[str, str | None]:
    daten = json.loads(inhalt)
    return daten["tag_name"], daten.get("published_at")


def _parse_hash(inhalt: bytes, header: dict) -> tuple[str, str | None]:
    return hashlib.sha256(inhalt).hexdigest()[:16], header.get("Last-Modified")


PARSER = {"github": _parse_github, "hash": _parse_hash}


def hole_stand_einer_quelle(name: str, holer: Holer) -> dict | None:
    """Liefert {"version":..., "datum":...} oder None bei Nicht-Erreichbarkeit.

    Ein Fehlschlag (Timeout, HTTP-Fehler, kaputtes JSON) darf den Lauf NIEMALS
    abbrechen -- deshalb der breite except. Das ist absichtlich, nicht
    nachlaessig: ein Melder, der bei einer gestoerten Quelle schweigt, ist
    von einem ohne Befund nicht unterscheidbar.
    """
    url, parser_kennung = QUELLEN[name]
    try:
        inhalt, header = holer(url, TIMEOUT_SEK)
        version, datum = PARSER[parser_kennung](inhalt, header)
        return {"version": version, "datum": datum}
    except Exception:
        return None


def vergleiche(alt: dict, neu: dict) -> list[dict]:
    """Reiner Vergleich, kein Netz, kein Modell. Meldet nur echte Differenzen.

    Erstlauf-Regel: fehlt ein Produkt im alten Stand, wird NICHTS gemeldet --
    sonst waere jeder erste Lauf eine Flut aus "Aenderung".
    """
    meldungen = []
    for produkt, eintrag in neu.items():
        if eintrag is None:
            continue
        alt_eintrag = alt.get(produkt)
        if alt_eintrag is None:
            continue
        if alt_eintrag.get("version") != eintrag.get("version"):
            meldungen.append({
                "produkt": produkt,
                "alt": alt_eintrag.get("version"),
                "neu": eintrag.get("version"),
            })
    return meldungen


def nicht_erreichte(neu: dict) -> list[str]:
    return [p for p, e in neu.items() if e is None]


def lehren_zu_produkt(begriffe: list[str]) -> list[str]:
    """Sucht lessons_learned nach den Begriffen. Keine Bewertung, nur Fund.

    Nutzt bewusst noch die Textsuche ueber description/root_cause/resolution/
    prevention/node_path -- eine spaeter ergaenzte Spalte `bezug` ersetzt das
    in einer Zeile, siehe Auftragskopf.
    """
    if not begriffe:
        return []
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))
        import speicher  # type: ignore
    except Exception:
        return []
    bedingung = " OR ".join(
        "description LIKE ? OR root_cause LIKE ? OR resolution LIKE ? "
        "OR prevention LIKE ? OR node_path LIKE ?"
        for _ in begriffe
    )
    parameter: list[str] = []
    for begriff in begriffe:
        muster = f"%{begriff}%"
        parameter.extend([muster] * 5)
    try:
        with speicher.lesen() as conn:
            zeilen = conn.execute(
                f"SELECT id FROM lessons_learned WHERE {bedingung}", parameter
            ).fetchall()
        return [z[0] for z in zeilen]
    except Exception:
        return []


def lade_stand(pfad: Path) -> dict:
    if not pfad.exists():
        return {}
    try:
        return json.loads(pfad.read_text())
    except Exception:
        return {}


def sichere_stand(pfad: Path, stand: dict) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(stand, ensure_ascii=False, indent=2, sort_keys=True))


def lauf(stand_pfad: Path = STAND_PFAD, holer: Holer = _echter_abruf) -> dict:
    alt = lade_stand(stand_pfad)
    neu = {name: hole_stand_einer_quelle(name, holer) for name in QUELLEN}

    meldungen = vergleiche(alt, neu)
    for meldung in meldungen:
        meldung["lehren"] = lehren_zu_produkt(PRODUKT_BEGRIFFE.get(meldung["produkt"], []))

    fehlend = nicht_erreichte(neu)

    # alten Stand fuer nicht erreichte Quellen behalten, sonst verlieren wir
    # die Vergleichsbasis wegen einer einzelnen Netzstoerung.
    zusammengefuehrt = dict(alt)
    for name, eintrag in neu.items():
        if eintrag is not None:
            zusammengefuehrt[name] = eintrag
    sichere_stand(stand_pfad, zusammengefuehrt)

    return {"meldungen": meldungen, "nicht_erreicht": fehlend}


def _bericht(ergebnis: dict) -> str:
    zeilen = []
    if not ergebnis["meldungen"]:
        zeilen.append("Keine Standaenderung seit dem letzten Lauf.")
    for m in ergebnis["meldungen"]:
        lehren = f", betrifft Lehren: {', '.join(m['lehren'])}" if m["lehren"] else ""
        zeilen.append(f"ANLASS: {m['produkt']} {m['alt']} -> {m['neu']}{lehren}")
    if ergebnis["nicht_erreicht"]:
        zeilen.append("Nicht erreicht: " + ", ".join(ergebnis["nicht_erreicht"]))
    return "\n".join(zeilen)


def _selftest() -> None:
    # gleicher Stand -> keine Meldung
    alt = {"x": {"version": "1.0", "datum": None}}
    neu = {"x": {"version": "1.0", "datum": None}}
    assert vergleiche(alt, neu) == []

    # geaenderter Stand -> Meldung mit altem und neuem Wert
    neu2 = {"x": {"version": "2.0", "datum": None}}
    m = vergleiche(alt, neu2)
    assert m == [{"produkt": "x", "alt": "1.0", "neu": "2.0"}]

    # Erstlauf (kein alter Stand) -> keine Meldung
    assert vergleiche({}, neu2) == []

    # nicht erreichte Quelle -> eigene Liste, keine Meldung, kein Absturz
    neu3 = {"x": {"version": "1.0", "datum": None}, "y": None}
    assert vergleiche(alt, neu3) == []
    assert nicht_erreichte(neu3) == ["y"]

    print("Selbsttest ok.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    start = time.monotonic()
    ergebnis = lauf()
    dauer = time.monotonic() - start
    print(_bericht(ergebnis))
    print(f"Laufzeit: {dauer:.1f}s")
    sys.exit(0)
