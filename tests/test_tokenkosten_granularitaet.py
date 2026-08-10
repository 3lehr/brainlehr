"""Guard: niemand darf die vier Tokenspalten von access_log stillschweigend
als 0 lesen (Auftrag 2026-08-08, Entscheidung in tokenkosten.py).

ROT VOR DIESER ÄNDERUNG: tokenkosten.py existierte nicht -- dieses Modul und
dieser Test sind neu. Der Negativfall (fehlendes Feld -> None statt 0) ist
der eigentliche Beleg; ohne ihn wäre `sum((None, 1, 2))` ein TypeError statt
einer stillen Falschzahl, aber ein `or 0`-Leser würde den Fehler genauso
verschlucken -- deshalb prüft dieser Test die Funktion, nicht nur, dass sie
nicht crasht.
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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tokenkosten import fuellstand_zeile  # noqa: E402


def test_drei_fuellstandsspalten_addieren_sich():
    zeile = {"tokens_input": 2, "tokens_cache_creation": 718, "tokens_cache_read": 923054, "tokens_output": 999999}
    assert fuellstand_zeile(zeile) == 2 + 718 + 923054


def test_output_zaehlt_nicht_mit():
    mit_output = {"tokens_input": 10, "tokens_cache_creation": 10, "tokens_cache_read": 10, "tokens_output": 500}
    ohne_output = {"tokens_input": 10, "tokens_cache_creation": 10, "tokens_cache_read": 10}
    assert fuellstand_zeile(mit_output) == fuellstand_zeile(ohne_output) == 30


def test_fehlendes_feld_erzeugt_keine_0():
    """Negativfall: NULL (fehlend) und 0 (gemessen, keine Kosten) sind
    verschiedene Aussagen. Eine 0 hier wäre die falsche Aussage."""
    for fehlt in ("tokens_input", "tokens_cache_creation", "tokens_cache_read"):
        zeile = {"tokens_input": 1, "tokens_cache_creation": 1, "tokens_cache_read": 1}
        zeile[fehlt] = None
        assert fuellstand_zeile(zeile) is None, f"fehlendes {fehlt} wurde als 0 gelesen"


def test_alle_felder_fehlen():
    assert fuellstand_zeile({}) is None


def test_echte_nullen_bleiben_von_fehlend_unterscheidbar():
    assert fuellstand_zeile({"tokens_input": 0, "tokens_cache_creation": 0, "tokens_cache_read": 0}) == 0
