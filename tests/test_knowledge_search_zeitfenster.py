"""Tests fuer das Zeitfenster (erstellt_von/erstellt_bis) in knowledge_search().

Aufgabe 88 Schritt 1 (docs/PLAN_ZEITACHSE_2026-08-14.md): ENTSTEHUNGSZEIT
(created_at) ist eine andere Frage als stichtag/nur_geltende, die die GELTUNG
(gilt_ab/gilt_bis) pruefen -- siehe test_knowledge_search_geltung.py fuer
diese. Der Filter wirkt in der Schleife, die final_ids zu Eintraegen macht
(NACH der FTS/Embedding-Fusion), nicht in der SQL-WHERE-Klausel: der
Bedeutungskanal liefert seine Kandidaten getrennt an der FTS vorbei, ein
WHERE dort wuerde nur die Stichworthaelfte treffen.

Lehren tragen kein entschiedenes "gemacht"-Feld (first_seen UND last_seen
existieren, keins ist es) -- sie fallen bei gesetztem Zeitraum komplett aus
dem Ergebnis, gezaehlt unter "lehren_uebersprungen_zeitfilter" statt
stillschweigend zu verschwinden.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import json
import sqlite3
import sys

import pytest

SHARED_KNOWLEDGE = _Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

WORT = "Zeitachsentest"


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "knowledge_test.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    conn.executemany(
        """INSERT INTO knowledge_nodes
           (id, path, project_id, title, summary, content, level, source,
            norm_entscheidung, norm_entschieden_von, norm_entschieden_grund, created_at, updated_at)
           VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung', ?, ?)""",
        [
            # weit vor dem Fenster
            ("z-alt", "/zeit/alt", f"{WORT} alt", f"{WORT} Knoten alt",
             "2020-01-01T00:00:00+01:00", "2020-01-01T00:00:00+01:00"),
            # genau einen Tag VOR der unteren Grenze -- muss rausfallen
            ("z-davor", "/zeit/davor", f"{WORT} davor", f"{WORT} Knoten davor",
             "2026-08-09T23:59:59+01:00", "2026-08-09T23:59:59+01:00"),
            # genau AUF der unteren Grenze -- inklusiv, muss bleiben
            ("z-von-rand", "/zeit/von-rand", f"{WORT} von-rand", f"{WORT} Knoten am unteren Rand",
             "2026-08-10T00:00:00+01:00", "2026-08-10T00:00:00+01:00"),
            # innerhalb
            ("z-mitte", "/zeit/mitte", f"{WORT} mitte", f"{WORT} Knoten mittendrin",
             "2026-08-11T12:00:00+01:00", "2026-08-11T12:00:00+01:00"),
            # genau AUF der oberen Grenze -- inklusiv, muss bleiben
            ("z-bis-rand", "/zeit/bis-rand", f"{WORT} bis-rand", f"{WORT} Knoten am oberen Rand",
             "2026-08-12T23:59:59+01:00", "2026-08-12T23:59:59+01:00"),
            # genau einen Tag NACH der oberen Grenze -- muss rausfallen
            ("z-danach", "/zeit/danach", f"{WORT} danach", f"{WORT} Knoten danach",
             "2026-08-13T00:00:00+01:00", "2026-08-13T00:00:00+01:00"),
        ],
    )
    conn.execute(
        """INSERT INTO lessons_learned (id, type, description, projects, status)
           VALUES ('L-zeittest', 'insight', ?, ?, 'active')""",
        (f"{WORT} Lehre ohne Entstehungsfeld", json.dumps(["shared"])),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def _node_ids(result):
    return [r["id"] for r in result["results"] if r["kind"] == "node"]


def _all_ids(result):
    return [r["id"] for r in result["results"]]


VON, BIS = "2026-08-10", "2026-08-12"
IM_FENSTER = {"z-von-rand", "z-mitte", "z-bis-rand"}
AUSSERHALB = {"z-alt", "z-davor", "z-danach"}


def test_rot_vor_gruen_echte_teilmenge(temp_db):
    """Abnahme 1: mit Zeitraum eine ECHTE Teilmenge dessen, was ohne
    Zeitraum zurueckkommt -- an einem Fall, bei dem die Zeit den Ausschlag
    gibt (drei Knoten ausserhalb des Fensters, drei drin)."""
    ohne = kms.knowledge_search(WORT)
    mit_zeitraum = kms.knowledge_search(WORT, erstellt_von=VON, erstellt_bis=BIS)

    ohne_ids = set(_node_ids(ohne))
    mit_ids = set(_node_ids(mit_zeitraum))

    assert ohne_ids == IM_FENSTER | AUSSERHALB
    assert mit_ids == IM_FENSTER
    assert mit_ids < ohne_ids  # echte Teilmenge, nicht gleich


def test_negativfall_voller_zeitraum_aendert_nichts(temp_db):
    """Abnahme 2: ein Zeitraum, der alles umfasst, aendert an der
    Knoten-Trefferliste nichts (Lehren sind hier ausgenommen, siehe
    test_lehren_zaehlung -- sie kennen kein Entstehungsfeld und fallen bei
    JEDEM gesetzten Zeitraum weg, unabhaengig von dessen Breite)."""
    ohne = kms.knowledge_search(WORT)
    voller_zeitraum = kms.knowledge_search(WORT, erstellt_von="2000-01-01", erstellt_bis="2100-01-01")
    assert set(_node_ids(voller_zeitraum)) == set(_node_ids(ohne))


@pytest.mark.parametrize("knoten_id,erwartet_drin", [
    ("z-davor", False),      # einen Tag vor der unteren Grenze
    ("z-von-rand", True),    # exakt auf der unteren Grenze -- inklusiv
    ("z-bis-rand", True),    # exakt auf der oberen Grenze -- inklusiv
    ("z-danach", False),     # einen Tag nach der oberen Grenze
])
def test_grenzwerte_beide_enden_inklusiv(temp_db, knoten_id, erwartet_drin):
    result = kms.knowledge_search(WORT, erstellt_von=VON, erstellt_bis=BIS)
    ids = set(_node_ids(result))
    assert (knoten_id in ids) == erwartet_drin


def test_lehren_zaehlung_nur_bei_gesetztem_zeitraum(temp_db):
    """Abnahme 4: die Anzahl der aus Zeitgruenden fallengelassenen Lehren
    steht in der Antwort, NUR wenn ein Zeitraum gesetzt ist (kein Rauschen
    im Vorgabefall ohne Filter)."""
    ohne = kms.knowledge_search(WORT)
    assert "lehren_uebersprungen_zeitfilter" not in ohne
    assert "L-zeittest" in _all_ids(ohne)  # Lehre ist ohne Filter normal dabei

    mit_zeitraum = kms.knowledge_search(WORT, erstellt_von=VON, erstellt_bis=BIS)
    assert mit_zeitraum["lehren_uebersprungen_zeitfilter"] == 1
    assert "L-zeittest" not in _all_ids(mit_zeitraum)

    # auch mit nur EINER gesetzten Grenze aktiv (von=None waere sonst
    # zeitfilter_aktiv=False und liesse die Lehre lautlos durch)
    nur_bis = kms.knowledge_search(WORT, erstellt_bis=BIS)
    assert nur_bis["lehren_uebersprungen_zeitfilter"] == 1


def test_knoten_ohne_created_at_kann_nicht_entstehen(temp_db):
    """Abnahme 5, GEMESSEN statt angenommen: schema.sql erklaert
    knowledge_nodes.created_at NOT NULL (Zeile 28) -- ein Knoten ohne
    Entstehungszeit kann in diesem Schema nicht angelegt werden, weder per
    INSERT noch nachtraeglich per UPDATE. Die Verteidigung im Suchcode
    (created_at is None -> ausschliessen statt raten) ist damit unerreichbar,
    aber bewusst nicht entfernt -- ein NOT NULL kann durch eine kuenftige
    Migration wegfallen, der Suchcode soll dann nicht wieder raten."""
    conn = sqlite3.connect(str(temp_db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, project_id, title, summary, level, source,
                norm_entscheidung, norm_entschieden_von, norm_entschieden_grund, created_at)
               VALUES ('z-ohne-created', '/zeit/ohne-created', 'shared', 'x', 'x', 0, 'test',
                       'keine_norm', 'skript:test', 'Testvorrichtung', NULL)"""
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE knowledge_nodes SET created_at = NULL WHERE id = 'z-alt'")
    conn.close()


def test_fakten_unveraendert_ohne_zeitraum(temp_db):
    """Nichtaenderung: ein Aufruf ohne erstellt_von/erstellt_bis liefert
    exakt dieselbe Form wie vor diesem Auftrag (kein zusaetzliches Feld,
    keine Lehre verschwindet)."""
    result = kms.knowledge_search(WORT)
    assert "lehren_uebersprungen_zeitfilter" not in result
    assert set(_node_ids(result)) == IM_FENSTER | AUSSERHALB
    assert "L-zeittest" in _all_ids(result)


# --- Nachtrag 2026-08-14: der Fall, den die urspruengliche Abnahme nicht hatte

@pytest.fixture()
def temp_db_viele(tmp_path, monkeypatch):
    """Sechs starke Treffer AUSSERHALB des Fensters, ein schwacher INNERHALB.

    Die Vorrichtung oben hat sechs Knoten und laeuft mit max_results=10 --
    dort passt alles in die Kappungsgrenze, und ob der Filter vor oder nach
    der Fusion wirkt, faellt nicht auf. Genau daran ist die erste Fassung
    vorbeigelaufen: _fuse_with_keyword_floor() kappt auf max_results, und ein
    Filter danach zieht seine Teilmenge aus den bereits abgeschnittenen
    Rangplaetzen. Liegt dort nichts im Zeitraum, kommt nichts zurueck --
    obwohl weiter hinten ein passender Knoten steht.
    """
    db_path = tmp_path / "knowledge_viele.db"
    schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    conn.executescript(schema)
    zeilen = []
    for n in range(6):
        zeilen.append((
            f"v-stark-{n}", f"/viele/stark-{n}",
            f"{WORT} {WORT} {WORT}", f"{WORT} {WORT} {WORT} starker Treffer {n}",
            "2020-01-01T00:00:00+01:00", "2020-01-01T00:00:00+01:00"))
    zeilen.append((
        "v-schwach-im-fenster", "/viele/schwach",
        "Randnotiz", f"Beilaeufig {WORT} erwaehnt, sonst nur Fuelltext ohne Bezug",
        "2026-08-11T12:00:00+01:00", "2026-08-11T12:00:00+01:00"))
    conn.executemany(
        """INSERT INTO knowledge_nodes
           (id, path, project_id, title, summary, content, level, source,
            norm_entscheidung, norm_entschieden_von, norm_entschieden_grund, created_at, updated_at)
           VALUES (?, ?, 'shared', ?, ?, NULL, 0, 'test', 'keine_norm', 'skript:test', 'Testvorrichtung', ?, ?)""",
        zeilen)
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def test_treffer_hinter_der_kappungsgrenze_geht_nicht_verloren(temp_db_viele):
    """ROT vor dem Fix: der Filter lief nach _fuse_with_keyword_floor() und
    sah nur die gekappten Top-max_results -- alle ausserhalb des Fensters,
    Ergebnis leer. Der passende Knoten stand direkt dahinter.

    Damit ist das kein Randfall, sondern der Normalfall: bei 2184 Knoten und
    max_results=10 liegt fast jeder Treffer aus 'letzter Woche' hinter der
    Kappungsgrenze."""
    ohne = kms.knowledge_search(WORT, max_results=3)
    assert len(_node_ids(ohne)) == 3, "Vorbedingung: ohne Zeitraum kappt es auf 3"
    assert "v-schwach-im-fenster" not in _node_ids(ohne), (
        "Vorbedingung der Probe: der Knoten im Fenster darf NICHT unter den "
        "ersten 3 sein, sonst prueft der Test nichts")

    mit = kms.knowledge_search(WORT, max_results=3, erstellt_von=VON, erstellt_bis=BIS)
    assert _node_ids(mit) == ["v-schwach-im-fenster"], (
        "Der einzige Knoten im Zeitraum steht hinter der Kappungsgrenze und "
        f"muss trotzdem kommen, bekam: {_node_ids(mit)}")


def test_zaehlung_der_lehren_ist_selbst_nicht_gekappt(temp_db):
    """Die Zahl, die gegen stille Kuerzung steht, darf nicht selbst gekappt
    sein. Mit max_results=1 wuerde eine Zaehlung in der Ergebnisschleife
    hoechstens 1 melden -- gezaehlt wird deshalb ueber die volle
    Kandidatenmenge."""
    eng = kms.knowledge_search(WORT, max_results=1, erstellt_von=VON, erstellt_bis=BIS)
    weit = kms.knowledge_search(WORT, max_results=10, erstellt_von=VON, erstellt_bis=BIS)
    assert eng["lehren_uebersprungen_zeitfilter"] == weit["lehren_uebersprungen_zeitfilter"] == 1
