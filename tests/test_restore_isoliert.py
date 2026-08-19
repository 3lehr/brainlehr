"""Restore-Test fuer BDW-E16 -- eine Sicherung wird in eine ISOLIERTE
Umgebung zurueckgespielt und dort auf Vollstaendigkeit und Lesbarkeit
geprueft, inklusive der ADR-029-Zusicherung: nach Vernichtung eines
Schluessels ist der Inhalt AUCH IN DER WIEDERHERGESTELLTEN Sicherung
unlesbar, waehrend die Tatsache seiner Existenz erhalten bleibt.

Ruehrt weder ort.DB noch eine laufende Sitzung an: Quelle, Sicherung und
Restore-Ziel sind ausschliesslich selbst angelegte tmp-Dateien (kein
Schnappschuss-Mechanismus dieses Tests haengt an ort.WURZEL). Alles laeuft
in einem einzigen TemporaryDirectory, das am Ende dieses Tests wieder
verschwindet -- kein Verzeichnis, keine Datei bleibt liegen.

Sieht der Code anders aus als hier beschrieben: dem Code folgen, Abweichung
melden. Harness-Abweichung ist ein Befund, nicht selbst umgehen.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WURZEL))
sys.path.insert(0, str(WURZEL / "kern"))

import schnappschuss  # noqa: E402
from kundenschluessel import KeinSchluessel, Kundenschluesselspeicher  # noqa: E402

TS0 = 1_700_000_000.0


def _neue_inhalts_db(pfad: Path) -> None:
    """Minimaler Bestand: eine Tabelle fuer chiffrierte Wissensinhalte,
    genau die Form, die eine echte DB-Sicherung (schnappschuss.py) traegt --
    Chiffretext und Metadaten, nie einen Schluessel."""
    conn = sqlite3.connect(str(pfad))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            "CREATE TABLE inhalte (ref TEXT PRIMARY KEY, blob BLOB, angelegt_ts REAL)"
        )
        conn.commit()
    finally:
        conn.close()


def _ablegen(pfad: Path, ref: str, blob: bytes, ts: float) -> None:
    conn = sqlite3.connect(str(pfad))
    try:
        conn.execute(
            "INSERT INTO inhalte (ref, blob, angelegt_ts) VALUES (?, ?, ?)",
            (ref, blob, ts),
        )
        conn.commit()
    finally:
        conn.close()


def _aufbau(arbeitsordner: Path) -> tuple[Path, bytes]:
    """Baut den 'lebenden' Bestand: zwei Refs. ref-vernichtet wird VOR der
    Sicherung widerrufen (Schluessel weg) -- das ist der Normalfall einer
    abgelaufenen Frist (kern/aufbewahrung.py::fristlauf). Gibt den Pfad der
    Quell-DB und den extern verwahrten Schluessel des UEBERLEBENDEN Refs
    zurueck -- genau das, was `sichern()` an den Aufrufer liefert, damit er
    es ausserhalb dieses Prozesses aufhebt."""
    quelle_db = arbeitsordner / "inhalte.db"
    _neue_inhalts_db(quelle_db)

    speicher = Kundenschluesselspeicher()

    speicher.neuer_schluessel("ref-ueberlebt", TS0)
    speicher.ablegen("ref-ueberlebt", "Klartext, der ueberlebt", TS0)
    schluessel_ueberlebt = speicher.sichern("ref-ueberlebt")
    _ablegen(quelle_db, "ref-ueberlebt", speicher.chiffretext("ref-ueberlebt"), TS0)

    speicher.neuer_schluessel("ref-vernichtet", TS0)
    speicher.ablegen("ref-vernichtet", "Klartext, der vernichtet wird", TS0)
    _ablegen(quelle_db, "ref-vernichtet", speicher.chiffretext("ref-vernichtet"), TS0)
    speicher.widerrufen("ref-vernichtet")  # Schluessel weg, VOR der Sicherung

    return quelle_db, schluessel_ueberlebt


def test_restore_isoliert_vollstaendig_und_adr029_zusicherung():
    with tempfile.TemporaryDirectory(prefix="brainlehr_restore_test_") as td:
        arbeitsordner = Path(td)
        quelle_db, schluessel_ueberlebt = _aufbau(arbeitsordner)

        # 1) Sicherung ziehen -- WAL-konsistente Online-Backup-Kopie, EXPLIZIT
        #    gegen die selbst angelegte Quelle, niemals gegen ort.DB.
        sicherungsordner = arbeitsordner / "sicherungen"
        stand = schnappschuss.festhalten(quelle_db, sicherungsordner)

        # 2) ISOLIERTE Umgebung: frischer, leerer Kundenschluesselspeicher --
        #    nichts aus dem Aufbau oben wird wiederverwendet ausser der
        #    Sicherung selbst und dem extern verwahrten Schluessel.
        restore_speicher = Kundenschluesselspeicher()
        with schnappschuss.lesen(stand) as conn:
            zeilen = conn.execute(
                "SELECT ref, blob, angelegt_ts FROM inhalte ORDER BY ref"
            ).fetchall()

        # Vollstaendigkeit: beide Zeilen sind da, unabhaengig vom Schluesselstatus.
        assert {r["ref"] for r in zeilen} == {"ref-ueberlebt", "ref-vernichtet"}, (
            "Sicherung unvollstaendig -- eine Zeile fehlt"
        )

        for row in zeilen:
            restore_speicher.inhalt_wiederherstellen(row["ref"], row["blob"], row["angelegt_ts"])

        # Nur der Schluessel des UEBERLEBENDEN Refs kommt aus der externen
        # Verwahrung zurueck -- fuer ref-vernichtet gibt es keinen (er wurde
        # nie gesichert, weil er vor der Sicherung widerrufen wurde).
        restore_speicher.wiederherstellen("ref-ueberlebt", schluessel_ueberlebt, TS0)

        # POSITIVFALL: unversehrte Sicherung + richtiger Schluessel -> lesbar.
        assert restore_speicher.lesen("ref-ueberlebt") == "Klartext, der ueberlebt"

        # ADR-029-ZUSICHERUNG: Tatsache bleibt, Inhalt bleibt unlesbar.
        assert restore_speicher.hat_bestanden("ref-vernichtet")
        assert restore_speicher.angelegt_ts("ref-vernichtet") == TS0
        try:
            restore_speicher.lesen("ref-vernichtet")
            raise AssertionError(
                "ref-vernichtet haette auch in der wiederhergestellten Sicherung "
                "unlesbar sein muessen"
            )
        except KeinSchluessel:
            pass


def test_restore_erkennt_beschaedigte_sicherung():
    """Gegenprobe zur anderen Richtung: eine BESCHAEDIGTE Sicherung liefert
    keinen falschen Klartext, sondern faellt beim Entschluesseln auf --
    AESGCM ist ein authentifizierender Modus, ein veraendertes Byte im
    Chiffretext scheitert an der Tag-Pruefung, nicht an einer stillen
    Verzerrung."""
    with tempfile.TemporaryDirectory(prefix="brainlehr_restore_test_") as td:
        arbeitsordner = Path(td)
        quelle_db, schluessel_ueberlebt = _aufbau(arbeitsordner)

        sicherungsordner = arbeitsordner / "sicherungen"
        stand = schnappschuss.festhalten(quelle_db, sicherungsordner)

        with schnappschuss.lesen(stand) as conn:
            zeilen = conn.execute("SELECT ref, blob, angelegt_ts FROM inhalte").fetchall()
        blobs = {r["ref"]: (r["blob"], r["angelegt_ts"]) for r in zeilen}

        # Ein Bit im Chiffretext von ref-ueberlebt kippen -- simuliert eine
        # beschaedigte Sicherung (Bitrot, unvollstaendige Kopie).
        blob_kaputt = bytearray(blobs["ref-ueberlebt"][0])
        blob_kaputt[-1] ^= 0x01

        restore_speicher = Kundenschluesselspeicher()
        restore_speicher.inhalt_wiederherstellen(
            "ref-ueberlebt", bytes(blob_kaputt), blobs["ref-ueberlebt"][1]
        )
        restore_speicher.wiederherstellen("ref-ueberlebt", schluessel_ueberlebt, TS0)

        try:
            restore_speicher.lesen("ref-ueberlebt")
            raise AssertionError(
                "eine beschaedigte Sicherung haette beim Entschluesseln auffallen muessen, "
                "nicht stillschweigend (falschen) Klartext liefern"
            )
        except Exception as exc:  # AESGCM wirft cryptography.exceptions.InvalidTag
            assert "InvalidTag" in type(exc).__name__, (
                f"erwartete InvalidTag, bekam {type(exc).__name__}: {exc}"
            )

        # Gegenprobe in die andere Richtung, in derselben Sicherung: eine
        # UNVERSEHRTE Zeile (ref-vernichtet, hier nur die Tatsache) bleibt von
        # der Beschaedigung der anderen Zeile unberuehrt.
        restore_speicher.inhalt_wiederherstellen(
            "ref-vernichtet", *blobs["ref-vernichtet"]
        )
        assert restore_speicher.hat_bestanden("ref-vernichtet")


if __name__ == "__main__":
    test_restore_isoliert_vollstaendig_und_adr029_zusicherung()
    test_restore_erkennt_beschaedigte_sicherung()
    print("test_restore_isoliert.py: selftest ok (2 Faelle)")
