#!/usr/bin/env python3
"""Beinahefehler auszaehlen -- welche Fehlerklasse, wie oft, und WAS hat sie gefangen.

Die Frage aus docs/PLAN_BEINAHEFEHLER_2026-08-16.md §6 ist nicht "wie viele",
sondern: **welche Schutzform faengt die meisten?** Ist die haeufigste Antwort
'zufall', ist das der wertvollste Befund -- dann fehlt an dieser Stelle ein
Mechanismus, und die naechste Wiederholung faellt niemandem auf.

Die Zahl ist eine UNTERGRENZE und wird als solche ausgewiesen (Plan §5): ein
Teil der Beinahefehler wird nie gemeldet, weil er nicht einmal bemerkt wird.
Sie ist auch keine Aussage ueber Personen -- gezaehlt wird die Fehlerklasse
und was sie gefangen hat, nie wer sie gemacht hat.

Aufruf:
    python3 berichte/beinahefehler.py
    python3 berichte/beinahefehler.py --selftest
"""
# ausloeser: auf-abruf -- Lesebericht fuer die Frage aus Plan §6 ("welche
# Schutzform faengt die meisten"); ein Mensch ruft ihn, wenn er die Zahl
# braucht, kein Wert im Dauerlauf ohne Leser.
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL), str(WURZEL / "kern"), str(WURZEL / "haken")]

import speicher  # noqa: E402

# Was die Angabe fuer die Frage nach dem Mechanismus bedeutet. Nicht kosmetisch:
# 'zufall' und 'zahl' sind die beiden Faelle OHNE Vorrichtung -- sie beantworten
# §6 direkt, waehrend die uebrigen fuenf belegen, dass eine gebaute Schutzform
# getragen hat.
OHNE_MECHANISMUS = {"zufall", "zahl"}
ERLAEUTERUNG = {
    "zahl": "eine Zahl/Ausgabe passte nicht -- kein Mechanismus beteiligt",
    "zufall": "beim Lesen von etwas anderem aufgefallen -- kein Mechanismus",
    "test": "ein Test oder Selbsttest schlug an",
    "waechter": "Hook, Trigger, Lint, Guard",
    "gegenprobe": "bewusste Gegenprobe / Rot-Probe",
    "wissen": "eingespielte Lehre oder Knoten",
    "betreiber": "ein Mensch hat es gesagt",
}


def erhebung(conn) -> dict:
    zeilen = conn.execute(
        "SELECT type, bemerkt_woran, id, first_seen FROM lessons_learned "
        "WHERE beinahefehler = 1"
    ).fetchall()
    gesamt = conn.execute("SELECT count(*) FROM lessons_learned").fetchone()[0]
    return {
        "gesamt": gesamt,
        "beinahefehler": len(zeilen),
        "je_woran": Counter(z[1] for z in zeilen),
        "je_klasse": Counter(z[0] for z in zeilen),
        "kreuz": Counter((z[0], z[1]) for z in zeilen),
        "zeilen": sorted(zeilen, key=lambda z: z[3] or ""),
    }


def _balken(anteil: float, breite: int = 24) -> str:
    return "#" * round(anteil * breite)


def bericht(daten: dict) -> str:
    n = daten["beinahefehler"]
    aus = ["BEINAHEFEHLER -- bemerkt und behoben, bevor Schaden entstand",
           "=" * 72,
           f"{n} gekennzeichnet von {daten['gesamt']} Lehren "
           f"({n / daten['gesamt'] * 100:.1f} %). UNTERGRENZE: was nicht bemerkt "
           "wurde, ist nicht gezaehlt."]
    if not n:
        aus.append("")
        aus.append("Noch keine Kennzeichnung. Der Erfassungsweg steht "
                   "(lesson_record beinahefehler=true, bemerkt_woran=...);")
        aus.append("solange niemand meldet, sagt dieser Bericht nichts ueber die "
                   "Wirklichkeit, nur ueber die Meldung.")
        return "\n".join(aus)

    aus += ["", "VORBEHALT zur Nulllinie: Eintraege bis 2026-08-16 stammen aus einer "
                "rueckwirkenden Sichtung.",
            "Sie verlangte, dass der Text SELBST sagt, woran es bemerkt wurde -- wer "
            "es nicht aufschrieb,",
            "faellt heraus. Das trifft 'zufall' am haertesten (unbenannt, weil "
            "unspektakulaer) und hebt",
            "'gegenprobe' an. Belastbar wird die Verteilung erst mit Meldungen, die "
            "im Fluss entstehen.",
            "", "WAS HAT SIE GEFANGEN (die Frage aus Plan §6)", "-" * 72]
    for woran, anzahl in daten["je_woran"].most_common():
        aus.append(f"  {woran:<11} {anzahl:>4}  {_balken(anzahl / n):<24} "
                   f"{ERLAEUTERUNG.get(woran, '')}")
    ohne = sum(a for w, a in daten["je_woran"].items() if w in OHNE_MECHANISMUS)
    aus += ["", f"  ohne Mechanismus (zahl/zufall): {ohne} von {n} "
                f"({ohne / n * 100:.0f} %)"]
    if ohne * 2 > n:
        aus.append("  BEFUND: Die Mehrheit haengt an Aufmerksamkeit, nicht an einer "
                   "Vorrichtung.")
        aus.append("          Genau dort fehlt ein Mechanismus -- Plan §6.")

    aus += ["", "WELCHE FEHLERKLASSE", "-" * 72]
    for klasse, anzahl in daten["je_klasse"].most_common():
        woran = ", ".join(f"{w}:{a}" for (k, w), a in
                          sorted(daten["kreuz"].items(), key=lambda p: -p[1]) if k == klasse)
        aus.append(f"  {klasse:<12} {anzahl:>4}   {woran}")

    aus += ["", "EINZELN (aelteste zuerst)", "-" * 72]
    for typ, woran, lid, first in daten["zeilen"]:
        aus.append(f"  {(first or '')[:10]}  {lid:<10} {typ:<12} {woran}")
    return "\n".join(aus)


def _selftest() -> None:
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE lessons_learned (id TEXT, type TEXT, "
                 "beinahefehler INTEGER DEFAULT 0, bemerkt_woran TEXT, first_seen TEXT)")
    conn.executemany("INSERT INTO lessons_learned VALUES (?,?,?,?,?)", [
        ("L-1", "error", 1, "zufall", "2026-08-01"),
        ("L-2", "error", 1, "zufall", "2026-08-02"),
        ("L-3", "antipattern", 1, "waechter", "2026-08-03"),
        ("L-4", "insight", 0, None, "2026-08-04"),
    ])
    d = erhebung(conn)
    assert d["beinahefehler"] == 3, d
    assert d["gesamt"] == 4, d
    assert d["je_woran"]["zufall"] == 2, d
    assert d["je_klasse"]["error"] == 2, d
    text = bericht(d)
    # Die Warnung ist der eigentliche Zweck des Berichts: 2 von 3 ohne
    # Mechanismus muss sie ausloesen.
    assert "fehlt ein Mechanismus" in text, text
    conn.execute("UPDATE lessons_learned SET beinahefehler = 0")
    assert "Noch keine Kennzeichnung" in bericht(erhebung(conn))
    print("selftest ok: 4 Zeilen, 3 Kennzeichnungen, Warnung ausgeloest, Leerfall sauber")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        with speicher.lesen() as conn:
            print(bericht(erhebung(conn)))
