"""Deckt messungen/okkultation.py fuer die volle Suite ab -- vor allem die
Regression vom 2026-08-13: eine Projektwurzel wie '/brainlehr' darf nicht
ueber ihr 'Endstueck' (der Projektname selbst) als Zieltreffer zaehlen, weil
der in praktisch jeder Antwort ueber das Projekt vorkommt. Im echten Lauf
zeigte sich das als Fehlalarm in der NEG-Bedingung (Fremdblock 'traf'
angeblich das Ziel, tatsaechlich nur ueber das Wort 'brainlehr-interne').

Rot-Probe: vor dem Fix (Endstueck-Fallback ohne Ausnahme fuer Projektwurzeln)
war test_projektwurzel_kein_fehlalarm rot -- die Antwort "Das ist eine
brainlehr-interne Messaufgabe ohne Bezug." traf faelschlich auf
{"id": "/brainlehr"}.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "messungen")]

import okkultation as ok  # noqa: E402


def test_zieltreffer_voller_pfad():
    assert ok._ziel_treffer("siehe /a/b/c fuer Details",
                             [{"art": "knoten", "id": "/a/b/c"}])


def test_zieltreffer_endstueck():
    assert ok._ziel_treffer("Datei heisst existenzpruefung.py",
                             [{"art": "knoten", "id": "haken/existenzpruefung.py"}])


def test_zieltreffer_fehlschlag():
    assert not ok._ziel_treffer("nichts Passendes hier",
                                 [{"art": "knoten", "id": "/x/y/z"}])


def test_zieltreffer_grenzwert_zu_kurz():
    # Grenzwert: ein 2-Zeichen-Endstueck (<4) darf nicht faelschlich treffen.
    assert not ok._ziel_treffer("ab", [{"art": "knoten", "id": "/x/ab"}])


def test_projektwurzel_kein_fehlalarm():
    """Rot vor dem Fix (2026-08-13): traf faelschlich ueber das blosse
    Wort 'brainlehr', ganz ohne dass der Zielknoten gemeint war."""
    assert not ok._ziel_treffer(
        "Das ist eine brainlehr-interne Messaufgabe ohne Bezug.",
        [{"art": "knoten", "id": "/brainlehr"}])


def test_projektwurzel_echter_treffer_bleibt_moeglich():
    # Gegenprobe: der volle Pfad trifft weiterhin, nur das blosse Endstueck nicht.
    assert ok._ziel_treffer("siehe /brainlehr fuer Details",
                             [{"art": "knoten", "id": "/brainlehr"}])


def test_format_block_enthaelt_knoten_und_lehre():
    block = ok.format_block(
        [{"path": "/a/b", "title": "T", "summary": "S", "updated_at": None}],
        [{"id": "L-aaaaaa", "severity": "low", "type": "insight",
          "occurrences": 1, "description": "D", "prevention": None}],
    )
    assert "<knowledge-recall>" in block and "/a/b" in block and "L-aaaaaa" in block


def _synthetische_aufgaben() -> dict:
    return {"schiefe_gegenprobe": {"drei_haeufigste_anteil": 0.1}, "zellen": [
        {"key": "m1-00|MIT", "gruppe": "M1", "case_id": "m1-00", "condition": "MIT",
         "ziele": [{"art": "knoten", "id": "/x/y"}],
         "prompt": "Frage\n\n<knowledge-recall>\n- [/x/y] ...\n</knowledge-recall>"},
        {"key": "m1-00|OHNE", "gruppe": "M1", "case_id": "m1-00", "condition": "OHNE",
         "ziele": [{"art": "knoten", "id": "/x/y"}]},
        {"key": "m1-00|NEG", "gruppe": "M1", "case_id": "m1-00", "condition": "NEG",
         "ziele": [{"art": "knoten", "id": "/x/y"}]},
        {"key": "m2-00|MIT", "gruppe": "M2", "case_id": "m2-00", "condition": "MIT", "ziele": None},
        {"key": "m2-00|OHNE", "gruppe": "M2", "case_id": "m2-00", "condition": "OHNE", "ziele": None},
    ]}


def test_auswerten_drei_bedingungen_und_lieferanalyse():
    aufgaben = _synthetische_aufgaben()
    # Seit 2026-08-13 ist `werkzeuge_benutzt` Pflicht: eine Antwort ohne das
    # Feld koennte ueber ein Suchwerkzeug doch an den Speicher gekommen sein,
    # und die OHNE-Bedingung waere wertlos. Fail-closed, siehe den Test
    # darunter.
    antworten = {"antworten": {
        "m1-00|MIT": {"antwort": "Ich stuetze mich auf /x/y, das passt genau.",
                      "werkzeuge_benutzt": False},
        "m1-00|OHNE": {"antwort": "Ich rate auf gut Glueck, kein Anhaltspunkt.",
                       "werkzeuge_benutzt": False},
        "m1-00|NEG": {"antwort": "Der fremde Block handelt von etwas anderem, ich rate.",
                      "werkzeuge_benutzt": False},
        "m2-00|MIT": {"antwort": "Ja, das ist moeglich, siehe die genannte Einschraenkung.",
                      "werkzeuge_benutzt": False},
        "m2-00|OHNE": {"antwort": "Ja, das ist grundsaetzlich moeglich.",
                       "werkzeuge_benutzt": False},
    }}
    erg = ok.auswerten(aufgaben, antworten)
    assert erg["m1"]["MIT"]["treffer"] == 1 and erg["m1"]["MIT"]["n"] == 1
    assert erg["m1"]["OHNE"]["treffer"] == 0
    assert erg["m1"]["NEG"]["treffer"] == 0
    assert erg["m2"]["faelle_mit_mit_bedingung"] == 1
    la = erg["m1"]["liefer_analyse"]
    assert la["geliefert_gesamt"] == 1 and la["geliefert_und_benutzt"] == 1


def test_auswerten_fehlbestand_wird_nicht_still_uebergangen():
    aufgaben = _synthetische_aufgaben()
    luecke = ok.auswerten(aufgaben, {"antworten": {
        "m1-00|MIT": "x", "m1-00|OHNE": "y",
        "m2-00|MIT": "a", "m2-00|OHNE": "b"}})
    assert "m1-00|NEG" in luecke["m1"]["fehlbestand"]


def test_m1_pool_schliesst_kennung_aus():
    """Selbstbezug-Ausschluss (s. Modulkopf okkultation.py): Faelle, deren
    Ziel-Kennung woertlich im Aufgabentext steht, duerfen nicht in den
    M1-Pool -- sonst koennte eine Antwort die Kennung einfach abschreiben,
    unabhaengig von MIT/OHNE."""
    if not ok.M1_QUELLE.exists():
        return  # Datenquelle liegt in dieser Umgebung nicht vor -- kein Fall.
    pool = ok.m1_pool()
    assert pool, "M1-Pool ist leer -- Datenquelle pruefen"
    assert all(f["klasse"] in ok.M1_ERLAUBTE_KLASSEN for f in pool)
    assert not any(f["klasse"] == "kennung" for f in pool)


def test_selftest_laeuft_durch():
    ok._selftest()


def test_antwort_ohne_werkzeugfeld_geht_nicht_in_die_quote():
    """Das Altformat -- ein nackter String ohne Angabe zur Werkzeugnutzung --
    darf NICHT stillschweigend als "kein Werkzeug benutzt" gelesen werden.

    Der Grund ist der Kern der ganzen Messung: Holt sich die antwortende
    Instanz das Wissen waehrend der OHNE-Bedingung ueber ein Suchwerkzeug,
    bekommt sie es auf einem zweiten Weg, und der Vergleich MIT gegen OHNE
    misst nichts mehr. Fail-open waere hier also nicht bequem, sondern falsch.

    Dieser Test ist zugleich die Ratsche dagegen, dass jemand die Pruefung
    spaeter wieder aufweicht, weil alte Antwortdateien nicht mehr durchlaufen.
    Sie sollen nicht durchlaufen -- ihre Werkzeugnutzung ist unbekannt.
    """
    aufgaben = _synthetische_aufgaben()
    alt = {"antworten": {
        "m1-00|MIT": "Ich stuetze mich auf /x/y, das passt genau.",
        "m1-00|OHNE": "Ich rate auf gut Glueck.",
        "m1-00|NEG": "Ich rate.",
    }}
    erg = ok.auswerten(aufgaben, alt)
    assert erg["m1"]["MIT"]["n"] == 0
    assert erg["m1"]["MIT"]["anteil"] is None
    assert erg["m1"]["MIT"]["hinweis"] == "keine verwertbaren Zellen"
    # Und die Zahl der ausgeschlossenen Zellen wird GENANNT, nicht verschwiegen
    # -- eine stille Kuerzung sieht in der Auswertung aus wie Vollstaendigkeit.
    assert len(erg["m1"]["werkzeug_ausgeschlossen"]) == 3


def test_werkzeugnutzung_ausdruecklich_verneint_geht_normal_ein():
    """Gegenrichtung, sonst wuerde der Test darueber auch bei einer Pruefung
    bestehen, die schlicht ALLES ausschliesst."""
    aufgaben = _synthetische_aufgaben()
    sauber = {"antworten": {
        "m1-00|MIT": {"antwort": "Ich stuetze mich auf /x/y.", "werkzeuge_benutzt": False},
        "m1-00|OHNE": {"antwort": "Ich rate.", "werkzeuge_benutzt": False},
        "m1-00|NEG": {"antwort": "Ich rate.", "werkzeuge_benutzt": False},
    }}
    erg = ok.auswerten(aufgaben, sauber)
    assert erg["m1"]["MIT"]["n"] == 1 and erg["m1"]["MIT"]["treffer"] == 1
    assert erg["m1"]["werkzeug_ausgeschlossen"] == []
