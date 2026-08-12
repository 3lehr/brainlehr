#!/usr/bin/env python3
"""Zeigt beim Sitzungsstart, welche Eilmeldungen verfallen sind, statt in
eilmeldung_eskalation.jsonl zu verstauben.

Befund 2026-08-12: hub/scripts/eilmeldung_hook.py (PostToolUse, feuert bei
jedem Werkzeugaufruf jeder ARBEITENDEN Sitzung) stellt "dringend"-Knoten zu,
wiederholt nach Zaehler-Backoff und schreibt nach drei unquittierten
Zustellungen einen Befund nach eilmeldung_eskalation.jsonl "fuer den
Betreiber". Diese Datei liest niemand -- 65 Zeilen seit 2026-08-08 fuer sechs
Knoten, vier Tage lang unbemerkt. Der einzige Kanal, von dem belegt ist, dass
der Betreiber ihn liest, ist der Sitzungsstart (SessionStart-Hook).

Der Hook selbst liefert seit demselben Datum keine Knoten mehr aus, die
aelter als VERFALL_TAGE sind (siehe dort, _verfallen) -- eine Meldung, die
seit Tagen niemand quittiert, ist keine Eilmeldung mehr. Dieser Melder holt
genau diese verfallenen, aber immer noch offenen Knoten hierher: einmal pro
Sitzungsstart, statt bei jedem Werkzeugaufruf.

Schweigt, wenn nichts verfallen ist -- der vierzehnte Startmelder, der immer
redet, waere einer zu viel (siehe offene_arbeit.py, gleiches Prinzip).

Projekt-Zuschnitt geprueft und verworfen: knowledge_nodes.project_id steht
bei ALLEN sechs "dringend"-Knoten auf "shared", kein Knoten traegt eine
projektspezifische Kennung. Eine Zuordnung ueber Tags oder Pfadtext waere
Raten (ein Tag "openlehr" heisst nicht, dass eine brainlehr-Sitzung es nicht
auch wissen muss) -- keine saubere Grundlage, also keine Filterung.

VERFALL_TAGE ist hier bewusst dupliziert statt aus dem Hook importiert:
brainlehr ist eigenstaendig und soll auch ohne den hub-Verbund laufen (siehe
haken/ort.py), der Hook liegt in hub/scripts. Ein Integer zweimal zu pflegen
ist billiger als eine Abhaengigkeit in die falsche Richtung.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "kern"))
import speicher  # noqa: E402

VERFALL_TAGE = 3  # muss mit hub/scripts/eilmeldung_hook.py:VERFALL_TAGE uebereinstimmen
MAX_ZEILEN = 6


def _verfallen(created_at: str, jetzt: datetime) -> bool:
    try:
        erstellt = datetime.fromisoformat(created_at)
    except Exception:
        return False
    return (jetzt - erstellt).days >= VERFALL_TAGE


def _faellige(db: Path | None, jetzt: datetime | None = None) -> list[dict]:
    if db is not None and not db.exists():
        return []
    jetzt = jetzt or datetime.now(timezone.utc)
    try:
        with speicher.lesen(db) as con:
            rows = con.execute(
                "SELECT path, title, created_at FROM knowledge_nodes "
                "WHERE zurueckgezogen = 0 AND tags LIKE '%\"dringend\"%'"
            ).fetchall()
    except sqlite3.OperationalError:
        return []  # keine DB an dem Pfad -- nichts zu melden, kein Crash
    return [dict(r) for r in rows if _verfallen(r["created_at"] or "", jetzt)]


def melde(db: Path | None = None, jetzt: datetime | None = None) -> str:
    faellig = _faellige(db, jetzt)
    if not faellig:
        return ""
    kopf = (f"{len(faellig)} Eilmeldung(en) seit mehr als {VERFALL_TAGE} Tagen "
            f"unquittiert, wird nicht mehr wie frisch zugestellt:")
    zeig = [f"  {r['path']}: {r['title']}" for r in faellig[:MAX_ZEILEN]]
    if len(faellig) > MAX_ZEILEN:
        zeig.append(f"  ... und {len(faellig) - MAX_ZEILEN} weitere")
    return "\n".join([kopf, *zeig])


def _selftest() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        db = Path(tmp_dir) / "test.db"
        with speicher.schreiben(db) as con:
            con.execute(
                "CREATE TABLE knowledge_nodes (path TEXT, title TEXT, tags TEXT, "
                "zurueckgezogen INTEGER, created_at TEXT)"
            )
            con.execute(
                "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?)",
                ("/a/alt", "Vier Tage alt", '["dringend"]', 0, "2026-08-08T09:00:00+00:00"),
            )
            con.execute(
                "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?)",
                ("/a/neu", "Heute", '["dringend"]', 0, "2026-08-12T09:00:00+00:00"),
            )
            con.execute(
                "INSERT INTO knowledge_nodes VALUES (?,?,?,?,?)",
                ("/a/zurueck", "Zurueckgezogen trotz Alter", '["dringend"]', 1, "2026-08-01T09:00:00+00:00"),
            )

        jetzt = datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc)
        aus = melde(db, jetzt)
        assert "/a/alt" in aus, aus
        assert "/a/neu" not in aus, "frischer Knoten haette nicht gemeldet werden duerfen"
        assert "/a/zurueck" not in aus, "zurueckgezogener Knoten haette nicht gemeldet werden duerfen"

        # Negativfall: nichts verfallen -> Stille
        with speicher.schreiben(db) as con:
            con.execute("DELETE FROM knowledge_nodes WHERE path='/a/alt'")
        assert melde(db, jetzt) == "", melde(db, jetzt)

        # kein Datenbankfile -> Stille, kein Crash
        assert melde(Path(tmp_dir) / "nicht-vorhanden.db", jetzt) == ""
    print("eilmeldung_faellig: Selbsttest gruen")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        text = melde()
        if text:
            print(text)
