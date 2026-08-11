#!/usr/bin/env python3
"""Eine Tuer zur Wissensdatenbank statt hundert -- die Naht vor dem Umzug.

ANLASS, gemessen am 2026-08-11: Ab 14:10 konnte keine Sitzung mehr schreiben.
Eine einzige Verbindung eines fremden Serverprozesses hielt die Schreibsperre
und war dabei untaetig (0,68 s Rechenzeit in 2:40 h). Der Fix sitzt seit
9ab128d im Server -- aber die Fehlerklasse lebt weiter, weil 100
Produktivdateien ihre Verbindung SELBST oeffnen. Jede davon kann dasselbe noch
einmal tun, und keine Regel im Klartext haelt das auf.

Dieselbe Zahl ist auch der Preis eines spaeteren Datenbankwechsels: 78 Dateien
(100 minus 22 einmalige Migrationsskripte) plus 67 Testdateien haengen direkt
an sqlite3. Nicht die Datenmenge macht einen Umzug teuer -- 65 MB sind ein
Nachmittag -- sondern dass es keine Stelle gibt, an der man ihn vornehmen
koennte. Diese Datei ist diese Stelle.

ZWEI TUEREN, und der Unterschied ist der ganze Punkt:

    with speicher.lesen() as conn:     # kann NICHT schreiben (mode=ro)
    with speicher.schreiben() as conn: # Transaktion, commit/rollback, close

lesen() oeffnet nur-lesend auf Dateiebene. Ein Schreibversuch scheitert dort
sofort und laut, statt still zu gelingen -- damit ist "das liest nur" keine
Behauptung mehr, sondern eine Eigenschaft. Diese Sorte Zusicherung im
Quelltext hat hier schon zweimal nicht getragen (L-a69129: eine Regel im
Klartext aendert das Verhalten nicht).

schreiben() nimmt die Schreibsperre AM ANFANG (BEGIN IMMEDIATE), nicht beim
ersten INSERT. Das ist der Unterschied zwischen "scheitert sofort, nichts
passiert" und "scheitert mitten drin, halb geschrieben". Und es schliesst im
finally -- die Fehlerklasse vom 2026-08-11 kann durch diese Tuer nicht mehr
entstehen.

WAS HIER BEWUSST NICHT DRIN IST: kein Verbindungsvorrat, kein Wiederholen,
kein Abbildungsschicht-Aufbau. busy_timeout erledigt das Warten, SQLite den
Rest. Ein Vorrat waere Vorbau fuer eine Last, die es nicht gibt (gemessen:
2102 Knoten, 763 Lehren).

WAS ER SPAETER MOEGLICH MACHT, ohne dass heute etwas dafuer gebaut wird: Wird
aus dem Dateizugriff einmal ein Dienst oder ein Postgres, aendert sich diese
Datei -- nicht die aufrufende. Das ist kein Versprechen auf Vorrat, sondern
die schlichte Folge davon, dass es nur eine Stelle gibt.

Aufruf:
    python3 speicher.py --selftest
"""
from __future__ import annotations

import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent / "haken"))
import ort  # noqa: E402

# 2 s wie im Server (knowledge_mcp_server.BUSY_TIMEOUT_MS). Bewusst derselbe
# Wert und nicht groesser: eine laengere Wartezeit verdeckt genau den Fall,
# der am 2026-08-11 stundenlang unbemerkt blieb -- ein Halter, der nie fertig
# wird. Wer lange wartet, merkt spaet.
BUSY_TIMEOUT_MS = 2000


@contextmanager
def lesen(db: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Nur-lesender Zugang. Ein Schreibversuch scheitert, statt zu gelingen.

    Zweiter, heute selbst erlittener Nutzen (L-0f4036): mode=ro legt eine
    fehlende Datei NICHT an. Ohne ihn erzeugt ein Tippfehler im Pfad eine
    leere Datenbank, und die naechste Messung zaehlt null und sieht aus wie
    ein Befund.
    """
    pfad = Path(db or ort.DB)
    conn = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def schreiben(db: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Schreibender Zugang: eine Transaktion, die entweder ganz gilt oder gar
    nicht -- und deren Sperre in jedem Fall zurueckgegeben wird.

    BEGIN IMMEDIATE steht am Anfang, damit ein besetzter Schreibplatz sofort
    auffaellt statt nach der halben Arbeit. commit() bei Erfolg, rollback()
    bei jeder Ausnahme, close() im finally -- in dieser Reihenfolge, weil ein
    close() ohne vorheriges rollback() den Ausgang der Aufraeumreihenfolge
    ueberlaesst.
    """
    pfad = Path(db or ort.DB)
    conn = sqlite3.connect(str(pfad), timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except BaseException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def _selftest() -> None:
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    db = tmp / "probe.db"

    # Aufbau ueber die schreibende Tuer -- ein Fall zaehlt nur, wenn er den
    # echten Weg nimmt.
    with schreiben(db) as conn:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, wert TEXT)")
        conn.execute("INSERT INTO t (wert) VALUES ('eins')")

    # 1) Was begangen wurde, ist da.
    with lesen(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1

    # 2) Eine geplatzte Schreibung hinterlaesst NICHTS -- weder Satz noch Sperre.
    try:
        with schreiben(db) as conn:
            conn.execute("INSERT INTO t (wert) VALUES ('geist')")
            raise RuntimeError("mitten drin geplatzt")
    except RuntimeError:
        pass
    with lesen(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t WHERE wert='geist'").fetchone()[0] == 0, \
            "die geplatzte Schreibung wurde nicht zurueckgerollt"
    with schreiben(db) as conn:      # kommt sofort dran -> keine Sperre haengen geblieben
        conn.execute("SELECT 1")

    # 3) Gegenprobe zur Nur-Lese-Tuer: ein Schreibversuch MUSS scheitern.
    #    Ohne diesen Fall waere 'lesen' nur ein Name.
    try:
        with lesen(db) as conn:
            conn.execute("INSERT INTO t (wert) VALUES ('schmuggel')")
        raise AssertionError("durch die Lesetuer wurde geschrieben")
    except sqlite3.OperationalError:
        pass
    with lesen(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM t WHERE wert='schmuggel'").fetchone()[0] == 0

    # 4) Eine fehlende Datei wird beim Lesen NICHT angelegt (L-0f4036).
    fehlt = tmp / "gibtsnicht.db"
    try:
        with lesen(fehlt) as conn:
            conn.execute("SELECT 1")
        raise AssertionError("fehlende Datenbank wurde klanglos geoeffnet")
    except sqlite3.OperationalError:
        pass
    assert not fehlt.exists(), "die Lesetuer hat eine leere Datenbank angelegt"

    print("selftest ok (4 Faelle, Gegenprobe in beide Richtungen)", file=sys.stderr)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
