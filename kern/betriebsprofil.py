#!/usr/bin/env python3
"""Betriebsprofil -- Einzelplatz oder Unternehmen, mit Rueckweg.

BDW-P09: Vor der Installation waehlt der Nutzer `einzelplatz` (Vorgabe,
Auslieferungszustand) oder `unternehmen`. Die Mandanten-Achse liegt seit B1
im Schema (`mandant TEXT NOT NULL DEFAULT 'lokal'` an knowledge_nodes und
lessons_learned) -- der Wechsel ist deshalb eine DATENAENDERUNG (der Bestand
wandert geschlossen auf einen benannten Mandanten), kein Umbau.

Der Profilwert selbst liegt in knowledge_config (Schluessel/Wert, wie
embed_model) -- eine Zeile, keine Migration.

Namen sind Betreiberwort 2026-08-21: `einzelplatz` und `unternehmen`, nicht
`standalone`/`multiuser`.

VOR jedem Wechsel: WAL-Checkpoint + Dateikopie, wie
kern/schema_nachzug.py::nachziehen es tut -- ein Wechsel ohne Sicherung auf
Dateiebene waere fahrlaessig, kein Rueckweg.

Aufruf:
    python3 kern/betriebsprofil.py --selftest
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(WURZEL / "haken"), str(WURZEL / "kern")]

import ort  # noqa: E402
import speicher  # noqa: E402

EINZELPLATZ = "einzelplatz"
UNTERNEHMEN = "unternehmen"
PROFILE = (EINZELPLATZ, UNTERNEHMEN)
KONFIG_SCHLUESSEL = "betriebsprofil"
MANDANT_LOKAL = "lokal"

# Beide Tabellen tragen dieselbe Achse (Auftrag B1) -- ein Wechsel bewegt
# beide gemeinsam, sonst waere der Bestand nach dem Wechsel gespalten.
TABELLEN = ("knowledge_nodes", "lessons_learned")


def profil(db: Path | str | None = None) -> str:
    """Das eingestellte Profil, sonst die Vorgabe `einzelplatz`
    (Auslieferungszustand, BDW-P09)."""
    with speicher.lesen(db) as conn:
        row = conn.execute(
            "SELECT value FROM knowledge_config WHERE key = ?", (KONFIG_SCHLUESSEL,)
        ).fetchone()
    return row["value"] if row else EINZELPLATZ


def zaehlung(db: Path | str | None = None) -> dict[str, int]:
    """Bestandszaehlung -- muss vor und nach einem Wechsel gleich bleiben."""
    with speicher.lesen(db) as conn:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABELLEN}


def _sicherung(db_path: Path) -> Path:
    """WAL-Checkpoint, dann Dateikopie -- dieselbe Form wie
    kern/schema_nachzug.py::nachziehen. Bricht der Checkpoint (ein anderer
    Prozess schreibt gerade), wird NICHT stumm weitergewechselt."""
    conn = speicher.verbinde_bestand(db_path)
    try:
        busy, log_frames, checkpointed = conn.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        ).fetchone()
        if busy:
            raise RuntimeError(
                f"Sicherung vor Profilwechsel blockiert (WAL-Checkpoint busy={busy}, "
                f"{log_frames} Frames, {checkpointed} checkpointed) -- vermutlich schreibt "
                "gerade ein anderer Prozess. Wechsel abgebrochen, nichts geaendert."
            )
    finally:
        conn.close()
    stempel = datetime.now().strftime("%Y%m%dT%H%M%S")
    ziel = db_path.parent / f"{db_path.name}.bak-{stempel}"
    shutil.copy2(db_path, ziel)
    return ziel


def wechsel(ziel_profil: str, mandant: str | None = None,
            db: Path | str | None = None) -> dict:
    """Wechselt das Betriebsprofil und bewegt die Mandanten-Achse mit.

    `ziel_profil=unternehmen` braucht einen benannten Mandanten (kommt von
    aussen, wird nicht geraten) -- der ganze Bestand wandert von `lokal` auf
    diesen Namen. `ziel_profil=einzelplatz` ist der Rueckweg: alles zurueck
    auf `lokal`.

    Ein unbekannter Profilname wird abgelehnt, ein leerer Mandantenname auch
    -- beides VOR der Sicherung, damit ein Fehlaufruf keine Datei anlegt."""
    if ziel_profil not in PROFILE:
        raise ValueError(f"unbekanntes Betriebsprofil: {ziel_profil!r} (erlaubt: {PROFILE})")
    if ziel_profil == UNTERNEHMEN:
        if not mandant or not mandant.strip():
            raise ValueError("Wechsel zu 'unternehmen' braucht einen benannten Mandanten")
        neuer_mandant = mandant.strip()
    else:
        neuer_mandant = MANDANT_LOKAL

    db_path = Path(db) if db is not None else ort.DB
    vorher = zaehlung(db_path)
    sicherungspfad = _sicherung(db_path)

    conn = speicher.verbinde_bestand(db_path)
    try:
        for tabelle in TABELLEN:
            conn.execute(f"UPDATE {tabelle} SET mandant = ?", (neuer_mandant,))
        conn.execute(
            "INSERT INTO knowledge_config (key, value, updated_at) "
            "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (KONFIG_SCHLUESSEL, ziel_profil),
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()

    nachher = zaehlung(db_path)
    if vorher != nachher:
        raise RuntimeError(
            f"Wechsel hat Zeilen verloren oder gewonnen: vorher {vorher}, nachher {nachher} "
            f"-- Sicherung liegt unter {sicherungspfad}"
        )
    return {
        "profil": ziel_profil,
        "mandant": neuer_mandant,
        "sicherung": str(sicherungspfad),
        "vorher": vorher,
        "nachher": nachher,
    }


def _selftest() -> None:
    import tempfile

    # ueber speicher.schreiben() aufgebaut statt mit einer eigenen
    # sqlite3.connect-Tuer -- genau das haelt tests/test_naht_ratsche.py fest
    # (kern/speicher.py ist die einzige Naht).
    tmp = Path(tempfile.mkdtemp())
    db = tmp / "probe.db"
    with speicher.schreiben(db) as conn:
        conn.executescript(
            "CREATE TABLE knowledge_nodes (id TEXT PRIMARY KEY, mandant TEXT NOT NULL DEFAULT 'lokal');"
            "CREATE TABLE lessons_learned (id TEXT PRIMARY KEY, mandant TEXT NOT NULL DEFAULT 'lokal');"
            "CREATE TABLE knowledge_config (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL);"
            "INSERT INTO knowledge_nodes (id) VALUES ('n1'), ('n2');"
            "INSERT INTO lessons_learned (id) VALUES ('l1');"
        )

    assert profil(db) == EINZELPLATZ, "Vorgabe ohne Zeile muss einzelplatz sein"

    # Negativfall: unbekannter Profilname wird abgelehnt, nichts geschieht.
    try:
        wechsel("weltraum", db=db)
        raise AssertionError("unbekanntes Profil wurde akzeptiert")
    except ValueError:
        pass
    assert not list(tmp.glob("probe.db.bak-*")), "abgelehnter Wechsel hat trotzdem gesichert"

    # Negativfall: leerer Mandantenname scheitert.
    try:
        wechsel(UNTERNEHMEN, mandant="   ", db=db)
        raise AssertionError("leerer Mandantenname wurde akzeptiert")
    except ValueError:
        pass

    vorher = zaehlung(db)

    ergebnis = wechsel(UNTERNEHMEN, mandant="kunde-x", db=db)
    assert ergebnis["mandant"] == "kunde-x"
    assert zaehlung(db) == vorher, "Bestandszaehlung darf sich durch den Wechsel nicht aendern"
    assert profil(db) == UNTERNEHMEN
    with speicher.lesen(db) as c:
        werte = {r["mandant"] for r in c.execute("SELECT mandant FROM knowledge_nodes")}
    assert werte == {"kunde-x"}, werte

    rueckweg = wechsel(EINZELPLATZ, db=db)
    assert rueckweg["mandant"] == MANDANT_LOKAL
    assert zaehlung(db) == vorher, "Ruecksweg darf keine Zeile verlieren"
    assert profil(db) == EINZELPLATZ
    with speicher.lesen(db) as c:
        werte = {r["mandant"] for r in c.execute("SELECT mandant FROM knowledge_nodes")}
        werte |= {r["mandant"] for r in c.execute("SELECT mandant FROM lessons_learned")}
    assert werte == {MANDANT_LOKAL}, werte

    print("betriebsprofil: alle Proben bestanden")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(f"profil={profil()} zaehlung={zaehlung()}")
