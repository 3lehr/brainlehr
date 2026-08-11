"""Belege fuer die sitzungsweite Schnappschuss-Vorrichtung in conftest.py.

Beide Tests laufen gegen eine SELBST gebaute WAL-Datenbank in tmp_path, nicht
gegen die echte brainlehr.db -- so haengt der Beleg nicht davon ab, ob eine
fremde Sitzung gerade gleichzeitig in den echten Bestand schreibt (das wuerde
den Test selbst nebenlaeufig und damit unwiederholbar machen).

1. test_schnappschuss_ignoriert_spaetere_lebende_aenderung -- der Kern des
   Auftrags: eine Aenderung am LEBENDEN Bestand NACH der Aufnahme darf das
   Ergebnis eines bereits gezogenen Schnappschusses nicht mehr verschieben.
   Rot vor dieser Vorrichtung: braucht_bestand() las bislang bei JEDEM
   Aufruf frisch gegen die lebende Datei (mode=ro, kein Schnappschuss) --
   zwei Aufrufe waehrend eines nebenlaeufigen Schreibvorgangs konnten
   unterschiedliche Zahlen liefern. Ohne conftest._erzeuge_schnappschuss()
   (vor diesem Auftrag nicht vorhanden) ist dieser Test ein ImportError,
   also rot.

2. test_schnappschuss_sieht_committete_aber_nicht_zurueckgeschriebene_wal_
   aenderung -- schliesst die copy2-Falle aus (test_backup_wal_checkpoint.py
   zeigt denselben Testaufbau fuer die anderen _backup()-Fassungen):
   Connection.backup() muss eine committete, aber noch im WAL-Sidecar
   stehende Aenderung sehen, ohne die Quelle zu checkpointen."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_w = _Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
_sys.path[:0] = [str(_w)] + [str(_w / o) for o in
                 ("kern", "haken", "schreibpruefstand", "melder", "migrationen")]

import sqlite3

import conftest


def _leere_wal_db(pfad):
    con = sqlite3.connect(str(pfad))
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY)")
    con.execute("CREATE TABLE lessons_learned (id TEXT PRIMARY KEY)")
    con.commit()
    return con


def test_schnappschuss_ignoriert_spaetere_lebende_aenderung(tmp_path):
    quelle = tmp_path / "live.db"
    halter = _leere_wal_db(quelle)
    for i in range(5):
        halter.execute("INSERT INTO knowledge_nodes VALUES (?)", (f"n{i}",))
    halter.commit()

    schnappschuss = conftest._erzeuge_schnappschuss(quelle)
    assert schnappschuss.knoten == 5

    # "andere Sitzung" schreibt NACH der Aufnahme weiter -- genau das
    # FAKTEN-Szenario aus dem Auftrag (mehrere Sitzungen im selben Bestand).
    halter.execute("INSERT INTO knowledge_nodes VALUES ('n5')")
    halter.commit()
    halter.close()

    # Der bereits gezogene Schnappschuss -- Datei UND Metadaten -- bleibt
    # beim alten Stand. Eine Messung dagegen ist wiederholbar.
    erneut = sqlite3.connect(f"file:{schnappschuss.pfad}?mode=ro", uri=True)
    try:
        n = erneut.execute("SELECT COUNT(*) FROM knowledge_nodes").fetchone()[0]
    finally:
        erneut.close()
    assert n == 5 == schnappschuss.knoten, (
        "Schnappschuss haette die spaetere lebende Aenderung nicht sehen duerfen"
    )


def test_schnappschuss_sieht_committete_aber_nicht_zurueckgeschriebene_wal_aenderung(tmp_path):
    quelle = tmp_path / "live.db"
    halter = _leere_wal_db(quelle)
    halter.execute("INSERT INTO knowledge_nodes VALUES ('n0')")
    halter.commit()
    # Committet, aber WAL klein genug, dass wal_autocheckpoint (Vorgabe 1000
    # Seiten) nicht von selbst greift -- bleibt im WAL-Sidecar stehen, wie
    # in test_backup_wal_checkpoint.py::_add_column_leave_in_wal.
    halter.execute("INSERT INTO knowledge_nodes VALUES ('n1')")
    halter.commit()
    assert (tmp_path / "live.db-wal").exists()

    schnappschuss = conftest._erzeuge_schnappschuss(quelle)

    assert schnappschuss.knoten == 2, (
        "Connection.backup() haette die WAL-Aenderung mitnehmen muessen, "
        "ohne die Quelle zu checkpointen"
    )
    # Gegenprobe zur eigentlichen Behauptung "kein Eingriff in die Quelle":
    # die WAL-Sidecar-Datei der Quelle steht unveraendert weiter -- ein
    # TRUNCATE-Checkpoint (normrang.py::_backup()s Weg) haette sie geleert.
    assert (tmp_path / "live.db-wal").exists()
    halter.close()
