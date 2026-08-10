#!/usr/bin/env python3
"""nachschlagewerk_suche.py -- Auftrag S1b (docs/PLAN_DESTILLE_2026-08-09.md),
Teil 3: die eigene Tuer.

Nachschlagewerke (gattung='nachschlagewerk', s. schema.sql/migrate_gattung.py)
nehmen am automatischen Abruf NICHT mehr teil (haken/knowledge_recall_hook.py
+ gattung_filter.py). Sie bleiben trotzdem durchsuchbar -- von Hand, gezielt,
wenn die Frage lautet "hat das jemand vor uns bezahlt?": schlaegt eine fremde,
teuer erkaufte Sammlung (NASA LLIS) zu einer eigenen Regel nach.

Eigenstaendiges Modul mit Kommandozeile, KEIN MCP-Werkzeug (knowledge_mcp_
server.py ist tabu fuer diesen Auftrag) -- Aufruf per
`.venv/bin/python shared-knowledge/nachschlagewerk_suche.py "<stichworte>"`.

Nutzt denselben Stichwort-Apparat wie der Recall-Haken (keywords()/
fts_match()/hits()) fuer vergleichbare Treffer, aber OHNE MIN_HITS/Radar/
Ensemble -- eine Handsuche darf mehr liefern als der automatische Abruf, der
bewusst knapp bleibt.

Usage:
    .venv/bin/python shared-knowledge/nachschlagewerk_suche.py <stichworte...> [--limit N]
    .venv/bin/python shared-knowledge/nachschlagewerk_suche.py --selftest
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "haken"))
import knowledge_recall_hook as rh  # noqa: E402 -- keywords()/fts_match(), kein neuer Apparat
import ort  # noqa: E402


def suche(text: str, conn: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """Durchsucht AUSSCHLIESSLICH gattung='nachschlagewerk' -- die eigene
    Tuer, spiegelbildlich zu gattung_filter.SQL_ARBEITSBESTAND_NUR im Haken."""
    kws = rh.keywords(text)
    if not kws:
        return []
    rows = conn.execute(
        "SELECT n.id, n.path, n.title, n.summary, n.source, "
        "bm25(knowledge_fts) AS score "
        "FROM knowledge_fts f JOIN knowledge_nodes n ON n.rowid = f.rowid "
        "WHERE knowledge_fts MATCH ? AND n.zurueckgezogen = 0 AND n.gattung = 'nachschlagewerk' "
        "ORDER BY bm25(knowledge_fts) LIMIT ?",
        (rh.fts_match(kws), limit),
    ).fetchall()
    return [dict(r) for r in rows]


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    args = [a for a in sys.argv[1:] if not a.startswith("--limit")]
    limit = 10
    for a in sys.argv[1:]:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
    if not args:
        print("Usage: nachschlagewerk_suche.py <stichworte...> [--limit=N]")
        return 1
    text = " ".join(args)
    conn = sqlite3.connect(f"file:{ort.DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        treffer = suche(text, conn, limit=limit)
    finally:
        conn.close()
    if not treffer:
        print("Kein Treffer im Nachschlagewerk.")
        return 0
    for t in treffer:
        print(f"{t['id']}  {t['path']}")
        print(f"  {t['title']} -- {t['summary']}")
        print(f"  Quelle: {t['source']}")
    return 0


def _selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "knowledge.db"
        schema_sql = (HERE / "schema.sql").read_text(encoding="utf-8")
        conn = sqlite3.connect(str(db_path))
        conn.executescript(schema_sql)
        for id_, path, title, summary, gattung in (
            ("n1", "/nasa-llis/x", "Vibration", "Vibrationstest vor Start pruefen", "nachschlagewerk"),
            ("n2", "/eigenes", "Vibration eigen", "Eigene Vibrationsregel im Haus", "arbeitsbestand"),
        ):
            conn.execute(
                "INSERT INTO knowledge_nodes (id, path, project_id, title, summary, content, level, "
                "source, gattung, norm_entscheidung, norm_entschieden_von, norm_entschieden_grund) "
                "VALUES (?, ?, 'shared', ?, ?, ?, 0, 'https://nen.nasa.gov/x', ?, "
                "'keine_norm', 'skript:test', 'Testvorrichtung')",
                (id_, path, title, summary, summary, gattung),
            )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        treffer = suche("vibration", conn, limit=10)
        conn.close()

        ids = {t["id"] for t in treffer}
        assert ids == {"n1"}, f"eigene Tuer soll NUR Nachschlagewerke liefern, bekam {ids}"

    print("SELFTEST OK: nachschlagewerk_suche liefert ausschliesslich gattung='nachschlagewerk'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
