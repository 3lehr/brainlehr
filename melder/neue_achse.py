#!/usr/bin/env python3
"""Kommt eine neue Achse dazu -- welche Spalten werden dadurch zweiseitig?

DER ANLASS ist eine Betreiberfrage vom 2026-08-20: "Und was ist wenn uns in
3 Monaten etwas aehnliches auffaellt?" -- gestellt, nachdem an EINEM Tag
viermal dieselbe Fehlerklasse aufgetreten war (L-6af5ac): eine ZWEISEITIGE
Groesse einer Seite zugeschrieben. Aufgriffsquote (Frage x Eintrag),
access_count (Leser x Eintrag), eine Ursachenaussage ohne ihren Zustand -- und
zuletzt die Geltung (Empfaenger x Regel). Alle vier hat der Betreiber
gefunden, nicht der Assistent.

DIE EINSICHT AUS DEM VIERTEN FALL, und sie ist der Grund fuer dieses Modul:
Eine Groesse kann HEUTE einseitig und MORGEN zweiseitig sein, ohne dass sich
an ihr etwas aendert -- es genuegt, dass eine zweite Achse hinzukommt.
`gilt_bis` ist als Spalte voellig richtig, solange alle Regeln fuer alle
gelten. Sobald es Personenkreise gibt, ist "gilt bis 31.12." unvollstaendig:
bis wann FUER WEN?

Damit ist der Fehler nicht vorhersehbar, wohl aber sein AUSLOESER. Eine neue
Achse ist am Bestand erkennbar: wenige unterschiedliche Werte ueber viele
Zeilen.

WAS DIESER MELDER TUT UND WAS NICHT: Er beantwortet die Frage nicht. Ob eine
Spalte fachlich zweiseitig wird, ist eine Aussage ueber Bedeutung -- die
trifft kein Zaehlwerk. Er STELLT sie, an dem einen Punkt, an dem sie sich
stellt, und ohne dass jemand daran denken muss.

melder/pruefer.py findet Spalten, die NICHTS unterscheiden. Dies ist die
Umkehrung: eine, die neuerdings etwas unterscheidet.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

# Beide Schwellen sind GERATEN. Eine Achse gruppiert -- sie hat mehr als einen
# Wert (sonst unterscheidet sie nichts, das meldet bereits pruefer.py) und
# deutlich weniger Werte als Zeilen (sonst ist sie eine Kennung).
MIN_WERTE = 2            # ungemessen
MAX_ANTEIL = 0.05        # ungemessen: hoechstens 5 % so viele Werte wie Zeilen

# Spalten, die eine AUSSAGE ueber den Eintrag tragen und deshalb zweiseitig
# werden koennen. Technische Felder (Kennung, Zeitstempel, Pruefsumme) koennen
# es nicht -- sie sagen nichts, worueber zwei Empfaenger verschiedener
# Meinung sein koennten.
AUSSAGEND = ("gilt_", "norm_", "freigabe", "rang", "access_count", "trust",
             "sensibel", "gattung", "geltung", "confidence", "severity")
TECHNISCH = ("id", "path", "_at", "checksum", "vector", "dim", "rowid",
             "created", "updated", "timestamp")


def neue_spalten(bekannt: dict, jetzt: dict) -> list:
    """Welche Spalten sind seit dem letzten Lauf dazugekommen?

    DER UMBAU nach dem ersten Lauf gegen den echten Bestand: Die statistische
    Erkennung unten meldete 21 Faelle, darunter quell_hash, session und
    zurueckgezogen_am -- keine davon eine Achse, es sind Eigenschaften. Der
    Unterschied zwischen ZUGEHOERIGKEIT (Mandant, Kreis, Projekt) und
    EIGENSCHAFT (Hash, Zeitstempel, Zaehler) ist semantisch, nicht
    statistisch; keine Zaehlung findet ihn. Und ein Melder mit 21 Zeilen wird
    ueberlesen -- dann ist er schlechter als keiner, weil er Sicherheit
    vortaeuscht.

    Eine NEUE SPALTE dagegen ist ein Ereignis: rauschfrei, ohne Heuristik,
    und die Frage stellt sich genau einmal. Weggefallene Spalten melden
    nichts -- sie nehmen hoechstens eine Achse zurueck."""
    raus = []
    for tabelle, spalten in jetzt.items():
        for s in spalten:
            if s not in bekannt.get(tabelle, []):
                raus.append((tabelle, s))
    return raus


def ist_achse(verschiedene: int, zeilen: int) -> bool:
    """Gruppiert diese Spalte -- oder ist sie eine Kennung?"""
    if zeilen <= 0 or verschiedene < MIN_WERTE:
        return False
    return verschiedene <= max(MIN_WERTE, zeilen * MAX_ANTEIL)


def moeglich_zweiseitig(spalten: list) -> list:
    """Welche Spalten koennten durch eine neue Achse zweiseitig werden?

    Eine Kennung oder ein Zeitstempel kann es nicht: Zwei Empfaenger koennen
    nicht verschiedener Meinung darueber sein, wann ein Eintrag entstand. Ueber
    seine GELTUNG oder seinen RANG sehr wohl."""
    raus = []
    for s in spalten:
        k = s.lower()
        if any(t in k for t in TECHNISCH):
            continue
        if any(a in k for a in AUSSAGEND):
            raus.append(s)
    return raus


def pruefe(db: Path, tabellen=("knowledge_nodes", "lessons_learned")) -> list:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    funde = []
    try:
        for t in tabellen:
            spalten = [r[1] for r in c.execute(f"pragma table_info({t})")]
            if not spalten:
                continue
            zeilen = c.execute(f"select count(*) from {t}").fetchone()[0]
            for s in spalten:
                try:
                    v = c.execute(
                        f"select count(distinct {s}) from {t} "
                        f"where {s} is not null and trim(cast({s} as text)) <> ''"
                    ).fetchone()[0]
                except sqlite3.Error:
                    continue
                if ist_achse(v, zeilen):
                    kand = [x for x in moeglich_zweiseitig(spalten) if x != s]
                    if kand:
                        funde.append({"tabelle": t, "spalte": s, "verschiedene": v,
                                      "zeilen": zeilen, "kandidaten": kand})
    finally:
        c.close()
    return funde


def als_text(funde: list, bekannt: set | None = None) -> str:
    """Nur NEUE Achsen melden -- die bekannten sind entschieden."""
    bekannt = bekannt or set()
    neu = [f for f in funde if f["spalte"] not in bekannt]
    if not neu:
        return ""
    z = ["Achsen im Bestand -- fuer jede die Frage aus L-6af5ac:"]
    for f in neu:
        z.append(f"  {f['tabelle']}.{f['spalte']}  "
                 f"({f['verschiedene']} Werte ueber {f['zeilen']} Zeilen)")
        z.append(f"     Werden diese Spalten dadurch ZWEISEITIG? "
                 f"{', '.join(f['kandidaten'][:6])}")
        z.append(f"     Pruefsatz: \"<Spalte> ist <Wert>\" -- vollstaendig, "
                 f"oder fehlt ein \"fuer wen\"?")
    return "\n".join(z)


ZUSTAND = Path.home() / ".brainlehr-spalten.json"


def _jetzt(db: Path, tabellen) -> dict:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        return {t: [r[1] for r in c.execute(f"pragma table_info({t})")] for t in tabellen}
    finally:
        c.close()


def main() -> int:
    import json
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--statistisch", action="store_true",
                   help="die verworfene Heuristik trotzdem fahren (21 Treffer, "
                        "davon keiner eine echte Achse -- siehe Modulkopf)")
    p.add_argument("--bekannt", nargs="*", default=[
        # Achsen, die bereits entschieden sind -- ihre Zweiseitigkeit ist
        # geprueft oder bewusst in Kauf genommen.
        "project_id", "freigabe", "norm_rang", "gattung", "anlass", "level",
        "type", "severity", "status", "norm_entscheidung", "gedaechtnisart",
        "norm_art", "kind", "sensibel", "bezug", "norm_entschieden_von"])
    args = p.parse_args()
    import ort
    tabellen = ("knowledge_nodes", "lessons_learned")

    if args.statistisch:
        text = als_text(pruefe(Path(ort.DB)), set(args.bekannt))
        if text:
            print(text)
        return 0

    # Der wirksame Weg: eine NEUE Spalte ist ein Ereignis.
    jetzt = _jetzt(Path(ort.DB), tabellen)
    try:
        bekannt = json.loads(ZUSTAND.read_text())
    except (OSError, ValueError):
        # Erster Lauf: den Stand aufnehmen, ohne zu melden. Sonst waeren alle
        # 40 Spalten "neu" -- und das ist genau das Rauschen, das dieser Umbau
        # beseitigt hat.
        ZUSTAND.write_text(json.dumps(jetzt, indent=1))
        return 0
    funde = neue_spalten(bekannt, jetzt)
    if funde:
        print("Neue Spalte(n) im Bestand -- fuer jede die Frage aus L-6af5ac:")
        for t, sp in funde:
            kand = [x for x in moeglich_zweiseitig(jetzt[t]) if x != sp]
            print(f"  {t}.{sp}")
            if kand:
                print(f"     Ist das eine ACHSE (Zugehoerigkeit) oder eine "
                      f"Eigenschaft?")
                print(f"     Falls Achse: werden diese Spalten dadurch "
                      f"zweiseitig? {', '.join(kand[:6])}")
                print(f"     Pruefsatz: \"<Spalte> ist <Wert>\" -- vollstaendig, "
                      f"oder fehlt ein \"fuer wen\"?")
    ZUSTAND.write_text(json.dumps(jetzt, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
