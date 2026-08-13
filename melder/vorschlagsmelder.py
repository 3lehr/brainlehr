#!/usr/bin/env python3
"""Melder: nur die NEUEN Vorschlaege aus berichte/vorschlag.py.

Auftrag 84. FAKT: vorschlag.py liefert 25 Pruefstein- und 30
Faehigkeit-Kandidaten, aber niemand ruft es auf (0 Treffer in beiden
settings.json). Ein Ausloeser allein loest das nicht -- ein Bericht, der bei
JEDEM Stop-Ereignis wieder alle 55 zeigt, wird nach dem zweiten Mal
ueberblaettert. Gebraucht wird ein NEUHEITSFILTER: nur was seit dem letzten
Lauf dazugekommen ist.

ENTWURFSFRAGE (Auftragstext): woran wird "schon gezeigt" festgehalten?

Gewaehlt: eine JSON-Datei neben dem Bestand, `vorschlag_gezeigt.json`,
Inhalt eine Liste von Lehrkennungen -- der aktuelle Kandidatenstand nach dem
letzten Lauf, nicht ein Verlauf. Begruendung gegen die beiden Alternativen:

  - Ein Feld im Bestand (z.B. lessons_learned.vorgeschlagen_am) haette
    vorschlag.py von einem reinen Leser zu einem Schreiber gemacht -- das
    verletzt die woertliche Sperre im dortigen Modulkopf ("liest die
    Datenbank, schreibt NICHTS hinein"). Dieser Melder ruft vorschlag.py nur
    auf, aendert es nicht.
  - Ein reiner Zeitstempel ("letzter Lauf um HH:MM") reicht nicht: er kann
    nicht unterscheiden zwischen "Kandidat X ist neu seit dem letzten Lauf"
    und "Kandidat X gehoerte schon vorher dazu, aber die Sortierung hat sich
    verschoben" -- Grenzwert 4 der Abnahme (ein Kandidat faellt weg und
    kommt zurueck) braucht Identitaet je Kennung, keine Uhrzeit.

PREIS der Wahl: die Datei ist eine weitere, nicht versionierte
Laufzeitmarke (wie recall_log.jsonl, sichtbarkeit_stand/) -- geht sie
verloren (z.B. durch `git clean`), gilt beim naechsten Lauf wieder ALLES als
neu. Das ist bewusst hingenommen: der Melder blockiert nichts, ein
Ruecksprung auf "alles neu" ist hoechstens einmal laut, nie falsch.

Der Bestandwert selbst ist der KANDIDATENSTAND, nicht ein Verlauf: beim
Schreiben wird immer die aktuelle Kandidatenmenge abgelegt (nicht die
Vereinigung mit allem, was je gezeigt wurde). Ein weggefallener Kandidat
(Lehre behoben, Pruefstein nachgezogen) verschwindet damit aus der Datei --
kommt er spaeter zurueck, ist er nicht mehr enthalten und gilt wieder als
neu (Grenzwert 4 der Abnahme). Eine reine Vereinigungsmenge wuerde das
verhindern.

GRENZEN: reine Textausgabe, kein JSON auf stdout, endet immer mit 0. Ruft
vorschlag.py nur auf (import, keine Kopie der Auswahllogik). Schreibt
NICHTS in die Datenbank -- nur in die eigene JSON-Datei neben ihr.

Aufruf:
    python3 melder/vorschlagsmelder.py --melder     # nur Neues, oder still
    python3 melder/vorschlagsmelder.py --selftest
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(_w / "haken"))
import ort  # noqa: E402 -- liefert DB/WURZEL, kein fest verdrahteter Name hier

sys.path.insert(0, str(_w / "berichte"))
import vorschlag  # noqa: E402 -- Kandidatenauswahl bleibt dort, nicht kopiert

import speicher  # noqa: E402 -- Tuer statt einer eigenen DB-Verbindung (Naht-Ratsche)


def zustand_pfad() -> Path:
    return ort.WURZEL / "vorschlag_gezeigt.json"


def lade_gezeigt(pfad: Path) -> set[str]:
    """Leere Menge bei fehlender/kaputter Datei -- der Erstlauf gilt dann
    als "alles neu", was inhaltlich richtig ist (siehe Modulkopf, Preis der
    Wahl)."""
    try:
        return set(json.loads(pfad.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def schreibe_gezeigt(pfad: Path, ids: set[str]) -> None:
    pfad.write_text(json.dumps(sorted(ids), ensure_ascii=False), encoding="utf-8")


def neue_kandidaten(
    conn: sqlite3.Connection, repo_root: Path, pfad: Path
) -> tuple[list[dict], list[dict]]:
    """Kandidaten aus vorschlag.erhebe(), gefiltert auf das seit dem letzten
    Lauf Neue -- UND schreibt anschliessend den aktuellen Kandidatenstand
    zurueck (nicht die Vereinigung, siehe Modulkopf)."""
    pruefstein, faehigkeit = vorschlag.erhebe(conn, repo_root)
    gezeigt = lade_gezeigt(pfad)
    neu_p = [k for k in pruefstein if k["id"] not in gezeigt]
    neu_f = [k for k in faehigkeit if k["id"] not in gezeigt]
    aktuell = {k["id"] for k in pruefstein} | {k["id"] for k in faehigkeit}
    schreibe_gezeigt(pfad, aktuell)
    return neu_p, neu_f


def melde(db: Path | None = None, repo_root: Path | None = None,
          pfad: Path | None = None) -> str:
    db = db if db is not None else ort.DB
    repo_root = repo_root if repo_root is not None else ort.WURZEL
    pfad = pfad if pfad is not None else zustand_pfad()

    with speicher.lesen(db) as conn:
        neu_p, neu_f = neue_kandidaten(conn, repo_root, pfad)

    if not neu_p and not neu_f:
        return ""
    return (
        "NEU seit dem letzten Lauf (vorschlagsmelder) -- Entwuerfe, keine "
        "Auftraege:\n\n" + vorschlag.render(neu_p, neu_f)
    )


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--melder", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return

    if a.melder:
        try:
            text = melde()
        except Exception:
            return
        if text:
            print(text)
        return

    p.print_help()


# ---------- Selbsttest gegen eine temporaere Datenbank ----------

def _fixture(td: Path) -> tuple[sqlite3.Connection, Path, Path]:
    repo = td / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE lessons_learned (id TEXT, type TEXT, occurrences INTEGER, "
        "description TEXT, root_cause TEXT, prevention TEXT)"
    )
    return conn, repo, td / "vorschlag_gezeigt.json"


def _insert(conn: sqlite3.Connection, id_: str, art: str = "antipattern",
            occ: int = 2) -> None:
    conn.execute(
        "INSERT INTO lessons_learned VALUES (?,?,?,?,?,?)",
        (id_, art, occ, f"Fehler {id_} passiert.", f"Ursache {id_}.", f"Vermeide {id_}."),
    )


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tdraw:
        td = Path(tdraw)

        # (1) Erster Lauf meldet den vorhandenen Kandidaten, der zweite Lauf
        # unmittelbar danach meldet NICHTS mehr -- vorher (reines
        # vorschlag.py --bericht) gab es diesen Unterschied nicht: jeder
        # Aufruf zeigte alle Kandidaten erneut, ungeachtet frueherer Laeufe.
        conn, repo, zustand = _fixture(td)
        _insert(conn, "L-aaaaaa")
        conn.commit()

        neu_p, neu_f = neue_kandidaten(conn, repo, zustand)
        assert {k["id"] for k in neu_p} == {"L-aaaaaa"}, neu_p
        print("  (1a) erster Lauf meldet den vorhandenen Kandidaten: ok")

        neu_p2, neu_f2 = neue_kandidaten(conn, repo, zustand)
        assert neu_p2 == [] and neu_f2 == [], (neu_p2, neu_f2)
        print("  (1b) zweiter Lauf unmittelbar danach meldet nichts mehr: ok")

        # (2) Ein neu erfasster Wiederholungsfall taucht im naechsten Lauf
        # als neu auf und im uebernaechsten nicht mehr.
        _insert(conn, "L-bbbbbb")
        conn.commit()
        neu_p3, _ = neue_kandidaten(conn, repo, zustand)
        assert {k["id"] for k in neu_p3} == {"L-bbbbbb"}, neu_p3
        neu_p4, _ = neue_kandidaten(conn, repo, zustand)
        assert neu_p4 == [], neu_p4
        print("  (2) neu erfasster Fall: einmal neu, danach nicht mehr: ok")

        # (3) Negativfall: ein Lauf ohne neue Kandidaten erzeugt keine
        # Ausgabe -- melde() liefert einen leeren String, keine Leermeldung.
        # Echte Datei statt :memory:, weil melde() ueber speicher.lesen()
        # (Dateipfad, mode=ro) liest -- ueber speicher.schreiben() angelegt,
        # nicht ueber eine eigene sqlite3.connect-Verbindung hier (Naht-Ratsche).
        repo2 = td / "still" / "repo"
        repo2.mkdir(parents=True, exist_ok=True)
        zustand2 = td / "still" / "vorschlag_gezeigt.json"
        dbfile = td / "still.db"
        with speicher.schreiben(dbfile) as conn2:
            conn2.execute(
                "CREATE TABLE lessons_learned (id TEXT, type TEXT, occurrences INTEGER, "
                "description TEXT, root_cause TEXT, prevention TEXT)"
            )
            _insert(conn2, "L-cccccc")
        text1 = melde(db=dbfile, repo_root=repo2, pfad=zustand2)
        assert "L-cccccc" in text1, text1
        text2 = melde(db=dbfile, repo_root=repo2, pfad=zustand2)
        assert text2 == "", repr(text2)
        print("  (3) kein neuer Kandidat -> melde() liefert leeren String: ok")

        # (4) Grenzwert: ein Kandidat faellt weg (z.B. Lehre behoben, aus
        # der Tabelle geloescht) und kommt spaeter zurueck -- gilt wieder
        # als neu.
        conn3, repo3, zustand3 = _fixture(td / "grenzwert")
        _insert(conn3, "L-dddddd")
        conn3.commit()
        neue_kandidaten(conn3, repo3, zustand3)  # einmal zeigen, Zustand schreiben
        conn3.execute("DELETE FROM lessons_learned WHERE id = 'L-dddddd'")
        conn3.commit()
        weg_p, _ = neue_kandidaten(conn3, repo3, zustand3)
        assert weg_p == [], weg_p
        _insert(conn3, "L-dddddd")
        conn3.commit()
        zurueck_p, _ = neue_kandidaten(conn3, repo3, zustand3)
        assert {k["id"] for k in zurueck_p} == {"L-dddddd"}, zurueck_p
        print("  (4) weggefallener und zurueckgekehrter Kandidat gilt wieder als neu: ok")

    print("Alle Selbsttests gruen.")


if __name__ == "__main__":
    main()
