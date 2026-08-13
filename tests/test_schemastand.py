"""melder/schemastand.py: haelt schema.sql (SOLL) gegen die installierte
Datenbank (IST). Rot-vor-gruen fuer den Melder selbst -- Aufgabe 96.

ANLASS: L-55075a (2026-08-13, ein Trigger in schema.sql korrigiert, die
INSTALLIERTE Fassung blieb falsch, `CREATE TRIGGER IF NOT EXISTS` ersetzt
nicht) und L-96db3e (2026-08-08, Erstanlage aus schema.sql fehlten 2
Trigger, 6 Tabellen, 2 Spalten). Beide Male gruene Tests. Dieser Test belegt,
dass ein Melder, der IMMER meldet, hier nicht durchrutscht (Negativfall) und
dass der historische Trigger-Fall NAMENTLICH und mit der richtigen Klasse
('abweichendes_sql', nicht bloss 'vorhanden') gefunden wird.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import schemastand  # noqa: E402 -- via conftest.py im sys.path (melder/)
import speicher  # noqa: E402 -- via conftest.py im sys.path (kern/)

WURZEL = Path(__file__).resolve().parents[1]


def _exakter_nachbau(ziel: Path) -> None:
    with speicher.schreiben(ziel) as conn:
        conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))


def test_negativfall_exakter_nachbau_meldet_nichts(tmp_path):
    """Ohne diesen Test bestuende der historische Fall auch bei einem
    Melder, der immer meldet -- er ist die Gegenprobe."""
    db = tmp_path / "exakt.db"
    _exakter_nachbau(db)
    ergebnis = schemastand.vergleich(db=db)
    assert ergebnis == {"nur_in_schema_sql": [], "nur_installiert": [], "abweichendes_sql": []}


def test_historischer_fall_abweichender_trigger_wird_namentlich_gemeldet(tmp_path):
    """Rot-Probe mit dem echten historischen Fall (L-55075a): ein Trigger ist
    installiert, dessen SQL von schema.sql abweicht. Muss als
    'abweichendes_sql' erscheinen -- nicht nur als 'vorhanden' durchgehen."""
    db = tmp_path / "abweichend.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("DROP TRIGGER knowledge_ad")
        conn.execute(
            "CREATE TRIGGER knowledge_ad AFTER DELETE ON knowledge_nodes BEGIN "
            "SELECT 1; END"
        )
    ergebnis = schemastand.vergleich(db=db)
    assert ("trigger", "knowledge_ad") in ergebnis["abweichendes_sql"]
    assert ("trigger", "knowledge_ad") not in ergebnis["nur_installiert"]
    assert ("trigger", "knowledge_ad") not in ergebnis["nur_in_schema_sql"]


def test_erstanlage_luecke_fehlender_trigger_wird_gemeldet(tmp_path):
    """L-96db3e: ein in schema.sql definiertes Objekt fehlt installiert."""
    db = tmp_path / "luecke.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("DROP TRIGGER knowledge_ad")
    ergebnis = schemastand.vergleich(db=db)
    assert ("trigger", "knowledge_ad") in ergebnis["nur_in_schema_sql"]


def test_gewachsener_ueberhang_wird_gemeldet(tmp_path):
    """L-96db3e, Gegenrichtung: die Datenbank ist gewachsen, schema.sql weiss
    nichts davon."""
    db = tmp_path / "ueberhang.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("CREATE TABLE gewachsen (id INTEGER PRIMARY KEY)")
    ergebnis = schemastand.vergleich(db=db)
    assert ("table", "gewachsen") in ergebnis["nur_installiert"]


def test_grenzwert_nur_leerraum_ist_keine_abweichung(tmp_path):
    """Entscheidung: reine Formatierung (Leerraum) ist keine inhaltliche
    Abweichung -- siehe Docstring in melder/schemastand.py."""
    db = tmp_path / "nur_leerraum.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("DROP INDEX idx_nodes_path")
        conn.execute("CREATE   INDEX   idx_nodes_path ON knowledge_nodes(path)")
    ergebnis = schemastand.vergleich(db=db)
    assert ("index", "idx_nodes_path") not in ergebnis["abweichendes_sql"]
    assert ergebnis == {"nur_in_schema_sql": [], "nur_installiert": [], "abweichendes_sql": []}


def test_grenzwert_gross_kleinschreibung_ist_eine_abweichung(tmp_path):
    """Gegenprobe zur anderen Seite derselben Entscheidung: Gross-/
    Kleinschreibung wird NICHT normalisiert und WIRD gemeldet -- der belegte
    Anlassfall war ein Textfehler in einem Trigger, keine Formatierung."""
    db = tmp_path / "nur_gross.db"
    _exakter_nachbau(db)
    with speicher.schreiben(db) as conn:
        conn.execute("DROP INDEX idx_nodes_path")
        conn.execute("CREATE INDEX idx_nodes_path ON KNOWLEDGE_NODES(path)")
    ergebnis = schemastand.vergleich(db=db)
    assert ("index", "idx_nodes_path") in ergebnis["abweichendes_sql"]


def test_gegen_echte_datenbank_laeuft_nur_lesend():
    """Kein rot/gruen-Anspruch hier -- der echte Bestand darf Abweichungen
    haben, das ist ja der Punkt des Melders. Die Probe ist: der Aufruf
    laeuft durch (rein lesend, wirft nicht) und liefert die drei erwarteten
    Schluessel zurueck."""
    ergebnis = schemastand.vergleich()
    assert set(ergebnis) == {"nur_in_schema_sql", "nur_installiert", "abweichendes_sql"}
