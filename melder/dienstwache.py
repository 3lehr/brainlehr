#!/usr/bin/env python3
"""Wacht ueber den Dokumentdienst -- aber nur ueber das, was keinen Normalfall hat.

G2 aus `docs/PLAN_SICHERHEIT_2026-08-14.md`.

DIE TRENNUNG IST DER GANZE INHALT. Der Dienst zaehlt acht Groessen
(`kern/dokumentdienst.Kennzahlen`). Vier davon haben im Normalbetrieb den Wert
NULL -- sie brauchen keine Schwelle, weil jedes Vorkommen bereits die Meldung
ist:

    abgewiesene_zugaenge   das erste, was ein Scanner ausloest
    unbekannte_arten       jemand spricht ein anderes Protokoll
    kennungsverstoesse     ein Klient, der die 2^32-Auflage nicht kennt
    zweite Herkunftsadresse  ein Geraet, das dort nicht stehen sollte

Die anderen vier (`verbindungen`, `updates`, `bytes_empfangen`,
`gebremste_nachrichten`) sind MENGENHAFT. Fuer sie gibt es hier bewusst KEINE
Schwelle -- die entsteht erst aus einer Nullmessung im echten Betrieb (G3).
Eine geratene Schwelle schlaegt entweder nie an oder staendig, und staendig
heisst: weggeklickt. Genau diese Fehlerklasse hat am 2026-08-14 dreimal
zugeschlagen (`L-528f0c`).

WAS DIESER MELDER NICHT KANN, und es steht hier, damit niemand aus seinem
Schweigen etwas anderes schliesst: Er liest eine DATEI, die der Dienst
schreibt. Laeuft kein Dienst, schweigt er -- das ist kein "alles in Ordnung",
sondern "nichts gemessen". Der Unterschied steht in der Ausgabe.

ZWEITE HERKUNFTSADRESSE, und warum sie eine Einstellung braucht: In einem
Heimnetz mit einem Mac und einem Mini sind ZWEI Adressen der Normalfall. Die
erwartete Zahl steht darum in BRAINLEHR_ERWARTETE_GERAETE (Vorgabe 1) -- wer
sie nicht setzt, bekommt beim zweiten Geraet eine Meldung, und das ist die
richtige Vorgabe: lieber einmal zu viel melden, als das fremde Geraet
uebersehen.

Aufruf:
    python3 melder/dienstwache.py --pruefen [--kennzahlen DATEI]
    python3 melder/dienstwache.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

VORGABE_DATEI = Path(os.environ.get("BRAINLEHR_KENNZAHLEN", "")) if os.environ.get(
    "BRAINLEHR_KENNZAHLEN") else Path.home() / ".brainlehr" / "dienst-kennzahlen.json"

# Zaehler ohne Normalfall: jedes Vorkommen ist die Meldung.
OHNE_NORMALFALL = {
    "abgewiesene_zugaenge": "abgewiesener Zugang -- jemand hat sich ohne gueltigen Ausweis verbunden",
    "unbekannte_arten": "unbekannte Nachrichtenart -- jemand spricht ein anderes Protokoll",
    "kennungsverstoesse": "Kennungsverstoss -- ein Klient haelt die 2^32-Auflage nicht ein",
}

# Mengenhafte Zaehler. Hier steht ausdruecklich KEINE Schwelle, siehe Kopf.
MENGENHAFT = ("verbindungen", "updates", "bytes_empfangen", "gebremste_nachrichten")


def erwartete_geraete() -> int:
    roh = os.environ.get("BRAINLEHR_ERWARTETE_GERAETE", "1")
    try:
        return max(1, int(roh))
    except ValueError:
        return 1


def lies(datei: Path) -> dict | None:
    """Der Stand, oder None -- und None heisst 'nichts gemessen', nicht 'alles gut'."""
    try:
        return json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def befunde(stand: dict, geraete: int | None = None) -> list[str]:
    """Was gemeldet gehoert. Leere Liste heisst: nichts Auffaelliges gesehen."""
    erwartet = geraete if geraete is not None else erwartete_geraete()
    aus = []
    for feld, satz in OHNE_NORMALFALL.items():
        anzahl = int(stand.get(feld) or 0)
        if anzahl:
            aus.append(f"{anzahl}x {satz}")

    herkunft = stand.get("herkunft") or {}
    if len(herkunft) > erwartet:
        adressen = ", ".join(sorted(herkunft))
        aus.append(f"{len(herkunft)} Herkunftsadressen statt {erwartet} erwarteten: {adressen}")
    return aus


def bericht(datei: Path) -> tuple[int, str]:
    """Rueckgabe: (Beanstandungen, Text). Nie ein blosses 'ok'."""
    stand = lies(datei)
    if stand is None:
        return 0, (f"Dienstwache: keine Kennzahlen unter {datei} -- nichts gemessen. "
                   "Der Dienst schreibt sie mit --kennzahlen DATEI.")

    treffer = befunde(stand)
    mengen = " · ".join(f"{f}={stand.get(f, 0)}" for f in MENGENHAFT)
    kopf = f"Dienstwache (Stand {stand.get('stand', 'unbekannt')}): {mengen}"
    if not treffer:
        return 0, kopf + " -- nichts ohne Normalfall aufgetreten."
    zeilen = "\n".join(f"  - {t}" for t in treffer)
    return len(treffer), f"{kopf}\nWARNUNG, {len(treffer)} Befund(e):\n{zeilen}"


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        datei = Path(tmp) / "k.json"

        # Fehlende Datei ist KEIN gruener Befund.
        anzahl, text = bericht(datei)
        assert anzahl == 0 and "nichts gemessen" in text, text
        assert "in Ordnung" not in text

        def schreibe(**felder):
            grund = {f: 0 for f in ("verbindungen", "abgewiesene_zugaenge",
                                    "abgelehnte_updates", "unbekannte_arten",
                                    "kennungsverstoesse", "gebremste_nachrichten",
                                    "updates", "bytes_empfangen")}
            grund["herkunft"] = {"127.0.0.1": 3}
            grund["stand"] = "2026-08-14T12:00:00Z"
            grund.update(felder)
            datei.write_text(json.dumps(grund), encoding="utf-8")

        # Der Normalfall schlaegt NICHT an -- ohne diesen Fall waere jeder
        # Positivbefund wertlos.
        schreibe(verbindungen=12, updates=4000, bytes_empfangen=900000)
        anzahl, text = bericht(datei)
        assert anzahl == 0, text
        assert "updates=4000" in text, "die Mengen gehoeren in den Bericht, ohne Urteil"

        # Jeder der drei Zaehler schlaegt einzeln an.
        for feld in OHNE_NORMALFALL:
            schreibe(**{feld: 1})
            anzahl, text = bericht(datei)
            assert anzahl == 1, (feld, text)
            assert "WARNUNG" in text

        # Herkunft: Grenzwert dreifach.
        schreibe()
        assert befunde(lies(datei), geraete=1) == [], "eine Adresse ist der Normalfall"
        datei_stand = lies(datei)
        datei_stand["herkunft"] = {"127.0.0.1": 3, "192.168.178.99": 1}
        assert len(befunde(datei_stand, geraete=1)) == 1, "zwei Adressen bei einem Geraet melden"
        assert befunde(datei_stand, geraete=2) == [], "zwei Adressen bei zwei Geraeten nicht"
        datei_stand["herkunft"] = {"127.0.0.1": 3, "a": 1, "b": 1}
        assert len(befunde(datei_stand, geraete=2)) == 1, "drei Adressen bei zwei Geraeten melden"

        # Die Adressen stehen IM Befund -- eine Meldung ohne Adresse zwingt
        # zum Nachsehen an einer Stelle, die der Melder schon kennt.
        assert "192.168.178.99" in " ".join(
            befunde({"herkunft": {"127.0.0.1": 1, "192.168.178.99": 1}}, geraete=1))

        # Mengenhaftes schlaegt NIE an, auch nicht bei absurden Werten --
        # solange keine Nullmessung vorliegt (G3).
        schreibe(verbindungen=10**6, updates=10**9, bytes_empfangen=10**12,
                 gebremste_nachrichten=10**5)
        assert bericht(datei)[0] == 0, "mengenhafte Zaehler haben hier keine Schwelle"

        # Kaputte Datei: wie fehlend, nicht wie leer.
        datei.write_text("{kein json", encoding="utf-8")
        assert bericht(datei)[0] == 0 and "nichts gemessen" in bericht(datei)[1]

    print("dienstwache: Selbsttest bestanden")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pruefen", action="store_true")
    p.add_argument("--kennzahlen", default=None)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)

    if a.selftest:
        return _selftest()
    if a.pruefen:
        datei = Path(a.kennzahlen) if a.kennzahlen else VORGABE_DATEI
        anzahl, text = bericht(datei)
        print(text)
        return 0        # meldet, blockiert nicht
    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
