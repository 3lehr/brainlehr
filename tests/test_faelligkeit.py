#!/usr/bin/env python3
"""Der Faelligkeitskanal: was raus muss, unabhaengig von der Frage.

ANLASS, Betreiber 2026-08-20: "wenn die frist abgelaufen ist und vom
chat/user noch nie abgefragt wurde sollte sie mit prio zum pruefen
eingespielt werden? ... wichtige dinge und oder dinge welche direkte
auswirkungen haben nichtbeachten teurer wird sollten schon frueher
eingespielt werden".

Er trifft damit denselben Punkt wie die Alarmmedizin im Konsil desselben
Tages (IEC 60601-1-8): Die Prioritaet eines Alarms kommt aus SCHADENSFOLGE,
nie aus der Messsicherheit. Ein Monitor piepst nicht lauter, weil der Sensor
sicherer ist.

GEMESSEN am 2026-08-20, und das ist die Grundlage: Von allen geprueften
Groessen trennen genau zwei aufgegriffene von nie aufgegriffenen Eintraegen,
und beide sind Schadensmasse -- severity (critical 42,4 % > high 37,5 % >
medium 22,8 % > low 12,0 %) und occurrences (1x 26,2 % < 2-3x 59,4 %). Kein
Aehnlichkeitsmass hat an diesem Tag irgendetwas getrennt (drei Verfahren,
drei Nullbefunde).

DIE VIER KLASSEN, mit ihren gemessenen Bestandszahlen:
  Norm nie gelesen                       100
  Lehre high/critical, 2+ Vorkommen       68
  Lehre auf Regelrang eskaliert           30
  Knoten mit abgelaufener Geltung          2

ALARMMUEDIGKEIT ist die Hauptgefahr, nicht die Auswahl: Ein Kanal, der
taeglich dieselben sechs Eintraege zeigt, wird in einer Woche ueberlesen --
und dann wirkt auch der wichtige nicht mehr. Deshalb Rotation, und deshalb
ein sehr kleiner Deckel: dieser Melder kommt zu vierzehn anderen
Startmeldern hinzu.

ROT VOR GRUEN: Jeder Fall unten faellt gegen den Stand davor mit
ModuleNotFoundError -- melder/faelligkeit.py existiert dort nicht.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "melder")]

import pytest  # noqa: E402

import faelligkeit  # noqa: E402


def _k(kennung, art="norm_nie_gelesen", titel="Titel", schwere="high"):
    return {"kennung": kennung, "art": art, "titel": titel, "schwere": schwere}


def test_deckel_haelt():
    """Hoechstens MAX_ZEILEN, egal wieviele Kandidaten es gibt."""
    kandidaten = [_k(f"L-{i:06d}") for i in range(200)]
    zeilen = faelligkeit.auswahl(kandidaten, tagesnummer=0)
    assert len(zeilen) <= faelligkeit.MAX_ZEILEN, len(zeilen)


def test_rotation_zeigt_ueber_tage_verschiedene():
    """Der Kern gegen Alarmmuedigkeit: an zwei Tagen NICHT dieselben.

    Ohne das zeigt der Kanal 200 Kandidaten lang immer die ersten drei --
    und der Rest wird nie gesehen, egal wie dringend er ist."""
    kandidaten = [_k(f"L-{i:06d}") for i in range(200)]
    tag1 = {z["kennung"] for z in faelligkeit.auswahl(kandidaten, tagesnummer=0)}
    tag2 = {z["kennung"] for z in faelligkeit.auswahl(kandidaten, tagesnummer=1)}
    assert tag1 != tag2, (tag1, tag2)


def test_rotation_deckt_ueber_zeit_alles_ab():
    """Jeder Kandidat kommt irgendwann dran -- sonst ist die Rotation nur
    Abwechslung und kein Durchlauf."""
    kandidaten = [_k(f"L-{i:06d}") for i in range(9)]
    gesehen = set()
    for tag in range(9):
        gesehen |= {z["kennung"] for z in faelligkeit.auswahl(kandidaten, tagesnummer=tag)}
    assert gesehen == {k["kennung"] for k in kandidaten}, sorted(gesehen)


def test_gleicher_tag_gleiche_auswahl():
    """Zustandslos und wiederholbar: zweimal am selben Tag gefragt gibt
    dasselbe. Ein Melder, der bei jedem Aufruf etwas anderes zeigt, ist
    nicht nachpruefbar."""
    kandidaten = [_k(f"L-{i:06d}") for i in range(50)]
    a = faelligkeit.auswahl(kandidaten, tagesnummer=7)
    b = faelligkeit.auswahl(kandidaten, tagesnummer=7)
    assert a == b


def test_schwerere_klasse_zuerst():
    """Reihenfolge nach SCHADENSFOLGE, nicht nach Alphabet oder Zufall --
    das ist der ganze Punkt des Kanals."""
    kandidaten = [
        _k("L-leicht", art="norm_nie_gelesen", schwere="medium"),
        _k("L-schwer", art="lehre_wiederholt", schwere="critical"),
    ]
    zeilen = faelligkeit.auswahl(kandidaten, tagesnummer=0)
    assert zeilen[0]["kennung"] == "L-schwer", zeilen


def test_leer_bleibt_still():
    """NEGATIVFALL: Ohne Kandidaten kein Wort. Der fuenfzehnte Startmelder,
    der immer redet, waere einer zu viel."""
    assert faelligkeit.auswahl([], tagesnummer=0) == []
    assert faelligkeit.melde([], tagesnummer=0) == ""


def test_meldung_nennt_grund_und_gesamtzahl():
    """Eine Zeile ohne Grund ist eine Aufforderung ohne Begruendung -- und
    die Gesamtzahl verhindert den Eindruck, es seien nur diese drei."""
    kandidaten = [_k(f"L-{i:06d}") for i in range(40)]
    text = faelligkeit.melde(kandidaten, tagesnummer=0)
    assert "40" in text, text
    assert any(w in text for w in ("nie gelesen", "wiederholt", "Regelrang", "Geltung")), text


def test_zeit_wird_hereingereicht_nicht_gelesen():
    """Die Tagesnummer ist ein PARAMETER. Ein Melder, der die Uhr selbst
    liest, ist nicht pruefbar -- und ein Test mit festem Datum altert weg
    (L-cdce13, am selben Tag an einer anderen Datei passiert)."""
    import inspect
    sig = inspect.signature(faelligkeit.auswahl)
    assert "tagesnummer" in sig.parameters, sig


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_schwerste_klasse_kommt_jeden_tag_dran():
    """DER FEHLER, DER IM ECHTEN LAUF SICHTBAR WURDE.

    Die erste Fassung rotierte EIN Fenster ueber die nach Schwere sortierte
    Gesamtliste. Bei 179 Kandidaten, davon 30 auf Regelrang, landete das
    Fenster an rund 83 Prozent der Tage ausserhalb der schweren Klassen --
    gemessen am 2026-08-20 zeigten Tag und Folgetag ausschliesslich
    `norm_nie_gelesen`, die SCHWAECHSTE Klasse.

    Damit war die Ordnung nach Schadensfolge zwar vorhanden und wirkungslos:
    genau das Gegenteil der Betreiberforderung, dass Dinge mit direkter
    Auswirkung frueher kommen. Die Rotation muss JE KLASSE laufen, nicht
    ueber die Gesamtliste."""
    kandidaten = ([_k(f"L-regel{i}", art="lehre_regelrang", schwere="high") for i in range(30)]
                  + [_k(f"L-wied{i}", art="lehre_wiederholt", schwere="high") for i in range(47)]
                  + [_k(f"/n/{i}", art="norm_nie_gelesen", schwere="medium") for i in range(100)])
    for tag in range(40):
        arten = {z["art"] for z in faelligkeit.auswahl(kandidaten, tagesnummer=tag)}
        assert "lehre_regelrang" in arten, (tag, arten)


def test_auch_die_schwache_klasse_kommt_vor():
    """NEGATIVFALL zur Gegenrichtung: Die schwerste Klasse darf die anderen
    nicht dauerhaft verdraengen -- sonst sind die 100 ungelesenen Normen nach
    dem Umbau unerreichbar, und der Kanal hat nur sein Problem getauscht.

    MIT ALLEN VIER KLASSEN, und genau daran faellt die zweite Fassung: Bei
    vier Klassen und drei Plaetzen bekommt die schwaechste NIE einen -- im
    echten Bestand sind das 100 von 179 Kandidaten, also die Mehrheit."""
    kandidaten = ([_k(f"L-regel{i}", art="lehre_regelrang", schwere="high") for i in range(30)]
                  + [_k(f"L-wied{i}", art="lehre_wiederholt", schwere="high") for i in range(47)]
                  + [_k(f"/g/{i}", art="geltung_abgelaufen", schwere="high") for i in range(2)]
                  + [_k(f"/n/{i}", art="norm_nie_gelesen", schwere="medium") for i in range(100)])
    gesehen = set()
    for tag in range(10):
        gesehen |= {z["art"] for z in faelligkeit.auswahl(kandidaten, tagesnummer=tag)}
    assert "norm_nie_gelesen" in gesehen, gesehen
    # Und die schwerste bleibt trotzdem JEDEN Tag dabei -- die Loesung darf
    # nicht sein, dass jetzt reihum alle mal wegfallen.
    for tag in range(10):
        arten = {z["art"] for z in faelligkeit.auswahl(kandidaten, tagesnummer=tag)}
        assert "lehre_regelrang" in arten, (tag, arten)


def test_rotation_je_klasse_deckt_die_klasse_ab():
    """Innerhalb einer Klasse kommt weiterhin jeder dran."""
    kandidaten = [_k(f"L-regel{i}", art="lehre_regelrang", schwere="high") for i in range(6)]
    gesehen = set()
    for tag in range(12):
        gesehen |= {z["kennung"] for z in faelligkeit.auswahl(kandidaten, tagesnummer=tag)}
    assert gesehen == {k["kennung"] for k in kandidaten}, sorted(gesehen)
