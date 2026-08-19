#!/usr/bin/env python3
"""Meldet abgeleitete Dokumente, die AELTER sind als ihre Quelle.

ANLASS: Eilmeldung 2dd8a01d vom 2026-08-19 aus buckeberg. Dort wurden zwei
Antworten an den Betreiber auf ein Handout gestuetzt statt auf den Vertrag.
Die Gegenprobe ergab nicht das Erwartete -- das Zitat STIMMTE. Irrefuehrend
war es trotzdem: das Handout war 26 Tage alt und zeigte das nirgends, es
trug eine seit drei Tagen bestrittene Zeile ohne Vermerk, und es verschwieg
die wichtigere Klausel.

DIE FEHLKLASSE, und sie ist die gefaehrlichere Sorte: Ein Stellvertreter,
der die Stichprobe BESTEHT, wirkt danach geprueft. Die Gegenprobe bestaetigt
ihn, und der Leser schliesst daraus, das ganze Dokument sei belastbar.

WAS DIESE WACHE FAENGT, und in welcher Reihenfolge sie es gelernt hat:

  (1) ALTER. Das Derivat erklaert einen Stand, der laenger als eine Frist
      zurueckliegt. Klingt stumpf und ist der Griff, der den Anlassfall
      GEFANGEN haette -- siehe (2), warum der naheliegendere es nicht tut.

  (2) FRISCHE. Das Derivat ist aelter als eine Datei, auf die es sich
      beruft. Das war die vorgeschlagene Bauform (a) der Eilmeldung, und
      GEMESSEN faengt sie den Anlassfall NICHT: `swb.pdf` wurde zuletzt am
      2026-07-23 geaendert, das Handout trug Stand 2026-07-24 -- das Derivat
      war JUENGER als seine Quelle und trotdem 26 Tage ueberholt. Ein
      Vertragstext aendert sich eben nicht; was altert, ist das Verstaendnis
      davon. Die Frischeprobe bleibt trotzdem drin, weil sie den anderen
      Fall faengt (Quelle wurde nachgeliefert oder korrigiert) -- aber sie
      ist nicht die Antwort auf die Eilmeldung.

WAS SIE AUSDRUECKLICH NICHT FAENGT, damit niemand sie fuer mehr haelt:
  * UNVOLLSTAENDIGKEIT. Dass ein Derivat den entscheidenden Absatz
    weglaesst, ist von aussen nicht sichtbar -- die Datei ist frisch, das
    Zitat stimmt, es fehlt nur etwas. Das ist keine Bequemlichkeit dieser
    Umsetzung, sondern eine Grenze: ohne den Quelltext zu LESEN gibt es kein
    Merkmal, an dem sich ein fehlender Absatz zeigt.
  * WIDERSPRUCH. Dass eine Aussage im Derivat inzwischen bestritten ist,
    setzt voraus, dass der widersprechende Wissensknoten die betroffene
    Datei MASCHINENLESBAR nennt. Gemessen am 2026-08-19: 13 Knoten tragen
    einen Widerspruchsvermerk, 5 davon (38 %) nennen eine Datei so, dass ein
    Programm sie findet. Die Obergrenze dieser Pruefung liegt damit heute
    bei 38 % -- und das ist eine BEHEBBARE Grenze, anders als die
    Unvollstaendigkeit: wer beim Bestreiten die betroffene Datei nennt, hebt
    sie. Nachzumessen mit --widerspruchslage, nicht zu glauben.

Beide Grenzen gehoeren gemeldet statt ueberspielt: eine Wache, die drei
Dinge verspricht und eines kann, ist schlimmer als eine, die eines
verspricht -- weil der Leser die anderen zwei fuer erledigt haelt.

WIE DIE QUELLEN GEFUNDEN WERDEN. Nicht ueber ein neues Kopffeld, das erst
in alle Derivate eingetragen werden muesste (dann faengt die Wache genau die
alten Dokumente nicht, um die es geht), sondern ueber das, was schon
dasteht: Dateinamen in Links und im Text. Die Handouts verlinken ihre PDFs
als URL mit `file=%2Fquellen%2Fswb.pdf`; ein Pfadvergleich scheitert daran,
ein Vergleich ueber den DATEINAMEN nicht. Mehrdeutige Namen werden gemeldet
statt geraten.

Aufruf:
    python3 derivatfrische.py [--wurzel PFAD]      Zahlen + Befunde
    python3 derivatfrische.py --melder             nur sprechen, wenn etwas anschlaegt
    python3 derivatfrische.py --widerspruchslage   misst Grenze 2 statt sie zu behaupten
    python3 derivatfrische.py --selftest
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path

# Ein Derivat erklaert seinen Stand -- in genau der Form, die die Hausregel
# fuer Fliesstext vorschreibt (ISO 8601 mit Uhrzeit und Zone).
_STAND = re.compile(r"\*{0,2}Stand:?\*{0,2}\s*:?\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})")

# Dateinamen mit Endung, wie sie in Links, Klammern und Fliesstext stehen.
# Bewusst ohne Pfad: Derivate verlinken ihre Quellen als URL, teils
# prozentkodiert -- der Name ueberlebt beides, der Pfad nicht.
_DATEINAME = re.compile(r"[\w./-]+\.(?:pdf|md|json|csv|xlsx|docx|jsonl|yaml|yml|sql|py)")

# Endungen, die als QUELLE eines Derivats in Frage kommen. Ein Derivat, das
# ein Skript erwaehnt, wird dadurch nicht zu dessen Ableitung.
_QUELLENDUNGEN = {".pdf", ".md", ".json", ".csv", ".xlsx", ".docx", ".jsonl"}


def _lauf(args: list[str], wurzel: Path) -> str:
    return subprocess.run(args, cwd=wurzel, capture_output=True, text=True).stdout


def letzte_aenderung(wurzel: Path) -> dict[str, str]:
    """Datei -> Zeitpunkt des letzten Commits, in EINEM git-Aufruf.

    Je Datei `git log -1` aufzurufen waere bei tausend Dateien tausend
    Prozesse; ein einziger Durchlauf mit --name-only liefert dasselbe.
    Die Historie kommt neu-zuerst, der ERSTE Treffer je Datei gewinnt.
    """
    roh = _lauf(["git", "log", "--format=%x00%cI", "--name-only", "--no-renames"], wurzel)
    stand: dict[str, str] = {}
    zeit = ""
    for zeile in roh.splitlines():
        if zeile.startswith("\x00"):
            zeit = zeile[1:]
        elif zeile.strip() and zeit:
            stand.setdefault(zeile.strip(), zeit)
    return stand


def _namensindex(dateien: list[str]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for pfad in dateien:
        index[Path(pfad).name].append(pfad)
    return index


# Nur das ZIEL eines Links zaehlt, nicht jede Erwaehnung im Fliesstext.
#
# Der erste Anlauf nahm jeden Dateinamen im Text -- Ergebnis auf dem echten
# Bestand: 635 Befunde in buckeberg, fast alle unsinnig. Ein Uebergabetext,
# der STAND.md ERWAEHNT, ist deswegen keine Ableitung davon. Und ein Plan
# vom 22. Juli SOLL aelter sein als das, was danach kam -- eine Momentaufnahme
# altert nicht, sie ist datiert.
#
# Eine Wache mit dieser Fehlalarmquote wird binnen einer Woche ignoriert
# (an zwei anderen Werkzeugen dieses Hauses mit 73 % und 54 % gemessen).
# Der Unterschied zwischen Erwaehnung und BERUFUNG ist der Link: Wer sich
# auf eine Quelle beruft, verlinkt sie -- genau das tun die Handouts mit
# ihren Tiefenlinks (PDF + Seite + Suchbegriff).
_LINKZIEL = re.compile(r"\]\(([^)\s]+)")


def _genannte_dateien(text: str) -> set[str]:
    """Dateinamen, auf die sich das Dokument BERUFT -- Linkziele, nicht
    Erwaehnungen. Prozentkodierte URLs werden mitgelesen, weil die Handouts
    ihre Quellen als `?file=%2Fquellen%2Fswb.pdf` verlinken."""
    namen = set()
    for ziel in _LINKZIEL.findall(text):
        try:
            ziel = urllib.parse.unquote(ziel)
        except Exception:
            pass
        for treffer in _DATEINAME.findall(ziel):
            name = Path(treffer).name
            if Path(name).suffix.lower() in _QUELLENDUNGEN:
                namen.add(name)
    return namen


# Frist, ab der ein erklaerter Stand als ueberholt gilt. 21 Tage, nicht 30:
# der Anlassfall war 26 Tage alt und hat geschadet, 30 haette ihn erst nach
# dem Schaden gemeldet. Kein gemessener Wert -- eine Setzung, und als solche
# benannt statt als Erkenntnis ausgegeben.
_FRIST_TAGE = 21


def pruefe(wurzel: Path, frist_tage: int = _FRIST_TAGE, jetzt: str | None = None) -> dict:
    dateien = [z for z in _lauf(["git", "ls-files"], wurzel).splitlines() if z]
    if not dateien:
        return {"fehler": f"kein git-Bestand unter {wurzel}"}
    stand = letzte_aenderung(wurzel)
    index = _namensindex(dateien)

    from datetime import datetime, timezone
    heute = datetime.fromisoformat(jetzt) if jetzt else datetime.now(timezone.utc)
    befunde, veraltet, mehrdeutig, derivate = [], [], [], 0
    for pfad in dateien:
        if not pfad.endswith(".md"):
            continue
        datei = wurzel / pfad
        try:
            text = datei.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        m = _STAND.search(text)
        if not m:
            # Ohne erklaerten Stand behauptet das Dokument keine Aktualitaet.
            # Eine Momentaufnahme (Plan, Uebergabe, Nachtbericht) DARF aelter
            # sein als das, was danach kam -- sie zu melden waere Laerm.
            continue
        erklaerter_stand = m.group(1)
        genannt = _genannte_dateien(text) - {Path(pfad).name}
        quellen = []
        for name in genannt:
            treffer = index.get(name, [])
            if len(treffer) == 1:
                quellen.append(treffer[0])
            elif len(treffer) > 1:
                mehrdeutig.append({"derivat": pfad, "name": name, "kandidaten": treffer})
        if not quellen:
            continue
        derivate += 1
        try:
            alter = (heute - _als_zeit(erklaerter_stand)).days
        except ValueError:
            alter = None
        if alter is not None and alter > frist_tage:
            veraltet.append({"derivat": pfad, "stand": erklaerter_stand, "tage": alter})
        # Der eigene Zeitpunkt: der erklaerte Stand, wenn es einen gibt --
        # er ist die AUSSAGE des Dokuments ueber sich selbst und damit das,
        # worauf der Leser sich verlaesst. Sonst der letzte Commit.
        eigen = erklaerter_stand
        for q in quellen:
            qz = stand.get(q)
            if not qz:
                continue
            if _juenger(qz, eigen):
                befunde.append({
                    "derivat": pfad,
                    "quelle": q,
                    "derivat_stand": eigen,
                    "quelle_geaendert": qz,
                    "erklaert": True,
                })
    return {"wurzel": str(wurzel), "dateien": len(dateien), "derivate": derivate,
            "frist_tage": frist_tage, "veraltet": veraltet,
            "befunde": befunde, "mehrdeutig": mehrdeutig}


def _als_zeit(s: str):
    """ISO 8601 mit Zone, auch in der kompakten Form +0200 statt +02:00."""
    from datetime import datetime
    s = s.strip()
    if len(s) >= 5 and (s[-5] in "+-") and ":" not in s[-5:]:
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s)


def _juenger(a: str, b: str) -> bool:
    """Ist Zeitpunkt a spaeter als b? Beide ISO 8601, ggf. verschiedene Zonen."""
    try:
        return _als_zeit(a) > _als_zeit(b)
    except ValueError:
        return False


def widerspruchslage() -> dict:
    """Misst Grenze 2, statt sie zu behaupten: Wie viele Knoten, die eine
    Aussage bestreiten oder berichtigen, nennen die betroffene Datei
    ueberhaupt in einer Form, die ein Programm findet?"""
    import sqlite3
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))
    import speicher  # noqa: E402
    conn = sqlite3.connect(f"file:{speicher.ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    zeilen = conn.execute(
        "SELECT id, title, summary, content, source FROM knowledge_nodes "
        "WHERE zurueckgezogen = 0 AND ("
        "  upper(title) LIKE '%BESTRITTEN%' OR upper(summary) LIKE '%BESTRITTEN%'"
        "  OR upper(title) LIKE '%BERICHTIGT%' OR upper(summary) LIKE '%BERICHTIGT%'"
        "  OR upper(content) LIKE '%BESTRITTEN%')").fetchall()
    conn.close()
    mit_datei = sum(1 for r in zeilen
                    if _DATEINAME.search((r["source"] or "") + " " + (r["content"] or "")))
    return {"widersprechende_knoten": len(zeilen), "davon_mit_dateinamen": mit_datei}


def _selftest() -> int:
    fehler = []
    if not _juenger("2026-08-19T08:00:00+0200", "2026-08-19T09:00:00+0200"):
        pass
    else:
        fehler.append("_juenger haelt frueher fuer spaeter")
    if not _juenger("2026-08-19T09:00:00+0200", "2026-08-19T08:00:00+0200"):
        fehler.append("_juenger erkennt spaeter nicht")
    # Zonen: 08:00+0200 == 06:00Z ist FRUEHER als 07:00Z
    if not _juenger("2026-08-19T07:00:00+0000", "2026-08-19T08:00:00+0200"):
        fehler.append("_juenger rechnet Zeitzonen nicht um")
    if _STAND.search("**Stand:** 2026-08-19T08:15:00+0200") is None:
        fehler.append("_STAND findet die Kopfzeile nicht")
    if _STAND.search("Stand 2026-08-19") is not None:
        fehler.append("_STAND nimmt ein Datum ohne Uhrzeit an")
    # Der echte Fall: Tiefenlink auf ein PDF, prozentkodiert im Query.
    echt = "[Quelle: Vertragsentwurf](https://x/viewer.html?file=%2Fquellen%2Fswb.pdf#page=2)"
    if "swb.pdf" not in _genannte_dateien(echt):
        fehler.append("_genannte_dateien scheitert an prozentkodierten Linkzielen")
    # NEGATIVFALL, der die 635 Fehlalarme erzeugt hat: blosse Erwaehnung im
    # Fliesstext ist keine Berufung. Ohne diesen Fall wird die Wache ignoriert.
    if _genannte_dateien("der Stand steht in STAND.md, siehe daten/kosten.json"):
        fehler.append("_genannte_dateien haelt eine Erwaehnung fuer eine Berufung")
    # Negativfall: ein Skriptname ist keine Quelle
    if _genannte_dateien("[so](bauen.py)"):
        fehler.append("_genannte_dateien haelt ein Skript fuer eine Quelle")
    # Ein Dokument OHNE erklaerten Stand ist eine Momentaufnahme, kein Derivat.
    if _STAND.search("# Plan\nkein Stand hier"):
        fehler.append("_STAND findet einen Stand, wo keiner steht")
    for f in fehler:
        print("FEHLER:", f)
    print("selftest:", "ok" if not fehler else f"{len(fehler)} Fehler")
    return 1 if fehler else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wurzel", default=None)
    p.add_argument("--frist", type=int, default=_FRIST_TAGE,
                   help=f"Tage, ab denen ein erklaerter Stand als ueberholt gilt (Vorgabe {_FRIST_TAGE})")
    p.add_argument("--jetzt", default=None, help="Bezugszeitpunkt (ISO), fuer wiederholbare Proben")
    p.add_argument("--melder", action="store_true")
    p.add_argument("--widerspruchslage", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()
    if a.selftest:
        return _selftest()
    if a.widerspruchslage:
        z = widerspruchslage()
        anteil = (100.0 * z["davon_mit_dateinamen"] / z["widersprechende_knoten"]
                  if z["widersprechende_knoten"] else 0.0)
        print(f"Knoten mit Widerspruchsvermerk: {z['widersprechende_knoten']} · "
              f"davon mit maschinenlesbarem Dateinamen: {z['davon_mit_dateinamen']} "
              f"({anteil:.0f} %)")
        return 0

    # Vorgabe ist das Repo, in dem gerade GEARBEITET wird -- nicht das, in
    # dem diese Datei liegt. Sonst prueft eine Sitzung in buckeberg die
    # Derivate von brainlehr, und die Wache haengt zwar ueberall, meldet aber
    # ueberall dasselbe.
    if a.wurzel:
        wurzel = Path(a.wurzel).resolve()
    else:
        aus_cwd = _lauf(["git", "rev-parse", "--show-toplevel"], Path.cwd()).strip()
        wurzel = Path(aus_cwd) if aus_cwd else Path(__file__).resolve().parent.parent
    e = pruefe(wurzel, frist_tage=a.frist, jetzt=a.jetzt)
    if "fehler" in e:
        print(e["fehler"], file=sys.stderr)
        return 2
    if a.melder:
        if e["veraltet"]:
            print(f"⚠️ Derivatfrische: {len(e['veraltet'])} abgeleitete(s) Dokument(e) "
                  f"erklaeren einen Stand aelter als {e['frist_tage']} Tage -- was "
                  f"dasteht kann stimmen und trotzdem ueberholt sein:")
            for v in sorted(e["veraltet"], key=lambda x: -x["tage"])[:5]:
                print(f"   {v['derivat']} ({v['tage']} Tage)")
            if len(e["veraltet"]) > 5:
                print(f"   ... und {len(e['veraltet']) - 5} weitere")
        if e["befunde"]:
            print(f"⚠️ Derivatfrische: {len(e['befunde'])} abgeleitete(s) Dokument(e) "
                  f"aelter als ihre Quelle -- was dasteht kann stimmen und trotzdem "
                  f"ueberholt sein:")
            for b in e["befunde"][:5]:
                wie = "erklaerter Stand" if b["erklaert"] else "letzter Commit"
                print(f"   {b['derivat']} ({wie} {b['derivat_stand'][:10]}) "
                      f"< {b['quelle']} ({b['quelle_geaendert'][:10]})")
            if len(e["befunde"]) > 5:
                print(f"   ... und {len(e['befunde']) - 5} weitere")
        return 0
    print(f"Bestand: {e['dateien']} Dateien · {e['derivate']} Dokumente mit erklaertem Stand und Quellenlink")
    print(f"Ueberholt (Stand aelter als {e['frist_tage']} Tage): {len(e['veraltet'])}")
    for v in sorted(e["veraltet"], key=lambda x: -x["tage"]):
        print(f"  {v['derivat']}  ({v['tage']} Tage, Stand {v['stand']})")
    print(f"Befunde: {len(e['befunde'])} aelter als ihre Quelle")
    for b in e["befunde"]:
        wie = "erklaerter Stand" if b["erklaert"] else "letzter Commit"
        print(f"  {b['derivat']}  ({wie} {b['derivat_stand']})")
        print(f"    < {b['quelle']}  (geaendert {b['quelle_geaendert']})")
    if e["mehrdeutig"]:
        print(f"\nMehrdeutig (nicht geraten, {len(e['mehrdeutig'])}):")
        for m in e["mehrdeutig"][:5]:
            print(f"  {m['derivat']} nennt '{m['name']}' -> {len(m['kandidaten'])} Kandidaten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
