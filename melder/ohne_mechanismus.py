#!/usr/bin/env python3
"""Welche Lehren wiederholen sich -- und haben trotzdem keinen Mechanismus?

ANLASS (Betreiberfrage 2026-08-20): *"wie machen wir nun mit brainlehr am
smartesten weiter?"* Die Antwort stand im Bestand, nicht im Nachdenken.

GEMESSEN am selben Tag:

  Lehren gesamt                                   1 135
  davon mit Mechanismus-Bezug in der Praevention    185   16,3 %
  Lehren mit 2 oder mehr Vorkommen                   97
  davon OHNE Mechanismus                             68

Das ist eine fertige, endliche und nach Dringlichkeit sortierte Arbeitsliste,
die das System UEBER SICH SELBST erzeugt: 68 Fehler, die nachweislich
wiederkehren, und gegen die nichts anschlaegt. Spitzenreiter am 2026-08-20:
`L-0e0ab6` mit eff Vorkommen.

WARUM DIE ZAHL DER VORKOMMEN DER RICHTIGE MASSSTAB IST und nicht die Schwere:
Eine Lehre mit einem Vorkommen kann ein Einzelfall sein. Eine mit fuenf ist
eine Fehlerklasse, und eine Fehlerklasse ohne Ausloeser wiederholt sich
weiter -- das ist an diesem Tag mehrfach belegt worden.

WAS ALS MECHANISMUS ZAEHLT: ein Melder, ein Test, ein Haken, ein Trigger, eine
Ratsche oder ein Lint, benannt in der Praevention oder der Beschreibung. Die
Erkennung ist bewusst grob -- sie soll eine Arbeitsliste erzeugen, kein Urteil
faellen. Ein Fehlalarm kostet einen Blick, eine uebersehene Wiederholung
kostet den naechsten Vorfall.

    python3 melder/ohne_mechanismus.py            # Arbeitsliste
    python3 melder/ohne_mechanismus.py --selftest
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

MECHANISMUS = re.compile(
    r"melder/|haken/|test_|tests/|waechter|wächter|trigger|pre-push|commit-msg"
    r"|ratsche|lint|selbsttest|hook",
    re.I)


def hat_mechanismus(lehre: dict) -> bool:
    text = (lehre.get("prevention") or "") + " " + (lehre.get("description") or "")
    return bool(MECHANISMUS.search(text))


def lade(db: Path | None = None) -> list[dict]:
    import ort
    pfad = db or Path(ort.DB)
    conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(z) for z in conn.execute(
            "SELECT id, description, prevention, severity, occurrences, type "
            "FROM lessons_learned")]
    finally:
        conn.close()


def arbeitsliste(lehren: list[dict], ab_vorkommen: int = 2) -> list[dict]:
    """Wiederholungstaeter ohne Mechanismus, die haeufigsten zuerst."""
    offen = [l for l in lehren
             if (l.get("occurrences") or 1) >= ab_vorkommen and not hat_mechanismus(l)]
    return sorted(offen, key=lambda l: -(l.get("occurrences") or 1))


def bericht(db: Path | None = None, ab_vorkommen: int = 2, zeige: int = 12) -> int:
    import rueckwirkung as r
    lehren = lade(db)
    mit = r.zaehle(lehren, hat_mechanismus, lambda l: l["id"], hoechstens_beispiele=0)
    print(mit.zeile("Lehren mit Mechanismus"))
    liste = arbeitsliste(lehren, ab_vorkommen)
    wiederholt = [l for l in lehren if (l.get("occurrences") or 1) >= ab_vorkommen]
    print(f"Lehren mit {ab_vorkommen}+ Vorkommen: {len(wiederholt)}, "
          f"davon ohne Mechanismus: {len(liste)}")
    print("\nArbeitsliste, haeufigste zuerst:")
    for l in liste[:zeige]:
        print(f"  {l.get('occurrences') or 1:2d}x [{l.get('severity','?'):6s}] "
              f"{l['id']}  {(l.get('description') or '')[:88]}")
    if len(liste) > zeige:
        print(f"  ... und {len(liste) - zeige} weitere")
    return 0


def _selftest() -> int:
    lehren = [
        {"id": "L-a", "occurrences": 5, "severity": "high",
         "description": "Fehler A", "prevention": "Kuenftig aufpassen."},
        {"id": "L-b", "occurrences": 3, "severity": "high",
         "description": "Fehler B", "prevention": "melder/xy.py faengt das jetzt."},
        {"id": "L-c", "occurrences": 1, "severity": "high",
         "description": "Einzelfall", "prevention": "Aufpassen."},
        {"id": "L-d", "occurrences": 2, "severity": "low",
         "description": "Fehler D", "prevention": "Ein test_ deckt es ab."},
        {"id": "L-e", "occurrences": 9, "severity": "medium",
         "description": "Fehler E", "prevention": "Sorgfalt."},
    ]
    liste = arbeitsliste(lehren)
    # a) Nur Wiederholungstaeter ohne Mechanismus, haeufigste zuerst.
    assert [l["id"] for l in liste] == ["L-e", "L-a"], [l["id"] for l in liste]
    # b) NEGATIVFALL: ein Einzelfall steht NICHT drin -- sonst waere die Liste
    #    so lang wie der Bestand und damit nutzlos.
    assert "L-c" not in [l["id"] for l in liste]
    # c) NEGATIVFALL: eine Lehre MIT Mechanismus steht nicht drin, egal wie oft.
    assert "L-b" not in [l["id"] for l in liste]
    assert "L-d" not in [l["id"] for l in liste]
    # d) Die Schwelle ist einstellbar und wirkt.
    assert len(arbeitsliste(lehren, ab_vorkommen=9)) == 1
    assert len(arbeitsliste(lehren, ab_vorkommen=99)) == 0
    # e) Erkennung: Praevention UND Beschreibung zaehlen.
    assert hat_mechanismus({"description": "haken/x.py fehlte", "prevention": ""})
    assert not hat_mechanismus({"description": "nichts", "prevention": "achtsam sein"})
    # UNVERDRAHTETE MELDER, zweite Haelfte derselben Frage. Der pre-push
    # zaehlt als Ausloeser -- ohne ihn meldete die Liste Waechter als tot,
    # die bei jedem Push laufen (25 statt 32 nach dieser Korrektur).
    liste = unverdrahtete_melder()
    namen = {n for n, _ in liste}
    assert "melder/ohne_mechanismus.py" in namen, "dieser Melder haengt selbst an nichts"
    assert "melder/rueckfrageschleife.py" not in namen, "verdrahtet ueber settings.json"
    assert "melder/ablaufpflicht.py" not in namen, "verdrahtet ueber pre-push"

    print("ohne_mechanismus: Selbsttest gruen (5 Faelle: Reihenfolge nach "
          "Vorkommen, Einzelfall raus, Mechanismus deckt, Schwelle wirkt, "
          "Erkennung liest beide Felder, unverdrahtete Melder samt pre-push)")
    return 0


def unverdrahtete_melder() -> list[tuple[str, str]]:
    """(Modul, Zweck) der Melder, die an KEINEM Ereignis haengen.

    Zweite Haelfte derselben Frage: Eine Lehre ohne Mechanismus und ein
    Mechanismus ohne Ausloeser sind derselbe Fehler in zwei Richtungen --
    einmal fehlt das Werkzeug, einmal der Anlass. Gemessen 2026-08-20 von
    tool/faehigkeitskarte.py: 32 von 48 Meldern haengen an nichts.

    Gelesen wird die ECHTE Einstellungsdatei, nicht eine Liste hier."""
    import json as _json
    einst = Path.home() / ".claude" / "settings.json"
    try:
        d = _json.loads(einst.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    verdrahtet = set()
    for gruppen in (d.get("hooks") or {}).values():
        for g in gruppen:
            for h in g.get("hooks", []):
                for teil in re.findall(r"([\w_]+)\.py", h.get("command", "")):
                    verdrahtet.add(teil)
    # Auch der pre-push zaehlt als Ausloeser -- er ist verdrahtet, nur nicht
    # in settings.json. Ohne diese Zeile meldete der Melder Waechter als tot,
    # die bei jedem Push laufen.
    try:
        push = (_w / "haken" / "git" / "pre-push").read_text(encoding="utf-8")
        verdrahtet |= set(re.findall(r"([\w_]+)\.py", push))
    except OSError:
        pass
    out = []
    for p in sorted((_w / "melder").glob("*.py")):
        if p.stem.startswith("_") or p.stem in verdrahtet:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        m = re.search(r'\"\"\"(.*?)(?:\n|\"\"\")', text, re.S)
        out.append((f"melder/{p.name}", (m.group(1).strip() if m else "")[:80]))
    return out


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--melder" in sys.argv:
        liste = unverdrahtete_melder()
        alle = len(list((_w / "melder").glob("*.py")))
        print(f"Melder ohne Ausloeser: {len(liste)} von {alle}")
        for name, zweck in liste:
            print(f"  {name:38s} {zweck}")
        sys.exit(0)
    sys.exit(bericht())
