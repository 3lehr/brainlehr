"""INT-SNAP-001 fuer kern/messlauf_abrufguete.py: der Lauf liest gegen einen
gepinnten Schnappschuss (kern/schnappschuss.py), nicht bei jedem Aufruf gegen
den lebendigen, wachsenden Bestand (docs/REQUIREMENTS_INTERFACE_KOMPAT.md).

ROT-Beleg vor dem Fix (hier als Gegenprobe nachgestellt): hook.DB zeigte
direkt auf die lebendige Datei -- eine Aenderung, die WAEHREND eines Laufs
committet wurde, war beim naechsten Lesen sofort sichtbar. GRUEN: mit
messlauf_abrufguete._gegen_schnappschuss() bleibt hook.DB fuer die Dauer des
Laufs auf dem gezogenen Stand, unabhaengig von Schreibungen an der Quelle.

Faehrt gegen eine eigene Wegwerf-DB (nicht den echten Bestand) --
_gegen_schnappschuss() nimmt dafuer optionale quelle/verzeichnis-Parameter.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w)] + [str(_w / "kern"), str(_w / "haken")]

import messlauf_abrufguete as m  # noqa: E402


def _lebendige_db(tmp: Path) -> Path:
    live = tmp / "live.db"
    conn = sqlite3.connect(str(live))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, wert TEXT)")
    conn.execute("INSERT INTO t (wert) VALUES ('vor')")
    conn.commit()
    conn.close()
    return live


def test_ohne_schnappschuss_sieht_lauf_aenderung_waehrend_des_laufs():
    """ROT-Probe: der Vorzustand (hook.DB == lebendige Datei, wie vor dem
    Fix) sieht eine Schreibung, die zwischen zwei Lesevorgaengen committet
    wird -- genau das Verhalten, das der Fix fuer den echten Lauf
    ausschliessen soll."""
    tmp = Path(tempfile.mkdtemp(prefix="messlauf_schnapp_rot_"))
    try:
        live = _lebendige_db(tmp)
        writer = sqlite3.connect(str(live))
        orig = m.hook.DB
        m.hook.DB = str(live)
        try:
            n1 = sqlite3.connect(m.hook.DB).execute("SELECT COUNT(*) FROM t").fetchone()[0]
            writer.execute("INSERT INTO t (wert) VALUES ('waehrend-lauf')")
            writer.commit()
            n2 = sqlite3.connect(m.hook.DB).execute("SELECT COUNT(*) FROM t").fetchone()[0]
        finally:
            m.hook.DB = orig
            writer.close()
        assert (n1, n2) == (1, 2), (
            f"ROT-Beleg erwartet 1->2 ohne Schnappschuss, war {n1}->{n2}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_mit_schnappschuss_sieht_lauf_aenderung_waehrend_des_laufs_nicht():
    """GRUEN: _gegen_schnappschuss() pinnt hook.DB -- dieselbe Schreibung
    waehrend des Laufs bleibt unsichtbar, und der Schnappschuss ist nach dem
    Lauf wieder entfernt (Punkt 4 des Auftrags)."""
    tmp = Path(tempfile.mkdtemp(prefix="messlauf_schnapp_gruen_"))
    try:
        live = _lebendige_db(tmp)
        verzeichnis = tmp / "schnappschuesse"
        writer = sqlite3.connect(str(live))

        with m._gegen_schnappschuss(quelle=live, verzeichnis=verzeichnis) as stand:
            n1 = sqlite3.connect(m.hook.DB).execute("SELECT COUNT(*) FROM t").fetchone()[0]
            writer.execute("INSERT INTO t (wert) VALUES ('waehrend-lauf')")
            writer.commit()
            n2 = sqlite3.connect(m.hook.DB).execute("SELECT COUNT(*) FROM t").fetchone()[0]
            kennung = stand.kennung
        writer.close()

        assert (n1, n2) == (1, 1), (
            f"GRUEN erwartet 1->1 mit Schnappschuss, war {n1}->{n2}"
        )
        assert not (verzeichnis / kennung).exists(), (
            "Schnappschuss haette nach dem Lauf aufgeraeumt sein muessen (Punkt 4)"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_zwei_laeufe_gegen_denselben_schnappschuss_liefern_dieselbe_zahl():
    """Wiederholungsprobe (Abnahme): derselbe Stand, zweimal gelesen, liefert
    dieselbe Zahl -- unabhaengig davon, was in der Zwischenzeit an der
    lebendigen Quelle passiert."""
    tmp = Path(tempfile.mkdtemp(prefix="messlauf_schnapp_wdh_"))
    try:
        live = _lebendige_db(tmp)
        verzeichnis = tmp / "schnappschuesse"
        writer = sqlite3.connect(str(live))

        with m._gegen_schnappschuss(quelle=live, verzeichnis=verzeichnis) as stand:
            n1 = sqlite3.connect(m.hook.DB).execute("SELECT COUNT(*) FROM t").fetchone()[0]
            writer.execute("INSERT INTO t (wert) VALUES ('zwischen-den-beiden-laeufen')")
            writer.commit()
            n2 = sqlite3.connect(m.hook.DB).execute("SELECT COUNT(*) FROM t").fetchone()[0]
        writer.close()

        assert n1 == n2 == 1, f"Wiederholungsprobe erwartet zweimal dieselbe Zahl, war {n1} und {n2}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def demo() -> None:
    test_ohne_schnappschuss_sieht_lauf_aenderung_waehrend_des_laufs()
    test_mit_schnappschuss_sieht_lauf_aenderung_waehrend_des_laufs_nicht()
    test_zwei_laeufe_gegen_denselben_schnappschuss_liefern_dieselbe_zahl()
    print("demo ok")


if __name__ == "__main__":
    demo()
