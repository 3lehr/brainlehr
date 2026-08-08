#!/usr/bin/env python3
"""
build_node_index.py — Landkarte aller Knoten in knowledge.db.

Vorbild: begod/scripts/knowledge_index.py (Konsile+ADRs). Dasselbe Muster,
hier ueber die Knoten der Datenbank, die dort fehlen -- Agent sieht sonst
nur die 0-3 Treffer des Recall-Hooks und weiss nie, dass mehr existiert.

Frueher: jeder Knoten als eigene Zeile (path+title) -- bei 323 Knoten ~9000
Token JEDE Sitzung. Jetzt (2026-08-07, Auftrag "Knotenindex ankommen"):
gezaehlt statt aufgezaehlt --
  - Landkarte: ein Ast (Ebene-1-Pfadsegment) = eine Zeile mit Anzahl.
  - Lehren: gebuendelt nach Art und Projekt, nicht einzeln gelistet.
  - Nur die JUENGSTEN Knoten/Lehren (siehe NEUESTE_N) bekommen den vollen
    Titel -- die scharfe Kante, die der Recall-Hook nachweislich verpasst
    (LIMIT ohne Sortierung, s. hub/shared-knowledge Fund 2026-08-07).
Ziel: ~1000-1500 Token statt ~9000.

Usage:
  python3 build_node_index.py            # schreibt NODE_INDEX.md
  python3 build_node_index.py --print    # zusaetzlich auf stdout (fuer Hook)
  python3 build_node_index.py --selftest
"""
from datetime import datetime
from pathlib import Path
import json
import sqlite3
import sys
import tempfile
import os

sys.path.insert(0, str(Path(__file__).resolve().parent))
from haken.ort import DB as _DB, WURZEL  # noqa: E402

DB = str(_DB)
OUT = WURZEL / "NODE_INDEX.md"

NEUESTE_N = 15  # Anzahl juengster Knoten/Lehren mit vollem Titel

INTRO = (
    "Landkarte, keine Volltexte. Gezielt nachladen: `knowledge_read <path>`, "
    "`knowledge_search <begriff>`, `lesson_query <begriff>`."
)


def _top_segment(path: str) -> str:
    p = path.strip("/")
    return "/" + (p.split("/", 1)[0] if p else "?")


def fetch_nodes(db_path: str) -> list[tuple[str, str, str]]:
    """(path, title, created_at) aller Knoten."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    try:
        return conn.execute(
            "SELECT path, title, created_at FROM knowledge_nodes ORDER BY path"
        ).fetchall()
    finally:
        conn.close()


def fetch_lessons(db_path: str) -> list[tuple[str, str, str, str]]:
    """(type, projects_json, description, first_seen) aller Lehren."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    try:
        return conn.execute(
            "SELECT type, projects, description, first_seen FROM lessons_learned"
        ).fetchall()
    finally:
        conn.close()


def render(nodes: list[tuple[str, str, str]],
           lessons: list[tuple[str, str, str, str]]) -> str:
    from collections import Counter

    aeste: Counter = Counter(_top_segment(p) for p, _, _ in nodes)

    lines = [
        "# Knoten-Index (generiert — nicht von Hand editieren)",
        "",
        f"Quelle: `shared-knowledge/build_node_index.py`. Knoten: {len(nodes)} "
        f"in {len(aeste)} Aesten · Lehren: {len(lessons)} · erzeugt: "
        f"{datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')}",
        "",
        INTRO,
        "",
        "## Landkarte (Ast: Anzahl Knoten)",
        "",
    ]
    for top, cnt in sorted(aeste.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"- {top}: {cnt}")
    lines.append("")

    if lessons:
        typ_cnt: Counter = Counter(t for t, *_ in lessons)
        proj_cnt: Counter = Counter()
        for _, projs, _, _ in lessons:
            try:
                for proj in json.loads(projs or "[]"):
                    proj_cnt[proj] += 1
            except (json.JSONDecodeError, TypeError):
                pass
        lines.append(f"## Lehren gebuendelt ({len(lessons)} gesamt)")
        lines.append("")
        lines.append("nach Art: " + ", ".join(
            f"{t} {c}" for t, c in typ_cnt.most_common()))
        top_proj = proj_cnt.most_common(8)
        rest_proj = sum(c for _, c in proj_cnt.most_common()[8:])
        proj_str = ", ".join(f"{p} {c}" for p, c in top_proj)
        if rest_proj:
            proj_str += f", +{len(proj_cnt) - 8} weitere Projekte ({rest_proj})"
        lines.append("nach Projekt: " + proj_str)
        lines.append("")

    lines.append(f"## Juengste {NEUESTE_N} Knoten")
    lines.append("")
    neueste_nodes = sorted(nodes, key=lambda r: r[2] or "", reverse=True)[:NEUESTE_N]
    for path, title, created in neueste_nodes:
        lines.append(f"- {(created or '?')[:10]} {path} — {title}")
    lines.append("")

    if lessons:
        lines.append(f"## Juengste {NEUESTE_N} Lehren")
        lines.append("")
        neueste_lessons = sorted(
            lessons, key=lambda r: r[3] or "", reverse=True)[:NEUESTE_N]
        for typ, _, desc, first_seen in neueste_lessons:
            desc = (desc or "").strip().splitlines()[0]
            if len(desc) > 140:
                desc = desc[:140].rsplit(" ", 1)[0] + "…"
            lines.append(f"- {(first_seen or '?')[:10]} [{typ}] {desc}")
        lines.append("")

    return "\n".join(lines)


def build(db_path: str = DB, out_path: Path = OUT) -> str | None:
    try:
        nodes = fetch_nodes(db_path)
        lessons = fetch_lessons(db_path)
    except sqlite3.Error:
        return None
    text = render(nodes, lessons)
    out_path.write_text(text)
    return text


def main() -> None:
    if "--selftest" in sys.argv:
        selftest()
        return
    text = build()
    if text is None:
        return
    if "--print" in sys.argv:
        print(text)


_NODES_DDL = "CREATE TABLE knowledge_nodes (path TEXT UNIQUE, title TEXT, created_at TEXT)"
_LESSONS_DDL = (
    "CREATE TABLE lessons_learned (type TEXT, projects TEXT, "
    "description TEXT, first_seen TEXT)"
)


def selftest() -> None:
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "t.db")
        conn = sqlite3.connect(db_path)
        conn.execute(_NODES_DDL)
        conn.execute(_LESSONS_DDL)
        sample = [
            ("/fahrtenbuch/gobd/hash-kette", "GoBD Hash-Kette", "2026-08-01"),
            ("/fahrtenbuch/ui/dashboard", "Dashboard-Layout", "2026-08-05"),
            ("/setfunk/webrtc/latenz", "WebRTC Latenz", "2026-08-03"),
        ]
        conn.executemany(
            "INSERT INTO knowledge_nodes(path, title, created_at) VALUES (?, ?, ?)",
            sample,
        )
        lessons = [
            ("error", '["fahrtenbuch"]', "Reconnect vergessen", "2026-08-06"),
            ("insight", '["fahrtenbuch","shared"]', "Ebene statt Funktion pruefen", "2026-08-02"),
        ]
        conn.executemany(
            "INSERT INTO lessons_learned(type, projects, description, first_seen) "
            "VALUES (?, ?, ?, ?)",
            lessons,
        )
        conn.commit()
        conn.close()

        out_path = Path(td) / "NODE_INDEX.md"
        text = build(db_path, out_path)
        assert text is not None
        assert out_path.exists()

        assert "Knoten: 3 in 2 Aesten" in text, text
        assert "Lehren: 2" in text
        assert "- /fahrtenbuch: 2" in text
        assert "- /setfunk: 1" in text
        assert "nach Art: error 1, insight 1" in text
        assert "nach Projekt: fahrtenbuch 2, shared 1" in text
        # Juengste-Liste sortiert nach created_at absteigend, voller Titel.
        idx_ui = text.index("Dashboard-Layout")
        idx_latenz = text.index("WebRTC Latenz")
        idx_hash = text.index("GoBD Hash-Kette")
        assert idx_ui < idx_latenz < idx_hash, "nicht nach Datum absteigend sortiert"
        assert "Reconnect vergessen" in text
        print("  gezaehlt statt aufgezaehlt, Juengste-Sortierung ok")

        # Leere DB darf nicht abstuerzen und keine Falschaussage erzeugen.
        empty_db = os.path.join(td, "empty.db")
        econn = sqlite3.connect(empty_db)
        econn.execute(_NODES_DDL)
        econn.execute(_LESSONS_DDL)
        econn.commit()
        econn.close()
        empty_out = Path(td) / "EMPTY.md"
        empty_text = build(empty_db, empty_out)
        assert empty_text is not None
        assert "Knoten: 0 in 0 Aesten" in empty_text
        assert "Lehren: 0" in empty_text  # Zahl ehrlich, aber kein Bloedsinn-Abschnitt
        assert "## Lehren gebuendelt" not in empty_text
        assert "## Landkarte" in empty_text
        print("  leere DB stuerzt nicht ab, keine irrefuehrende Ausgabe ok")

        # DB nicht lesbar -> still, kein Absturz.
        missing = os.path.join(td, "does_not_exist.db")
        missing_out = Path(td) / "MISSING.md"
        result = build(missing, missing_out)
        assert result is None
        assert not missing_out.exists()
        print("  fehlende DB -> still, exit ok")

    print("selftest ok")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
