"""Rot-vor-gruen fuer den Befund 2026-08-06: eine bestehende Datenbank ohne
die Spalte anlass liess knowledge_add mit einem rohen SQLite-Fehler
abbrechen (schreibpruefstand/demo/schreibpruefstand.db). Fix: ensure_schema()
holt die Spalte je Verbindung nach (siehe _ensure_anlass_columns), additiv,
mit WAL-Checkpoint + Sicherungskopie davor (Lehre L-218f1e).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

# Findet die Repo-Wurzel an schema.sql statt an einer Anzahl von Ebenen.
# Eine feste Ebenenzahl (parent.parent) bricht beim naechsten Umzug lautlos;
# ein Merkmal der Wurzel bricht nie. Danach liegen Wurzel und die beiden
# Ordner mit importierbaren Modulen im Suchpfad.
_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import re
import sqlite3
import sys
import time
from pathlib import Path

import pytest

SHARED_KNOWLEDGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SHARED_KNOWLEDGE))

import knowledge_mcp_server as kms  # type: ignore  # noqa: E402


def _old_schema_without_anlass() -> str:
    """Wie migrate_anlass.py::_selftest() -- echtes schema.sql, anlass-Block
    an beiden Tabellen herausgeschnitten, damit die Alt-DB nicht von Hand
    nachgebaut werden muss und garantiert synchron mit dem echten Schema
    bleibt."""
    schema_sql = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
    # abgeleitet_von TEXT.*?\n\); statt eines festen Endes: nicht-gierig bis
    # zur naechsten schliessenden Klammer, damit spaeter additiv angehaengte
    # Spalten (z.B. zurueckgezogen*, Auftrag 2026-08-06 Zuruecknahme) hier
    # automatisch mitentfernt werden, ohne dieses Muster jedes Mal
    # nachzuziehen -- alte DBs vor dem anlass-Feld kannten auch diese nicht.
    old_schema, n1 = re.subn(
        r",\n    -- Anlass \(Auftrag 2026-08-06\).*?anlass TEXT NOT NULL DEFAULT 'unbekannt',\n"
        r"(    -- abgeleitet_von.*?\n)*    abgeleitet_von TEXT.*?\n\);",
        "\n);", schema_sql, count=1, flags=re.DOTALL,
    )
    assert n1 == 1, "Anlass-Block an knowledge_nodes nicht wie erwartet gefunden"
    # Nicht-gierig bis zur naechsten schliessenden Klammer (statt eines festen
    # Endes) -- selber Grund wie beim knowledge_nodes-Muster oben: spaeter
    # additiv angehaengte Spalten (z.B. actor/session, Auftrag 2026-08-06
    # Schreiber-am-Datensatz) werden automatisch mitentfernt.
    old_schema, n2 = re.subn(
        r",(\s*-- 1 wenn bereits Regel generiert\n)"
        r"    anlass TEXT NOT NULL DEFAULT 'unbekannt'.*?\n\);",
        r"\1);", old_schema, count=1, flags=re.DOTALL,
    )
    assert n2 == 1, "Anlass-Spalte an lessons_learned nicht wie erwartet gefunden"
    # JEDER Trigger, der NEW.anlass nennt, muss mit heraus -- sonst ist jedes
    # INSERT ein "no such column: NEW.anlass" statt des hier zu simulierenden
    # Alt-Zustands. Bewusst ueber den INHALT gesucht statt ueber Triggernamen:
    # eine Namensliste altert. Genau daran ist dieser Test am 2026-08-10
    # gescheitert -- er kannte die beiden anlass_check-Trigger und nicht die
    # zwei spaeter dazugekommenen normrang_herkunft-Trigger, die NEW.anlass
    # ebenfalls lesen. Ein Wortlaut-Kriterium bricht beim naechsten Trigger
    # nicht mehr.
    entfallen = _entfallene_spalten(schema_sql, old_schema)
    assert "anlass" in entfallen["knowledge_nodes"], (
        f"anlass nicht ausgeschnitten (entfallen={entfallen})"
    )
    # Nur Trigger auf DIESEN beiden Tabellen pruefen: Spaltennamen sind nicht
    # eindeutig. knowledge_embeddings hat ebenfalls ein `model`, und sein
    # Pruef-Trigger ist voellig in Ordnung -- ihn mitzuschneiden hiesse, das
    # Alt-Schema an einer Stelle zu veraendern, die mit anlass nichts zu tun
    # hat.
    def betrifft(blk: str) -> str | None:
        treffer = re.search(r"\bON (knowledge_nodes|lessons_learned)\b", blk)
        return treffer.group(1) if treffer else None

    bloecke = re.findall(r"CREATE TRIGGER.*?\nEND;\n?", old_schema, flags=re.DOTALL)
    n3 = 0
    for blk in bloecke:
        tabelle = betrifft(blk)
        if tabelle and {m for m in re.findall(r"NEW\.(\w+)", blk)} & entfallen[tabelle]:
            old_schema = old_schema.replace(blk, "", 1)
            n3 += 1
    assert n3 >= 2, f"anlass-Trigger nicht wie erwartet gefunden (n={n3})"
    uebrig = {
        m
        for blk in re.findall(r"CREATE TRIGGER.*?\nEND;\n?", old_schema, flags=re.DOTALL)
        if (tabelle := betrifft(blk))
        for m in re.findall(r"NEW\.(\w+)", blk)
        if m in entfallen[tabelle]
    }
    assert not uebrig, f"Alt-Schema nennt weiter entfallene Spalten: {sorted(uebrig)}"
    # Dieselbe Behandlung fuer INDIZES, und zwar aus demselben Grund wie oben
    # bei den Triggern: Ein `CREATE INDEX ... ON knowledge_nodes(mandant)`
    # bricht auf dem Alt-Schema mit "no such column: mandant" ab. Am
    # 2026-08-21 ist genau das passiert, als B1 die ersten Indizes auf
    # NACHGEZOGENEN Spalten einfuehrte -- vorher gab es keinen einzigen
    # (freigabe, gattung, gedaechtnisart, anlass tragen alle keinen), deshalb
    # hat diese Luecke elf Monate lang nicht wehgetan. Wieder ueber den
    # INHALT bestimmt, nicht ueber eine Namensliste (L-1ffae7).
    for blk in re.findall(r"CREATE INDEX[^;]*;\n?", old_schema):
        tabelle = betrifft(blk)
        if tabelle and {m for m in re.findall(r"\((\w+)\)", blk)} & entfallen[tabelle]:
            old_schema = old_schema.replace(blk, "", 1)
    uebrig_idx = {
        m
        for blk in re.findall(r"CREATE INDEX[^;]*;", old_schema)
        if (tabelle := betrifft(blk))
        for m in re.findall(r"\((\w+)\)", blk)
        if m in entfallen[tabelle]
    }
    assert not uebrig_idx, f"Alt-Schema indiziert weiter entfallene Spalten: {sorted(uebrig_idx)}"
    return old_schema


def _entfallene_spalten(neu: str, alt: str) -> dict[str, set[str]]:
    """Spalten, die der Schnitt oben aus knowledge_nodes/lessons_learned
    entfernt hat. Wird gebraucht, um JEDEN Trigger mitzuentfernen, der eine
    davon liest -- sonst bricht die Alt-DB mit 'no such column: NEW.x'.

    Ueber den Inhalt bestimmt statt ueber eine Namensliste, weil eine Liste
    altert: derselbe Test fiel am 2026-08-10 zweimal hintereinander aus,
    erst wegen zweier neuer Trigger auf NEW.anlass, dann wegen NEW.freigabe.
    Beide Male war nicht der gepruefte Nachzug kaputt, sondern die
    Testvorrichtung veraltet."""
    def spalten(text: str) -> dict[str, set[str]]:
        gefunden: dict[str, set[str]] = {}
        for tab in ("knowledge_nodes", "lessons_learned"):
            m = re.search(rf"CREATE TABLE IF NOT EXISTS {tab} \((.*?)\n\);",
                          text, flags=re.DOTALL)
            if m:
                gefunden[tab] = set(re.findall(r"^\s{4}(\w+) ", m.group(1), flags=re.M))
            else:
                gefunden[tab] = set()
        return gefunden
    neu_spalten, alt_spalten = spalten(neu), spalten(alt)
    return {tab: neu_spalten[tab] - alt_spalten[tab] for tab in neu_spalten}


@pytest.fixture()
def old_db(tmp_path, monkeypatch):
    db_path = tmp_path / "alt_ohne_anlass.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_old_schema_without_anlass())
    conn.execute(
        "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, source, norm_entscheidung, "
        "norm_entschieden_von, norm_entschieden_grund) "
        "VALUES ('n1', '/x', 'shared', 'Bestandsknoten', 'x', 'x', 0, 'x', 'keine_norm', 'skript:test', 'Testvorrichtung')"
    )
    conn.execute(
        "INSERT INTO lessons_learned (id, type, description) VALUES ('L-1', 'insight', 'Bestandslehre')"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)
    return db_path


def test_rot_vor_fix_alte_db_wirft_rohen_sqlite_fehler(old_db):
    """Beweis, dass die Luecke real ist: OHNE den Nachzug (ensure_schema
    umgangen, Verbindung wie vor dem Fix von Hand aufgebaut) bricht INSERT
    mit dem rohen Fehlertext ab, den ein Betreiber nicht einordnen kann."""
    conn = sqlite3.connect(str(old_db))
    with pytest.raises(sqlite3.OperationalError, match="has no column named anlass"):
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, project_id, title, summary, "
            "content, level, tags, source, created_at, updated_at, norm_rang, gilt_ab, gilt_bis, anlass) "
            "VALUES ('n2','/y',NULL,'shared','t','s','c',0,'[]','src','now','now',NULL,NULL,NULL,'unbekannt')"
        )
    conn.close()


def test_knowledge_add_auf_alter_db_zieht_spalte_automatisch_nach(old_db):
    res = kms.knowledge_add("/", "Neuer Knoten", "Zusammenfassung", source="test")
    assert res.get("status") == "created", res

    conn = sqlite3.connect(str(old_db))
    cols = {row[1] for row in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    assert "anlass" in cols
    row = conn.execute("SELECT anlass FROM knowledge_nodes WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("unbekannt",), row


def test_lesson_record_auf_alter_db_zieht_lessons_spalte_nach(old_db):
    res = kms.lesson_record("insight", "Neuer Fund auf alter DB")
    assert res.get("status") == "recorded", res
    conn = sqlite3.connect(str(old_db))
    row = conn.execute("SELECT anlass FROM lessons_learned WHERE id = ?", (res["id"],)).fetchone()
    conn.close()
    assert row == ("unbekannt",), row


def test_nachzug_verliert_keine_bestandszeile(old_db):
    """Gegenprobe: Bestandszeile (vor dem Nachzug ohne anlass eingefuegt)
    bleibt nach dem automatischen ALTER TABLE erhalten und bekommt den
    Vorgabewert."""
    conn = sqlite3.connect(str(old_db))
    vorher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    conn.close()
    assert vorher == 1

    kms.knowledge_add("/", "Ausloeser fuer den Nachzug", "x", source="test")

    conn = sqlite3.connect(str(old_db))
    nachher = conn.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    row = conn.execute("SELECT title, anlass FROM knowledge_nodes WHERE id = 'n1'").fetchone()
    conn.close()
    assert nachher == vorher + 1, (vorher, nachher)
    assert row == ("Bestandsknoten", "unbekannt"), row


def test_backup_datei_entsteht_vor_dem_nachzug(old_db):
    kms.knowledge_add("/", "Loest Sicherung aus", "x", source="test")
    backups = list(old_db.parent.glob(f"{old_db.name}.bak-*"))
    assert len(backups) == 1, backups


def test_zweiter_lauf_auf_bereits_migrierter_db_ist_ein_reiner_noop(old_db):
    """Negativfall: vollstaendige DB (Spalte schon da) -> kein weiterer
    Nachzug, kein zweites Backup, Verhalten unveraendert."""
    kms.knowledge_add("/", "Erster Aufruf zieht nach", "x", source="test")
    backups_after_first = list(old_db.parent.glob(f"{old_db.name}.bak-*"))
    assert len(backups_after_first) == 1

    kms.knowledge_add("/", "Zweiter Aufruf auf bereits migrierter DB", "x", source="test")
    backups_after_second = list(old_db.parent.glob(f"{old_db.name}.bak-*"))
    assert len(backups_after_second) == 1, "zweiter Nachzug haette kein weiteres Backup erzeugen duerfen"


def test_kosten_pro_verbindung_bei_bereits_vollstaendiger_db(tmp_path, monkeypatch):
    """Kostenmessung fuer den Normalfall (Spalte vorhanden, wie bei jeder
    schon migrierten DB) -- PRAGMA table_info x2 pro Verbindung, kein Scan."""
    db_path = tmp_path / "vollstaendig.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript((SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()
    monkeypatch.setattr(kms, "DB_PATH", db_path)

    n = 200
    start = time.perf_counter()
    for _ in range(n):
        conn = kms.get_db()
        conn.close()
    elapsed_ms = (time.perf_counter() - start) * 1000 / n
    print(f"\nKosten je get_db()-Aufruf (inkl. ensure_schema, Spalte bereits vorhanden): {elapsed_ms:.3f} ms")
    assert elapsed_ms < 20, f"ensure_schema verzoegert jede Verbindung um {elapsed_ms:.3f} ms -- zu teuer"
