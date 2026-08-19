#!/usr/bin/env python3
"""Haelt die Zahlen der anderen Melder fest und meldet beim naechsten Lauf
nur, WAS sich seit dem letzten Mal bewegt hat -- Richtung und Betrag.

ANLASS (Knoten 79487bf9, 2026-08-19): sechs Melder liefern jeden Lauf eine
Zahl (gatestand, vektorstand, rasterblick, kennungskollision, vier_nenner,
derivatfrische), und niemand vergleicht sie mit dem letzten Mal. Vorlage ist
`fremdstandsvergleich.py` -- gespeicherter Stand gegen abgerufenen Stand,
nur die Differenz wird gemeldet.

"28/56 auf 26/56" ist eine Meldung, keine Anklage -- es kann eine
Verschlechterung sein oder eine ehrlichere Zaehlung. Dieser Melder beurteilt
NICHT, ob eine Bewegung gut oder schlecht ist, nur dass und wie viel sie war.

HINWEISRECHT, KEIN VETO: er endet IMMER mit Code 0.

KEIN MODELL, KEIN NETZ: jeder Untermelder laeuft als eigener Unterprozess
(subprocess), seine Textausgabe wird mit regulaeren Ausdruecken in Zahlen
zerlegt und mit dem gespeicherten Stand verglichen -- reiner Textvergleich.

MOCKBARE AUSSENWELT (Walkthrough-Doktrin Punkt 2): der Unterprozess-Aufruf
laeuft ausschliesslich durch den injizierbaren Parameter `ausfuehrer`. Der
Test ruft NIE die echten Melder, sondern stellt gecannte Ausgaben.

BEFUND BEIM BAU (2026-08-19): `vier_nenner.py` macht ohne `--ohne-c` bis zu
45 echte Ollama-Aufrufe und blockiert damit ueber zwei Minuten -- fuer einen
Sitzungsstart untauglich. Dieser Melder ruft es deshalb mit `--ohne-c` auf;
die Kennzahl C bleibt dadurch dauerhaft "nicht gemessen" und wird hier nicht
verglichen.

Aufruf:
    python3 melder/bewegungsmelder.py            # Lauf + Bericht
    python3 melder/bewegungsmelder.py --selftest  # nur Selbsttest
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

STAND_PFAD = Path(__file__).resolve().parent.parent / "runs" / "bewegungsmelder_letzter_lauf.json"
MELDER_DIR = Path(__file__).resolve().parent
TIMEOUT_SEK = 60

Ausfuehrer = Callable[[list[str]], str]


def _echter_ausfuehrer(argv: list[str]) -> str:
    r = subprocess.run(
        [sys.executable, *argv], cwd=MELDER_DIR.parent,
        capture_output=True, text=True, timeout=TIMEOUT_SEK,
    )
    return r.stdout


# --- Parser: Text der Untermelder -> flache Zahlen-Dicts --------------------

def _p_gatestand(text: str) -> dict[str, int]:
    werte: dict[str, int] = {}
    for m in re.finditer(
        r"^(\S+\.md): (\d+)/(\d+) belegt, (\d+) ohne Gate-Lauf(?:, (\d+) vertagt)?",
        text, re.M,
    ):
        datei, belegt, gesamt, offen, vertagt = m.groups()
        p = datei[:-3]
        werte[f"{p}.belegt"] = int(belegt)
        werte[f"{p}.gesamt"] = int(gesamt)
        werte[f"{p}.offen"] = int(offen)
        if vertagt is not None:
            werte[f"{p}.vertagt"] = int(vertagt)
    return werte


def _p_vektorstand(text: str) -> dict[str, int]:
    werte: dict[str, int] = {}
    m = re.search(
        r"Knoten: (\d+) gesamt, (\d+) ohne Einbettung, (\d+) mit veralteter "
        r"Pruefsumme, (\d+) beim Einbetten gekappt", text,
    )
    if m:
        werte["knoten.gesamt"], werte["knoten.fehlt"], werte["knoten.veraltet"], werte["knoten.gekappt"] = (
            int(x) for x in m.groups()
        )
    m = re.search(
        r"Lehren: (\d+) gesamt, (\d+) ohne Einbettung, (\d+) mit veralteter "
        r"Pruefsumme, (\d+) beim Einbetten gekappt", text,
    )
    if m:
        werte["lehren.gesamt"], werte["lehren.fehlt"], werte["lehren.veraltet"], werte["lehren.gekappt"] = (
            int(x) for x in m.groups()
        )
    return werte


def _p_rasterblick(text: str) -> dict[str, int]:
    m = re.search(r"(\d+) Ergebnisdatei\(en\) ohne Rastervermerk", text)
    if m:
        return {"ohne_vermerk": int(m.group(1))}
    if "alle Ergebnisdateien unter runs/ haben einen Vermerk" in text:
        return {"ohne_vermerk": 0}
    return {}


def _p_kennungskollision(text: str) -> dict[str, int]:
    m = re.search(r"(\d+) Kennungskollision\(en\), (\d+) spaeteres Wiederaufgreifen", text)
    if not m:
        return {}
    return {"kollisionen": int(m.group(1)), "wiederaufgreifen": int(m.group(2))}


def _p_vier_nenner(text: str) -> dict[str, int]:
    werte: dict[str, int] = {}
    for zeile, praefix in (("A", "a"), ("B", "b")):
        m = re.search(rf"^{zeile}: (\d+)/(\d+)", text, re.M)
        if m:
            werte[f"{praefix}.trefer"] = int(m.group(1))
            werte[f"{praefix}.nenner"] = int(m.group(2))
    return werte


def _p_derivatfrische(text: str) -> dict[str, int]:
    werte: dict[str, int] = {}
    m = re.search(r"Bestand: (\d+) Dateien . (\d+) Dokumente mit erklaertem Stand", text)
    if m:
        werte["dateien"] = int(m.group(1))
        werte["derivate"] = int(m.group(2))
    m = re.search(r"Ueberholt \(Stand aelter als \d+ Tage\): (\d+)", text)
    if m:
        werte["ueberholt"] = int(m.group(1))
    m = re.search(r"Befunde: (\d+) aelter als ihre Quelle", text)
    if m:
        werte["befunde"] = int(m.group(1))
    return werte


# Name -> (argv, Parser)
LAEUFER: dict[str, tuple[list[str], Callable[[str], dict[str, int]]]] = {
    "gatestand": (["melder/gatestand.py"], _p_gatestand),
    "vektorstand": (["melder/vektorstand.py"], _p_vektorstand),
    "rasterblick": (["melder/rasterblick.py"], _p_rasterblick),
    "kennungskollision": (["melder/kennungskollision.py"], _p_kennungskollision),
    "vier_nenner": (["melder/vier_nenner.py", "--ohne-c"], _p_vier_nenner),
    "derivatfrische": (["melder/derivatfrische.py"], _p_derivatfrische),
}


def sammeln(ausfuehrer: Ausfuehrer) -> dict[str, dict]:
    """Ruft jeden Untermelder ueber `ausfuehrer` auf und zerlegt seine
    Ausgabe. Ein Fehlschlag (Absturz, leere/unlesbare Ausgabe) bricht den
    Lauf NICHT ab -- der Melder erscheint als 'nicht gelesen'."""
    ergebnis: dict[str, dict] = {}
    for name, (argv, parser) in LAEUFER.items():
        try:
            text = ausfuehrer(argv)
            werte = parser(text)
            if not werte:
                ergebnis[name] = {"ok": False, "fehler": "keine lesbare Zahl in der Ausgabe"}
            else:
                ergebnis[name] = {"ok": True, "werte": werte}
        except Exception as exc:  # noqa: BLE001 -- Hinweisrecht, kein Absturz
            ergebnis[name] = {"ok": False, "fehler": f"{type(exc).__name__}: {exc}"}
    return ergebnis


def vergleichen(alt: dict[str, dict], neu: dict[str, dict]) -> list[str]:
    """Reine Funktion: gespeicherter Stand gegen neuen Stand, Zahl gegen
    Zahl. Kein gespeicherter Stand fuer einen Melder -> Erstlauf fuer ihn,
    keine Meldung. Gleiche Zahl -> keine Meldung."""
    zeilen: list[str] = []
    for name, neu_eintrag in neu.items():
        if not neu_eintrag.get("ok"):
            continue
        alt_eintrag = alt.get(name)
        if not alt_eintrag or not alt_eintrag.get("ok"):
            continue
        for k, nv in neu_eintrag["werte"].items():
            av = alt_eintrag["werte"].get(k)
            if av is None:
                zeilen.append(f"{name}.{k}: neu erschienen ({nv})")
            elif av != nv:
                richtung = "gestiegen" if nv > av else "gefallen"
                zeilen.append(f"{name}.{k}: {av} -> {nv} ({richtung} um {abs(nv - av)})")
    return zeilen


def _stand_lesen() -> dict[str, dict]:
    if not STAND_PFAD.exists():
        return {}
    try:
        return json.loads(STAND_PFAD.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _stand_schreiben(neu: dict[str, dict]) -> None:
    STAND_PFAD.parent.mkdir(parents=True, exist_ok=True)
    STAND_PFAD.write_text(json.dumps(neu, indent=2, ensure_ascii=False, sort_keys=True))


def main() -> None:
    if "--selftest" in sys.argv:
        _selftest()
        return

    t0 = time.time()
    alt = _stand_lesen()
    neu = sammeln(_echter_ausfuehrer)
    dauer = time.time() - t0

    nicht_gelesen = [n for n, e in neu.items() if not e.get("ok")]
    if nicht_gelesen:
        print("nicht gelesen: " + ", ".join(f"{n} ({neu[n]['fehler']})" for n in nicht_gelesen))

    if not alt:
        print(f"Erstlauf: {len(neu) - len(nicht_gelesen)} Melder-Stand(e) gespeichert, keine Meldung.")
    else:
        bewegungen = vergleichen(alt, neu)
        if bewegungen:
            print(f"{len(bewegungen)} Bewegung(en):")
            for z in bewegungen:
                print(f"  {z}")
        else:
            print("keine Bewegung seit dem letzten Lauf.")

    _stand_schreiben(neu)
    print(f"Laufzeit: {dauer:.1f}s")


# --- Selbsttest (rot vor gruen) ----------------------------------------------

def _selftest() -> None:
    # Gleiche Zahl -> keine Meldung.
    alt = {"gatestand": {"ok": True, "werte": {"x.belegt": 28}}}
    neu = {"gatestand": {"ok": True, "werte": {"x.belegt": 28}}}
    assert vergleichen(alt, neu) == []

    # Geaenderte Zahl -> Meldung mit alt, neu, Richtung (beide Richtungen).
    neu_hoch = {"gatestand": {"ok": True, "werte": {"x.belegt": 30}}}
    z = vergleichen(alt, neu_hoch)
    assert z == ["gatestand.x.belegt: 28 -> 30 (gestiegen um 2)"], z

    neu_runter = {"gatestand": {"ok": True, "werte": {"x.belegt": 26}}}
    z = vergleichen(alt, neu_runter)
    assert z == ["gatestand.x.belegt: 28 -> 26 (gefallen um 2)"], z

    # Erstlauf: kein gespeicherter Stand -> keine Meldung.
    assert vergleichen({}, neu_hoch) == []

    # Negativfall: ein Melder liefert Muell/stuerzt ab -> "nicht gelesen",
    # der Lauf bricht nicht ab und die anderen werden trotzdem gesammelt.
    def _ausfuehrer_mit_absturz(argv: list[str]) -> str:
        if "vier_nenner.py" in argv[0]:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=1)
        if "kennungskollision.py" in argv[0]:
            return "voellig unlesbarer Text ohne Zahl"
        return "REQUIREMENTS_X.md: 5/10 belegt, 1 ohne Gate-Lauf"

    e = sammeln(_ausfuehrer_mit_absturz)
    assert e["vier_nenner"]["ok"] is False
    assert e["kennungskollision"]["ok"] is False
    assert e["gatestand"]["ok"] is True
    assert e["gatestand"]["werte"] == {
        "REQUIREMENTS_X.belegt": 5, "REQUIREMENTS_X.gesamt": 10, "REQUIREMENTS_X.offen": 1,
    }

    # Parser-Proben gegen wirklich gesehene Ausgabeformen der Untermelder.
    assert _p_vektorstand(
        "Knoten: 5197 gesamt, 0 ohne Einbettung, 10 mit veralteter Pruefsumme, 14 beim Einbetten gekappt\n"
        "Lehren: 1113 gesamt, 0 ohne Einbettung, 9 mit veralteter Pruefsumme, 0 beim Einbetten gekappt"
    ) == {
        "knoten.gesamt": 5197, "knoten.fehlt": 0, "knoten.veraltet": 10, "knoten.gekappt": 14,
        "lehren.gesamt": 1113, "lehren.fehlt": 0, "lehren.veraltet": 9, "lehren.gekappt": 0,
    }
    assert _p_rasterblick("83 Ergebnisdatei(en) ohne Rastervermerk:\n  a.json\n") == {"ohne_vermerk": 83}
    assert _p_rasterblick("Rasterblick: alle Ergebnisdateien unter runs/ haben einen Vermerk.") == {"ohne_vermerk": 0}
    assert _p_kennungskollision("docs/: 0 Kennungskollision(en), 4 spaeteres Wiederaufgreifen (kein Befund)") == {
        "kollisionen": 0, "wiederaufgreifen": 4,
    }
    assert _p_vier_nenner("A: 192/387 ...\nB: 17/192 ...\nC: nicht gemessen (--ohne-c)") == {
        "a.trefer": 192, "a.nenner": 387, "b.trefer": 17, "b.nenner": 192,
    }
    assert _p_derivatfrische(
        "Bestand: 1535 Dateien · 6 Dokumente mit erklaertem Stand und Quellenlink\n"
        "Ueberholt (Stand aelter als 21 Tage): 0\n"
        "Befunde: 1 aelter als ihre Quelle\n"
    ) == {"dateien": 1535, "derivate": 6, "ueberholt": 0, "befunde": 1}

    print("selftest ok (12 Proben, Gegenprobe in beide Richtungen, Erstlauf, Negativfall)")


if __name__ == "__main__":
    main()
