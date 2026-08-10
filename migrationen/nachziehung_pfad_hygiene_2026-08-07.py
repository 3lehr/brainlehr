#!/usr/bin/env python3
"""EINMALIGER Nachzieh-Lauf (ADR-032 Gruppe 1, Auftrag 2026-08-07) -- kein
Zeitplan, kein wiederkehrender Aufruf. Saeubert das letzte Pfadsegment jener
Bestandsknoten, die find_path_hygiene() (knowledge_lint.py) als Satzzeichen-
oder Genau-SLUG_MAX_LEN-Fund meldet -- dieselbe Bedingung, wortgleich aus
knowledge_lint.py uebernommen (_PATH_PUNCT_RE / SLUG_MAX_LEN), sonst behebt
der Lauf etwas anderes als das, was gemeldet wird.

Schreibzeit-Seite ist bereits erledigt (knowledge_mcp_server.py: _slugify()
kappt nie mehr genau bei SLUG_MAX_LEN, _normalize_path() saeubert neu
angelegte Aeste). Dieser Lauf ist NUR die Nachziehung fuer die 139 Altfunde.

Sicherheitsregel (Auftrags-Grenze): ein Pfad, auf den eine Relation zeigt
(Quelle oder Ziel), der als parent_path eines Kindes dient, oder auf den eine
Lesson per node_path verweist, wird NICHT umbenannt -- er wuerde sonst
unauffindbar. Stattdessen gemeldet und ausgelassen.
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

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import knowledge_mcp_server as kms  # _slugify(), now_iso() -- dieselbe Regel wie am Schreibvorgang

DB_PATH = Path(__file__).parent / "knowledge.db"
_PATH_PUNCT_RE = re.compile(r"[^A-Za-z0-9/\-]")  # wortgleich aus knowledge_lint.py
SLUG_MAX_LEN = kms.SLUG_MAX_LEN


def find_bad(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    out = []
    for r in conn.execute("SELECT id, path FROM knowledge_nodes"):
        last = r["path"].rsplit("/", 1)[-1]
        if _PATH_PUNCT_RE.search(r["path"]) or len(last) == SLUG_MAX_LEN:
            out.append((r["id"], r["path"]))
    return out


def main() -> int:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    bad = find_bad(conn)
    bad_paths = {p for _, p in bad}
    protected = (
        {r[0] for r in conn.execute("SELECT DISTINCT target_path FROM knowledge_relations")}
        | {r[0] for r in conn.execute("SELECT DISTINCT source_path FROM knowledge_relations")}
        | {r[0] for r in conn.execute("SELECT DISTINCT parent_path FROM knowledge_nodes")}
        | {r[0] for r in conn.execute("SELECT DISTINCT node_path FROM lessons_learned WHERE node_path IS NOT NULL")}
    )

    renamed, skipped_protected, skipped_collision = [], [], []
    for node_id, old_path in bad:
        if old_path in protected:
            skipped_protected.append(old_path)
            continue
        row = conn.execute("SELECT title, parent_path FROM knowledge_nodes WHERE id = ?", (node_id,)).fetchone()
        parent = row["parent_path"] or "/"
        new_slug = kms._slugify(row["title"])
        new_path = f"{parent}/{new_slug}" if parent != "/" else f"/{new_slug}"
        if new_path == old_path:
            continue
        collision = conn.execute("SELECT 1 FROM knowledge_nodes WHERE path = ?", (new_path,)).fetchone()
        if collision:
            skipped_collision.append((old_path, new_path))
            continue
        conn.execute(
            "UPDATE knowledge_nodes SET path = ?, updated_at = ? WHERE id = ?",
            (new_path, kms.now_iso(), node_id),
        )
        renamed.append((old_path, new_path))

    conn.commit()
    conn.close()

    print(f"Gefunden (path_hygiene): {len(bad)}")
    print(f"Umbenannt: {len(renamed)}")
    for old, new in renamed:
        print(f"  {old} -> {new}")
    print(f"Ausgelassen (referenziert, MELDEN statt raten): {len(skipped_protected)}")
    for p in skipped_protected:
        print(f"  SKIP {p}")
    print(f"Ausgelassen (Zielpfad kollidiert bereits): {len(skipped_collision)}")
    for old, new in skipped_collision:
        print(f"  KOLLISION {old} -> {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
