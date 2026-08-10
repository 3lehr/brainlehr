#!/usr/bin/env python3
"""kurator_taeglich.py [--force] [--heute ISO8601] | --selbsttest

Ruft kurator_lauf(scharf=False) auf (siehe shared-knowledge/knowledge_mcp_
server.py, Auftrag 2026-08-07) und schreibt den Bericht als EINEN
Wissensknoten -- fortgeschrieben, nie verdoppelt. Ohne dieses Skript wird
kurator_lauf() von niemandem ausser seinem eigenen Test aufgerufen: kein
Zeitplan, kein Hook, kein Skript (Auftrag 2026-08-07, Befund).

TAEGLICHER AUSLOESER: kein neuer Mechanismus. Dieses Skript wird an die
bestehende SessionStart-Hook-Kette in ~/.claude/settings.json angehaengt
(derselbe Block, der schon retrofit_hint.py/knowledge_index.py/
stand_index_hook.py bei jedem Sessionstart faehrt) -- Hooks/launchd/cron
waren die einzigen im Verbund vorhandenen Ausloeser, launchd/cron hatten
keinen einzigen hub-Eintrag (gemessen: `launchctl list`, `crontab -l`
leer). Eigener Tagesmarker (MARKER) verhindert, dass mehrere Sessions am
selben Tag mehrfach schreiben -- SessionStart feuert pro Session, nicht
pro Tag.

DREI GRENZEN AUS DEM AUFTRAG:
- Immer Trockenlauf: scharf=False fest verdrahtet, kein Schalter dafuer.
- Kein Duplikat: fester Titel/Pfad unter /agents/governance. Erster Lauf
  legt an (knowledge_add), jeder weitere schreibt denselben Knoten fort
  (knowledge_update) -- knowledge_add lehnt einen doppelten Pfad selbst ab
  ("Node already exists at path", inkl. existing_id), das ist hier der
  Normalweg ab dem zweiten Lauf, kein Fehlerfall.
- Schiefgeht die Auswertung: Bericht wird VOLLSTAENDIG im Speicher gebaut,
  bevor irgendetwas geschrieben wird -- Abbruch vor dem Schreiben laesst
  keinen halben Knoten zurueck.
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

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHARED_KNOWLEDGE = HERE.parent / "shared-knowledge"
sys.path.insert(0, str(SHARED_KNOWLEDGE))
import knowledge_mcp_server as kms  # type: ignore  # noqa: E402

MARKER = SHARED_KNOWLEDGE / ".kurator_taeglich_marker"
PARENT_PATH = "/agents/governance"
TITLE = "Kurator-Trockenlauf: taeglicher Bestandscheck"


def _heute(heute: str | None = None) -> str:
    return heute or datetime.now(timezone.utc).astimezone().date().isoformat()


def bereits_heute_gelaufen(heute: str, marker_path: Path = MARKER) -> bool:
    return marker_path.exists() and marker_path.read_text(encoding="utf-8").strip() == heute


def markiere_gelaufen(heute: str, marker_path: Path = MARKER) -> None:
    marker_path.write_text(heute, encoding="utf-8")


def _kategorien_zeilen(bericht: dict) -> list[str]:
    zeilen = []
    for name, eintrag in sorted(bericht["kategorien"].items()):
        zusatz = f", davon hart={eintrag['anzahl_hart']}" if "anzahl_hart" in eintrag else ""
        zeilen.append(f"- {name}: {eintrag.get('anzahl')}{zusatz} ({eintrag['handlung']})")
    return zeilen


def bericht_text(bericht: dict, heute: str, laufzeit_s: float) -> tuple[str, str]:
    """(summary, content) fuer den Wissensknoten."""
    hart = bericht["kategorien"]["injection_suspects"].get("anzahl_hart", 0)
    summary = (f"Trockenlauf {heute}: {len(bericht['kategorien'])} Kategorien geprueft, "
               f"{hart} harte Einschleusungsverdaechte, {bericht['aktionen_ausgefuehrt']} "
               f"Aktionen ausgefuehrt (Trockenlauf -> immer 0).")
    content = (f"Stand: {heute}, Laufzeit {laufzeit_s:.1f}s, Modus {bericht['modus']}.\n\n"
               + "\n".join(_kategorien_zeilen(bericht))
               + f"\n\nAktionen (im Trockenlauf nie ausgefuehrt): {len(bericht['aktionen'])}")
    return summary, content


def schreibe_bericht(summary: str, content: str, heute: str) -> dict:
    source = f"erzeugt aus hub/scripts/kurator_taeglich.py (Lauf {heute})"
    ergebnis = kms.knowledge_add(PARENT_PATH, TITLE, summary, content, source=source, anlass="skript",
                                  norm_entscheidung="keine_norm",
                                  norm_entschieden_grund="taeglicher Kurator-Bericht ist kein Normtext, sondern ein Messprotokoll")
    if ergebnis.get("error", "").startswith("Node already exists at path") and "existing_id" in ergebnis:
        return kms.knowledge_update(ergebnis["existing_id"], summary=summary, content=content)
    return ergebnis


def main(heute: str | None = None, force: bool = False) -> int:
    heute = _heute(heute)
    if not force and bereits_heute_gelaufen(heute):
        print(f"kurator_taeglich: heute ({heute}) bereits gelaufen, ueberspringe.")
        return 0

    start = time.monotonic()
    try:
        bericht = kms.kurator_lauf(scharf=False, actor="kurator_taeglich", model="skript")
    except Exception as exc:  # noqa: BLE001 -- Grenzfall: sprechend abbrechen, nichts schreiben
        print(f"kurator_taeglich: Auswertung fehlgeschlagen, kein Knoten geschrieben: {exc}", file=sys.stderr)
        return 1
    laufzeit_s = time.monotonic() - start

    if bericht.get("modus") != "trockenlauf":
        print(f"kurator_taeglich: unerwarteter Modus {bericht.get('modus')!r} -- Abbruch, kein Knoten geschrieben.",
              file=sys.stderr)
        return 1

    summary, content = bericht_text(bericht, heute, laufzeit_s)
    ergebnis = schreibe_bericht(summary, content, heute)
    if "error" in ergebnis:
        print(f"kurator_taeglich: Schreiben fehlgeschlagen: {ergebnis['error']}", file=sys.stderr)
        return 1

    markiere_gelaufen(heute)
    print(f"kurator_taeglich: Bericht geschrieben ({heute}, {laufzeit_s:.1f}s).")
    return 0


def _selbsttest() -> None:
    import sqlite3
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        db_path = tmp / "kurator_taeglich_test.db"
        schema = (SHARED_KNOWLEDGE / "schema.sql").read_text(encoding="utf-8")
        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema)
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, title, summary, content, source) "
            "VALUES ('root1', '/agents', 't', 's', 'c', 'test')"
        )
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, parent_path, title, summary, content, source) "
            "VALUES ('root2', '/agents/governance', '/agents', 't', 's', 'c', 'test')"
        )
        conn.commit()
        conn.close()
        kms.DB_PATH = db_path
        kms.RECALL_LOG_PATH = tmp / "recall_log.jsonl"
        global MARKER
        MARKER = tmp / "marker"

        rc = main(heute="2026-08-07", force=True)
        assert rc == 0, "erster Lauf muss erfolgreich sein"
        conn = sqlite3.connect(str(db_path))
        n = conn.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE title = ?", (TITLE,)).fetchone()[0]
        assert n == 1, f"erster Lauf muss genau einen Knoten anlegen, war {n}"

        # Negativfall: zweiter Lauf am selben Tag (force, damit der Tagesmarker
        # nicht schon vorher greift) darf KEINEN zweiten Knoten erzeugen.
        rc = main(heute="2026-08-07", force=True)
        assert rc == 0, "zweiter Lauf muss erfolgreich sein"
        conn2 = sqlite3.connect(str(db_path))
        n2 = conn2.execute("SELECT COUNT(*) FROM knowledge_nodes WHERE title = ?", (TITLE,)).fetchone()[0]
        assert n2 == 1, f"zweiter Lauf darf nicht duplizieren, war {n2}"
        conn2.close()

        # Tagesmarker: ohne --force blockt derselbe Tag den dritten Lauf.
        assert bereits_heute_gelaufen("2026-08-07")
        conn.close()

    print("kurator_taeglich: Selbsttest gruen.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Tagesmarker ignorieren (Handprobe)")
    p.add_argument("--heute", default=None, help="ISO-Datum statt heutigem Datum (Walkthrough-Doktrin)")
    p.add_argument("--selbsttest", action="store_true")
    args = p.parse_args()

    if args.selbsttest:
        _selbsttest()
        sys.exit(0)

    sys.exit(main(heute=args.heute, force=args.force))
