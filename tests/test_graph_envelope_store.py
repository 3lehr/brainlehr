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


def test_backup_restore_corruption_and_explicit_gc_lifecycle(tmp_path: Path):
    graph, backup = tmp_path / "graph.json", tmp_path / "backup.json"
    saved = store.save(graph, {"nodes": [{"id": "a"}]}, revision="r1", analyzer_version="v1")
    assert store.backup(graph, backup) == saved
    store.garbage_collect(graph, reason="retention-expired")
    assert store.load(graph)["status"] == "deleted"
    assert store.restore(backup, graph) == saved
    backup.write_text('{"schema":1,"status":"active"}', encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        store.restore(backup, graph)


# BDW-P60: fail-closed shrink guard -----------------------------------------

def test_shrink_guard_blocks_silent_overwrite(tmp_path: Path):
    path = tmp_path / "graph.json"
    store.save(path, {"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{"src": "a", "dst": "b"}]},
               revision="r1", analyzer_version="v1")
    with pytest.raises(ValueError, match="shrink"):
        store.save(path, {"nodes": [{"id": "a"}]}, revision="r2", analyzer_version="v1")
    # force=True erlaubt die Überschreibung explizit
    store.save(path, {"nodes": [{"id": "a"}]}, revision="r2", analyzer_version="v1", force=True)


def test_atomic_write_survives_crash_before_replace(tmp_path: Path):
    """Simulierter Abbruch vor os.replace: das alte File bleibt intakt."""
    import os as _os
    path = tmp_path / "graph.json"
    original = store.save(path, {"nodes": [{"id": "a"}]}, revision="r1", analyzer_version="v1")

    real_replace = _os.replace
    def crashing_replace(src, dst):
        raise OSError("simulated crash before atomic replace")
    _os.replace = crashing_replace  # type: ignore[assignment]
    try:
        with pytest.raises(OSError, match="crash"):
            store.save(path, {"nodes": [{"id": "z"}]}, revision="r2", analyzer_version="v1", force=True)
    finally:
        _os.replace = real_replace  # type: ignore[assignment]

    # Das Original-File muss unverändert lesbar sein.
    assert store.load(path) == original
    # Das Tempfile darf nicht zurückbleiben.
    assert not any(f.name.startswith(".") for f in path.parent.iterdir())


def test_partial_never_overwrite_is_fail_closed(tmp_path: Path):
    """Ein vollständiger Graph darf nie still durch einen partiellen Neubau
    überschrieben werden."""
    path = tmp_path / "graph.json"
    store.save(path, {"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                    "edges": [{"src": "a", "dst": "b"}], "meta": {"count": 3}},
               revision="r1", analyzer_version="v1")
    # Payload verliert alle structural keys -> shrink
    with pytest.raises(ValueError, match="shrink"):
        store.save(path, {"meta": {"count": 3}}, revision="r2", analyzer_version="v1")
    # Payload fällt unter 50% der Top-Level-Keys -> shrink
    with pytest.raises(ValueError, match="shrink"):
        store.save(path, {"nodes": [{"id": "a"}]}, revision="r2", analyzer_version="v1")
    # Reduzieren auf genau 50% (3 -> 1.5, abgerundet 1 key) ist shrink
    with pytest.raises(ValueError, match="shrink"):
        store.save(path, {"nodes": [{"id": "a"}, {"id": "b"}]},
                   revision="r2", analyzer_version="v1")
    # force=True erlaubt die Schrumpfung explizit
    store.save(path, {"nodes": [{"id": "a"}]}, revision="r2", analyzer_version="v1", force=True)
    # Gleich großes Update ist erlaubt
    store.save(path, {"nodes": [{"id": "a"}]},
               revision="r2b", analyzer_version="v1")
    # Größeres Update ist erlaubt
    store.save(path, {"nodes": [{"id": "a"}, {"id": "b"}]},
               revision="r3", analyzer_version="v1")
