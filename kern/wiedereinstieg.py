#!/usr/bin/env python3
"""Wiedereinstieg nach Verdichtung: spielt zurueck, was in DIESER Sitzung
tatsaechlich getragen hat -- aus dem Bestand, nicht aus dem Kontext-Fenster.

Anlass (Auftrag 2026-08-06): bei ~950k Token Promptgroesse verdichtet der
Harness selbsttaetig. Verdichtung waehlt aus -- Zahlen werden zu Adjektiven,
offene Faeden verschwinden, ohne sichtbare Luecke. SessionStart-Hook mit
Anlass "compact" (bestaetigt im CLI-Binary: SessionStart.source hat die
Werte startup|resume|clear|compact, matchQuery=source -- Matcher "compact"
in settings.json filtert korrekt) laeuft unmittelbar danach.

Rangfolge der drei Listen ist der Kern, nicht Beiwerk:
  1. SELBST GESCHRIEBEN (knowledge_nodes/lessons_learned, Sitzungs-Praefix)
     -- staerkstes Signal, diese Sitzung hat es selbst festgehalten.
  2. BEWUSST GELESEN (access_log, action read|browse) -- jemand hat es
     gezielt geholt.
  3. GESCHEITERT (access_log, status='rejected', nach query=Grund gruppiert)
     -- zeigt Sackgassen, die sonst niemand mehr sieht.
Bewusst NICHT nach Haeufigkeit aus recall_log.jsonl (passiver Auto-Recall
in knowledge_recall_hook.py) ranken: derselbe openlehr-ADR-Block kam am
2026-08-06 rund zehnmal ueber den passiven Abruf hoch und war jedes Mal
unpassend. Haeufig ist nicht wichtig; der passive Abruf ist das Rauschen,
bewusster Zugriff (Liste 2) und eigenes Schreiben (Liste 1) sind das Signal.

Form: Verweise (Kennung, Pfad, Titel), keine Fliesstexte -- die Sitzung
liest den Inhalt bei Bedarf FRISCH nach. Ein neu gelesener Knoten traegt
den aktuellen Stand, ein im Kontext mitgeschleppter den von damals (Beispiel
2026-08-06: "238 nie gezogen" wurde einen halben Tag mitgeschleppt, obwohl
laengst falsch).

Harte Grenze: <=60 Zeilen Ausgabe -- laeuft bei jeder Verdichtung, darf den
frisch geleerten Kontext nicht sofort wieder fuellen. Ueberschuss wird
gekuerzt und gezaehlt, nie stillschweigend abgeschnitten.

Sitzungskennung: SessionStart liefert session_id (voll) im Hook-Stdin-JSON.
DB-Spalten (access_log.session, knowledge_nodes.session) sind uneinheitlich
befuellt -- teils "<session_id[:8]>-<freitext>", teils "unbekannt". Deshalb
Praefix-Match auf session_id[:8]. Fehlt session_id -> Fallback "seit
Mitternacht des heutigen Tages", ausdruecklich als Naeherung ausgegeben.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB = Path("/Volumes/daten/Begod2026/brainlehr") / "knowledge.db"  # A3: brainlehr ist eigenstaendig, nicht mehr hub/shared-knowledge
MAX_LINES = 60
PER_LIST = 12


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    return conn


def _session_filter(session_id: str | None, today_start: str) -> tuple[str, tuple, str]:
    """Liefert (SQL-Bedingung, Parameter, Erklaertext) fuer Zeitspalte + Praefix.

    Rueckgabe ist generisch (Platzhalter %TSCOL% fuer die jeweilige
    Zeitspalte), weil die drei Abfragen unterschiedliche Zeitspalten
    benutzen (updated_at / timestamp).

    Kennung ODER Zeitraum, nicht mehr entweder/oder (Auftrag 2026-08-07):
    ein Schreibweg, der die Kennung vergisst (z.B. session='unbekannt'),
    machte das Werkzeug blind, sobald ueberhaupt eine session_id vorlag --
    der Zeitraum-Zweig griff dann nie mehr. Praefix-Treffer bleiben das
    staerkere Signal, der Zeitraum faengt auf, was ohne Kennung geschrieben
    wurde."""
    if session_id:
        prefix = session_id[:8]
        return ("(session LIKE ? OR %TSCOL% >= ?)", (prefix + "%", today_start),
                f"Sitzung {prefix}… oder seit Mitternacht heute")
    return "%TSCOL% >= ?", (today_start,), "Kennung fehlte -- Naeherung: seit Mitternacht heute"


def _ast(pfad: str) -> str:
    """Elternast eines Pfades -- '/a/b/c' -> '/a/b'."""
    return pfad.rsplit("/", 1)[0] or "/"


def je_ast_hoechstens(rows, grenze: int, limit: int) -> list:
    """Laesst je Elternast hoechstens `grenze` Eintraege durch.

    Grund (gemessen 2026-08-07, erster Feldlauf des Wiedereinstiegs): ein
    Stapelimport von zwoelf ADR-Knoten in einen einzigen Ast belegte alle
    zwoelf Plaetze der Liste. Ein Stapelimport ist immer das Neueste und hat
    nie etwas zu sagen -- Neuheit allein ist die falsche Rangfolge.
    """
    gesehen: dict[str, int] = {}
    out = []
    for r in rows:
        ast = _ast(r["path"])
        if gesehen.get(ast, 0) >= grenze:
            continue
        gesehen[ast] = gesehen.get(ast, 0) + 1
        out.append(r)
        if len(out) >= limit:
            break
    return out


def selbst_geschrieben(conn: sqlite3.Connection, session_id: str | None,
                        today_start: str) -> list[str]:
    cond, params, _ = _session_filter(session_id, today_start)
    out = []
    rows = conn.execute(
        f"SELECT path, title FROM knowledge_nodes "
        f"WHERE {cond.replace('%TSCOL%', 'updated_at')} AND zurueckgezogen = 0 "
        f"ORDER BY updated_at DESC LIMIT {PER_LIST * 6}", params).fetchall()
    out += [f"K {r['path']} — {r['title']}"
            for r in je_ast_hoechstens(rows, 2, PER_LIST)]
    rows = conn.execute(
        f"SELECT id, description FROM lessons_learned "
        f"WHERE {cond.replace('%TSCOL%', 'last_seen')} "
        f"ORDER BY last_seen DESC LIMIT {PER_LIST}", params).fetchall()
    out += [f"L {r['id']} — {r['description'][:80]}" for r in rows]
    return out


def bewusst_gelesen(conn: sqlite3.Connection, session_id: str | None,
                     today_start: str) -> list[str]:
    cond, params, _ = _session_filter(session_id, today_start)
    rows = conn.execute(
        f"SELECT DISTINCT node_path, action FROM access_log "
        f"WHERE {cond.replace('%TSCOL%', 'timestamp')} "
        f"AND action IN ('read','browse') AND node_path IS NOT NULL "
        f"ORDER BY id DESC LIMIT {PER_LIST}", params).fetchall()
    return [f"{r['action']} {r['node_path']}" for r in rows]


def gescheitert(conn: sqlite3.Connection, session_id: str | None,
                 today_start: str) -> list[str]:
    cond, params, _ = _session_filter(session_id, today_start)
    rows = conn.execute(
        f"SELECT query AS grund, COUNT(*) AS n FROM access_log "
        f"WHERE {cond.replace('%TSCOL%', 'timestamp')} AND status = 'rejected' "
        f"GROUP BY query ORDER BY n DESC LIMIT {PER_LIST}", params).fetchall()
    return [f"{r['grund'] or '(ohne Grund)'} ({r['n']}x)" for r in rows]


def build(session_id: str | None, db_path: Path = DB, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    today_start = now.strftime("%Y-%m-%dT00:00:00")
    conn = _connect(db_path)
    try:
        _, _, herkunft = _session_filter(session_id, today_start)
        l1 = selbst_geschrieben(conn, session_id, today_start)
        l2 = bewusst_gelesen(conn, session_id, today_start)
        l3 = gescheitert(conn, session_id, today_start)
    finally:
        conn.close()

    if not l1 and not l2 and not l3:
        return (f"<wiedereinstieg>\nNichts aus dieser Sitzung im Bestand "
                f"({herkunft}) -- kein Schreiben, kein bewusstes Lesen, "
                f"keine Ablehnung protokolliert.\n</wiedereinstieg>")

    lines = ["<wiedereinstieg>", f"Nach Verdichtung, aus dem Bestand ({herkunft}):"]
    for label, items in (("Selbst geschrieben", l1),
                          ("Bewusst gelesen", l2),
                          ("Gescheitert (Grund)", l3)):
        if not items:
            continue
        lines.append(f"-- {label} --")
        lines.extend(items)

    if len(lines) > MAX_LINES:
        omitted = len(lines) - (MAX_LINES - 1)
        lines = lines[:MAX_LINES - 1]
        lines.append(f"… {omitted} weitere ausgelassen (Grenze {MAX_LINES} Zeilen)")
    lines.append("</wiedereinstieg>")
    return "\n".join(lines)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if payload.get("source") != "compact":
        return
    print(build(payload.get("session_id")))


if __name__ == "__main__":
    main()
