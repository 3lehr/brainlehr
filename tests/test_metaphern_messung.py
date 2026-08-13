"""Deckt messungen/metaphern_messung.py ab -- Schritt 2 aus
docs/PLAN_METAPHERN_2026-08-13.md (blinder Durchlauf und Auswertung, KEINE
Faelle/Fassungen -- die kommen unveraendert aus messungen/metaphern_regelpaare.py).

Prueft zwei Dinge, die der Auftrag ausdruecklich verlangt:
1. Blindheit ist nachweisbar, nicht behauptet (items_blind traegt weder
   Fassung noch Menge noch Paar-Bezug, weder als Feld noch ueber die ID).
2. Fehlbestand in der Antwortdatei wird GENANNT, nicht stillschweigend als
   'nicht angewandt' gelesen -- mit Gegenprobe (vollstaendige Datei geht
   normal ein), sonst bestuende der Test auch bei einer Auswertung, die
   schlicht alles ausschliesst.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "messungen")]

import metaphern_messung as mm  # noqa: E402
import metaphern_regelpaare as mr  # noqa: E402


# ------------------------------------------------------------------ Blindheit
def test_items_blind_hat_kein_fassung_menge_oder_paar_feld():
    aufgaben = mm.aufgaben_erzeugen(seed=1)
    for item in aufgaben["items_blind"]:
        assert set(item.keys()) == {"id", "regel_text", "fall_text"}, item
        assert "fassung" not in item and "menge" not in item and "paar_id" not in item


def test_items_blind_id_kodiert_fassung_oder_menge_nicht():
    aufgaben = mm.aufgaben_erzeugen(seed=1)
    for item in aufgaben["items_blind"]:
        # reine Laufnummer 'it-000' -- keine der Bezeichnungen taucht darin auf.
        assert item["id"].startswith("it-")
        rest = item["id"][3:]
        assert rest.isdigit()
        for verboten in (*mr.FASSUNGEN, *mr.MENGEN, *[p["id"] for p in mr.REGELPAARE]):
            assert verboten not in item["id"]


def test_zuordnung_liegt_getrennt_und_deckt_alle_items_ab():
    aufgaben = mm.aufgaben_erzeugen(seed=1)
    ids_blind = {i["id"] for i in aufgaben["items_blind"]}
    assert ids_blind == set(aufgaben["zuordnung"].keys())
    for meta in aufgaben["zuordnung"].values():
        assert set(meta.keys()) == {"paar_id", "fassung", "menge"}


def test_seed_ist_protokolliert_und_reihenfolge_deterministisch():
    a1 = mm.aufgaben_erzeugen(seed=42)
    a2 = mm.aufgaben_erzeugen(seed=42)
    assert a1["seed"] == 42
    assert [i["id"] for i in a1["items_blind"]] == [i["id"] for i in a2["items_blind"]]
    assert [i["fall_text"] for i in a1["items_blind"]] == [i["fall_text"] for i in a2["items_blind"]]


def test_codestand_in_aufgabendatei():
    aufgaben = mm.aufgaben_erzeugen(seed=1)
    assert {"commit", "zweig", "schmutzig"} <= set(aufgaben["codestand"].keys())


# --------------------------------------------------------------- Auswertung
def _alle_antworten(aufgaben: dict, ja_wenn) -> dict:
    """Baut eine vollstaendige Antwortdatei -- ja_wenn(meta) -> bool."""
    return {"antworten": {
        iid: {"angewandt": ja_wenn(meta)}
        for iid, meta in aufgaben["zuordnung"].items()
    }}


def test_negativfall_fehlbestand_wird_gezaehlt_nicht_als_nein_gelesen():
    """Eine unvollstaendige Antwortdatei darf NICHT so aussehen wie eine
    vollstaendige mit lauter 'nein' -- die fehlenden Zellen muessen als
    Fehlbestand auftauchen und duerfen die Quote nicht fuellen."""
    aufgaben = mm.aufgaben_erzeugen(seed=3)
    vollstaendig = _alle_antworten(aufgaben, lambda meta: True)
    ids = list(aufgaben["zuordnung"].keys())
    luecke = {"antworten": {k: v for k, v in vollstaendig["antworten"].items()
                             if k != ids[0]}}

    ergebnis = mm.auswerten(aufgaben, luecke)
    assert ergebnis["n_fehlbestand"] == 1
    assert ids[0] in ergebnis["fehlbestand"]

    # Die fehlende Zelle darf keine Quote als 'nein' fuellen: Summe der n
    # ueber alle Fassungen/Mengen der betroffenen Zelle ist um genau 1 kleiner
    # als bei der vollstaendigen Auswertung, nicht identisch (was hiesse: die
    # Luecke wurde als 'nein' mitgezaehlt).
    voll = mm.auswerten(aufgaben, vollstaendig)
    n_voll = sum(w[teil]["n"] for p in voll["paare"] for w in p["fassungen"].values()
                 for teil in ("reichweite", "fehlanwendung", "genannt_getroffen"))
    n_luecke = sum(w[teil]["n"] for p in ergebnis["paare"] for w in p["fassungen"].values()
                   for teil in ("reichweite", "fehlanwendung", "genannt_getroffen"))
    assert n_luecke == n_voll - 1


def test_gegenprobe_vollstaendige_datei_geht_normal_ein():
    """Ohne Luecke: kein Fehlbestand, jede Zelle geht in genau eine Quote ein."""
    aufgaben = mm.aufgaben_erzeugen(seed=3)
    vollstaendig = _alle_antworten(aufgaben, lambda meta: True)
    ergebnis = mm.auswerten(aufgaben, vollstaendig)
    assert ergebnis["n_fehlbestand"] == 0
    assert ergebnis["n_unlesbar"] == 0
    n = sum(w[teil]["n"] for p in ergebnis["paare"] for w in p["fassungen"].values()
            for teil in ("reichweite", "fehlanwendung", "genannt_getroffen"))
    assert n == len(aufgaben["zuordnung"])


def test_unlesbare_antwort_wird_getrennt_von_fehlbestand_gezaehlt():
    aufgaben = mm.aufgaben_erzeugen(seed=3)
    ids = list(aufgaben["zuordnung"].keys())
    antworten = {"antworten": {iid: {"angewandt": True} for iid in ids}}
    antworten["antworten"][ids[0]] = {"antwort": "vielleicht"}  # weder ja noch nein
    ergebnis = mm.auswerten(aufgaben, antworten)
    assert ergebnis["n_unlesbar"] == 1 and ids[0] in ergebnis["unlesbar"]
    assert ergebnis["n_fehlbestand"] == 0


def test_reichweite_und_fehlanwendung_getrennt_je_paar_und_fassung():
    """Reichweite (Menge 'gemeint') und Fehlanwendung (Menge 'nicht_gemeint')
    sind unabhaengig voneinander -- Konstruktion, bei der alle 'gemeint'
    Faelle 'ja' und alle 'nicht_gemeint' Faelle 'nein' beantwortet werden,
    muss Reichweite=1.0 und Fehlanwendung=0.0 ergeben, nicht irgendeine
    verrechnete Zahl dazwischen."""
    aufgaben = mm.aufgaben_erzeugen(seed=5)
    antworten = _alle_antworten(
        aufgaben, lambda meta: meta["menge"] in ("genannt", "gemeint"))
    ergebnis = mm.auswerten(aufgaben, antworten)
    for paar in ergebnis["paare"]:
        for fassung, werte in paar["fassungen"].items():
            assert werte["reichweite"]["anteil"] == 1.0
            assert werte["fehlanwendung"]["anteil"] == 0.0
            assert werte["gueltig_in_diesem_lauf"] is True


def test_paar_wird_ungueltig_wenn_ein_genannter_fall_nicht_getroffen_wird():
    aufgaben = mm.aufgaben_erzeugen(seed=5)
    antworten = _alle_antworten(aufgaben, lambda meta: True)
    # genau einen 'genannt'-Fall auf 'nein' kippen.
    for iid, meta in aufgaben["zuordnung"].items():
        if meta["menge"] == "genannt":
            antworten["antworten"][iid] = {"angewandt": False}
            betroffen = meta
            break
    ergebnis = mm.auswerten(aufgaben, antworten)
    paar = next(p for p in ergebnis["paare"] if p["paar_id"] == betroffen["paar_id"])
    assert paar["fassungen"][betroffen["fassung"]]["gueltig_in_diesem_lauf"] is False


def test_jedes_regelpaar_und_jede_fassung_kommt_in_der_auswertung_vor():
    aufgaben = mm.aufgaben_erzeugen(seed=7)
    antworten = _alle_antworten(aufgaben, lambda meta: False)
    ergebnis = mm.auswerten(aufgaben, antworten)
    assert len(ergebnis["paare"]) == len(mr.REGELPAARE)
    for paar in ergebnis["paare"]:
        assert set(paar["fassungen"].keys()) == set(mr.FASSUNGEN)
