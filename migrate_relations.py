#!/usr/bin/env python3
"""Add explicit knowledge relations and access provenance; safe and idempotent."""

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import knowledge_mcp_server as kms


def migrate(path: Path, backup: bool = True) -> Path | None:
    backup_path = None
    connection = sqlite3.connect(str(path))
    try:
        if backup:
            stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            backup_path = path.with_name(f"{path.name}.bak-{stamp}-relations")
            destination = sqlite3.connect(str(backup_path))
            try:
                connection.backup(destination)
            finally:
                destination.close()
        kms.ensure_schema(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(access_log)")}
        assert {"actor", "model", "session", "status"} <= columns
        connection.execute("SELECT 1 FROM knowledge_relations LIMIT 1")
    finally:
        connection.close()
    return backup_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=kms.DB_PATH)
    parser.add_argument("--no-backup", action="store_true", help="Only for disposable test databases")
    args = parser.parse_args()
    print(f"Datenbank: {args.db.resolve()}")
    backup = migrate(args.db.resolve(), not args.no_backup)
    print(f"migrated: {args.db.resolve()}")
    print(f"backup: {backup}" if backup else "backup: skipped")


if __name__ == "__main__":
    main()
