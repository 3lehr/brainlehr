#!/usr/bin/env python3
"""Die Plankennungen als GEGENSTAENDE -- die Erstanwendung von ADR-028.

WARUM PLANKENNUNGEN UND NICHT PERSONEN (Betreiberentscheidung 2026-08-21): An
Plaenen haengt kein Bestand Dritter. Traegt die Bauform an 57 Plandateien,
traegt sie auch an Menschen -- und der Fehler kostet hier nichts.

DAS PROBLEM, gemessen: `S12` ist DREIMAL echt vergeben (PLAN_DESTILLE_2026-08-09,
PLAN_S12_ZWEITER_ANLAUF_2026-08-11, SPRINTS.md), `S1` VIERMAL. Wer heute in
einer ADR oder einem Commit auf "S12" verweist, verweist auf drei Sachen. Der
Betreiber verlangte einen Schluessel, der Datum und Projekt mittraegt -- das
sind NAMEN, und ADR-028 verbietet Namen als Schluessel. Aufloesung ohne
Umnummerierung: jeder Vergabeort wird ein Gegenstand mit bedeutungslosem
Schluessel; Kennung, Ablagedatei, Datum und Projekt sind seine NAMEN mit
eigener Geltung. Ein alter Verweis auf `S12` bleibt aufloesbar, weil dasteht,
wann und wo dieser Name galt.

DIE UNTERSCHEIDUNG, an der schon einmal eine doppelt zu hohe Zahl entstand:
Eine VERGABE ist eine Ueberschrift, die mit der Kennung beginnt, oder eine
Tabellenzeile, deren erste Spalte die Kennung IST. Eine ERWAEHNUNG ist alles
andere -- 'Warum F und G, und nicht S1, S2, S3' vergibt nichts, obwohl drei
Kennungen in einer Ueberschrift stehen.

WAS DIESES MODUL NICHT TUT: zusammenfuehren. Ob zwei gleichnamige Vergaben
dieselbe Sache meinen, ist eine Beurteilung und keine Regel -- SPRINTS.md ist
die Uebersicht ZU PLAN_DESTILLE und meint dieselben Sprints, PLAN_DREITEILUNG
meint etwas voellig anderes. Der Bericht legt die Kollisionen vor, entschieden
wird sie nicht automatisch.

Aufruf:
    python3 kern/gegenstand_plankennungen.py --selftest
    python3 kern/gegenstand_plankennungen.py --lauf runs/<datei>.json
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "kern"))
sys.path.insert(0, str(WURZEL / "haken"))

import gegenstand  # noqa: E402

KENNUNG = r"S\d+[a-z]?"
# Nach der Kennung MUSS ein Trenner folgen oder das Zeilenende. Ohne diese
# Bedingung zaehlt '### S1 bis S4 abgeschlossen' als Vergabe von S1 -- es ist
# eine Standmeldung ueber vier bereits vergebene Sprints.
_UEBERSCHRIFT = re.compile(rf"^#{{1,6}}\s+({KENNUNG})\s*(?:[·—–\-:,]|$)")
_DATUM = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class Vergabe:
    kennung: str
    datei: str
    zeile: int
    art: str          # ueberschrift | tabelle
    titel: str


def vergaben(text: str, datei: str) -> list[Vergabe]:
    """Echte Vergaben, ohne Erwaehnungen. Je Kennung und Datei die ERSTE --
    'S12 ist kein Forschungsschritt mehr' ist ein Nachtrag zum selben
    Abschnitt, kein zweiter Sprint."""
    gefunden: dict[str, Vergabe] = {}
    for nr, ln in enumerate(text.splitlines(), 1):
        m = _UEBERSCHRIFT.match(ln)
        if m:
            gefunden.setdefault(m.group(1), Vergabe(m.group(1), datei, nr, "ueberschrift",
                                                    ln.lstrip("# ").strip()))
            continue
        if ln.startswith("|"):
            zellen = [z.strip() for z in ln.strip().strip("|").split("|")]
            erste = zellen[0].strip("`* ") if zellen else ""
            if re.fullmatch(KENNUNG, erste):
                titel = zellen[1].strip() if len(zellen) > 1 else ""
                gefunden.setdefault(erste, Vergabe(erste, datei, nr, "tabelle", titel))
    return list(gefunden.values())


def plandateien(wurzel: Path) -> list[Path]:
    return sorted((wurzel / "docs").glob("PLAN_*.md")) + [wurzel / "docs" / "SPRINTS.md"]


def _datum(pfad: Path, text: str) -> str:
    """Das Datum der Ablage -- aus dem Dateinamen, sonst aus dem Kopf.

    Dateinamen tragen nur das Datum (sortierbar), die volle Uhrzeit steht im
    Kopf. SPRINTS.md traegt gar keins im Namen und nennt seinen Erhebungsstand
    in Zeile 1."""
    m = _DATUM.search(pfad.name)
    if m:
        return m.group(1) + "T00:00:00+0200"
    kopf = "\n".join(text.splitlines()[:10])
    m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4})", kopf)
    if m:
        return m.group(1)
    m = _DATUM.search(kopf)
    if not m:
        raise ValueError(f"{pfad.name}: kein Datum im Namen und keins im Kopf -- "
                         f"geraten wird hier nicht")
    return m.group(1) + "T00:00:00+0200"


def erfassen(conn: sqlite3.Connection, wurzel: Path, projekt: str = "brainlehr") -> dict:
    """Legt je Vergabeort einen Gegenstand an und haengt vier Namen daran."""
    gegenstand.ensure_schema(conn)
    bericht: dict = {"projekt": projekt, "dateien": 0, "vergaben": 0,
                     "gegenstaende": [], "kollisionen": []}
    nach_kennung: dict[str, list[dict]] = {}

    for pfad in plandateien(wurzel):
        text = pfad.read_text(encoding="utf-8")
        rel = str(pfad.relative_to(wurzel))
        ts = _datum(pfad, text)
        bericht["dateien"] += 1
        for v in sorted(vergaben(text, rel), key=lambda x: x.zeile):
            beleg = f"{rel}:{v.zeile} ({v.art})"
            gid = gegenstand.anlegen(conn, "plankennung", v.kennung, beleg=beleg, ts=ts)
            # Datei, Datum und Projekt sind NAMEN, nicht Teile des Schluessels
            # -- genau die Trennung, die der Betreiber verlangt hat.
            gegenstand.benennen(conn, gid, rel, art_des_namens="pfad", beleg=beleg, ts=ts)
            gegenstand.benennen(conn, gid, ts[:10], art_des_namens="datum", beleg=beleg, ts=ts)
            gegenstand.benennen(conn, gid, projekt, art_des_namens="projekt", beleg=beleg, ts=ts)
            eintrag = {"id": gid, "kennung": v.kennung, "datei": rel, "zeile": v.zeile,
                       "art_der_vergabe": v.art, "titel": v.titel,
                       "namen": gegenstand.namen(conn, gid)}
            bericht["gegenstaende"].append(eintrag)
            bericht["vergaben"] += 1
            nach_kennung.setdefault(v.kennung, []).append(eintrag)

    for kennung, liste in sorted(nach_kennung.items()):
        if len(liste) > 1:
            bericht["kollisionen"].append({
                "kennung": kennung, "anzahl": len(liste),
                "vergaben": [{"id": e["id"], "datei": e["datei"], "zeile": e["zeile"],
                              "titel": e["titel"], "urteil": _urteil(kennung, e["datei"], liste)}
                             for e in liste],
                "beurteilung": _beurteilung(kennung, liste),
            })
    dieselbe = sum(1 for k in bericht["kollisionen"]
                   for v in k["vergaben"] if v["urteil"] == "dasselbe, zweitbenannt")
    bericht["zusammenfassung"] = {
        "vergaben": bericht["vergaben"],
        "zweitbenennungen": dieselbe,
        "verschiedene_sachen": bericht["vergaben"] - dieselbe,
        "hinweis": "Zweitbenennungen sind NICHT zusammengefuehrt. Der naechste "
                   "Handgriff waere, die zweite Datei als weiteren `pfad`-Namen "
                   "an den bestehenden Gegenstand zu haengen statt einen neuen "
                   "anzulegen -- eine Entscheidung, keine Regel.",
    }
    conn.commit()
    return bericht


# Die beiden Regeln, nach denen unten geurteilt wird -- beide belegt, nicht
# geraten. Wer sie aendert, aendert eine Beurteilung, nicht eine Zahl.
ZWEITBENENNUNG = {
    # SPRINTS.md sagt in Zeile 3 ueber sich selbst: "Grundlage:
    # docs/PLAN_DESTILLE_2026-08-09.md (21 Sprint-Abschnitte: S1, S1b, S1c,
    # S1d, S2-S18)". Es ist die UEBERSICHT zu dieser Datei, keine zweite
    # Vergabe -- die Titel decken sich Zeile fuer Zeile.
    "docs/SPRINTS.md": "docs/PLAN_DESTILLE_2026-08-09.md",
}


def _urteil(kennung: str, datei: str, liste: list[dict]) -> str:
    dateien = {e["datei"] for e in liste}
    grundlage = ZWEITBENENNUNG.get(datei)
    if grundlage and grundlage in dateien:
        return "dasselbe, zweitbenannt"
    # Ein Plan, dessen DATEINAME die Kennung traegt, ist die Fortsetzung
    # dieser Kennung, nicht eine neue Vergabe: PLAN_S12_ZWEITER_ANLAUF heisst
    # so, weil es derselbe S12 ist -- der zweite Anlauf.
    if kennung in Path(datei).name and any(kennung not in Path(d).name for d in dateien):
        return "dasselbe, zweitbenannt"
    return "eigene Sache"


def _beurteilung(kennung: str, liste: list[dict]) -> str:
    eigen = [e for e in liste if _urteil(kennung, e["datei"], liste) == "eigene Sache"]
    if len(eigen) == 1:
        return (f"EINE Sache, {len(liste)}-mal benannt. Massgeblich "
                f"{eigen[0]['datei']}:{eigen[0]['zeile']}; die uebrigen sind Uebersicht "
                f"oder Fortsetzung desselben Abschnitts.")
    return (f"{len(eigen)} VERSCHIEDENE Sachen, die zufaellig gleich heissen: "
            + " | ".join(f"{e['datei']} -> {e['titel'][:60]}" for e in eigen)
            + ". Jeder Plan zaehlt seine Schritte fuer sich; ein Verweis auf "
              f"'{kennung}' ohne Datei und Zeitpunkt ist nicht aufloesbar.")


def _selftest() -> int:
    conn = sqlite3.connect(":memory:")
    gegenstand.ensure_schema(conn)

    probe = ("# S12, zweiter Anlauf\n"
             "### Warum F und G — und nicht S1, S2, S3\n"
             "### S3 · Ein echter Abschnitt\n"
             "### S3 ist kein Forschungsschritt mehr\n"
             "Im Fliesstext steht S7.\n"
             "| S4 | Tabellenvergabe |\n"
             "| irgendwas | hier steht S8 |\n")
    k = sorted(v.kennung for v in vergaben(probe, "x.md"))
    assert k == ["S12", "S3", "S4"], k

    # Zwei Dateien desselben Tages duerfen dieselbe Kennung vergeben, ohne
    # dass die Gegenstaende still zusammenfallen.
    a = gegenstand.anlegen(conn, "plankennung", "S1", beleg="a.md:1", ts="2026-08-09T00:00:00+0200")
    b = gegenstand.anlegen(conn, "plankennung", "S1", beleg="b.md:1", ts="2026-08-09T00:00:00+0200")
    assert a != b, "gleicher Tag, gleiche Kennung, ein Schluessel -- der Beleg fehlt im Anlass"
    assert len(gegenstand.aufloesen(conn, "S1")) == 2

    assert _datum(Path("PLAN_X_2026-08-09.md"), "") == "2026-08-09T00:00:00+0200"
    assert _datum(Path("SPRINTS.md"), "# Stand: 2026-08-12T05:20:28+0200") == "2026-08-12T05:20:28+0200"
    try:
        _datum(Path("ohne.md"), "kein Datum")
    except ValueError:
        pass
    else:
        raise AssertionError("ohne Datum haette abgewiesen werden muessen")

    print("gegenstand_plankennungen: Selbsttest gruen (Vergabe vs Erwaehnung, "
          "kein stiller Zusammenfall, Datum erzwungen)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    if "--lauf" in sys.argv:
        ziel = WURZEL / sys.argv[sys.argv.index("--lauf") + 1]
        import speicher
        with speicher.schreiben() as conn:
            bericht = erfassen(conn, WURZEL)
        ziel.write_text(json.dumps(bericht, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{bericht['dateien']} Dateien, {bericht['vergaben']} Vergaben, "
              f"{len(bericht['kollisionen'])} kollidierende Kennungen -> {ziel}")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
