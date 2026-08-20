#!/usr/bin/env python3
"""Stellt FRISCHE Eilmeldungen mitten in eine laufende Sitzung zu.

ANLASS (Betreiberfrage 2026-08-20): *"in den Startkontext -- sprich wir muessen
dann neue chats starten, oder kannst du das per eilmeldung injezieren?"*

GEMESSENE LAGE VORHER, und sie war halb gut:
- `haken/regelwechsel.py` laeuft bei JEDEM Prompt und spielt Aenderungen an
  Regeldateien und an Knoten mit norm_rang 1/2 ein. Belegt am 2026-08-20:
  vier Einspielungen in einer Sitzung, darunter eine Rang-2-Norm, die
  waehrend derselben Sitzung entstand und beim naechsten Prompt ankam.
- `melder/eilmeldung_faellig.py` laeuft nur bei SessionStart -- und meldet
  ueberdies nur die VERALTETEN (>3 Tage unquittiert). Eine Eilmeldung, die
  waehrend einer Sitzung entsteht, erreichte die laufende Sitzung also nie.

Das ist die Luecke, die dieser Haken schliesst: was seit dem letzten Prompt
DIESER Sitzung neu mit `dringend` etikettiert wurde, wird einmal zugestellt.

EINMAL, und das ist der ganze Trick. Der Zustand liegt je Sitzung; eine
Meldung, die zugestellt wurde, kommt nicht wieder. Ohne diese Buchhaltung
haette der Haken bei jedem Prompt dieselben 21 offenen Eilmeldungen
eingespielt -- und wer einmal 21 Zeilen Rauschen bekommt, liest die
zweiundzwanzigste nicht mehr.

WARUM DAS KEINE PROMPT-INJECTION IST: Eingespielt wird ausschliesslich aus der
eigenen Wissensdatenbank, und dorthin schreibt nur, wer einen Ausweis hat.
Dieselbe Abgrenzung wie in regelwechsel.py -- keine Datei aus dem
Arbeitsverzeichnis, kein Muster, kein Verzeichnisdurchlauf.

Fail-open in jedem Zweig: kann der Haken nicht lesen oder schreiben, gibt er
nichts aus und der Prompt laeuft weiter.

    python3 haken/eilmeldung_frisch.py --selftest
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

_w = Path(__file__).resolve().parent
while not (_w / "schema.sql").exists() and _w != _w.parent:
    _w = _w.parent
sys.path[:0] = [str(_w), str(_w / "kern"), str(_w / "haken")]

ZUSTAND = Path.home() / ".brainlehr-eilmeldung-frisch.json"
ETIKETT = "dringend"
HOECHSTENS = 3          # je Prompt, sonst wird aus Zustellung Rauschen


def _db() -> Path:
    import ort
    return Path(ort.DB)


def _lies_zustand() -> dict:
    try:
        return json.loads(ZUSTAND.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def frische(db: Path, gesehen: list[str]) -> list[tuple[str, str, str]]:
    """(id, pfad, titel) der dringenden Knoten, die diese Sitzung nicht kennt."""
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2.0)
    except sqlite3.Error:
        return []
    try:
        zeilen = conn.execute(
            "SELECT id, path, title FROM knowledge_nodes "
            "WHERE tags LIKE ? AND IFNULL(zurueckgezogen,0)=0 "
            "ORDER BY updated_at DESC LIMIT 200", (f'%"{ETIKETT}"%',)).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    bekannt = set(gesehen)
    return [(z[0], z[1], z[2]) for z in zeilen if z[0] not in bekannt]


def melde(sitzung: str, db: Path | None = None, zustand: Path | None = None) -> str:
    db = db or _db()
    ablage = zustand or ZUSTAND
    try:
        alt = json.loads(ablage.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        alt = {}
    gesehen = alt.get(sitzung, [])
    erstlauf = sitzung not in alt
    neu = frische(db, gesehen)

    # ERSTLAUF STELLT NICHTS ZU, er merkt sich nur den Stand. Sonst bekaeme
    # jede neue Sitzung beim ersten Prompt den gesamten Bestand an
    # Eilmeldungen -- dafuer gibt es den SessionStart-Kanal, und zweimal
    # dasselbe ist einmal zu viel.
    alt[sitzung] = [z[0] for z in neu] + gesehen if erstlauf else gesehen + [z[0] for z in neu[:HOECHSTENS]]
    try:
        ablage.write_text(json.dumps(alt)[:200_000], encoding="utf-8")
        os.chmod(ablage, 0o600)
    except OSError:
        pass
    if erstlauf or not neu:
        return ""
    zeigen = neu[:HOECHSTENS]
    kopf = (f"{len(neu)} frische Eilmeldung(en) seit deinem letzten Zug -- "
            "waehrend dieser Sitzung entstanden, also nicht im Startkontext:")
    zeilen = [f"  {p}: {t}" for _, p, t in zeigen]
    if len(neu) > HOECHSTENS:
        zeilen.append(f"  ... und {len(neu) - HOECHSTENS} weitere "
                      "(knowledge_search mit Etikett 'dringend')")
    return kopf + "\n" + "\n".join(zeilen)


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        db = d / "t.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE knowledge_nodes (id TEXT, path TEXT, title TEXT, "
                     "tags TEXT, updated_at TEXT, zurueckgezogen INTEGER DEFAULT 0)")
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('a','/x/a','Erste Meldung','[\"dringend\"]','2026-08-20T08:00:00Z',0)")
        conn.commit()
        z = d / "z.json"

        # ERSTLAUF: merkt sich den Stand und stellt NICHTS zu.
        assert melde("s1", db, z) == "", "der Erstlauf darf nichts zustellen"

        # Neue Meldung waehrend der Sitzung -> genau einmal.
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('b','/x/b','Zweite Meldung','[\"dringend\"]','2026-08-20T09:00:00Z',0)")
        conn.commit()
        erste = melde("s1", db, z)
        assert "Zweite Meldung" in erste, erste
        assert "Erste Meldung" not in erste, "der Bestand gehoert in den Startkanal"
        assert melde("s1", db, z) == "", "zweimal dieselbe Meldung ist Rauschen"

        # Eine ANDERE Sitzung hat ihren eigenen Stand.
        assert melde("s2", db, z) == "", "auch dort ist der Erstlauf still"

        # NEGATIVFALL: ein Knoten ohne das Etikett wird nie zugestellt.
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('c','/x/c','Kein Etikett','[\"notiz\"]','2026-08-20T10:00:00Z',0)")
        conn.commit()
        assert melde("s1", db, z) == "", "ohne Etikett keine Zustellung"

        # Und ein zurueckgezogener dringender Knoten ebenfalls nicht.
        conn.execute("INSERT INTO knowledge_nodes VALUES "
                     "('d','/x/d','Zurueckgezogen','[\"dringend\"]','2026-08-20T11:00:00Z',1)")
        conn.commit()
        assert melde("s1", db, z) == "", "zurueckgezogene Knoten sind keine Eilmeldung"
        conn.close()
    print("eilmeldung_frisch: Selbsttest gruen (6 Faelle: Erstlauf still, "
          "frische Meldung genau einmal, Bestand bleibt im Startkanal, zweite "
          "Sitzung eigenstaendig, ohne Etikett nichts, zurueckgezogen nichts)")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    try:
        eingabe = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    sitzung = str(eingabe.get("session_id") or "unbekannt")
    try:
        text = melde(sitzung)
    except Exception:
        return 0
    if text:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": f"<eilmeldung-frisch>\n{text}\n</eilmeldung-frisch>",
            }
        }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
