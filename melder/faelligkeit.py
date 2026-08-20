#!/usr/bin/env python3
"""Was raus muss, unabhaengig davon, was gefragt wurde.

ANLASS, Betreiber 2026-08-20, woertlich: "wenn die frist abgelaufen ist und
vom chat/user noch nie abgefragt wurde sollte sie mit prio zum pruefen
eingespielt werden? und hier koennte es ein ranking geben, wichtige dinge und
oder dinge welche direkte auswirkungen haben nichtbeachten teurer wird
sollten schon frueher eingespielt werden?"

Er trifft damit dieselbe Stelle wie die Alarmmedizin im Konsil desselben
Tages (IEC 60601-1-8): Die Prioritaet eines Alarms kommt aus der
SCHADENSFOLGE, nie aus der Messsicherheit. Ein Monitor piepst nicht lauter,
weil der Sensor sicherer ist.

WARUM ES DIESEN KANAL BRAUCHT, und das ist an diesem Tag gemessen worden:
Der bestehende Abruf waehlt ueber AEHNLICHKEIT zur Frage. Drei Verfahren
wurden geprueft, ob sich daraus ablesen laesst, ob ein Treffer auch RICHTIG
ist -- roher Kosinuswert, MAD-Sweep ueber den ganzen zulaessigen Bereich,
robuste Hintergrundnormierung ueber alle 5217 Knoten. Drei Nullbefunde. Von
allen an diesem Tag geprueften Groessen trennten genau ZWEI aufgegriffene
von nie aufgegriffenen Eintraegen, und beide sind Schadensmasse:

    severity      critical 42,4 % > high 37,5 % > medium 22,8 % > low 12,0 %
    occurrences   1x 26,2 %  <  2-3x 59,4 %  <  4x+ 100 % (n=10, zu klein)

(runs/aufgriff_je_merkmal_2026-08-20.json)

Ein Eintrag kommt hier also NICHT herein, weil er zur Frage passt, sondern
weil er faellig ist. Genau deshalb ist der Aufgriff auch kein Rangfaktor: er
ist eine Eigenschaft des PAARES aus Frage und Eintrag und haengt an Zeitraum
und Fragendem -- der Betreiber am selben Tag: "koennte aber beim 21. Mal
nuetzlich sein wenn die fragestellung anderst ist ... oder von jemand anderen
gefragt wuerde, oder zu einem anderen zeitpunkt".

DIE VIER KLASSEN, mit ihren Bestandszahlen vom 2026-08-20:

    norm_nie_gelesen    100   Norm im Bestand, access_count = 0
    lehre_wiederholt     68   severity high/critical UND occurrences >= 2
    lehre_regelrang      30   status = 'escalated_to_rule'
    geltung_abgelaufen    2   gilt_bis liegt in der Vergangenheit

Rund 200 von 5225 Knoten und 1154 Lehren. Klein genug, dass der Kanal nicht
laermt -- und jede Klasse traegt ein Merkmal, das mit der gestellten Frage
nichts zu tun hat.

ALARMMUEDIGKEIT IST DIE HAUPTGEFAHR, nicht die Auswahl. Ein Kanal, der
taeglich dieselben sechs Eintraege zeigt, wird in einer Woche ueberlesen, und
dann wirkt auch der wichtige nicht mehr. Zwei Vorkehrungen:

  1. SEHR KLEINER DECKEL. Dieser Melder kommt zu vierzehn anderen
     Startmeldern hinzu; drei Zeilen sind die Obergrenze.
  2. ROTATION OHNE ZUSTAND. Der Versatz kommt aus der Tagesnummer, nicht aus
     einer Zustandsdatei. Damit ist der Melder wiederholbar (zweimal am
     selben Tag gefragt -> dieselbe Auswahl) und deckt ueber die Tage den
     ganzen Bestand ab. Eine Zustandsdatei waere eine weitere Stelle, die
     verlorengehen kann.

SELBSTLOESEND, und das ist die eleganteste Eigenschaft: Die groesste Klasse
(`norm_nie_gelesen`) verschwindet durch Benutzung. Wer die Norm liest, hebt
ihren access_count und entfernt sie aus der Liste. Es braucht keine
Quittierung, kein Abhaken, keinen zweiten Mechanismus.

WAS DIESER MELDER NICHT TUT: Er aendert die Rangfolge des Abrufs nicht und
filtert nichts weg. Er ist ein ZWEITER Kanal neben der Aehnlichkeit, kein
Ersatz. Und er urteilt nicht darueber, ob ein Eintrag stimmt -- er sagt nur,
dass ihn noch niemand angesehen hat, obwohl er zaehlt.

Aufruf:
    python3 melder/faelligkeit.py              # Zahlen + Auswahl des Tages
    python3 melder/faelligkeit.py --alle       # alle Kandidaten, ohne Deckel
    python3 melder/faelligkeit.py --selftest
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern")]

import speicher  # noqa: E402

MAX_ZEILEN = 3

# Reihenfolge nach SCHADENSFOLGE, nicht nach Bestandsgroesse. Eine Regel, die
# schon zweimal gebrochen wurde, wiegt schwerer als eine ungelesene Norm --
# der Schaden ist bereits zweimal eingetreten.
KLASSEN = {
    "lehre_regelrang":    (0, "auf Regelrang eskaliert, gilt also ohnehin"),
    "lehre_wiederholt":   (1, "derselbe Fehler ist wiederholt passiert"),
    "geltung_abgelaufen": (2, "Geltung abgelaufen, steht noch im Bestand"),
    "norm_nie_gelesen":   (3, "Norm im Bestand, nie gelesen"),
}
SCHWERE_RANG = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _aus() -> bool:
    return os.environ.get("BRAINLEHR_FAELLIGKEIT", "").strip().lower() == "aus"


def tagesnummer(heute: date | None = None) -> int:
    """Tage seit dem Epochenbeginn -- der Rotationsversatz.

    Als Parameter hereingereicht, nie im Rumpf gelesen: ein Melder, der die
    Uhr selbst liest, ist nicht pruefbar, und ein Test mit festem Datum
    altert weg (L-cdce13, am selben Tag an einer anderen Datei passiert)."""
    return (heute or datetime.now(timezone.utc).date()).toordinal()


def kandidaten(db: Path | None = None, stichtag: str | None = None) -> list[dict]:
    """Die vier Klassen aus dem Bestand. Nur lesend."""
    stichtag = stichtag or datetime.now(timezone.utc).date().isoformat()
    raus: list[dict] = []
    try:
        with speicher.lesen(db) as con:
            for r in con.execute(
                    "SELECT id, path, title FROM knowledge_nodes "
                    "WHERE norm_rang IS NOT NULL AND access_count = 0 "
                    "AND zurueckgezogen = 0"):
                raus.append({"kennung": r["path"], "art": "norm_nie_gelesen",
                             "titel": r["title"], "schwere": "medium"})
            for r in con.execute(
                    "SELECT path, title, gilt_bis FROM knowledge_nodes "
                    "WHERE gilt_bis IS NOT NULL AND gilt_bis < ? "
                    "AND zurueckgezogen = 0", (stichtag,)):
                raus.append({"kennung": r["path"], "art": "geltung_abgelaufen",
                             "titel": r["title"], "schwere": "high"})
            for r in con.execute(
                    "SELECT id, description, severity, occurrences, status "
                    "FROM lessons_learned "
                    "WHERE status = 'escalated_to_rule' "
                    "   OR (severity IN ('high','critical') AND occurrences >= 2)"):
                art = ("lehre_regelrang" if r["status"] == "escalated_to_rule"
                       else "lehre_wiederholt")
                raus.append({"kennung": r["id"], "art": art,
                             "titel": (r["description"] or "")[:90],
                             "schwere": r["severity"] or "medium"})
    except sqlite3.OperationalError:
        return []
    return raus


def auswahl(alle: list[dict], tagesnummer: int) -> list[dict]:
    """Hoechstens MAX_ZEILEN, nach Schadensfolge geordnet, JE KLASSE rotierend.

    DIE ROTATION LAEUFT JE KLASSE, nicht ueber die Gesamtliste -- das ist der
    Unterschied zwischen einer Ordnung, die wirkt, und einer, die nur
    dasteht. Die erste Fassung schob EIN Fenster ueber die sortierte
    Gesamtliste; bei 179 Kandidaten mit 30 auf Regelrang landete es an rund
    83 Prozent der Tage ausserhalb der schweren Klassen. Gemessen am
    2026-08-20 zeigten Tag und Folgetag ausschliesslich `norm_nie_gelesen`,
    die SCHWAECHSTE Klasse -- das genaue Gegenteil dessen, was der Kanal
    leisten soll.

    Jede nichtleere Klasse bekommt der Reihe nach einen Platz, die schwerste
    zuerst; bleiben Plaetze uebrig, wird in derselben Reihenfolge ein zweites
    Mal vergeben. Innerhalb einer Klasse rotiert der Tagesversatz, damit ueber
    die Tage jeder Eintrag drankommt.

    Die Gegenrichtung ist ebenso geprueft: Die schwerste Klasse darf die
    anderen nicht dauerhaft verdraengen, sonst waeren die 100 ungelesenen
    Normen unerreichbar und der Kanal haette sein Problem nur getauscht."""
    if not alle:
        return []
    nach_klasse: dict[str, list] = {}
    for k in alle:
        nach_klasse.setdefault(k["art"], []).append(k)
    for art in nach_klasse:
        nach_klasse[art].sort(key=lambda k: (
            SCHWERE_RANG.get(k.get("schwere", "medium"), 9), k["kennung"]))

    reihenfolge = sorted(nach_klasse, key=lambda a: KLASSEN.get(a, (9, ""))[0])
    # Mehr Klassen als Plaetze: Die SCHWERSTE behaelt Platz eins, die
    # uebrigen rotieren um die restlichen Plaetze. Ohne diesen Griff bekommt
    # die schwaechste Klasse NIE einen Platz -- im Bestand vom 2026-08-20
    # waeren das 100 von 179 Kandidaten, also die Mehrheit, dauerhaft
    # unerreichbar. Die Gegenrichtung bleibt gewahrt: Platz eins gehoert
    # immer der schwersten Klasse, es faellt nicht reihum jede einmal weg.
    if len(reihenfolge) > MAX_ZEILEN:
        kopf, rest = reihenfolge[:1], reihenfolge[1:]
        versatz = tagesnummer % len(rest)
        reihenfolge = kopf + rest[versatz:] + rest[:versatz]
    gewaehlt: list[dict] = []
    runde = 0
    while len(gewaehlt) < MAX_ZEILEN and runde < MAX_ZEILEN:
        for art in reihenfolge:
            if len(gewaehlt) >= MAX_ZEILEN:
                break
            eintraege = nach_klasse[art]
            i = (tagesnummer * MAX_ZEILEN + runde) % len(eintraege)
            kandidat = eintraege[i]
            if kandidat not in gewaehlt:
                gewaehlt.append(kandidat)
        runde += 1
    return gewaehlt


def melde(alle: list[dict], tagesnummer: int) -> str:
    zeig = auswahl(alle, tagesnummer)
    if not zeig:
        return ""
    kopf = (f"Faellig, unabhaengig von der Frage: {len(alle)} Eintraege warten, "
            f"{len(zeig)} davon heute:")
    zeilen = [kopf]
    for k in zeig:
        grund = KLASSEN.get(k["art"], (9, k["art"]))[1]
        zeilen.append(f"  [{k['kennung']}] {k['titel']}")
        zeilen.append(f"      {grund}")
    zeilen.append("  (Rotation: morgen sind andere dran. Wer eine Norm liest, "
                  "nimmt sie aus der Liste.)")
    return "\n".join(zeilen)


def _selftest() -> int:
    k = [{"kennung": f"L-{i:06d}", "art": "norm_nie_gelesen",
          "titel": "T", "schwere": "high"} for i in range(200)]
    assert len(auswahl(k, 0)) == MAX_ZEILEN
    assert {z["kennung"] for z in auswahl(k, 0)} != {z["kennung"] for z in auswahl(k, 1)}
    assert auswahl(k, 7) == auswahl(k, 7), "nicht wiederholbar"
    assert auswahl([], 0) == [] and melde([], 0) == ""

    klein = [{"kennung": f"L-{i}", "art": "norm_nie_gelesen", "titel": "T",
              "schwere": "high"} for i in range(9)]
    gesehen = set()
    for tag in range(9):
        gesehen |= {z["kennung"] for z in auswahl(klein, tag)}
    assert gesehen == {x["kennung"] for x in klein}, "Rotation deckt nicht alles ab"

    gemischt = [{"kennung": "leicht", "art": "norm_nie_gelesen", "titel": "T", "schwere": "medium"},
                {"kennung": "schwer", "art": "lehre_regelrang", "titel": "T", "schwere": "critical"}]
    assert auswahl(gemischt, 0)[0]["kennung"] == "schwer", "Schadensfolge ignoriert"

    text = melde([{"kennung": f"L-{i}", "art": "lehre_wiederholt", "titel": "T",
                   "schwere": "high"} for i in range(40)], 0)
    assert "40" in text and "wiederholt passiert" in text, text

    # Abschaltung wirkt.
    os.environ["BRAINLEHR_FAELLIGKEIT"] = "aus"
    try:
        assert _aus() is True
    finally:
        del os.environ["BRAINLEHR_FAELLIGKEIT"]
    assert _aus() is False

    print("faelligkeit: Selbsttest gruen (8 Faelle: Deckel, Rotation ueber "
          "Tage, vollstaendige Abdeckung, Wiederholbarkeit, Schadensfolge vor "
          "Alphabet, Stille ohne Kandidaten, Grund und Gesamtzahl in der "
          "Meldung, Abschaltung)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--alle", action="store_true", help="alle Kandidaten, ohne Deckel")
    args = p.parse_args()
    if args.selftest:
        return _selftest()
    if _aus():
        return 0
    alle = kandidaten()
    if args.alle:
        from collections import Counter
        z = Counter(k["art"] for k in alle)
        for art, (_, grund) in sorted(KLASSEN.items(), key=lambda x: x[1][0]):
            print(f"{z.get(art, 0):>5}  {art:<20} {grund}")
        print(f"{len(alle):>5}  gesamt")
        return 0
    text = melde(alle, tagesnummer())
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
