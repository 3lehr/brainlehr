"""Fehlende Spalten aus schema.sql nachziehen -- generisch statt je Spalte.

Fehlklasse, gegen die dieses Modul steht: In knowledge_mcp_server.py wuchs
je nachgezogener Spalte eine eigene Funktion (`_ensure_anlass_columns`,
`_ensure_abgeleitet_von_column`, `_ensure_norm_art_column`, ... vierzehn
Stueck). Wer beim Anlegen einer Spalte die passende vergisst, merkt nichts:
`schema.sql` und die gewachsene Betriebsdatenbank laufen auseinander, und der
Bruch zeigt sich erst auf einer Datenbank, die aus `schema.sql` entstanden
ist -- als roher `sqlite3.OperationalError` mitten im Schreibpfad.

Am 2026-08-10 lag das mehrere Spalten tief hintereinander: `freigabe` an
knowledge_nodes (die Nachzugsfunktion daneben zog nur lessons_learned nach und
zitierte dabei die Lehre, die genau das verbietet), danach `gattung`. Eine
Handliste, die dreimal in Folge unvollstaendig ist, ist die falsche Bauform.

Was dieses Modul NICHT tut: raten. Nachgezogen werden nur einzeilige
Spaltendefinitionen, die SQLite per ALTER TABLE ADD COLUMN annimmt. Alles
andere (mehrzeilige CHECKs, PRIMARY KEY, NOT NULL ohne DEFAULT, gerechnete
DEFAULTs) bleibt liegen -- ein gemeldeter Rest ist besser als ein stiller
Teilnachzug, denn genau der ist die Fehlklasse oben.
"""
from __future__ import annotations

import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
SCHEMA = WURZEL / "schema.sql"

# Tabellen, deren Spalten nachgezogen werden. Bewusst eine Aufzaehlung und
# nicht "alle": FTS-Schattentabellen vertragen kein ALTER, und eine
# Bergungstabelle wie lost_and_found soll gar nicht mitwachsen.
TABELLEN = ("knowledge_nodes", "lessons_learned", "knowledge_relations", "access_log")


def _tabellenkoerper(schema: str, tabelle: str) -> str | None:
    m = re.search(rf"CREATE TABLE (?:IF NOT EXISTS )?{tabelle} \((.*?)\n\);",
                  schema, flags=re.DOTALL)
    return m.group(1) if m else None


def spalten_aus_schema(schema: str, tabelle: str) -> dict[str, str]:
    """Spaltenname -> Definition, nur was ALTER TABLE ADD COLUMN annimmt.

    Erkannt wird eine Spaltenzeile an genau vier fuehrenden Leerzeichen --
    dieselbe Einrueckung, die schema.sql durchgaengig benutzt. Kommentare und
    das abschliessende Komma fallen weg."""
    koerper = _tabellenkoerper(schema, tabelle)
    if koerper is None:
        return {}
    gefunden: dict[str, str] = {}
    for zeile in koerper.splitlines():
        if not re.match(r"^ {4}\w+ ", zeile):
            continue
        rest = re.sub(r"\s*--.*$", "", zeile.strip()).rstrip().rstrip(",")
        name, _, definition = rest.partition(" ")
        if not definition:
            continue
        # Tabellen-Constraints stehen auf derselben Einrueckung wie Spalten
        # und saehen sonst wie eine Spalte namens FOREIGN/UNIQUE/CHECK aus.
        if name.upper() in ("FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "PRIMARY"):
            continue
        gross = definition.upper()
        if "PRIMARY KEY" in gross:
            continue
        if "NOT NULL" in gross and "DEFAULT" not in gross:
            continue
        # Ein DEFAULT, das erst zur Laufzeit gerechnet wird (strftime,
        # CURRENT_*), lehnt SQLite bei ADD COLUMN ab -- auch wenn die Spalte
        # in CREATE TABLE genau so steht.
        if re.search(r"DEFAULT\s*\(", definition, flags=re.I):
            continue
        gefunden[name] = definition
    return gefunden


def fehlende(conn: sqlite3.Connection, schema: str) -> dict[str, dict[str, str]]:
    """Je Tabelle die Spalten, die schema.sql kennt und die Datenbank nicht."""
    vorhandene_tabellen = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    offen: dict[str, dict[str, str]] = {}
    for tabelle in TABELLEN:
        if tabelle not in vorhandene_tabellen:
            continue
        ist = {r[1] for r in conn.execute(f"PRAGMA table_info({tabelle})")}
        soll = spalten_aus_schema(schema, tabelle)
        luecke = {n: d for n, d in soll.items() if n not in ist}
        if luecke:
            offen[tabelle] = luecke
    return offen


def nachziehen(conn: sqlite3.Connection, schema: str | None = None,
               db_path: Path | None = None) -> dict[str, list[str]]:
    """Fehlende Spalten ergaenzen. Gibt zurueck, was ergaenzt wurde.

    Idempotent: ein zweiter Lauf findet nichts mehr und schreibt nicht --
    weder eine Spalte noch eine Sicherung.

    Mit `db_path` wird vor dem ERSTEN ALTER gesichert: WAL-Checkpoint, dann
    Dateikopie. Beides gehoert zusammen (Lehre L-218f1e: ein blosser copy2 im
    WAL-Betrieb kann committete, aber noch nicht zurueckgeschriebene Zeilen
    verlieren). Ist der Checkpoint blockiert, wird NICHT stumm weiter-ALTERt,
    sondern abgebrochen -- lieber ein sprechender Fehler als eine Aenderung
    ohne Rueckweg."""
    if schema is None:
        schema = SCHEMA.read_text(encoding="utf-8")
    offen = fehlende(conn, schema)
    if not offen:
        return {}

    if db_path is not None:
        busy, log_frames, checkpointed = conn.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if busy:
            raise RuntimeError(
                f"Spalten fehlen ({ {t: sorted(s) for t, s in offen.items()} }), aber die "
                f"Sicherung vor dem Nachzug ist blockiert (WAL-Checkpoint busy={busy}, "
                f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
                "gerade ein anderer Prozess auf dieselbe Datenbank. Nachzug abgebrochen, "
                "nichts geaendert."
            )
        if Path(db_path).exists():
            stempel = datetime.now().strftime("%Y%m%dT%H%M%S")
            ziel = Path(db_path).parent / f"{Path(db_path).name}.bak-{stempel}"
            shutil.copy2(db_path, ziel)

    ergaenzt: dict[str, list[str]] = {}
    for tabelle, luecke in offen.items():
        for name, definition in luecke.items():
            conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN {name} {definition}")
            ergaenzt.setdefault(tabelle, []).append(name)
    return ergaenzt


def _selftest() -> None:
    schema = SCHEMA.read_text(encoding="utf-8")

    soll = spalten_aus_schema(schema, "knowledge_nodes")
    assert "freigabe" in soll, "freigabe nicht aus schema.sql gelesen"
    assert "gattung" in soll, "gattung nicht aus schema.sql gelesen"
    assert "id" not in soll, "PRIMARY KEY darf nicht nachgezogen werden"

    # Alt-Datenbank: dieselbe Tabelle ohne die spaeten Spalten.
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, path TEXT)")
    conn.execute("INSERT INTO knowledge_nodes (id, path) VALUES ('n1', '/x')")

    offen = fehlende(conn, schema)
    assert "freigabe" in offen["knowledge_nodes"], offen

    ergaenzt = nachziehen(conn, schema)
    danach = {r[1] for r in conn.execute("PRAGMA table_info(knowledge_nodes)")}
    assert "freigabe" in danach and "gattung" in danach, sorted(danach)
    assert "freigabe" in ergaenzt["knowledge_nodes"], ergaenzt

    # Bestandszeile ueberlebt, und der Vorgabewert steht.
    zeile = conn.execute("SELECT id, freigabe FROM knowledge_nodes").fetchone()
    assert zeile == ("n1", "intern"), zeile

    # Zweiter Lauf ist ein Nulldurchgang -- sonst waere jede Verbindung ein
    # Schreibzugriff.
    assert nachziehen(conn, schema) == {}, "zweiter Lauf haette geschrieben"

    # Negativfall: eine Datenbank ohne diese Tabellen erzeugt keinen Fehler.
    leer = sqlite3.connect(":memory:")
    assert fehlende(leer, schema) == {}, "leere DB darf nichts melden"

    print("schema_nachzug: alle Proben bestanden")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        conn = sqlite3.connect(str(WURZEL / "knowledge.db"))
        print(fehlende(conn, SCHEMA.read_text(encoding="utf-8")) or "nichts offen")
