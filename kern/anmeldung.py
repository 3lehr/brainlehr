#!/usr/bin/env python3
"""Einen Teilnehmer anmelden -- ein Befehl, drei Fragen, fertiger Prompt.

    python3 kern/anmeldung.py hermes

Anlass 2026-08-10: Eine einzige Anmeldung kostete ueber eine Stunde und vier
Fehlversuche. Nicht am Verfahren -- das lief korrekt und hat jeden falschen
Versuch richtig abgewiesen -- sondern an der Bedienung: vier Schalter
(--einladen --fuer --rollen --art) mussten stimmen, das Geheimnis war nur
ueber eine Umgebungsvariable erreichbar, und wer es aus der falschen Zeile
einer Datei kopierte, bekam als Antwort ein stilles "unbeglaubigt" statt
eines Fehlers. Betreiber dazu: "das rafft so keine Sau".

Was dieses Modul NICHT tut, und warum: Es lockert keine Regel. Die
Einbuergerungsschranke, die Befristung der PIN und ihre Einmaligkeit gelten
unveraendert -- ausweis.py bleibt die einzige Stelle, an der Rechte
entstehen. Hier wird nur gefragt statt vorausgesetzt.

Eigenes Modul statt Anbau an ausweis.py (1593 Zeilen, Monolith-Bremse ab
1500): Bedienung und Rechtevergabe sind zwei Gegenstaende.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import getpass
import json
import os
import sys

import ausweis

# Was ein neuer Teilnehmer ueblicherweise wird. Nicht alle Rollen aus
# ausweis.ROLLEN: 'betreiber' und 'meldeamt' werden bewusst nicht angeboten --
# wer sie vergibt, soll das ausdruecklich tun und nicht aus einer Liste
# durchtippen.
ANGEBOTEN = [
    ("fachkundig", "lesen und schreiben, keine Normen, keine Ausweise"),
    ("leser", "nur lesen"),
    ("gast", "nur was ausdruecklich freigegeben ist"),
    ("schreiber", "lesen und schreiben, ohne Fachurteil"),
]


def _angemeldete() -> set[str]:
    """Namen aus der Ausweisdatei. ausweis.py bietet dafuer keine Funktion --
    die CLI liest die Datei selbst, und das tut hier dasselbe."""
    try:
        d = json.loads(ausweis.ausweisdatei().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {a["name"] for a in d.get("ausweise", []) if a.get("name")}


def _frage_rolle() -> str:
    print("\nWelche Rolle?")
    for i, (name, was) in enumerate(ANGEBOTEN, 1):
        vorgabe = "  (Vorgabe)" if i == 1 else ""
        print(f"  {i}) {name:12s} {was}{vorgabe}")
    roh = input("Nummer oder Name [1]: ").strip() or "1"
    if roh.isdigit() and 1 <= int(roh) <= len(ANGEBOTEN):
        return ANGEBOTEN[int(roh) - 1][0]
    if roh in {n for n, _ in ANGEBOTEN}:
        return roh
    print(f"'{roh}' ist keine der angebotenen Rollen.", file=sys.stderr)
    raise SystemExit(2)


def _frage_geheimnis(wer: str) -> str:
    """Verdeckt, mit sofortiger Rueckmeldung ob es passt.

    Die Rueckmeldung ist der Kern: ausweis.loese_auf faellt bei einem
    falschen Geheimnis auf 'unbeglaubigt:' zurueck statt zu scheitern --
    richtig so (ein falsches Geheimnis darf nie mehr Rechte ergeben als gar
    keines), aber fuer den Tippenden sieht es aus wie 'nichts passiert'.
    Genau daran sind am 2026-08-10 drei Versuche gescheitert.
    """
    for versuch in (1, 2, 3):
        g = getpass.getpass(f"Geheimnis von {wer} (bleibt verdeckt): ")
        if not g:
            print("  nichts eingegeben.", file=sys.stderr)
            continue
        aufgeloest = ausweis.loese_auf(wer, geheimnis=g)
        if not aufgeloest.protokollname.startswith(ausweis.UNBEGLAUBIGT):
            print(f"  erkannt als {aufgeloest.protokollname}, "
                  f"Rollen: {', '.join(aufgeloest.rollen) or '(keine)'}")
            return g
        print(f"  passt nicht (Versuch {versuch} von 3). Das Geheimnis ist die "
              f"Zeile OHNE Leerzeichen -- der Rest der Datei ist Erklaertext.",
              file=sys.stderr)
    raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("name", help="Name des neuen Teilnehmers, z.B. hermes")
    p.add_argument("--durch", default="markus",
                   help="wer einlaedt und verantwortet (Vorgabe: markus)")
    p.add_argument("--rolle", default=None, help="ueberspringt die Rueckfrage")
    p.add_argument("--art", default="maschine", choices=ausweis.ARTEN)
    a = p.parse_args(argv)

    if a.name in _angemeldete():
        print(f"'{a.name}' ist bereits angemeldet. Nichts getan.")
        return 0

    print(f"Neuer Teilnehmer: {a.name}   (verantwortet von {a.durch})")
    rolle = a.rolle or _frage_rolle()
    geheimnis = _frage_geheimnis(a.durch)

    os.environ[ausweis.ENV_GEHEIMNIS] = geheimnis
    try:
        pin = ausweis.einladen(a.name, bedient_von=a.durch, rollen=[rolle],
                               art=a.art)
    finally:
        # Nicht in der Umgebung stehen lassen: jeder Unterprozess dieses
        # Laufs wuerde es sonst erben.
        os.environ.pop(ausweis.ENV_GEHEIMNIS, None)

    print(f"\n  Anmeldename: {a.name}")
    print(f"  PIN:         {pin}")
    print(f"  Rolle:       {rolle}")
    print(f"\n  Gueltig {ausweis.EINLADUNG_GUELTIG_MINUTEN} Minuten, einmalig.")
    print(f"  Diese Zeile an {a.name} geben:\n")
    print(f'      knowledge_anmelden(name="{a.name}", pin="{pin}")\n')
    return 0


def _selftest() -> None:
    """Prueft die Teile, die ohne Eingabe pruefbar sind."""
    # Die angebotenen Rollen muessen ausweis.ROLLEN kennen -- ein Tippfehler
    # hier faellt sonst erst beim echten Anmelden auf.
    for name, _ in ANGEBOTEN:
        assert name in ausweis.ROLLEN, f"unbekannte Rolle angeboten: {name}"
    # Und die beiden gefaehrlichen duerfen NICHT dabei sein.
    angeboten = {n for n, _ in ANGEBOTEN}
    for heikel in ("betreiber", "meldeamt"):
        assert heikel not in angeboten, f"{heikel} darf nicht zur Auswahl stehen"
    # Ein bereits angemeldeter Name fuehrt zu einem sauberen Abbruch statt zu
    # einer zweiten Einladung -- ohne Eingabe pruefbar, weil die Abfrage vor
    # jeder Rueckfrage steht.
    vorhandene = _angemeldete()
    assert vorhandene, "kein Ausweis im Bestand -- Selbsttest nicht aussagekraeftig"
    ein_vorhandener = sorted(vorhandene)[0]
    assert main([ein_vorhandener]) == 0, "doppelte Anmeldung muss sauber enden"
    print(f"anmeldung.py: Selbsttest gruen ({len(ANGEBOTEN)} Rollen angeboten, "
          f"betreiber/meldeamt ausgeschlossen, Doppelanmeldung faengt ab)")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        raise SystemExit(main())
