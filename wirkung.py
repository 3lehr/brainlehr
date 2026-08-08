#!/usr/bin/env python3
"""
wirkung.py — Wirkungssignal fuer den passiven Abruf (Auftrag 2026-08-07,
Plan: docs/PLAN_SELBSTLERNEN_2026-08-07.md, Schritt 1 -- Voraussetzung fuer
Schritt 2 (trust_score in die Rangfolge). NICHT hier verdrahtet, siehe
Grenze im Auftrag: dieses Modul liefert nur das Signal.

Jede Einspielung des Recall-Hooks (recall_log.jsonl, siehe
knowledge_recall_hook.py::log_recall) bekommt einen BEOBACHTBAREN Ausgang --
drei Zustaende, kein Modellurteil:

    genutzt      der eingespielte Knoten/die Lehre wurde in DERSELBEN
                 Sitzung DANACH gelesen, geaendert oder (nur Knoten) in
                 eine neue Verknuepfung eingebaut
    ignoriert    eingespielt, nichts davon beruehrt
    widerlegt    in derselben Sitzung zurueckgezogen -- Knoten: action=
                 'zurueckziehen'; Lehre: geloescht (lesson_delete). Nur wo
                 STRUKTURELL erkennbar (Auftrag) -- fuer Lehren gibt es
                 sonst keine Widerspruchs-Aktion, dann bleibt es bei
                 genutzt/ignoriert.

Ableitung ausschliesslich aus access_log, knowledge_relations und
recall_log.jsonl -- KEIN Modell wird gefragt, ob eine Auskunft geholfen hat.

EHRLICHE GRENZE (in jeden Bericht gehoert dieser Satz): 'genutzt' ist ein
KORRELAT, kein Kausalitaetsnachweis. Ein Knoten kann eingespielt worden
sein, und die Sitzung haette dieselbe Loesung auch ohne ihn gefunden.

Wie trust_score (knowledge_mcp_server.py) und konfidenz.py: LIVE gerechnet,
NICHTS gespeichert -- keine Migration, keine neue Spalte/Tabelle. Wirkung
wird ab jetzt erhoben; fuer Recall-Zeilen von vor diesem Auftrag gibt es
sie nicht (kein Ruecktrag auf Altdaten, siehe Modul-Docstring-Grenze).

GRENZE bei Lehren: kein Lesesignal (access_log kennt keine Einzelabruf-
Aktion fuer Lehren, siehe knowledge_mcp_server.py::knowledge_trust_score
Docstring Punkt 1) und keine Verlinkung (knowledge_relations referenziert
per FK nur knowledge_nodes) -- fuer Lehren zaehlt nur lesson_update als
'genutzt', lesson_delete als 'widerlegt'.

GRENZFALL: derselbe Knoten/dieselbe Lehre in einer Sitzung mehrfach
eingespielt zaehlt EINMAL (fruehester Zeitpunkt als Cutoff), nicht mehrfach
-- siehe _recall_events().
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("BEGOD_KNOWLEDGE_DB") or (Path(__file__).parent / "knowledge.db"))
RECALL_LOG_PATH = Path(__file__).parent / "recall_log.jsonl"


def _parse_ts(s) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def _fmt_ts(d: datetime) -> str:
    # Gleiches Format wie access_log.timestamp/knowledge_relations.created_at
    # (schema.sql-Vorgabe strftime('%Y-%m-%dT%H:%M:%SZ')) -- sonst vergleicht
    # der SQL-Text-Vergleich unten Aepfel ('+00:00'-Suffix) mit Birnen ('Z').
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recall_events(kind: str, log_path: Path | str | None = None) -> dict[tuple[str, str], datetime]:
    """Ein Ereignis je (session, ref) -- Mehrfacheinspielung derselben
    Sitzung faellt auf den fruehesten Zeitpunkt zusammen (Grenzfall Auftrag).
    Zeilen ohne Sitzung/Zeitstempel bleiben aussen vor -- siehe unauswertbar()."""
    log_path = log_path if log_path is not None else RECALL_LOG_PATH
    field = "lessons" if kind == "lesson" else "nodes"
    first_seen: dict[tuple[str, str], datetime] = {}
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sess = entry.get("session")
                ts = _parse_ts(entry.get("ts"))
                if not sess or not ts:
                    continue
                for ref in entry.get(field) or []:
                    key = (sess, ref)
                    if key not in first_seen or ts < first_seen[key]:
                        first_seen[key] = ts
    except OSError:
        pass
    return first_seen


def unauswertbar(kind: str, log_path: Path | str | None = None) -> int:
    """Zeilen mit Treffern der gefragten Sorte, aber ohne Sitzung/Zeitstempel
    -- nicht ausgewertet, aber gezaehlt statt stillschweigend zu fehlen."""
    log_path = log_path if log_path is not None else RECALL_LOG_PATH
    field = "lessons" if kind == "lesson" else "nodes"
    n = 0
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get(field) and (not entry.get("session") or not _parse_ts(entry.get("ts"))):
                    n += 1
    except OSError:
        pass
    return n


def outcome(kind: str, ref: str, session: str, recall_ts: datetime, conn: sqlite3.Connection) -> str:
    """Ausgang EINER Einspielung: 'genutzt' | 'ignoriert' | 'widerlegt'.

    session-Vergleich per Praefix, nicht Gleichheit (Auftrag 2026-08-07):
    recall_log.jsonl schreibt immer die 8-stellig gekuerzte Form (siehe
    knowledge_recall_hook.py::log_recall), access_log/knowledge_relations
    tragen fuer Altzeilen (vor der Kuerzung von knowledge_mcp_server.py's
    _PROZESS_SITZUNG) noch die volle 36-stellige UUID -- ein exakter
    Gleichheitstest zwischen 8 und 36 Zeichen ist nie wahr. 'session || %'
    matcht beide Formen, ohne die Altzeilen zu migrieren: eine kuerzere
    DB-Zeile (schon 8-stellig) matcht exakt (leeres Suffix), eine laengere
    (volle UUID) matcht per Praefix. `session` selbst ist immer die kurze
    Form (kommt aus recall_log.jsonl), enthaelt also keine SQL-LIKE-
    Sonderzeichen (Hex-Ziffern)."""
    cutoff = _fmt_ts(recall_ts)
    session_prefix = f"{session}%"
    if kind == "node":
        row = conn.execute(
            "SELECT path FROM knowledge_nodes WHERE id = ? OR path = ?", (ref, ref)
        ).fetchone()
        canonical = row["path"] if row else ref
        widerlegt = conn.execute(
            "SELECT COUNT(*) FROM access_log WHERE node_path = ? AND session LIKE ? "
            "AND action = 'zurueckziehen' AND status = 'completed' AND timestamp > ?",
            (canonical, session_prefix, cutoff),
        ).fetchone()[0]
        if widerlegt:
            return "widerlegt"
        beruehrt = conn.execute(
            "SELECT COUNT(*) FROM access_log WHERE node_path = ? AND session LIKE ? "
            "AND action IN ('read','browse','update') AND status = 'completed' AND timestamp > ?",
            (canonical, session_prefix, cutoff),
        ).fetchone()[0]
        if not beruehrt:
            beruehrt = conn.execute(
                "SELECT COUNT(*) FROM knowledge_relations WHERE (source_path = ? OR target_path = ?) "
                "AND session LIKE ? AND created_at > ?",
                (canonical, canonical, session_prefix, cutoff),
            ).fetchone()[0]
        return "genutzt" if beruehrt else "ignoriert"
    if kind == "lesson":
        widerlegt = conn.execute(
            "SELECT COUNT(*) FROM access_log WHERE action = 'lesson_delete' AND query = ? "
            "AND session LIKE ? AND timestamp > ?",
            (ref, session_prefix, cutoff),
        ).fetchone()[0]
        if widerlegt:
            return "widerlegt"
        beruehrt = conn.execute(
            "SELECT COUNT(*) FROM access_log WHERE action = 'lesson_update' AND query = ? "
            "AND session LIKE ? AND status = 'completed' AND timestamp > ?",
            (ref, session_prefix, cutoff),
        ).fetchone()[0]
        return "genutzt" if beruehrt else "ignoriert"
    raise ValueError(f"kind muss 'node' oder 'lesson' sein, nicht {kind!r}")


def report(kind: str, log_path: Path | str | None = None, db_path: Path | str | None = None) -> dict:
    """Zaehlung ueber alle auswertbaren Einspielungen einer Sorte.
    'genutzt' ist ein Korrelat, kein Kausalitaetsnachweis (siehe Moduldoc)."""
    db_path = db_path if db_path is not None else DB_PATH
    events = _recall_events(kind, log_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    counts: Counter = Counter()
    try:
        for (session, ref), ts in events.items():
            counts[outcome(kind, ref, session, ts, conn)] += 1
    finally:
        conn.close()
    for zustand in ("genutzt", "ignoriert", "widerlegt"):
        counts.setdefault(zustand, 0)
    counts["unauswertbar"] = unauswertbar(kind, log_path)
    return dict(counts)


def selftest() -> None:
    import tempfile

    schema_path = Path(__file__).parent / "schema.sql"
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "wirkung_test.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, title, summary, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n1', '/x/genutzt', 't', 's', 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, title, summary, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n2', '/x/ignoriert', 't', 's', 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.execute(
            "INSERT INTO knowledge_nodes (id, path, title, summary, source, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
            "VALUES ('n3', '/x/widerlegt', 't', 's', 'test', 'keine_norm', 'skript:test', 'Testvorrichtung')"
        )
        conn.execute(
            "INSERT INTO lessons_learned (id, type, description, occurrences) "
            "VALUES ('L-1', 'insight', 'd', 1)"
        )
        # genutzt: nach dem Recall gelesen, gleiche Sitzung
        conn.execute(
            "INSERT INTO access_log (node_path, action, status, session, timestamp) "
            "VALUES ('/x/genutzt', 'read', 'completed', 's1', '2026-08-07T10:00:05Z')"
        )
        # widerlegt: nach dem Recall zurueckgezogen, gleiche Sitzung
        conn.execute(
            "INSERT INTO access_log (node_path, action, status, session, timestamp) "
            "VALUES ('/x/widerlegt', 'zurueckziehen', 'completed', 's1', '2026-08-07T10:00:05Z')"
        )
        # Lehre genutzt: lesson_update in gleicher Sitzung nach dem Recall
        conn.execute(
            "INSERT INTO access_log (node_path, action, status, session, query, timestamp) "
            "VALUES (NULL, 'lesson_update', 'completed', 's1', 'L-1', '2026-08-07T10:00:05Z')"
        )
        conn.commit()
        conn.close()

        log_path = Path(td) / "recall_log.jsonl"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": "2026-08-07T10:00:00+00:00", "session": "s1",
                "nodes": ["/x/genutzt", "/x/ignoriert", "/x/widerlegt"], "lessons": ["L-1"],
            }) + "\n")
            # Mehrfacheinspielung derselben (session, ref) -- Grenzfall, muss
            # trotzdem nur einmal zaehlen.
            f.write(json.dumps({
                "ts": "2026-08-07T10:05:00+00:00", "session": "s1",
                "nodes": ["/x/genutzt"], "lessons": [],
            }) + "\n")
            # Nicht auswertbar: keine Sitzung.
            f.write(json.dumps({
                "ts": "2026-08-07T10:00:00+00:00", "session": None,
                "nodes": ["/x/ohne-sitzung"], "lessons": [],
            }) + "\n")

        node_report = report("node", log_path, db_path)
        assert node_report["genutzt"] == 1, node_report
        assert node_report["ignoriert"] == 1, node_report
        assert node_report["widerlegt"] == 1, node_report
        assert node_report["unauswertbar"] == 1, node_report
        print(f"  Knoten-Bericht ok: {node_report}")

        lesson_report = report("lesson", log_path, db_path)
        assert lesson_report["genutzt"] == 1, lesson_report
        assert lesson_report["ignoriert"] == 0, lesson_report
        print(f"  Lehren-Bericht ok: {lesson_report}")

        events = _recall_events("node", log_path)
        assert events[("s1", "/x/genutzt")].isoformat().startswith("2026-08-07T10:00:00"), events
        print("  Grenzfall Mehrfacheinspielung -> ein Ereignis, fruehester Zeitpunkt ok")

    print("wirkung.py selftest: alle Pruefungen ok")


if __name__ == "__main__":
    selftest()
