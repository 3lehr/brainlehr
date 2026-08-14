"""Rot-vor-gruen fuer kern/domaene.py (PLAN_OPENLEHR_2026-08-14.md H8a).
Rot-Beleg fuer den Hauptfall steht als Kommentar bei der Funktion, die ihn
erzeugt hat -- siehe test_regel_ohne_beleg_wird_abgelehnt_mit_grund."""

import json

from kern.domaene import importiere

_QUELLEN = {"z1": {"bezeichnung": "Betriebsausgaben (netto)"}}


def _paket(regeln, quellen=None, **zusatz):
    basis = {
        "domaene": "steuer",
        "bezeichnung": "Steuer und Belege",
        "herkunft": "test",
        "stand": "2026-08-14T00:00:00+0200",
        "quellen": quellen if quellen is not None else _QUELLEN,
        "regeln": regeln,
    }
    basis.update(zusatz)
    return basis


def _schreibe(tmp_path, inhalt: dict | str):
    pfad = tmp_path / "paket.json"
    if isinstance(inhalt, str):
        pfad.write_text(inhalt, encoding="utf-8")
    else:
        pfad.write_text(json.dumps(inhalt), encoding="utf-8")
    return pfad


def test_paket_mit_belegter_regel_wird_angenommen(tmp_path):
    regeln = [{"id": "r1", "ziel_id": "z1", "fundstelle": "Betriebsausgaben"}]
    pfad = _schreibe(tmp_path, _paket(regeln))

    ergebnis = importiere(pfad)

    assert ergebnis == {"angenommen": True, "anzahl_regeln": 1, "grund": None}


def test_regel_ohne_beleg_wird_abgelehnt_mit_grund(tmp_path):
    """ROT-VOR-GRUEN (H8a): Paket mit einer Regel ohne belegte Fundstelle.

    Rot-Probe von Hand gefahren -- in kern/domaene.py den Aufruf
    `pruefe_regeln(regeln, quellen)` durch ein no-op ersetzt (Pruefung kurz
    entfernt) und diesen Test allein laufen lassen:
        FAILED tests/test_domaene.py::test_regel_ohne_beleg_wird_abgelehnt_mit_grund
        AssertionError: assert {'angenommen': True, 'anzahl_regeln': 1, 'grund': None} == {'angenommen': False, ...}
    Ohne die Pruefung waere eine unbelegte Regel klaglos uebernommen worden.
    Pruefung zurueckgesetzt, danach:
        1 passed in 0.02s
    """
    regeln = [{"id": "Bewirtung", "ziel_id": "z1", "fundstelle": "Erfundener Text"}]
    pfad = _schreibe(tmp_path, _paket(regeln))

    ergebnis = importiere(pfad)

    assert ergebnis["angenommen"] is False
    assert ergebnis["anzahl_regeln"] is None
    assert ergebnis["grund"] == "Die Regel 'Bewirtung' nennt keine Quelle, die zu ihrer Fundstelle passt."


def test_kaputtes_json_wird_abgelehnt_mit_grund(tmp_path):
    pfad = _schreibe(tmp_path, "{das ist kein json")

    ergebnis = importiere(pfad)

    assert ergebnis["angenommen"] is False
    assert ergebnis["anzahl_regeln"] is None
    assert ergebnis["grund"]


def test_fehlende_datei_wird_abgelehnt_mit_grund(tmp_path):
    ergebnis = importiere(tmp_path / "existiert-nicht.json")

    assert ergebnis["angenommen"] is False
    assert ergebnis["grund"]


def test_fehlender_pflichtschluessel_wird_abgelehnt_mit_grund(tmp_path):
    paket = _paket([])
    del paket["quellen"]
    pfad = _schreibe(tmp_path, paket)

    ergebnis = importiere(pfad)

    assert ergebnis["angenommen"] is False
    assert "quellen" in ergebnis["grund"]


def test_leere_regelmenge_wird_angenommen_mit_null_regeln(tmp_path):
    # Entscheidung: eine Domaene ohne Regeln behauptet nichts Unbelegtes und
    # wird angenommen (0 Regeln) -- der Vertrag verweigert nur eine Regel,
    # die ihre Fundstelle nicht zeigen kann, nicht das Fehlen von Regeln.
    pfad = _schreibe(tmp_path, _paket([]))

    ergebnis = importiere(pfad)

    assert ergebnis == {"angenommen": True, "anzahl_regeln": 0, "grund": None}
