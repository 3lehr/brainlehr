from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("selbstbeschreibung", ROOT / "melder/selbstbeschreibung.py")
selbstbeschreibung = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(selbstbeschreibung)


class _Cursor:
    rowcount = 0


class _Connection:
    def execute(self, *_args):
        return _Cursor()

    def commit(self):
        pass

    def close(self):
        pass


class _Kms:
    DB_PATH = Path("knowledge.db")

    def __init__(self):
        self.updates: list[dict] = []

    def knowledge_read(self, _path):
        return {}

    def knowledge_add(self, **_kwargs):
        return {"error": "Node already exists", "existing_id": "/existing"}

    def knowledge_update(self, **kwargs):
        self.updates.append(kwargs)


def test_existing_generated_nodes_are_updated(monkeypatch):
    kms = _Kms()
    monkeypatch.setitem(sys.modules, "knowledge_mcp_server", kms)
    monkeypatch.setattr(selbstbeschreibung.speicher, "verbinde_bestand", lambda _db: _Connection())

    result = selbstbeschreibung.anlegen()

    assert result["neu"] == 0
    assert len(kms.updates) == len(selbstbeschreibung.FAEHIGKEITEN) + len(selbstbeschreibung.PUBLIC_CONTEXT) + 1
    assert kms.updates[-1]["content"] == selbstbeschreibung.PUBLIC_CONTEXT[-1][2]
