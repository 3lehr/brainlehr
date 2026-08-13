"""Deckt kern/pruefkorpus_rivalen.py ab (AUFGABE 68, Nachbesserung):
Determinismus, Negativfall bei veraendertem Bestand, belegte Rivalinnen im
ECHTEN Bedeutungskanal (Einbettungs-Kosinus, nicht mehr Jaccard), Negativfall
bei fehlendem Vektor, nachschlagewerk niemals Ziel. Wiederholt die Faelle aus
dessen eigenem _selftest() als pytest-Funktionen (repo-weite Konvention:
Modul-Selftest UND pytest-Datei, siehe tests/test_pruefkorpus.py), damit die
volle Suite sie mitzieht statt nur ein manueller Aufruf.

Rot-Probe: vor dieser Datei existierte kern/pruefkorpus_rivalen.py nicht --
jeder Test hier war vor dem Bau zwangslaeufig rot (ImportError). Fuer die
Nachbesserung war die Rot-Probe die alte Jaccard-Messung selbst: Median
0,108 ueber 202 echte Faelle, siehe Modulkopf von pruefkorpus_rivalen.py.
"""
from __future__ import annotations

import json
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import pruefkorpus_rivalen as pr  # noqa: E402


def test_determinismus_gleiche_eingaben_gleiche_ausgabe():
    nodes, lessons = pr._fake_bestand()
    quelle = pr._fake_quelle()
    node_vek, lesson_vek = pr._fake_vektoren()
    a, ua = pr.baue(nodes, lessons, quelle, node_vek, lesson_vek)
    b, ub = pr.baue(nodes, lessons, quelle, node_vek, lesson_vek)
    assert a == b
    assert ua == ub
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_negativfall_veraendertes_bestand_ergibt_anderen_korpus():
    nodes, lessons = pr._fake_bestand()
    quelle = pr._fake_quelle()
    node_vek, lesson_vek = pr._fake_vektoren()
    basis, _ = pr.baue(nodes, lessons, quelle, node_vek, lesson_vek)

    nodes_veraendert = nodes + [{
        "path": "/a/stroke-naeher", "title": "Akuter Schlaganfall",
        "summary": "Sprachstoerung und haengender Mundwinkel akut, Notruf 112 sofort.",
        "content": "", "gattung": "arbeitsbestand"}]
    node_vek_veraendert = dict(node_vek, **{"/a/stroke-naeher": [20.0, 1.0, 0.0]})
    veraendert, _ = pr.baue(nodes_veraendert, lessons, quelle, node_vek_veraendert, lesson_vek)

    assert veraendert != basis, "eingefroren statt deterministisch"
    ziel_basis = next(f for f in basis if f["target_id"] == "/a/stroke")
    ziel_veraendert = next(f for f in veraendert if f["target_id"] == "/a/stroke")
    assert ziel_basis["ablenker_id"] != ziel_veraendert["ablenker_id"]
    assert ziel_veraendert["ablenker_id"] == "/a/stroke-naeher"


def test_rivalinnen_belegt_mit_plausibler_aehnlichkeit():
    nodes, lessons = pr._fake_bestand()
    quelle = pr._fake_quelle()
    node_vek, lesson_vek = pr._fake_vektoren()
    faelle, _ = pr.baue(nodes, lessons, quelle, node_vek, lesson_vek)
    mit_ablenker = [f for f in faelle if f["ablenker_id"]]
    assert mit_ablenker
    for f in mit_ablenker:
        assert 0.0 < f["ablenker_aehnlichkeit"] <= 1.0


def test_negativfall_ziel_ohne_vektor_bekommt_keinen_ablenker_wird_aber_gezaehlt():
    """Abnahme 3 der Nachbesserung: kein Vektor -> kein Ablenker, aber der
    Fall bleibt im Korpus (uebersprungen zaehlt nur unzulaessige Ziele, siehe
    test_nachschlagewerk_niemals_ziel -- eine fehlende Einbettung ist kein
    unzulaessiges Ziel)."""
    nodes, lessons = pr._fake_bestand()
    quelle = pr._fake_quelle()
    node_vek, lesson_vek = pr._fake_vektoren()
    mit_vektor, _ = pr.baue(nodes, lessons, quelle, node_vek, lesson_vek)
    ohne_vektor, uebersprungen_ohne = pr.baue(nodes, lessons, quelle)

    assert len(ohne_vektor) == len(mit_vektor), "Fall ohne Vektor wurde nicht gezaehlt"
    ziel = next(f for f in ohne_vektor if f["target_id"] == "/a/stroke")
    assert ziel["ablenker_id"] is None
    assert ziel["ablenker_kind"] is None
    assert ziel["ablenker_aehnlichkeit"] == 0.0


def test_nachschlagewerk_niemals_ziel():
    nodes, lessons = pr._fake_bestand()
    quelle = pr._fake_quelle()
    node_vek, lesson_vek = pr._fake_vektoren()
    faelle, uebersprungen = pr.baue(nodes, lessons, quelle, node_vek, lesson_vek)
    assert "/a/nachschlage" not in {f["target_id"] for f in faelle}
    assert uebersprungen >= 1


def test_nachschlagewerk_darf_ablenker_sein():
    """Heuhaufen bleibt Heuhaufen: als Ziel verboten (siehe oben), als
    Ablenker ist es genau seine vorgesehene Rolle -- kein Ausschluss dafuer
    im Code (naechster_nachbar_bedeutung() filtert nur ausgeschlossene
    ids/self, nicht nach gattung)."""
    nodes = [
        {"path": "/z/ziel", "title": "Alarm", "summary": "roter Alarmknopf drueckt Notaus.",
         "content": "", "gattung": "arbeitsbestand"},
        {"path": "/z/heuhaufen", "title": "Alarm Handbuch",
         "summary": "roter Alarmknopf, Notaus, Handbuchkapitel 4.",
         "content": "", "gattung": "nachschlagewerk"},
    ]
    node_vek = {"/z/ziel": [1.0, 0.0], "/z/heuhaufen": [0.9, 0.1]}
    quelle = {"faelle": [{"prompt": "roter Alarmknopf Notaus wo",
                           "ziele": [{"art": "knoten", "id": "/z/ziel"}]}]}
    faelle, _ = pr.baue(nodes, [], quelle, node_vek, {})
    assert faelle[0]["ablenker_id"] == "/z/heuhaufen"


def test_naechster_nachbar_bedeutung_numpy_und_python_liefern_gleiches_ergebnis():
    """Dieselbe Bauform wie kern/kanten_aus_bedeutung.py -- numpy-Pfad und
    reiner Python-Rueckfall (embeddings.cosine_similarity) muessen fuer
    dieselben Vektoren dasselbe Ergebnis liefern, nicht nur "irgendeins"."""
    vektoren = {
        "/a": [1.0, 0.0, 0.0],
        "/b": [10.0, 3.0, 0.0],
        "/c": [0.0, 0.0, 5.0],
        "/d": [1.0, 1.0, 3.0],
    }
    mit_numpy = pr.naechster_nachbar_bedeutung("/a", vektoren, set())
    assert pr._np is not None, "numpy ist laut Auftrag 87 installiert -- Test setzt das voraus"

    pr._np, gesichert = None, pr._np
    try:
        ohne_numpy = pr.naechster_nachbar_bedeutung("/a", vektoren, set())
    finally:
        pr._np = gesichert

    assert mit_numpy[0] == ohne_numpy[0]
    assert abs(mit_numpy[1] - ohne_numpy[1]) < 1e-9
