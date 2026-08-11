#!/usr/bin/env python3
"""Brueckenkopf zwischen der Ausweis-App (AppleScript) und kern/ausweis.py.

WARUM ES DIESE SCHICHT GIBT, statt dass die App `ausweis.py` direkt aufruft:

1. DAS GEHEIMNIS DARF NICHT IN DIE PROZESSLISTE. `ausweis.py` nimmt es aus
   der Umgebung oder fragt per getpass -- beides geht aus `do shell script`
   nicht: dort gibt es kein TTY, und alles, was im Befehl steht, ist fuer
   jeden Prozess desselben Nutzers in `ps` sichtbar. Auch die Shell-Historie
   war schon einmal der Anlass fuer eine Korrektur (Kommentar in ausweis.py,
   2026-08-10). Dieser Helfer liest das Geheimnis deshalb von STDIN.
2. DIE APP SOLL NICHT PARSEN. `ausweis.py` schreibt Fliesstext fuer Menschen
   ("Das Geheimnis steht genau EINMAL hier"). Eine Oberflaeche, die darauf
   mit Zeichenkettensuche zugreift, bricht beim naechsten Satzumbau. Hier
   kommt JSON heraus.
3. FEHLER SOLLEN ANKOMMEN. Jeder Fehler wird als {"fehler": "..."} gemeldet,
   im Wortlaut des Moduls -- eine Oberflaeche, die "abgelaufen" durch ein
   generisches "hat nicht geklappt" ersetzt, nimmt dem Nutzer die einzige
   Information, mit der er weiterkommt.

Aufruf:  echo -n "<geheimnis>" | python3 ausweis_helfer.py <befehl> [...]
         (ohne Geheimnis auf STDIN laeuft nur `liste` und `rollen`)

Befehle:
  rollen                             bekannte Rollen samt Rechten
  liste                              vorhandene Ausweise
  anlegen  <name> <art> <rollen>     neuer Ausweis, Geheimnis im Ergebnis
  einladen <name> <fuer> <rollen>    PIN fuer eine Anmeldung
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path.insert(0, str(_w / "kern"))

import ausweis  # noqa: E402


def _geheimnis() -> str | None:
    """Von STDIN, nie aus argv. Leere Eingabe ist kein Geheimnis."""
    if sys.stdin.isatty():
        return None
    return (sys.stdin.read() or "").strip() or None


def _rollen(text: str) -> list[str]:
    return [r.strip() for r in text.split(",") if r.strip()]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(json.dumps({"fehler": "kein Befehl"}))
        return 2
    befehl = argv[1]

    try:
        if befehl == "rollen":
            print(json.dumps({
                "rollen": {name: list(rechte)
                           for name, rechte in ausweis.ROLLEN.items()},
            }, ensure_ascii=False))
            return 0

        if befehl == "liste":
            eintraege = ausweis._lies_datei(ausweis.ausweisdatei())
            print(json.dumps({
                "datei": str(ausweis.ausweisdatei()),
                "ausweise": [{"name": e.get("name"),
                              "art": e.get("art", "maschine"),
                              "rollen": e.get("rollen", [])}
                             for e in eintraege],
            }, ensure_ascii=False))
            return 0

        geheim = _geheimnis()

        if befehl == "anlegen":
            _, _, name, art, rollen = argv[:5]
            # `aussteller` nimmt das GEHEIMNIS, nicht den Namen: das Modul
            # loest damit selbst auf (loese_auf(geheimnis=aussteller, ...)).
            # Der Parametername liest sich anders -- wer hier einen Namen
            # uebergibt, bekommt eine Ablehnung, die nach fehlendem Recht
            # aussieht statt nach falschem Argument. Genau darauf bin ich am
            # 2026-08-11 hereingefallen; zwei Tests haben es gefangen.
            neu = ausweis.anlegen(name, _rollen(rollen), art=art,
                                  aussteller=geheim)
            print(json.dumps({"name": name, "art": art,
                              "rollen": _rollen(rollen), "geheimnis": neu},
                             ensure_ascii=False))
            return 0

        if befehl == "einladen":
            _, _, name, fuer, rollen = argv[:5]
            pin = ausweis.einladen(name, bedient_von=fuer,
                                   rollen=_rollen(rollen), aussteller=geheim)
            print(json.dumps({
                "name": name, "fuer": fuer, "pin": pin,
                "gueltig_minuten": ausweis.EINLADUNG_GUELTIG_MINUTEN,
            }, ensure_ascii=False))
            return 0

    except PermissionError as fehler:
        # Wortlaut des Moduls behalten: er nennt den Grund (fehlendes Recht,
        # abgelaufen, verbraucht), und der ist die einzige Information, mit
        # der der Nutzer etwas anfangen kann.
        print(json.dumps({"fehler": str(fehler)}, ensure_ascii=False))
        return 1
    except (ValueError, KeyError, IndexError) as fehler:
        print(json.dumps({"fehler": f"Eingabe unvollstaendig: {fehler}"},
                         ensure_ascii=False))
        return 2

    print(json.dumps({"fehler": f"unbekannter Befehl: {befehl}"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
