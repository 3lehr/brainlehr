#!/usr/bin/env python3
"""Die rechte Seite des Paritaetsmessers: dieselbe Suche in Postgres.

WARUM pg_trgm UND NICHT to_tsvector: Beide FTS-Tabellen dieses Bestands
benutzen tokenize="trigram" (gemessen 2026-08-11 am Schema). FTS5-Trigramm und
pg_trgm arbeiten beide auf Zeichenfolgen, nicht auf Wortstaemmen -- das ist das
Gegenstueck. to_tsvector waere eine andere Suchart, kein Umzug derselben.

WARUM UEBER psql UND NICHT UEBER EINEN TREIBER: Dieses Modul misst, es
bedient nicht. Ein Treiber (psycopg) waere eine dauerhafte Abhaengigkeit fuer
35 Anfragen -- und die Wahl des Treibers gehoert zum Umzug selbst, nicht zu
seiner Vorbereitung. psql liegt ohnehin da, sobald Postgres da ist.
Preis, benannt: ein Prozessstart je Anfrage, rund 30 ms. Bei 35 Faellen
irrelevant, fuer den Betrieb voellig ungeeignet.

AUFBAU der Probe-Datenbank (einmalig, siehe Commit-Nachricht):
    createdb brainlehr_probe
    CREATE EXTENSION pg_trgm;
    CREATE TABLE suchtext (id TEXT PRIMARY KEY, art TEXT, text TEXT);
    -- gefuellt aus knowledge_nodes (zurueckgezogen=0) und
    -- lessons_learned (status='active'), dieselben Felder, die die
    -- FTS-Tabellen indizieren
    CREATE INDEX ... USING gin (text gin_trgm_ops);
"""
from __future__ import annotations

import subprocess
from typing import Callable

PSQL = "/opt/homebrew/opt/postgresql@17/bin/psql"


def suche_bauen(dsn: str, deckel_art: bool = True) -> Callable[[list[str], int], list[str]]:
    """Liefert eine Suchfunktion mit derselben Form wie suche_sqlite.

    Rangfolge nach `similarity()` absteigend -- das Gegenstueck zu FTS5s
    `rank`. Wie bei der SQLite-Seite werden Knoten und Lehren GETRENNT
    gedeckelt und dann aneinandergehaengt, damit der Vergleich nicht an
    unterschiedlicher Mischung scheitert statt an der Suche.
    """
    def suche(worte: list[str], deckel: int) -> list[str]:
        if not worte:
            return []
        muster = " ".join(w for w in worte if w.isalnum())
        if not muster:
            return []
        einzelworte = [w for w in worte if w.isalnum()]
        ergebnis: list[str] = []
        for art in ("knoten", "lehre"):
            # ILIKE '%wort%' je Stichwort, NICHT similarity(text, muster).
            #
            # Erste Fassung nahm den Aehnlichkeitsoperator % gegen den ganzen
            # Text und fand 0 von 35 Zielen. Das war kein Befund ueber
            # Postgres, sondern ein Fehler in der Formulierung: % vergleicht
            # zwei Zeichenketten als GANZE. Eine achtwortige Anfrage gegen ein
            # mehrere Kilobyte langes Dokument hat immer eine winzige
            # Aehnlichkeit -- die Schwelle 0,3 wird nie erreicht. FTS5-Trigramm
            # sucht dagegen TEILSTRINGS. Das Gegenstueck dazu ist ILIKE, vom
            # GIN-Index mit gin_trgm_ops beschleunigt.
            #
            # Rang: zuerst wie viele Stichworte ueberhaupt vorkommen, dann die
            # Wortaehnlichkeit. Das ist bewusst NICHT dasselbe Mass wie FTS5s
            # rank (BM25-artig) -- ein Rangunterschied zwischen beiden Seiten
            # ist deshalb erwartbar und kein Fehler.
            treffer_ausdruck = " + ".join(
                f"(text ILIKE '%%' || $${w}$$ || '%%')::int" for w in einzelworte)
            bedingung = " OR ".join(
                f"text ILIKE '%%' || $${w}$$ || '%%'" for w in einzelworte)
            sql = (
                f"SELECT id FROM suchtext "
                f"WHERE art = '{art}' AND ({bedingung}) "
                f"ORDER BY ({treffer_ausdruck}) DESC, "
                f"word_similarity($${muster}$$, text) DESC, id "
                f"LIMIT {int(deckel)}"
            )
            roh = subprocess.run([PSQL, "-d", dsn, "-tAc", sql],
                                  capture_output=True, text=True)
            if roh.returncode != 0:
                raise RuntimeError(f"psql fehlgeschlagen: {roh.stderr.strip()[:200]}")
            ergebnis += [z for z in roh.stdout.split() if z]
        return ergebnis

    return suche


def _selftest() -> None:
    """Netzlos nicht moeglich -- diese Datei IST der Zugang zur fremden
    Datenbank. Der Selbsttest prueft deshalb nur, was ohne sie pruefbar ist:
    dass eine leere Wortliste keine Anfrage stellt."""
    suche = suche_bauen("gibtsnicht")
    assert suche([], 10) == []
    assert suche(["!!!"], 10) == []
    print("selftest ok (2 Faelle, ohne Datenbank pruefbar)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
