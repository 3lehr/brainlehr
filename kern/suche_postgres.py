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


VARIANTEN = ("teilstring", "wortgrenze", "kurzfeld", "kurz_gewichtet")


def suche_bauen(dsn: str, variante: str = "teilstring") -> Callable[[list[str], int], dict[str, list[str]]]:
    r"""Liefert eine Suchfunktion mit derselben Form wie suche_sqlite.

    Vier Bauformen, weil die erste nicht die einzige moegliche ist und "6 von
    35" sonst als Eigenschaft von Postgres gelesen wuerde statt als Eigenschaft
    EINER Formulierung:

      teilstring       ILIKE '%wort%' ueber den ganzen Text. Naechstes
                       Gegenstueck zu FTS5-Trigramm, findet auch Wortteile
                       (Komposita, Kennungen) -- und Zufallstreffer mitten in
                       laengeren Woertern.
      wortgrenze       dasselbe mit Wortgrenzen (~* '\mwort\M'). Weniger
                       Zufall, verliert dafuer die Komposita-Treffer, die in
                       diesem deutschen Bestand haeufig sind.
      kurzfeld         Suche im KURZEN Feld (Titel+Zusammenfassung bzw.
                       description) statt im Volltext. Das ist der Text, den
                       der Abruf spaeter tatsaechlich einspielt.
      kurz_gewichtet   Suche im Volltext, aber Rang nach Treffern im kurzen
                       Feld -- ein Treffer im Titel wiegt schwerer als einer
                       auf Seite drei.
                       GEMESSEN 2026-08-11: liefert auf diesem Bestand exakt
                       dasselbe wie 'kurzfeld' -- 35 von 35 Faellen identisch,
                       und auch bei Deckel 50 kein einziger zusaetzlicher
                       Kandidat. Der Grund liegt im Bestand, nicht im SQL: das
                       kurze Feld ist hier Teil des Volltextes, also findet die
                       weitere Bedingung dieselben Zeilen, und der Rang nach
                       kurz-Treffern sortiert sie gleich. Die Variante bleibt
                       stehen, weil sie sich bei einem Bestand mit laengeren
                       Volltexten trennen WUERDE -- aber sie zaehlt heute nicht
                       als eigene Messung.

    Rang immer: erst wie viele Stichworte vorkommen, dann Wortaehnlichkeit.
    Bewusst NICHT dasselbe Mass wie FTS5s rank (BM25-artig) -- ein
    Rangunterschied ist deshalb erwartbar und kein Fehler.
    """
    if variante not in VARIANTEN:
        raise ValueError(f"unbekannte Variante {variante!r}, erlaubt: {', '.join(VARIANTEN)}")

    def suche(worte: list[str], deckel: int) -> list[str]:
        if not worte:
            return {"knoten": [], "lehre": []}
        einzelworte = [w for w in worte if w.isalnum()]
        muster = " ".join(einzelworte)
        if not muster:
            return {"knoten": [], "lehre": []}

        feld = "kurz" if variante == "kurzfeld" else "text"
        rangfeld = "kurz" if variante in ("kurzfeld", "kurz_gewichtet") else "text"

        if variante == "wortgrenze":
            bedingung = " OR ".join(f"text ~* ('\\m' || $${w}$$ || '\\M')" for w in einzelworte)
            treffer = " + ".join(f"(text ~* ('\\m' || $${w}$$ || '\\M'))::int" for w in einzelworte)
        else:
            bedingung = " OR ".join(f"{feld} ILIKE '%' || $${w}$$ || '%'" for w in einzelworte)
            treffer = " + ".join(f"({rangfeld} ILIKE '%' || $${w}$$ || '%')::int" for w in einzelworte)

        ergebnis: dict[str, list[str]] = {"knoten": [], "lehre": []}
        for art in ("knoten", "lehre"):
            sql = (
                f"SELECT id FROM suchtext "
                f"WHERE art = '{art}' AND ({bedingung}) "
                f"ORDER BY ({treffer}) DESC, "
                f"word_similarity($${muster}$$, {rangfeld}) DESC, id "
                f"LIMIT {int(deckel)}"
            )
            roh = subprocess.run([PSQL, "-d", dsn, "-tAc", sql],
                                  capture_output=True, text=True)
            if roh.returncode != 0:
                raise RuntimeError(f"psql fehlgeschlagen: {roh.stderr.strip()[:200]}")
            ergebnis[art] = [z for z in roh.stdout.split() if z]
        return ergebnis

    return suche


def _selftest() -> None:
    """Netzlos nicht moeglich -- diese Datei IST der Zugang zur fremden
    Datenbank. Der Selbsttest prueft deshalb nur, was ohne sie pruefbar ist:
    dass eine leere Wortliste keine Anfrage stellt."""
    suche = suche_bauen("gibtsnicht")
    leer = {"knoten": [], "lehre": []}
    assert suche([], 10) == leer
    assert suche(["!!!"], 10) == leer
    print("selftest ok (2 Faelle, ohne Datenbank pruefbar)")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
