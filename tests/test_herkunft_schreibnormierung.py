"""Aufgabe 79, Schritt 1: Modell- und Akteursnamen werden beim SCHREIBEN
vereinheitlicht -- speicher.normiere_modell() / speicher.normiere_akteur().

FAKTEN (gemessen 2026-08-13 ueber kern/speicher.lesen()), die dieser Test
woertlich verwendet: 'claude-opus-5' (1256x), 'Anthropic/claude-opus-5'
(12x), bei Knoten zusaetzlich 'Anthropic/Opus 5' (1x) -- drei Schreibweisen
fuer ein Modell. Daneben zwei Arten von Nichtwissen: der Text 'unbekannt'
und NULL.

Diese Datei prueft nur die reinen Funktionen -- keine Datenbank noetig,
kein eigenes sqlite3.connect (verboten, siehe test_naht_ratsche.py)."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]
_sys.path.insert(0, str(_w / "kern"))

import speicher  # noqa: E402


def test_drei_schreibweisen_werden_eine_gruppe():
    """VORHER (ohne Normierung) liefert eine Gruppierung nach Rohwert drei
    Gruppen fuer die drei echten Zeichenketten aus dem Bestand -- NACHHER
    (normiert) genau eine."""
    roh = ["claude-opus-5", "Anthropic/claude-opus-5", "Anthropic/Opus 5"]
    assert len(set(roh)) == 3, "die drei Rohwerte muessen sich vorher unterscheiden"

    normiert = [speicher.normiere_modell(w) for w in roh]
    assert len(set(normiert)) == 1, normiert
    assert normiert[0] == "claude-opus-5"


def test_fremdmodell_wird_nicht_mit_zusammengezogen():
    """NEGATIVFALL: ein echtes Fremdmodell darf nicht auf Opus 5 (oder
    irgendetwas anderes) abgebildet werden -- sonst waere die Funktion nur
    eine, die alles auf einen Wert zusammenzieht."""
    for fremd in ("gemma4:12b", "bge-m3"):
        assert speicher.normiere_modell(fremd) == fremd


def test_unbekannt_wird_zu_none_wie_null():
    """'unbekannt' und None sind danach dieselbe Sache -- eine Zaehlung
    kennt nur noch EINE Art von Nichtwissen."""
    assert speicher.normiere_modell("unbekannt") is None
    assert speicher.normiere_modell(None) is None
    assert speicher.normiere_akteur("unbekannt") is None
    assert speicher.normiere_akteur(None) is None

    # Gegenprobe: eine Zaehlung ueber gemischten Bestand liefert nach der
    # Normierung nur noch eine Kategorie fuer Nichtwissen.
    bestand = ["unbekannt", None, "unbekannt", "claude-opus-5"]
    normiert = [speicher.normiere_modell(w) for w in bestand]
    nichtwissen_arten = {type(None) if w is None else "wert" for w in normiert}
    assert nichtwissen_arten == {type(None), "wert"}
    assert normiert.count(None) == 3


def test_leerstring_und_leerzeichen_werden_none():
    """GRENZWERT: leerer String und reine Leerzeichen zaehlen wie
    'unbekannt' als Nichtwissen, nicht als (falscher) Modell-/Akteursname."""
    assert speicher.normiere_modell("") is None
    assert speicher.normiere_modell("   ") is None
    assert speicher.normiere_akteur("") is None
    assert speicher.normiere_akteur("\t\n") is None


def test_akteur_koernungen_bleiben_getrennt():
    """Die drei im Bestand gemischten Koernungen ('claude-code',
    'claude-code/opus-5', 'normbestand.py') sind NICHT nachgewiesen
    dieselbe Sache und werden darum NICHT zusammengezogen -- nur
    'unbekannt'/Leerstring wird vereinheitlicht."""
    for wert in ("claude-code", "claude-code/opus-5", "normbestand.py"):
        assert speicher.normiere_akteur(wert) == wert


def test_bekannter_wert_bleibt_unveraendert():
    assert speicher.normiere_modell("claude-opus-5") == "claude-opus-5"
    assert speicher.normiere_akteur("claude-code") == "claude-code"


def demo() -> None:
    test_drei_schreibweisen_werden_eine_gruppe()
    test_fremdmodell_wird_nicht_mit_zusammengezogen()
    test_unbekannt_wird_zu_none_wie_null()
    test_leerstring_und_leerzeichen_werden_none()
    test_akteur_koernungen_bleiben_getrennt()
    test_bekannter_wert_bleibt_unveraendert()
    print("test_herkunft_schreibnormierung.demo ok")


if __name__ == "__main__":
    demo()
