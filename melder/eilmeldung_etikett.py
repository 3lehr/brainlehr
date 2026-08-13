#!/usr/bin/env python3
"""Prueft, ob ein Titel Dringlichkeit BEHAUPTET, ohne das Etikett zu TRAGEN.

ANLASS, gemessen 2026-08-12/13: hub/scripts/eilmeldung_hook.py stellt
dringende Meldungen ausschliesslich nach dem TAG zu --
"WHERE zurueckgezogen = 0 AND tags LIKE '%\"dringend\"%'". Knoten a146403a
trug im TITEL 'EILMELDUNG:' und die Tags eilmeldung, belegpflicht,
agentenbericht, verschaerfung, quellentreue -- kein 'dringend'. Er wurde
deshalb NIE zugestellt, obwohl der Betreiber ihn ausdruecklich als
Eilmeldung anlegen liess. Der Tag ist inzwischen nachgetragen; diese Datei
ist die Wache dafuer, dass derselbe Fall beim naechsten Mal nicht wieder
unbemerkt durchrutscht.

FEHLKLASSE: gebaut, sichtbar, wirkungslos. Ein Titel, der 'EILMELDUNG:'
oder 'DRINGEND' voranstellt, ist eine Behauptung an den Leser -- die
Zustellung selbst schaut aber nur auf das Etikett (Tag), nie auf den Titel.
Faellt das Etikett aus, sieht der Knoten im Bestand trotzdem dringend aus
und bleibt in Wahrheit stumm.

NEGATIVFALL, ausdruecklich: 'Eilmeldung' irgendwo IM SATZ ist keine
Behauptung -- nur ein Titel, der mit dem Wort BEGINNT, behauptet etwas.
Sonst erzeugt diese Wache Fehlalarme, und eine Wache mit hoher
Fehlalarmquote wird binnen einer Woche ignoriert (am 2026-08-12/13 an zwei
anderen Werkzeugen mit 73 und 54 Prozent gemessen).

WAS HIER NICHT GEHT, und das ist ein Befund, keine Ausflucht: den Haken im
hub um den Tag 'eilmeldung' zu erweitern (jeder Titel, der mit 'eilmeldung'
markiert wird, koennte den Tag automatisch mitbekommen) waere die zweite
Haelfte der Loesung. Sie liegt in hub/scripts/eilmeldung_hook.py, einem
FREMDEN Repo, und wird von hier aus nicht angefasst -- der Betreiber
entscheidet das selbst.

Aufruf:
    python3 eilmeldung_etikett.py             # Zahlen + Befunde
    python3 eilmeldung_etikett.py --melder    # nur sprechen, wenn etwas anschlaegt
    python3 eilmeldung_etikett.py --selftest
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))
import speicher  # noqa: E402

# Nur der TITELANFANG zaehlt als Behauptung -- ein Wort mitten im Satz
# behauptet nichts (siehe Negativfall oben). Kleinschreibung wird toleriert,
# der Bestand traegt bislang nur Grossschreibung ('EILMELDUNG:', 'DRINGEND'),
# aber ein kuenftiger klein geschriebener Titel soll denselben Schutz haben.
_PRAEFIXE = ("eilmeldung", "dringend")


def _behauptet_dringlichkeit(title: str | None) -> bool:
    kern = (title or "").strip().lower()
    return any(kern.startswith(p) for p in _PRAEFIXE)


def _traegt_etikett(tags: str | None) -> bool:
    return '"dringend"' in (tags or "")


def pruefe(db: Path | None = None) -> dict:
    """Liefert die drei geforderten Zahlen plus die beanstandeten Knoten.

    vorhanden  -- Knoten, deren Titel Dringlichkeit behauptet
    geprueft   -- dieselbe Zahl (jeder vorhandene wird geprueft, keine
                  Stichprobe -- eine Eilmeldung darf nicht durch Auslassung
                  durchrutschen)
    beanstandet -- davon ohne das Etikett 'dringend'
    """
    try:
        with speicher.lesen(db) as con:
            rows = con.execute(
                "SELECT path, title, tags FROM knowledge_nodes WHERE zurueckgezogen = 0"
            ).fetchall()
    except sqlite3.OperationalError:
        return {"vorhanden": 0, "geprueft": 0, "beanstandet": 0, "befunde": []}

    vorhanden = [r for r in rows if _behauptet_dringlichkeit(r["title"])]
    befunde = [dict(r) for r in vorhanden if not _traegt_etikett(r["tags"])]
    return {
        "vorhanden": len(vorhanden),
        "geprueft": len(vorhanden),
        "beanstandet": len(befunde),
        "befunde": befunde,
    }


def melde(db: Path | None = None) -> str:
    ergebnis = pruefe(db)
    if not ergebnis["beanstandet"]:
        return ""
    kopf = (f"{ergebnis['beanstandet']} von {ergebnis['vorhanden']} Knoten mit "
            "Dringlichkeits-Titel ohne das Etikett 'dringend' -- werden vom "
            "Eilmeldungs-Kanal nie zugestellt:")
    zeilen = [f"  {b['path']}: {b['title']}" for b in ergebnis["befunde"]]
    return "\n".join([kopf, *zeilen])


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        db = Path(tmp_dir) / "test.db"
        with speicher.schreiben(db) as con:
            con.execute(
                "CREATE TABLE knowledge_nodes (path TEXT, title TEXT, tags TEXT, "
                "zurueckgezogen INTEGER)"
            )

        # ROT: Titel behauptet, Etikett fehlt -- muss anschlagen.
        with speicher.schreiben(db) as con:
            con.execute(
                "INSERT INTO knowledge_nodes VALUES (?,?,?,?)",
                ("/a/ohne-etikett", "EILMELDUNG: Belegpflicht verschaerft",
                 '["belegpflicht","agentenbericht"]', 0),
            )
        ergebnis = pruefe(db)
        assert ergebnis["vorhanden"] == 1, ergebnis
        assert ergebnis["geprueft"] == 1, ergebnis
        assert ergebnis["beanstandet"] == 1, ergebnis
        assert ergebnis["befunde"][0]["path"] == "/a/ohne-etikett"
        aus = melde(db)
        assert "/a/ohne-etikett" in aus, aus

        # GRUEN: Etikett nachgetragen -- muss verstummen (der reale Fall
        # aus dem Anlass, nachgestellt und zurueckgenommen).
        with speicher.schreiben(db) as con:
            con.execute(
                "UPDATE knowledge_nodes SET tags = ? WHERE path = ?",
                ('["belegpflicht","agentenbericht","dringend"]', "/a/ohne-etikett"),
            )
        ergebnis = pruefe(db)
        assert ergebnis["vorhanden"] == 1, ergebnis
        assert ergebnis["beanstandet"] == 0, ergebnis
        assert melde(db) == "", melde(db)

        # NEGATIVFALL: 'Eilmeldung' mitten im Satz behauptet nichts -- darf
        # trotz fehlendem Etikett nicht mitgezaehlt werden.
        with speicher.schreiben(db) as con:
            con.execute(
                "INSERT INTO knowledge_nodes VALUES (?,?,?,?)",
                ("/a/im-satz", "Die Eilmeldung von gestern im Rueckblick",
                 '["belegpflicht"]', 0),
            )
        ergebnis = pruefe(db)
        assert ergebnis["vorhanden"] == 1, ("Titel im Satz darf nicht als Behauptung zaehlen", ergebnis)
        assert ergebnis["beanstandet"] == 0, ergebnis

        # DRINGEND-Praefix ebenso, und zurueckgezogene Knoten zaehlen nicht
        # mit (gleiche Begruendung wie beim Zustell-Hook: ein zurueckgezogener
        # Knoten wird ohnehin nie zugestellt).
        with speicher.schreiben(db) as con:
            con.execute(
                "INSERT INTO knowledge_nodes VALUES (?,?,?,?)",
                ("/a/dringend-ohne", "DRINGEND Serverausfall", '[]', 0),
            )
            con.execute(
                "INSERT INTO knowledge_nodes VALUES (?,?,?,?)",
                ("/a/zurueckgezogen", "EILMELDUNG: alt und zurueckgezogen", '[]', 1),
            )
        ergebnis = pruefe(db)
        assert ergebnis["vorhanden"] == 2, ergebnis  # ohne-etikett(mit tag) + dringend-ohne, nicht der zurueckgezogene
        assert ergebnis["beanstandet"] == 1, ergebnis
        assert {b["path"] for b in ergebnis["befunde"]} == {"/a/dringend-ohne"}, ergebnis

        # Keine Datenbank -> stille Null, kein Absturz.
        leer = pruefe(Path(tmp_dir) / "nicht-vorhanden.db")
        assert leer == {"vorhanden": 0, "geprueft": 0, "beanstandet": 0, "befunde": []}, leer

    print("eilmeldung_etikett: Selbsttest gruen")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--melder", action="store_true", help="nur sprechen, wenn etwas anschlaegt")
    p.add_argument("--selftest", action="store_true")
    p.add_argument("--db", type=Path, default=None)
    a = p.parse_args()
    if a.selftest:
        _selftest()
        return
    if a.melder:
        text = melde(a.db)
        if text:
            print(text)
        return
    ergebnis = pruefe(a.db)
    print(f"vorhanden={ergebnis['vorhanden']} geprueft={ergebnis['geprueft']} "
          f"beanstandet={ergebnis['beanstandet']}")
    for b in ergebnis["befunde"]:
        print(f"  {b['path']}: {b['title']}")


if __name__ == "__main__":
    main()
