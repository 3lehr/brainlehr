"""Ein Tabellenneubau darf die Schranken der Tabelle nicht mitreissen.

Aufgabe 111 Schritt 2. Der Test existiert wegen eines Fehlers, den ich selbst
gemacht habe -- und er steht hier, statt stillschweigend behoben zu sein, weil
die Fehlerklasse groesser ist als dieser eine Fall.

WAS PASSIERT IST, 2026-08-14: migrationen/lauf_utc_vorgabewerte_2026-08-14.py
baute drei Tabellen neu, um ihren Zeitstempel-Vorgabewert auf UTC zu ziehen.
`DROP TABLE` nimmt in SQLite ALLE Indizes und Trigger der Tabelle mit. Der
Lauf loeschte damit 52 von 96 Schemaobjekten -- 7 Indizes und 45 Trigger,
darunter jede einzelne Norm- und Herkunftsschranke.

DIE DATEN WAREN UNVERSEHRT. Die Zusicherungen darueber waren weg. Eine
Datenbank ohne Trigger verhaelt sich voellig normal -- bis zum ersten
Schreibvorgang, den eigentlich eine Schranke haette abweisen muessen. Es gibt
keine Fehlermeldung, nur eine Zeile, die es nicht geben duerfte.

GEFUNDEN HAT ES NICHT DAS SKRIPT, sondern melder/schemastand.py beim naechsten
Aufruf: "49 in schema.sql, aber NICHT installiert". Der Melder aus Aufgabe 96
hat sich an einem Tag zweimal bezahlt gemacht, beide Male an einem Fehler, den
er nicht kennen konnte.

UND DREI DER TRIGGER STEHEN GAR NICHT IN schema.sql
(knowledge_nodes_herkunft_bu, knowledge_nodes_norm_entschieden_belegart_
pflicht_bi, lessons_herkunft_bu). Wer sie "einfach aus schema.sql neu erzeugt"
haette, haette sie endgueltig verloren -- die Wiederherstellung lief deshalb
aus einer Dateikopie, nicht aus dem Schema.

Rot vor gruen: gegen die Fassung ohne Sicherung der Anhaengsel ist
test_indizes_und_trigger_ueberleben_den_neubau rot.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
WURZEL = _w
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in ("kern", "haken", "melder")]

import pytest  # noqa: E402

import speicher  # noqa: E402

SKRIPT = WURZEL / "migrationen" / "lauf_utc_vorgabewerte_2026-08-14.py"
ALTER_VORGABEWERT = "strftime('%Y-%m-%dT%H:%M:%S+01:00', 'now', 'localtime')"


def _lade_migration():
    spec = importlib.util.spec_from_file_location("utc_migration", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture()
def alte_db(tmp_path, monkeypatch):
    """Eine Datenbank im Zustand VOR der Umstellung: alter Vorgabewert, dazu
    ein Index und ein Trigger, wie sie im Bestand an den Tabellen haengen."""
    pfad = tmp_path / "alt.db"
    conn = sqlite3.connect(str(pfad))
    conn.execute(f"""
        CREATE TABLE access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_path TEXT,
            action TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT ({ALTER_VORGABEWERT})
        )""")
    conn.execute("CREATE INDEX idx_probe_action ON access_log(action)")
    conn.execute("""
        CREATE TRIGGER access_log_action_check_bi BEFORE INSERT ON access_log
        WHEN NEW.action NOT IN ('read', 'search')
        BEGIN SELECT RAISE(ABORT, 'unbekannte Aktion'); END""")
    conn.executemany("INSERT INTO access_log (node_path, action) VALUES (?, 'read')",
                     [(f"/p/{i}",) for i in range(5)])
    conn.commit()
    conn.close()
    monkeypatch.setattr(speicher, "STANDARD_DB", pfad, raising=False)
    return pfad


def _lauf(pfad, monkeypatch):
    modul = _lade_migration()
    monkeypatch.setattr(modul, "BETROFFEN", ("access_log",))
    original = modul.speicher.schreiben

    def schreiben(db=None):
        return original(pfad)

    monkeypatch.setattr(modul.speicher, "schreiben", schreiben)
    modul.main()


def test_indizes_und_trigger_ueberleben_den_neubau(alte_db, monkeypatch):
    """Der Kern. Rot gegen die Fassung ohne Sicherung der Anhaengsel."""
    _lauf(alte_db, monkeypatch)

    conn = sqlite3.connect(str(alte_db))
    objekte = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('index','trigger') AND sql IS NOT NULL")}
    conn.close()
    assert "idx_probe_action" in objekte, "der Index wurde vom DROP TABLE mitgerissen"
    assert "access_log_action_check_bi" in objekte, (
        "der Trigger wurde mitgerissen -- die Daten waeren unversehrt, die "
        "Zusicherung darueber weg, und nichts wuerde es melden")


def test_der_trigger_wirkt_danach_noch(alte_db, monkeypatch):
    """Ein Trigger, der nur wieder DASTEHT, ist nicht dasselbe wie einer, der
    wieder WIRKT. Ohne diese Probe koennte die Wiederherstellung eine leere
    Huelle anlegen und der Test darueber waere trotzdem gruen."""
    _lauf(alte_db, monkeypatch)

    conn = sqlite3.connect(str(alte_db))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO access_log (node_path, action) VALUES ('/x', 'loeschen')")
    conn.close()


def test_vorgabewert_steht_danach_auf_utc(alte_db, monkeypatch):
    _lauf(alte_db, monkeypatch)

    conn = sqlite3.connect(str(alte_db))
    conn.execute("INSERT INTO access_log (node_path, action) VALUES ('/neu', 'read')")
    conn.commit()
    wert = conn.execute("SELECT timestamp FROM access_log WHERE node_path='/neu'").fetchone()[0]
    conn.close()
    assert wert.endswith("Z"), f"Vorgabewert liefert weiter Ortszeit: {wert!r}"
    assert "+01:00" not in wert


def test_keine_zeile_geht_verloren(alte_db, monkeypatch):
    """Die Gegenzaehlung steht im Skript VOR dem DROP. Hier die Probe von
    aussen -- ein Skript, das sich selbst zaehlt, zaehlt nur sein Ergebnis."""
    conn = sqlite3.connect(str(alte_db))
    vorher = conn.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    conn.close()

    _lauf(alte_db, monkeypatch)

    conn = sqlite3.connect(str(alte_db))
    nachher = conn.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    conn.close()
    assert nachher == vorher == 5


def test_zweiter_lauf_aendert_nichts(alte_db, monkeypatch):
    """Idempotenz, und sie ist hier nicht Kosmetik: ein Skript, das beim
    zweiten Lauf erneut umbaut, reisst beim zweiten Mal wieder alles mit --
    falls die Sicherung je bricht."""
    _lauf(alte_db, monkeypatch)
    conn = sqlite3.connect(str(alte_db))
    stand = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE sql IS NOT NULL")}
    conn.close()

    _lauf(alte_db, monkeypatch)

    conn = sqlite3.connect(str(alte_db))
    stand2 = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE sql IS NOT NULL")}
    conn.close()
    assert stand == stand2
