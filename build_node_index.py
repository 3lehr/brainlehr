#!/usr/bin/env python3
"""
build_node_index.py — Landkarte aller Knoten in knowledge.db.

Vorbild: begod/scripts/knowledge_index.py (Konsile+ADRs). Dasselbe Muster,
hier ueber die 219 Knoten der Datenbank, die dort fehlen -- Agent sieht sonst
nur die 0-3 Treffer des Recall-Hooks und weiss nie, dass mehr existiert.

Nur path+title (kein summary): 7k statt 30k Token je Sitzung.

Usage:
  python3 build_node_index.py            # schreibt NODE_INDEX.md
  python3 build_node_index.py --print    # zusaetzlich auf stdout (fuer Hook)
  python3 build_node_index.py --selftest
"""
from datetime import datetime
from pathlib import Path
import sqlite3
import sys
import tempfile
import os

DB = "/Volumes/daten/Begod2026/hub/shared-knowledge/knowledge.db"
OUT = Path("/Volumes/daten/Begod2026/hub/shared-knowledge/NODE_INDEX.md")

INTRO = (
    "Das ist die vollstaendige Landkarte aller Knoten in der Knowledge-DB. "
    "Inhalte NICHT hier -- bei Bedarf gezielt mit `knowledge_read <path>` "
    "nachladen."
)


def fetch_nodes(db_path: str) -> list[tuple[str, str]]:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2.0)
    try:
        rows = conn.execute(
            "SELECT path, title FROM knowledge_nodes ORDER BY path"
        ).fetchall()
    finally:
        conn.close()
    return rows


def render(rows: list[tuple[str, str]]) -> str:
    groups: dict[str, list[str]] = {}
    for path, title in rows:
        top = "/" + path.strip("/").split("/", 1)[0] if path.strip("/") else "/"
        groups.setdefault(top, []).append(f"- {path} — {title}")

    lines = [
        "# Knoten-Index (generiert — nicht von Hand editieren)",
        "",
        f"Quelle: `shared-knowledge/build_node_index.py`. Knoten: {len(rows)} · "
        f"erzeugt: {datetime.now().astimezone().strftime('%Y-%m-%dT%H:%M:%S%z')}",
        "",
        INTRO,
        "",
    ]
    for top in sorted(groups):
        lines.append(f"## {top}")
        lines.append("")
        lines.extend(groups[top])
        lines.append("")
    return "\n".join(lines)


def build(db_path: str = DB, out_path: Path = OUT) -> str | None:
    try:
        rows = fetch_nodes(db_path)
    except sqlite3.Error:
        return None
    text = render(rows)
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


def selftest() -> None:
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "t.db")
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE knowledge_nodes (path TEXT UNIQUE, title TEXT)"
        )
        sample = [
            ("/fahrtenbuch/gobd/hash-kette", "GoBD Hash-Kette"),
            ("/fahrtenbuch/ui/dashboard", "Dashboard-Layout"),
            ("/setfunk/webrtc/latenz", "WebRTC Latenz"),
        ]
        conn.executemany(
            "INSERT INTO knowledge_nodes(path, title) VALUES (?, ?)", sample
        )
        conn.commit()
        conn.close()

        out_path = Path(td) / "NODE_INDEX.md"
        text = build(db_path, out_path)
        assert text is not None
        assert out_path.exists()

        for path, title in sample:
            occ = text.count(f"- {path} — {title}")
            assert occ == 1, (path, occ)
        assert "## /fahrtenbuch" in text
        assert "## /setfunk" in text
        assert text.index("## /fahrtenbuch") < text.index("## /setfunk")
        assert "Knoten: 3" in text
        print("  Knoten je einmal, Gruppierung nach oberstem Segment ok")

        # Leere DB darf nicht abstuerzen.
        empty_db = os.path.join(td, "empty.db")
        econn = sqlite3.connect(empty_db)
        econn.execute("CREATE TABLE knowledge_nodes (path TEXT UNIQUE, title TEXT)")
        econn.commit()
        econn.close()
        empty_out = Path(td) / "EMPTY.md"
        empty_text = build(empty_db, empty_out)
        assert empty_text is not None and "Knoten: 0" in empty_text
        print("  leere DB stuerzt nicht ab ok")

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
