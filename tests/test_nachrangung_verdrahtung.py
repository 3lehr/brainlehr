"""Die Nachrangung haengt abschaltbar in knowledge_search -- und respektiert
die Trennung, die vor ihr da war.

Gemessen 2026-08-18 (runs/nachrangung_2026-08-18.json): top5 6/35 ohne,
18/35 mit Modell. Der Hebel ist echt, der Preis auch -- Median 48,6 s je
Anfrage. Deshalb ist `nachrangung` AUS in der Vorgabe; wer sie einschaltet,
bezahlt bewusst.

Der Fall, den dieser Test wirklich sichert: `nachrangig` sind Eintraege,
deren GELTUNG abgelaufen ist. Sie stehen hinten, weil sie abgelaufen sind,
nicht weil sie unpassend sind. Ein Nachranger, der nach Passung umordnet,
wuerde sie ohne diese Trennung nach oben holen und damit genau die Aussage
aufheben, die die Trennung traegt.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "kern")]

import knowledge_mcp_server as kms  # noqa: E402
from kern import nachrangung as nr  # noqa: E402


@pytest.fixture()
def bestand(tmp_path, monkeypatch):
    db = tmp_path / "nachrangung.db"
    conn = sqlite3.connect(db)
    conn.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db)
    for titel in ("Kesselregler erster Eintrag", "Kesselregler zweiter Eintrag",
                  "Kesselregler dritter Eintrag"):
        assert kms.knowledge_add("/", titel, "Kesselregler und Heizung",
                                 source="test", tags=["synthetisch"])["status"] == "created"
    # Abgelaufen: gehoert nach hinten, egal wie gut es passt.
    assert kms.knowledge_add("/", "Kesselregler abgelaufener Eintrag",
                             "Kesselregler und Heizung", source="test",
                             tags=["synthetisch"], norm_rang=1,
                             gilt_ab="2020-01-01", gilt_bis="2020-12-31",
                             norm_entscheidung="norm_befristet",
                             )["status"] == "created"
    return db


def _titel(res):
    return [r.get("title") for r in res if r.get("kind") == "node"]


def test_vorgabe_laesst_die_reihenfolge_unangetastet(bestand, monkeypatch):
    # Ehrlich benannt: dieser Test war auch VOR der Verdrahtung gruen -- er
    # kann gar nicht anders, solange der Schalter fehlt. Er belegt nichts
    # ueber die Aenderung, er haelt nur fest, dass die Vorgabe AUS bleibt,
    # falls jemand sie spaeter umdreht. Die beiden anderen Tests waren vorher
    # rot (TypeError: unexpected keyword argument 'nachrangung').
    def darf_nicht(*a, **k):
        raise AssertionError("Nachrangung lief ohne dass sie eingeschaltet war")
    monkeypatch.setattr(nr, "modell", darf_nicht)
    kms.knowledge_search("Kesselregler", max_results=10)


def test_eingeschaltet_ordnet_sie_um(bestand, monkeypatch):
    ohne = _titel(kms.knowledge_search("Kesselregler", max_results=10)["results"])
    monkeypatch.setattr(nr, "modell", lambda anfrage, k, **kw: list(range(len(k)))[::-1])
    mit = _titel(kms.knowledge_search("Kesselregler", max_results=10, nachrangung=True)["results"])
    assert sorted(mit) == sorted(ohne), "es darf nichts verschwinden und nichts dazukommen"
    assert mit != ohne, "eingeschaltet muss die Nachrangung sichtbar wirken"


def test_abgelaufenes_bleibt_hinten_auch_wenn_der_nachranger_es_vorziehen_will(
        bestand, monkeypatch):
    # Der Nachranger dreht ALLES um. Waere er auf die Gesamtliste angewandt,
    # stuende der abgelaufene Eintrag danach vorn.
    monkeypatch.setattr(nr, "modell", lambda anfrage, k, **kw: list(range(len(k)))[::-1])
    res = kms.knowledge_search("Kesselregler", max_results=10, nachrangung=True)["results"]
    knoten = [r for r in res if r.get("kind") == "node"]
    abgelaufen = [i for i, r in enumerate(knoten) if r.get("geltung") == "abgelaufen"]
    assert abgelaufen, "Vorbedingung: der abgelaufene Eintrag muss im Ergebnis stehen"
    assert abgelaufen == [len(knoten) - 1], _titel(res)
