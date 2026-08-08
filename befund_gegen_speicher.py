#!/usr/bin/env python3
"""
befund_gegen_speicher.py — haelt einen Fehlerbericht/Log/Diff GEGEN den
Wissensspeicher, statt auf den zufaelligen Wortlaut eines Prompts zu warten.

ANLASS (2026-08-08, fremde Sitzung, Projekt fahrtenbuch): sechs Befunde
wurden aus einem Fehlerbericht erarbeitet, FUENF standen bereits als Lehre
im Speicher, zwei laengst behoben. Ursache: der Recall-Hook
(haken/knowledge_recall_hook.py) fragt den Speicher mit dem PROMPT des
Betreibers ab ("schau dir den Fehlerbericht an" -> null Treffer). Die
Befunde entstanden aber aus einer DATEI, die der Hook nie zu sehen bekam.

Dieses Modul schliesst die Luecke: Text (Datei/Argument/Stdin) rein, je
unterscheidungskraeftigem Bezeichner ein Abgleich gegen lessons_learned und
knowledge_nodes, mit Kennung/Vorkommenszahl/Status.

Wiederverwendet statt neu gebaut (Auftrag: "Vorhandenes benutzen"):
  - fold_de()/_fts_phrase() aus knowledge_mcp_server.py (reine Textfunktionen,
    kein DB-Schreiber) fuer dieselbe Umlaut-Faltung und FTS5-Phrasen-Quotung
    wie knowledge_search()/lesson_query().
  - dieselben FTS5-Tabellen (knowledge_fts/lessons_fts, trigram-Tokenizer,
    siehe schema.sql) wie knowledge_search()/lesson_query().
Bewusst NICHT wiederverwendet: knowledge_search()/lesson_query() selbst --
beide rufen log_access() auf, das per INSERT+commit in die Betriebsdatenbank
schreibt (knowledge_mcp_server.py:1274). Auftrag verbietet das ("Nichts in
die Betriebsdatenbank schreiben"). Darum eigene, read-only Verbindung
(sqlite3 URI mode=ro, wie haken/knowledge_recall_hook.py::query() es fuer
denselben Zweck schon tut) mit denselben FTS5-Abfragen, ohne den
Logging-Pfad.

Auswahlregel Bezeichner (belegt an echtem Lehrentext, siehe demo() unten):
  1. schlangen_schrift / KONSTANTEN_SCHREIBUNG -- enthaelt '_'.
  2. punkt.getrennte.namen / Datei.endung -- enthaelt '.', jedes Segment
     >= 2 Zeichen UND Gesamtlaenge >= 6 (filtert Abkuerzungen wie 'z.B.',
     'd.h.' -- Segmentlaenge 1, kein Bezeichner).
  3. KamelCase -- Kleinbuchstabe direkt gefolgt von Grossbuchstabe im Token
     (faengt 'UniversalDongleManager', 'vinRetryDelayForFailure').
  Gewoehnlicher Fliesstext (nur Buchstaben, keine der drei Formen) erfuellt
  keine Regel und wird verworfen -- das ist der ganze Filter, kein NLP.

Aufruf:
  python3 befund_gegen_speicher.py bericht.txt
  cat bericht.txt | python3 befund_gegen_speicher.py
  python3 befund_gegen_speicher.py --selftest
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knowledge_mcp_server import fold_de, _fts_phrase  # noqa: E402 -- reine Textfunktionen

DB = os.environ.get("BEGOD_KNOWLEDGE_DB") or str(Path(__file__).resolve().parent / "knowledge.db")

_TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9_.]*")


def _is_distinctive(token: str) -> bool:
    if "_" in token:
        return True
    if "." in token:
        segs = token.split(".")
        return all(len(s) >= 2 for s in segs) and len(token) >= 6
    return bool(re.search(r"[a-zäöü][A-ZÄÖÜ]", token))


def extract_identifiers(text: str) -> list[tuple[str, int]]:
    """Unterscheidungskraeftige Bezeichner, absteigend nach Vorkommenszahl
    (chronisch vor einmalig, Auftrag: 'Was chronisch ist, gehoert vor alles
    Einmalige'), bei Gleichstand in erster Auftauchen-Reihenfolge (stabiler
    sort)."""
    counts: Counter = Counter()
    order: list[str] = []
    for raw in _TOKEN_RE.findall(text):
        tok = raw.strip(".")
        if not tok or not _is_distinctive(tok):
            continue
        if tok not in counts:
            order.append(tok)
        counts[tok] += 1
    order.sort(key=lambda t: counts[t], reverse=True)
    return [(t, counts[t]) for t in order]


def _connect_ro() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2.0)
    conn.row_factory = sqlite3.Row
    return conn


def _query_lessons(conn: sqlite3.Connection, ident: str) -> list[dict]:
    try:
        rows = conn.execute(
            """SELECT l.id, l.type, l.severity, l.status, l.occurrences, l.description
               FROM lessons_fts f JOIN lessons_learned l ON f.rowid = l.rowid
               WHERE lessons_fts MATCH ?""",
            (_fts_phrase(fold_de(ident)),),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        {"id": r["id"], "kind": "lesson", "type": r["type"], "severity": r["severity"],
         "status": r["status"], "occurrences": r["occurrences"],
         "summary": r["description"][:200]}
        for r in rows
    ]


def _query_nodes(conn: sqlite3.Connection, ident: str) -> list[dict]:
    try:
        rows = conn.execute(
            """SELECT n.id, n.path, n.title, n.zurueckgezogen
               FROM knowledge_fts f JOIN knowledge_nodes n ON f.rowid = n.rowid
               WHERE knowledge_fts MATCH ?""",
            (_fts_phrase(fold_de(ident)),),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [
        {"id": r["id"], "kind": "node", "path": r["path"], "title": r["title"],
         "status": "zurueckgezogen" if r["zurueckgezogen"] else "aktiv"}
        for r in rows
    ]


def befund_gegen_speicher(text: str, db: str | None = None) -> list[dict]:
    """Je Bezeichner (chronisch zuerst) die Treffer aus lessons_learned und
    knowledge_nodes -- status je Treffer kommt direkt aus der Spalte
    (active/resolved/escalated_to_rule bzw. aktiv/zurueckgezogen), NICHT nur
    implizit ueber Anwesenheit: 'bereits behoben' muss anders aussehen als
    'offen', das war der teuerste Einzelfall im Anlass (ein Vorschlag, ein
    Messgeraet zu bauen, das laengst existierte)."""
    conn = _connect_ro() if db is None else sqlite3.connect(
        f"file:{db}?mode=ro", uri=True, timeout=2.0
    )
    if db is not None:
        conn.row_factory = sqlite3.Row
    out = []
    try:
        for ident, count in extract_identifiers(text):
            lessons = _query_lessons(conn, ident)
            nodes = _query_nodes(conn, ident)
            out.append({
                "bezeichner": ident,
                "vorkommen_im_text": count,
                "lessons": lessons,
                "nodes": nodes,
                "gefunden": bool(lessons or nodes),
            })
    finally:
        conn.close()
    return out


def _format_report(befunde: list[dict]) -> str:
    lines = []
    for b in befunde:
        if not b["gefunden"]:
            continue
        lines.append(f"# {b['bezeichner']}  ({b['vorkommen_im_text']}x im Text)")
        for l in b["lessons"]:
            lines.append(
                f"  Lehre {l['id']}  [{l['status']}]  occurrences={l['occurrences']}  "
                f"{l['type']}/{l['severity']}: {l['summary']}"
            )
        for n in b["nodes"]:
            lines.append(f"  Knoten {n['id']}  [{n['status']}]  {n['path']}: {n['title']}")
    if not lines:
        return "(kein Treffer -- Text ohne Bezug zum Bestand)"
    return "\n".join(lines)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--selftest"]
    if "--selftest" in sys.argv:
        demo()
        return
    text = Path(args[0]).read_text(encoding="utf-8") if args else sys.stdin.read()
    print(_format_report(befund_gegen_speicher(text)))


def demo() -> None:
    """Rot-vor-gruen-Selbsttest, ohne Framework. Nachbau des ANLASS-Falls:
    ein Fehlerbericht-Ausschnitt fuer fahrtenbuch, gebaut aus Bezeichnern,
    die WOERTLICH in den sechs Lehren aus dem Anlass stehen (siehe
    ABWEICHUNG unten -- die drei im Auftrag genannten Ereignisnamen
    unknown_hardware_rebind/auto_drive.missed/drive_flow.completion kommen
    in der echten DB an keiner Stelle vor, geprueft per LIKE ueber
    description/root_cause/prevention aller 689 Lehren, 0 Treffer)."""
    bericht = (
        "universal_dongle_manager.dart:1569 ruft in dispose() weiter auf. "
        "confirm_blocked.unknownHardware trat mehrfach auf. "
        "UniversalDongleManager._maybeAutoBindSoleVehicle blockierte die Zuordnung. "
        "vinRetryDelayForFailure() gab nach zwei Versuchen auf. "
        "resolveAutoStartKmStart verlor den Vorlauf. "
        "runZonedGuarded fing den Fehler nicht ab. "
        "Geolocator.requestPermission() blieb denied. "
        "opaqueTripId wechselte 4x innerhalb einer Fahrt."
    )
    erwartete_kennungen = {
        "L-aa4995": "opaqueTripId",
        "L-05e18b": "universal_dongle_manager.dart",
        "L-8b4799": "confirm_blocked.unknownHardware / vinRetryDelayForFailure",
        "L-cbb443": "UniversalDongleManager._maybeAutoBindSoleVehicle",
        "L-319e01": "resolveAutoStartKmStart",
        "L-4750fc": "Geolocator.requestPermission",
    }
    befunde = befund_gegen_speicher(bericht)
    gefundene_ids = {l["id"] for b in befunde for l in b["lessons"]}
    print("--- Positivfall (Fehlerbericht-Nachbau) ---")
    print(_format_report(befunde))
    fehlend = set(erwartete_kennungen) - gefundene_ids
    assert not fehlend, f"erwartete Lehren nicht gefunden: {fehlend}"
    print(f"\nOK: alle {len(erwartete_kennungen)} erwarteten Lehren gefunden: {sorted(gefundene_ids)}")

    print("\n--- Negativfall (kein Bezug) ---")
    ohne_bezug = "Kartoffeln pflanzen im Fruehjahr braucht lockeren Boden und Sonne."
    befunde_neg = befund_gegen_speicher(ohne_bezug)
    assert not any(b["gefunden"] for b in befunde_neg), "Negativfall lieferte einen Treffer"
    print("OK: kein Treffer.")

    print("\n--- Grenzfall (Bezeichner existiert nicht im Speicher) ---")
    grenzfall = "quatschus_maximus_bezeichnerus wurde im Log 3x gesichtet."
    befunde_grenz = befund_gegen_speicher(grenzfall)
    treffer = [b for b in befunde_grenz if b["bezeichner"] == "quatschus_maximus_bezeichnerus"]
    assert treffer, "Bezeichner wurde nicht extrahiert"
    assert treffer[0]["gefunden"] is False, "unbekannter Bezeichner faelschlich als Treffer markiert"
    assert treffer[0]["lessons"] == [] and treffer[0]["nodes"] == [], "leere Liste erwartet"
    print("OK: 'nichts gefunden' ist im Ergebnis explizit (gefunden=False), nicht nur leere Liste.")

    print("\n--- ABWEICHUNG vom Auftrag, gemeldet statt verschwiegen ---")
    print(
        "Die drei im Auftrag genannten Ereignisnamen (unknown_hardware_rebind, "
        "auto_drive.missed, drive_flow.completion) stehen NICHT woertlich in der "
        "echten knowledge.db (LIKE-Suche ueber description/root_cause/prevention "
        "aller 689 Lehren: 0 Treffer je Name). Naeheste echte Entsprechung in den "
        "sechs genannten Lehren: 'confirm_blocked.unknownHardware' (L-8b4799), "
        "'Auto-Drive-Vorlauf-Kilometer' als Fliesstext (L-319e01, keine "
        "Bezeichnerform), kein Treffer fuer 'drive_flow.completion' -- 'drive_flow' "
        "alleine kommt vor (L-aa4995, als 'drive_flow-Diagnostics'/'drive_flow_"
        "diagnostics.dart'), '.completion' nirgends. L-4750fc taucht in keiner der "
        "beiden Fassungen der Ereignisnamen auf -- dieser Nachbau erreicht ihn "
        "ueber 'Geolocator.requestPermission', den einzigen Bezeichner aus seinem "
        "Text, der in Wortlaut oder chronischem Vorkommen als noch offen erkennbar "
        "waere; L-4750fc hat occurrences=1 wie alle sechs bis auf L-aa4995 (2x)."
    )


if __name__ == "__main__":
    main()
