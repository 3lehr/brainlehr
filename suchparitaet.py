#!/usr/bin/env python3
"""Was kostet der Umzug die Suche? Gemessen, bevor umgezogen wird.

ANLASS (Betreiberentscheidung 2026-08-11: zweiter Rechner schreibt mit, also
Postgres): Beim Wechsel der Datenbank wandern Daten und Regeln mit -- die
VOLLTEXTSUCHE nicht. SQLite FTS5 und Postgres zerlegen deutsche Woerter
anders, gewichten anders, ranken anders. Fuer ein Projekt, dessen Gegenstand
die Guete des Abrufs ist, ist das nicht ein Nebeneffekt des Umzugs, sondern
sein Kern: jede bisher erhobene Abrufzahl waere danach nicht mehr
vergleichbar, ohne dass es jemandem auffaellt.

Darum wird der Bruch GEMESSEN, bevor er passiert -- nicht hinterher als
"der Abruf fuehlt sich schlechter an" entdeckt.

VERFAHREN: Derselbe Prueffall geht durch beide Suchen. Verglichen werden drei
Dinge, weil eine einzelne Zahl den falschen Eindruck macht:

  ziel_gefunden  Steht der Zieleintrag in den ersten k Treffern? Das ist die
                 Groesse, an der die Nuetzlichkeit haengt.
  rangdifferenz  Auf welchem Platz? Ein Ziel von Platz 1 auf Platz 8 ist
                 formal noch ein Treffer und praktisch keiner mehr, weil der
                 Deckel des Abrufs frueher schneidet.
  ueberlappung   Wie aehnlich sind die Trefferlisten insgesamt? Zwei Suchen
                 koennen dasselbe Ziel finden und ringsum voellig
                 verschiedenes einspielen -- und eingespielt wird alles.

WOZU DIESES WERKZEUG NICHT DIENT -- korrigiert am 2026-08-11 nach Einspruch
des Betreibers, weil die erste Fassung dieses Absatzes eine Konservierung
begruendet haette, die niemand will:

Der Unterschied zwischen den Suchen ist KEIN Schadensmass und erst recht kein
Grund, beim alten Stand zu bleiben. Der Bruch ist beim Umzug ohnehin
unvermeidlich (trigram gegen pg_trgm, siehe unten) und obendrein gewollt --
die heutige Trefferlage ist die, die verbessert werden soll, nicht die, die
verteidigt werden muss.

Der Einspruch stuetzte sich auf Gemessenes, nicht auf Geschmack: das
Einbettungsmodell wurde hier bereits einmal getauscht (nomic-embed-text ->
bge-m3, Commit 1305390), der Einbettungspfad achtmal umgebaut, und die
Vektoren an vier Tagen neu gerechnet (2624 am 2026-08-07, 794 am 2026-08-11).
Neuberechnung ist in diesem Haus Routine, kein Ereignis.

Die Zahl, auf die es ankommt, ist deshalb nicht die Differenz zwischen links
und rechts, sondern `gefunden_links` gegen `gefunden_rechts`: welche Suche
findet den Zieleintrag oefter. Das ist eine Auswahl zwischen Bauformen, kein
Bestandsschutz. Die Differenzmasse (rangdifferenz, ueberlappung) bleiben --
aber als Beschreibung, WIE anders sich die neue Suche verhaelt, damit die
Aenderung erklaerbar ist und nicht als Raetsel auftaucht.

Die Suchen sind austauschbar (Parameter `suchen`), damit dieses Modul ohne
laufenden Postgres pruefbar bleibt -- der Selbsttest fuehrt zwei gestellte
Suchen gegeneinander.

Aufruf:
    python3 suchparitaet.py --korpus runs/pruefkorpus_v2.json --nur-sqlite
    python3 suchparitaet.py --korpus runs/pruefkorpus_v2.json --dsn postgresql://...
    python3 suchparitaet.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Iterable

WURZEL = Path(__file__).resolve().parent
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "haken"))

import speicher  # noqa: E402

DECKEL = 10  # so viele Treffer holt der echte Abruf je Anfrage

# GEMESSEN am 2026-08-11, und der wichtigste Einzelbefund fuer den Umzug:
# beide FTS-Tabellen benutzen tokenize="trigram", nicht die uebliche
# Wortzerlegung. Das Gegenstueck in Postgres ist deshalb pg_trgm mit einem
# GIN-Index -- NICHT to_tsvector/to_tsquery. Wer die Volltextsuche
# "naheliegend" nach tsvector portiert, tauscht eine Teilwort-Suche gegen eine
# Wortstamm-Suche und wundert sich hinterher ueber die Trefferlage.

Suche = Callable[[list[str], int], list[str]]


def stichworte(prompt: str) -> list[str]:
    """Zerlegung EINMAL fuer beide Suchen -- sonst misst der Vergleich die
    Zerlegung mit, und die ist nicht Teil des Umzugs."""
    import knowledge_recall_hook as rh
    return rh.keywords(prompt)


def suche_sqlite(worte: list[str], deckel: int = DECKEL) -> list[str]:
    """FTS5, der heutige Stand. Liefert Kennungen in Rangfolge."""
    if not worte:
        return []
    anfrage = " OR ".join(w for w in worte if w.isalnum())
    if not anfrage:
        return []
    with speicher.lesen() as conn:
        # Verknuepfung ueber rowid, nicht ueber id: beide FTS-Tabellen sind
        # 'external content' mit content_rowid='rowid' (siehe schema.sql) --
        # eine Spalte f.id gibt es dort gar nicht.
        knoten = conn.execute(
            "SELECT n.id FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
            "WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 "
            "ORDER BY rank LIMIT ?", (anfrage, deckel)).fetchall()
        lehren = conn.execute(
            "SELECT l.id FROM lessons_fts f JOIN lessons_learned l ON l.rowid = f.rowid "
            "WHERE lessons_fts MATCH ? AND l.status = 'active' "
            "ORDER BY rank LIMIT ?", (anfrage, deckel)).fetchall()
    return [r[0] for r in knoten] + [r[0] for r in lehren]


def vergleiche_fall(ziel: str, links: list[str], rechts: list[str]) -> dict:
    """Ein Fall, drei Groessen. rang* ist 1-basiert; None heisst 'nicht
    gefunden' und wird NICHT als grosse Zahl kodiert -- eine 999 wuerde in
    jeden Mittelwert einfliessen und ihn unbrauchbar machen."""
    def rang(liste: list[str]) -> int | None:
        return liste.index(ziel) + 1 if ziel in liste else None

    r_l, r_r = rang(links), rang(rechts)
    menge_l, menge_r = set(links), set(rechts)
    vereinigung = menge_l | menge_r
    return {
        "ziel": ziel,
        "rang_links": r_l,
        "rang_rechts": r_r,
        "gefunden_links": r_l is not None,
        "gefunden_rechts": r_r is not None,
        "rangdifferenz": (r_r - r_l) if (r_l is not None and r_r is not None) else None,
        "ueberlappung": (len(menge_l & menge_r) / len(vereinigung)) if vereinigung else 1.0,
    }


def messen(faelle: Iterable[dict], links: Suche, rechts: Suche,
           deckel: int = DECKEL) -> dict:
    einzeln = []
    for fall in faelle:
        worte = stichworte(fall["prompt"])
        einzeln.append({
            "fall": fall.get("target_id"),
            **vergleiche_fall(fall["target_id"], links(worte, deckel), rechts(worte, deckel)),
        })

    n = len(einzeln)
    nur_links = [e for e in einzeln if e["gefunden_links"] and not e["gefunden_rechts"]]
    nur_rechts = [e for e in einzeln if e["gefunden_rechts"] and not e["gefunden_links"]]
    beide = [e for e in einzeln if e["gefunden_links"] and e["gefunden_rechts"]]
    verschoben = [e for e in beide if e["rangdifferenz"]]

    return {
        "faelle": n,
        "gefunden_links": sum(1 for e in einzeln if e["gefunden_links"]),
        "gefunden_rechts": sum(1 for e in einzeln if e["gefunden_rechts"]),
        "nur_links_gefunden": [e["ziel"] for e in nur_links],
        "nur_rechts_gefunden": [e["ziel"] for e in nur_rechts],
        "rang_verschoben": len(verschoben),
        "groesste_verschlechterung": max((e["rangdifferenz"] for e in verschoben), default=0),
        "ueberlappung_mittel": round(sum(e["ueberlappung"] for e in einzeln) / n, 3) if n else None,
        "einzeln": einzeln,
    }


def _selftest() -> None:
    faelle = [{"target_id": "L-1", "prompt": "eins"},
              {"target_id": "L-2", "prompt": "zwei"},
              {"target_id": "L-3", "prompt": "drei"}]

    import unittest.mock as mock
    with mock.patch.object(sys.modules[__name__], "stichworte", lambda p: [p]):
        gleich = lambda w, k: {"eins": ["L-1", "X"], "zwei": ["L-2"], "drei": ["L-3"]}[w[0]]
        e = messen(faelle, gleich, gleich)
        assert e["gefunden_links"] == e["gefunden_rechts"] == 3
        assert e["rang_verschoben"] == 0 and e["ueberlappung_mittel"] == 1.0, e
        assert not e["nur_links_gefunden"] and not e["nur_rechts_gefunden"]

        # Gegenprobe: eine Suche, die dasselbe Ziel weiter hinten fuehrt und
        # ringsum anderes einspielt, MUSS auffallen -- sonst misst nichts.
        schlechter = lambda w, k: {"eins": ["A", "B", "L-1"], "zwei": ["C"], "drei": ["L-3"]}[w[0]]
        e2 = messen(faelle, gleich, schlechter)
        assert e2["gefunden_rechts"] == 2, e2["gefunden_rechts"]
        assert e2["nur_links_gefunden"] == ["L-2"], e2["nur_links_gefunden"]
        assert e2["rang_verschoben"] == 1 and e2["groesste_verschlechterung"] == 2, e2
        assert e2["ueberlappung_mittel"] < 1.0

        # Ein nicht gefundenes Ziel darf KEINE Rangdifferenz erzeugen --
        # sonst schleicht sich eine erfundene Zahl in den Mittelwert.
        fehlt = [x for x in e2["einzeln"] if x["ziel"] == "L-2"][0]
        assert fehlt["rangdifferenz"] is None and fehlt["rang_rechts"] is None

    print("selftest ok (3 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--korpus", type=Path)
    p.add_argument("--nur-sqlite", action="store_true",
                    help="beide Seiten mit FTS5 -- prueft den Messaufbau selbst, "
                         "muss null Unterschied ergeben")
    p.add_argument("--dsn", help="Postgres-Verbindung fuer die rechte Seite")
    p.add_argument("--out", type=Path)
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        _selftest()
        return
    if not a.korpus:
        p.error("--korpus fehlt")

    daten = json.loads(a.korpus.read_text(encoding="utf-8"))
    faelle = [f for f in daten.get("cases", []) if f.get("target_id") and f.get("prompt")]

    if a.nur_sqlite:
        rechts = suche_sqlite
    elif a.dsn:
        from suche_postgres import suche_bauen  # noqa: F401 -- erst wenn es sie gibt
        rechts = suche_bauen(a.dsn)
    else:
        p.error("entweder --nur-sqlite oder --dsn")

    ergebnis = messen(faelle, suche_sqlite, rechts)
    print(f"Faelle: {ergebnis['faelle']}")
    print(f"ZIEL GEFUNDEN (die Zahl, die entscheidet) -- links FTS5: "
          f"{ergebnis['gefunden_links']} | rechts: {ergebnis['gefunden_rechts']}")
    print(f"nur links gefunden: {len(ergebnis['nur_links_gefunden'])} | "
          f"nur rechts: {len(ergebnis['nur_rechts_gefunden'])}")
    print(f"Rang verschoben: {ergebnis['rang_verschoben']} "
          f"(groesste Verschiebung: {ergebnis['groesste_verschlechterung']} Plaetze) "
          f"-- Beschreibung des Unterschieds, kein Schadensmass")
    print(f"Ueberlappung der Trefferlisten im Mittel: {ergebnis['ueberlappung_mittel']}")
    if a.out:
        a.out.write_text(json.dumps(ergebnis, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print(f"\nGeschrieben: {a.out}")


if __name__ == "__main__":
    main()
