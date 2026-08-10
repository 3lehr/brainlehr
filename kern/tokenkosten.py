"""tokenkosten.py — sicherer Lesezugriff auf die vier Tokenspalten von access_log.

ANLASS (Auftrag 2026-08-08, Knoten /brainlehr/wiedervorlage-warum-vier-tokenspalten):
Alle 2167 access_log-Zeilen der Betriebs-DB haben tokens_input/tokens_output/
tokens_cache_creation/tokens_cache_read NULL. Kein Schreiber existiert.

GEMESSEN am echten Transcript dieser Sitzung (79fd74ff-1bc9-40d4-a606-
efb0ad79820b): 413 Anfragen (usage-Zeilen im Transcript) gegen 12 access_log-
Zeilen derselben Sitzung im selben Zeitraum -- und die 12 kamen als sechs
zeitgleiche Paare (status started/completed je Werkzeugaufruf), nicht als
zwoelf unabhaengige Zeitpunkte.

DIE KOERNUNG PASST NICHT: eine access_log-Zeile entsteht pro WISSENSZUGRIFF
(ein MCP-Werkzeugaufruf), eine Tokenzahl pro MODELLANFRAGE. Ein Zug des
Modells kann mehrere Werkzeugaufrufe parallel ausloesen (mehrere access_log-
Zeilen, eine Anfrage) oder gar keinen (eine Anfrage, keine access_log-Zeile).
Ein Schreiber, der die zeitlich naechste Anfrage per Zeitstempel raet, waere
zudem durch Client-UTC vs. DB-Localtime (+02:00) und doppelt geloggte
Zwischen-usage-Zeilen im Transcript zusaetzlich verfaelscht -- eine erfundene
Zuordnung, keine gemessene.

ENTSCHEIDUNG: kein Zeilen-Schreiber für access_log. Die vier Spalten bleiben
NULL, bis es eine eigene Tabelle je Modellanfrage gibt (nicht Teil dieses
Auftrags). Diese Datei ist nur die Sicherung dagegen, dass jemand NULL
stillschweigend als 0 liest -- 0 heisst "gemessen, keine Kosten", NULL heisst
"nicht gemessen". Eine Summe ueber unvollstaendige Zeilen taeuscht
Vollstaendigkeit vor.
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


def fuellstand_zeile(zeile: dict) -> int | None:
    """Fuellstand EINER access_log-Zeile: tokens_input + tokens_cache_creation
    + tokens_cache_read. output_tokens zaehlt bewusst NICHT mit (die Antwort
    wird erst bei der naechsten Anfrage Teil des Inputs).

    None, wenn eines der drei Felder fehlt -- NIE stillschweigend als 0
    gewertet, sonst waere eine ungemessene Zeile von einer echten
    Null-Kosten-Zeile nicht mehr zu unterscheiden."""
    teile = (zeile.get("tokens_input"), zeile.get("tokens_cache_creation"), zeile.get("tokens_cache_read"))
    if any(t is None for t in teile):
        return None
    return sum(teile)  # type: ignore[misc]


def demo() -> None:
    # Gemessenes Beispiel aus /brainlehr/wiedervorlage-warum-vier-tokenspalten
    voll = {"tokens_input": 2, "tokens_cache_creation": 718, "tokens_cache_read": 923054, "tokens_output": 300}
    assert fuellstand_zeile(voll) == 923774, "die drei Fuellstands-Spalten muessen sich addieren lassen"
    assert fuellstand_zeile(voll) != 923774 + 300, "output_tokens darf NICHT mitgezaehlt werden"

    unvollstaendig = {"tokens_input": None, "tokens_cache_creation": 718, "tokens_cache_read": 923054}
    assert fuellstand_zeile(unvollstaendig) is None, "fehlendes Feld darf keine 0 erzeugen"

    echte_null = {"tokens_input": 0, "tokens_cache_creation": 0, "tokens_cache_read": 0}
    assert fuellstand_zeile(echte_null) == 0, "echte Nullen bleiben von fehlenden Feldern unterscheidbar"

    print("ok")


if __name__ == "__main__":
    demo()
