"""Aufgabe 110: Was der Code LIEST, muss eine Erstinstallation HABEN.

Der Schemamelder (Aufgabe 96) meldete 19 Abweichungen zwischen schema.sql und
der installierten Datenbank. Die Zahl war zu grob, um damit zu arbeiten -- am
2026-08-14 auseinandergezogen:

  13 gemeldete "abweichendes SQL"
   -> 6 nur Text: Kommentare und Formatierung. Die installierten Objekte
      stammen aus einer aelteren schema.sql; strukturell identisch.
   -> 7 strukturell, und die zerfallen wieder:
      - 3x ZEITZONE: der Bestand stempelt '+01:00' mit 'localtime',
        schema.sql 'Z' (UTC). Getrennt zu entscheiden, siehe unten.
      - 2x SPALTE FEHLT IN schema.sql (dieser Test).
      - 2x TRIGGER: der installierte ist STRENGER als schema.sql -- ihm fehlt
        die Ausnahme fuer anlass='betreiber'.

DIE BEIDEN SPALTEN, und sie sind NICHT gleichwertig:

  lessons_learned.pruefstelle   -- fehlt in schema.sql UND wird nicht zur
      Laufzeit nachgeruestet. kern/raum_daten.py liest sie woertlich
      ("SELECT ... l.pruefstelle ... FROM lessons_learned l"). Eine
      Erstinstallation brach damit an "no such column: l.pruefstelle".
      Gemessen am 2026-08-14 in BEIDE Richtungen: frische DB bricht, der
      gewachsene Bestand laeuft.

  knowledge_embeddings.text_checksum -- fehlt in schema.sql, wird aber beim
      ersten Lauf von kern/build_embeddings.py nachgeruestet. Eine
      Erstinstallation bricht daran NICHT (gemessen). Trotzdem eingetragen:
      solange die Datei als SOLL unvollstaendig ist, meldet der Schemamelder
      eine Abweichung, die keine ist -- und verbraucht Aufmerksamkeit, die den
      echten Fall daneben verdeckt.

WARUM ES NIEMANDEM AUFFIEL, und das ist die uebertragbare Haelfte:
kern/raum_daten.py::_selftest baut sich seine EIGENE lessons_learned-Tabelle,
mit pruefstelle. Ein Test, der sein Schema selbst definiert, kann eine
Schemaluecke grundsaetzlich nicht finden -- er prueft seine eigene Annahme.
Deshalb prueft dieser Test gegen schema.sql, nicht gegen eine Handtabelle.

Rot vor gruen: gegen den Stand davor schlaegt test_gelesene_spalten_existieren
mit "no such column: l.pruefstelle" fehl.
"""
from __future__ import annotations

import re
import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w


def _frische_db(tmp_path) -> sqlite3.Connection:
    """Genau der Zustand einer Erstinstallation: schema.sql, sonst nichts.
    Kein Migrationslauf, keine Handtabelle -- sonst prueft der Test wieder
    seine eigene Annahme."""
    conn = sqlite3.connect(str(tmp_path / "erstinstallation.db"))
    conn.executescript((WURZEL / "schema.sql").read_text(encoding="utf-8"))
    return conn


def test_gelesene_spalten_existieren(tmp_path):
    """Die Abfrage stammt WOERTLICH aus kern/raum_daten.py -- nicht
    nachgebaut, damit sie mit dem echten Leser altert."""
    conn = _frische_db(tmp_path)
    conn.execute(
        "SELECT l.id, l.description, l.type, l.first_seen, l.severity, "
        "l.projects, l.pruefstelle, e.vector "
        "FROM lessons_learned l JOIN knowledge_embeddings e "
        "ON e.ref_id = l.id AND e.kind='lesson'"
    ).fetchall()
    conn.execute("SELECT text_checksum FROM knowledge_embeddings").fetchall()


def test_die_abfrage_steht_so_wirklich_im_leser():
    """Ohne diese Probe koennte der Test oben eine Abfrage pruefen, die
    niemand mehr benutzt -- gruen, und trotzdem wertlos."""
    quelle = (WURZEL / "kern" / "raum_daten.py").read_text(encoding="utf-8")
    assert "l.pruefstelle" in quelle, (
        "kern/raum_daten.py liest l.pruefstelle nicht mehr -- dann gehoert "
        "entweder dieser Test angepasst oder die Spalte geprueft, ob sie noch "
        "jemand braucht")


def test_jede_gelesene_lessons_spalte_steht_in_schema_sql():
    """Die Ratsche: nicht nur die eine bekannte Spalte, sondern jede, die ein
    Leser aus lessons_learned zieht. Eine Regel, die nur den bekannten Fall
    abdeckt, ist eine Liste."""
    schema = (WURZEL / "schema.sql").read_text(encoding="utf-8")
    tabelle = re.search(r"CREATE TABLE IF NOT EXISTS lessons_learned \((.*?)\n\);",
                        schema, re.S).group(1)
    spalten = {m.group(1) for m in re.finditer(r"^\s{4}([a-z_]+)\s+[A-Z]", tabelle, re.M)}
    fehlend = set()
    for datei in sorted((WURZEL / "kern").glob("*.py")):
        # Nicht von einer Klammer gefolgt: sonst faengt das Muster
        # Python-Methodenaufrufe auf einer Variablen namens `l` -- gemessen
        # l.strip(), l.get(). ponytail: Textmerkmal statt Parser. Deckenwert --
        # ein Alias, der nicht `l` heisst, faellt durch; auf einen SQL-Parser
        # umstellen, sobald so ein Fall auftritt.
        for m in re.finditer(r"\bl\.([a-z_]+)\b(?!\s*\()", datei.read_text(encoding="utf-8")):
            # SQLite supplies rowid for ordinary tables; it is intentionally
            # not a declared schema column (used by FTS bookkeeping).
            if m.group(1) not in spalten and m.group(1) not in {"id", "rowid"}:
                fehlend.add((datei.name, m.group(1)))
    assert not fehlend, (
        "Spalten, die ein Leser aus lessons_learned zieht, fehlen in schema.sql: "
        + ", ".join(f"{d}:{s}" for d, s in sorted(fehlend))
        + " -- eine Erstinstallation bricht daran, ein gewachsener Bestand nicht")
