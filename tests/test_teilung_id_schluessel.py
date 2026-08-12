"""S12, Nachtrag ID-Schluessel (2026-08-12): kern/teilung_s12.py::bestand()
las fuer Knoten bislang `path`. Der Pfad ist veraenderlich --
migrationen/nachziehung_pfad_hygiene_2026-08-07.py schreibt ihn in grosser
Zahl um -- und ein umbenannter Knoten waere mit dem Pfad als Schluessel
lautlos in die andere Haelfte gewandert, mitten im Versuch. Die `id`
(PRIMARY KEY) ist es nicht.

Dieser Test belegt die Eigenschaft, um die es geht: ein Umbenennen des Pfades
aendert die zugewiesene Haelfte NICHT mehr. Gegen den ALTEN Code (Schluessel
`path`) ist er rot -- ein Pfadwechsel aendert dort den Schluessel selbst und
damit fast immer auch die Haelfte.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "kern"))

import speicher  # noqa: E402
import teilung_s12 as t  # noqa: E402


def _db_mit_einem_knoten(pfad: str) -> Path:
    tmp = Path(tempfile.mkdtemp())
    db = tmp / "probe.db"
    schema_sql = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    jetzt = "2026-08-12T08:00:00+02:00"
    with speicher.schreiben(db) as conn:
        conn.executescript(schema_sql)
        conn.execute(
            """INSERT INTO knowledge_nodes
               (id, path, parent_path, project_id, title, summary, content, level, tags, source,
                created_at, updated_at, norm_entscheidung,
                norm_entschieden_von, norm_entschieden_am, norm_entschieden_grund)
               VALUES ('n-fix', ?, '/', 'shared', 'T', 'S', 'C', 1, '[]', 'test',
                       ?, ?, 'keine_norm', ?, ?, ?)""",
            (pfad, jetzt, jetzt, "test", jetzt, "Testvorrichtung"),
        )
    return db


def test_umbenennen_des_pfades_aendert_die_haelfte_nicht():
    """Rot vor der Umstellung auf id, gruen danach -- der Kern des Auftrags.

    Derselbe Knoten (feste id 'n-fix'), zwei verschiedene Pfade. bestand()
    liest die id als Schluessel -- ihre Haelfte bleibt beim Umbenennen gleich.
    """
    # Zwei Pfade suchen, deren HAELFTE SICH ALS PFAD UNTERSCHEIDEN WUERDE --
    # sonst waere der Test auch gegen den alten (pfadbasierten) Code zufaellig
    # gruen und bewiese nichts.
    kandidaten = [f"/a/{i}" for i in range(200)]
    pfad_a = next(p for p in kandidaten if t.haelfte("knoten", p) == t.BEHANDELT)
    pfad_b = next(p for p in kandidaten if t.haelfte("knoten", p) == t.UNBEHANDELT)
    assert t.haelfte("knoten", pfad_a) != t.haelfte("knoten", pfad_b), (
        "Testvorbedingung verletzt: die gewaehlten Pfade faerben nicht "
        "unterschiedlich -- der Test wuerde nichts pruefen"
    )

    db_a = _db_mit_einem_knoten(pfad_a)
    with speicher.lesen(db_a) as conn:
        haelfte_vorher = t.zaehlen(conn)["knoten"]

    # Denselben Knoten (gleiche id) umbenennen -- simuliert genau den
    # Migrationsschritt aus nachziehung_pfad_hygiene_2026-08-07.py.
    with speicher.schreiben(db_a) as conn:
        conn.execute("UPDATE knowledge_nodes SET path = ? WHERE id = 'n-fix'", (pfad_b,))

    with speicher.lesen(db_a) as conn:
        haelfte_nachher = t.zaehlen(conn)["knoten"]

    assert haelfte_vorher == haelfte_nachher, (
        f"Umbenennen des Pfades hat die Haelfte veraendert: "
        f"{haelfte_vorher} -> {haelfte_nachher}. Der Schluessel ist damit "
        "wieder der Pfad, nicht die id."
    )


def test_negativfall_id_ist_wirklich_der_schluessel_nicht_nur_stabil():
    """Gegenprobe: unterschiedliche ids fallen (ueberwiegend) in
    unterschiedliche Haelften, auch bei gleichem Pfad -- sonst waere der obige
    gruene Test nur ein Artefakt eines konstanten Schluessels."""
    ids = [f"n-{i}" for i in range(200)]
    werte = {t.haelfte("knoten", i) for i in ids}
    assert werte == {t.BEHANDELT, t.UNBEHANDELT}
