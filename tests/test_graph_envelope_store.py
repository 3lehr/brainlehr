from pathlib import Path

import pytest

from kern import graph_envelope_store as store


def test_round_trip_and_schema_migration_guard(tmp_path: Path):
    path = tmp_path / "graph.json"
    saved = store.save(path, {"nodes": [{"id": "a"}]}, revision="abc", analyzer_version="v1")
    assert store.load(path) == saved
    path.write_text(path.read_text().replace('"schema":1', '"schema":99'), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        store.load(path)


def test_corruption_is_detected(tmp_path: Path):
    path = tmp_path / "graph.json"
    store.save(path, {"nodes": []}, revision="abc", analyzer_version="v1")
    path.write_text(path.read_text().replace('"nodes":[]', '"nodes":[{"id":"changed"}]'), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        store.load(path)


def test_delete_is_a_verified_tombstone_and_missing_is_empty(tmp_path: Path):
    path = tmp_path / "graph.json"
    assert store.load(path) is None
    store.save(path, {"nodes": []}, revision="abc", analyzer_version="v1")
    tombstone = store.delete(path, reason="superseded")
    assert store.load(path) == tombstone
    assert tombstone["status"] == "deleted"
