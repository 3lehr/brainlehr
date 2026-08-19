"""Tests fuer melder/fremdstandsvergleich.py -- OHNE Netz.

Trennung von der Leitung: hole_stand_einer_quelle() nimmt den Netzabruf
ausschliesslich ueber den Parameter `holer` entgegen (Signatur
`(url, timeout) -> (bytes, headers)`). Jeder Testfall hier ersetzt `holer`
durch eine gecannte Funktion -- kein Testfall oeffnet einen Socket. Damit
misst ein roter Test die Vergleichslogik, nie die Leitung.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "melder"))
import fremdstandsvergleich as fsv  # noqa: E402


def _github_antwort(tag: str, datum: str = "2026-08-01T00:00:00Z"):
    inhalt = json.dumps({"tag_name": tag, "published_at": datum}).encode()
    return lambda url, timeout: (inhalt, {})


def test_gleicher_stand_keine_meldung():
    alt = {"flutter": {"version": "v1.0", "datum": "x"}}
    neu = {"flutter": {"version": "v1.0", "datum": "x"}}
    assert fsv.vergleiche(alt, neu) == []


def test_geaenderter_stand_meldet_alt_und_neu():
    alt = {"flutter": {"version": "v1.0", "datum": "x"}}
    neu = {"flutter": {"version": "v2.0", "datum": "y"}}
    meldungen = fsv.vergleiche(alt, neu)
    assert meldungen == [{"produkt": "flutter", "alt": "v1.0", "neu": "v2.0"}]


def test_nicht_erreichte_quelle_bricht_nichts_ab():
    neu = {"flutter": {"version": "v1.0", "datum": "x"}, "ollama": None}
    assert fsv.nicht_erreichte(neu) == ["ollama"]
    # nicht erreicht darf nie als Aenderung durchrutschen
    assert fsv.vergleiche({"flutter": {"version": "v1.0"}}, neu) == []


def test_erstlauf_meldet_nichts():
    # kein gespeicherter Stand -> auch bei "neuem" Produkt keine Meldung
    neu = {"flutter": {"version": "v1.0", "datum": "x"}}
    assert fsv.vergleiche({}, neu) == []


def test_hole_stand_einer_quelle_nutzt_gestellte_antwort():
    holer = _github_antwort("v3.99.0")
    ergebnis = fsv.hole_stand_einer_quelle("flutter", holer)
    assert ergebnis == {"version": "v3.99.0", "datum": "2026-08-01T00:00:00Z"}


def test_hole_stand_einer_quelle_timeout_liefert_none():
    def holer_wirft(url, timeout):
        raise TimeoutError("gestellter Timeout, kein echtes Netz")

    assert fsv.hole_stand_einer_quelle("flutter", holer_wirft) is None


def test_hole_stand_einer_quelle_http_fehler_liefert_none():
    def holer_500(url, timeout):
        raise OSError("gestellter HTTP-500, kein echtes Netz")

    assert fsv.hole_stand_einer_quelle("ollama", holer_500) is None


def test_lauf_end_zu_end_mit_gestellten_antworten(tmp_path):
    stand_pfad = tmp_path / "stand.json"

    def holer_v1(url, timeout):
        for name, (u, _) in fsv.QUELLEN.items():
            if u == url:
                return _github_antwort("v1.0")(url, timeout) if "github" in u else (b"AAA", {})
        raise AssertionError(url)

    # Erstlauf: kein Stand vorhanden -> keine Meldungen, Stand wird geschrieben
    ergebnis1 = fsv.lauf(stand_pfad, holer_v1)
    assert ergebnis1["meldungen"] == []
    assert stand_pfad.exists()

    def holer_v2(url, timeout):
        for name, (u, _) in fsv.QUELLEN.items():
            if u == url:
                if "github" in u:
                    return _github_antwort("v2.0")(url, timeout)
                return (b"BBB", {})  # anderer Inhalt -> anderer Hash
        raise AssertionError(url)

    ergebnis2 = fsv.lauf(stand_pfad, holer_v2)
    produkte = {m["produkt"] for m in ergebnis2["meldungen"]}
    assert produkte == set(fsv.QUELLEN)  # alle Quellen haben sich "bewegt"
    for m in ergebnis2["meldungen"]:
        assert m["alt"] != m["neu"]


def test_selftest_funktion_laeuft_durch():
    fsv._selftest()
