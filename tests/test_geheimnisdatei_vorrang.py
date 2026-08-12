"""Vorrang der Geheimnisdatei vor BRAINLEHR_GEHEIMNIS (Umgebung).

ANLASS: das Geheimnis stand im Klartext in ~/.claude.json und wurde dort am
2026-08-12 als Ganzes gelesen. Es kommt jetzt aus einer eigenen Datei
(kern/geheimnis.py, mein-geheimnis.txt neben ausweise.json), die Umgebungs-
variable bleibt nur Ruecktritt.

ROT VOR GRUEN: gegen den Stand vor dieser Aenderung faellt
test_datei_hat_vorrang_vor_umgebung durch -- ausweis.loese_auf() las bislang
nur os.environ.get(ausweis.ENV_GEHEIMNIS) und kannte keine Datei.

SICHERHEITSAUFLAGE: kein Test hier gibt den Wert eines Geheimnisses aus
(print, assert-Meldung, Log). Geprueft wird nur, WELCHE Quelle gewinnt und
DASS ein Widerspruch gemeldet wird -- nie der Wert selbst.
"""
from __future__ import annotations

import os
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import pytest

import ausweis  # noqa: E402
import geheimnis  # noqa: E402


@pytest.fixture()
def ausweisdatei(tmp_path, monkeypatch):
    pfad = tmp_path / "ausweise.json"
    monkeypatch.setenv(ausweis.ENV_AUSWEISDATEI, str(pfad))
    monkeypatch.delenv(ausweis.ENV_GEHEIMNIS, raising=False)
    return pfad


def _schreibe_geheimnisdatei(ausweisdatei, wert: str, modus: int = 0o600) -> _Path:
    datei = geheimnis.geheimnisdatei(ausweisdatei)
    fd = os.open(datei, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, modus)
    with os.fdopen(fd, "w") as f:
        f.write(wert)
    os.chmod(datei, modus)
    return datei


def test_datei_hat_vorrang_vor_umgebung(ausweisdatei):
    """Datei vorhanden -> ihr Wert wird genommen, auch ohne Umgebungsvariable."""
    g = ausweis.anlegen("azubi", ["leser"], pfad=ausweisdatei)
    _schreibe_geheimnisdatei(ausweisdatei, g)

    a = ausweis.loese_auf(pfad=ausweisdatei)

    assert a.beglaubigt and a.name == "azubi"


def test_nur_umgebungsvariable_ist_ruecktritt(ausweisdatei, monkeypatch):
    """Keine Datei -> BRAINLEHR_GEHEIMNIS traegt weiter, sonst braechen
    laufende Sitzungen beim naechsten Aufruf ab."""
    g = ausweis.anlegen("hausmeister", ["leser"], pfad=ausweisdatei)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)

    a = ausweis.loese_auf(pfad=ausweisdatei)

    assert a.beglaubigt and a.name == "hausmeister"


def test_beide_gesetzt_und_verschieden_ist_befund_datei_gewinnt(
        ausweisdatei, monkeypatch, capsys):
    """Widerspruch wird gemeldet, nicht still aufgeloest -- und die Datei
    gewinnt, weil sie fuer diesen Rechner die naehere Quelle ist."""
    gruender = ausweis.anlegen("gruender", ["betreiber"], pfad=ausweisdatei)
    g_datei = ausweis.anlegen("aus-datei", ["leser"], pfad=ausweisdatei,
                              aussteller=gruender)
    g_umgebung = ausweis.anlegen("aus-umgebung", ["leser"], pfad=ausweisdatei,
                                 aussteller=gruender)
    _schreibe_geheimnisdatei(ausweisdatei, g_datei)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g_umgebung)

    a = ausweis.loese_auf(pfad=ausweisdatei)
    gemeldet = capsys.readouterr().err

    assert a.beglaubigt and a.name == "aus-datei", \
        "bei Widerspruch muss die Datei gewinnen, nicht die Umgebung"
    assert "unterscheiden sich" in gemeldet, "der Widerspruch wurde nicht gemeldet"
    assert g_datei not in gemeldet and g_umgebung not in gemeldet, \
        "ein Geheimnis stand in der Meldung -- Sicherheitsauflage verletzt"


def test_beide_gleich_kein_befund(ausweisdatei, monkeypatch, capsys):
    """Kein Widerspruch, kein unnoetiger Alarm, wenn Datei und Umgebung
    denselben Wert tragen (z.B. waehrend der Umstellung)."""
    g = ausweis.anlegen("gleich", ["leser"], pfad=ausweisdatei)
    _schreibe_geheimnisdatei(ausweisdatei, g)
    monkeypatch.setenv(ausweis.ENV_GEHEIMNIS, g)

    a = ausweis.loese_auf(pfad=ausweisdatei)
    gemeldet = capsys.readouterr().err

    assert a.beglaubigt and a.name == "gleich"
    assert "unterscheiden sich" not in gemeldet


def test_weder_datei_noch_umgebung_bleibt_unbeglaubigt_ohne_rechte(ausweisdatei):
    """Fehlen beide, wird NICHT stillschweigend mit Rechten weitergearbeitet:
    derselbe unbeglaubigte Zweig wie bei einem falschen Geheimnis -- keine
    Rolle, und das Praefix 'unbeglaubigt:' im Protokollnamen macht es
    rueckwirkend sichtbar."""
    a = ausweis.loese_auf("wer-auch-immer", pfad=ausweisdatei)

    assert not a.beglaubigt
    assert a.rollen == ()
    assert a.protokollname == "unbeglaubigt:wer-auch-immer"
    assert not ausweis.darf(a, "wissen:schreiben")


def test_zu_weite_rechte_an_der_geheimnisdatei_werden_ignoriert(ausweisdatei):
    """Dieselbe Regel wie bei ausweise.json: eine Geheimnisdatei, die andere
    lesen duerfen, ist keine -- sie wird ignoriert, nicht stillschweigend
    genutzt."""
    g = ausweis.anlegen("offene-datei", ["leser"], pfad=ausweisdatei)
    _schreibe_geheimnisdatei(ausweisdatei, g, modus=0o644)

    a = ausweis.loese_auf(pfad=ausweisdatei)

    assert not a.beglaubigt, "weltlesbare Geheimnisdatei darf niemanden beglaubigen"


def test_explizites_geheimnis_argument_gewinnt_immer(ausweisdatei):
    """Der Parameter `geheimnis=` (Tests, interne Aufrufe wie _aussteller_name)
    bleibt unveraendert die hoechste Prioritaet -- Datei und Umgebung werden
    dafuer gar nicht erst angesehen."""
    gruender = ausweis.anlegen("gruender", ["betreiber"], pfad=ausweisdatei)
    g_datei = ausweis.anlegen("aus-datei", ["leser"], pfad=ausweisdatei,
                              aussteller=gruender)
    g_direkt = ausweis.anlegen("direkt-uebergeben", ["leser"], pfad=ausweisdatei,
                               aussteller=gruender)
    _schreibe_geheimnisdatei(ausweisdatei, g_datei)

    a = ausweis.loese_auf(geheimnis=g_direkt, pfad=ausweisdatei)

    assert a.beglaubigt and a.name == "direkt-uebergeben"
