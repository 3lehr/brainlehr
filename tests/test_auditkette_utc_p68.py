from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path


ROOT = Path(__file__).parents[1]


def _module():
    path = ROOT / "migrationen" / "migrate_auditkette_utc_p68.py"
    spec = importlib.util.spec_from_file_location("p68", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_manifest_is_hash_only_and_excludes_non_timestamp_changes(tmp_path):
    m = _module()
    current = tmp_path / "current.db"
    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.executescript((ROOT / "schema.sql").read_text())
    conn.execute("INSERT INTO access_log (id, action, status, timestamp) VALUES (1,'read','completed','old')")
    conn.commit(); conn.close()
    # Store the pre-rewrite chain hash in both DBs, then change only the
    # current timestamp.  The stored hash must deliberately stay untouched.
    conn = sqlite3.connect(old)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM access_log WHERE id=1").fetchone()
    import knowledge_mcp_server as kms
    stored = kms.compute_ketten_hash(None, node_path=row['node_path'], action=row['action'], query=row['query'], project_id=row['project_id'], actor=row['actor'], model=row['model'], session=row['session'], status=row['status'], timestamp=row['timestamp'], zeilen_hash=row['zeilen_hash'])
    conn.execute("UPDATE access_log SET ketten_hash=? WHERE id=1", (stored,))
    conn.commit(); conn.close()
    source = sqlite3.connect(old)
    target = sqlite3.connect(current)
    source.backup(target)
    target.close(); source.close()
    conn = sqlite3.connect(current)
    conn.execute("UPDATE access_log SET timestamp='new' WHERE id=1")
    conn.commit(); conn.close()
    found = m.candidates(current, old)
    assert len(found) == 1 and found[0]['access_log_id'] == 1
    report = m.manifest(found, old)
    assert report['count'] == 1
    assert "'old'" not in str(report) and "'new'" not in str(report)
