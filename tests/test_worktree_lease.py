import multiprocessing
import subprocess
import tempfile
from pathlib import Path

import pytest

from kern.worktree_lease import (LeaseCollision, LeaseConflict, WorktreeLeaseStore,
                                 git_status, git_worktrees, witness)


def _race_acquire(root, worktree, queue):
    try:
        WorktreeLeaseStore(root).acquire(owner=f"pid-{multiprocessing.current_process().pid}", task="race",
                                         worktree=worktree, branch="main", tree_hash="h", expiry=60)
    except LeaseCollision:
        queue.put("collision")
    else:
        queue.put("acquired")


def _crash_after_acquire(root):
    WorktreeLeaseStore(root).acquire(owner="crashed", task="crash", worktree="crashed",
                                     branch="main", tree_hash="h", expiry=1)
    __import__("os")._exit(0)


def test_atomic_collision_and_renewal():
    with tempfile.TemporaryDirectory() as td:
        store = WorktreeLeaseStore(td)
        first = store.acquire(owner="a", task="t", worktree="one", branch="main", tree_hash="h", expiry=20, now=0)
        with pytest.raises(LeaseCollision):
            store.acquire(owner="b", task="t", worktree="one", branch="main", tree_hash="h", expiry=20)
        with pytest.raises(LeaseConflict):
            store.renew("one", owner="b", expiry=30, now=1)
        renewed = store.renew("one", owner="a", expiry=30, now=1)
        assert renewed.expiry == 30 and store.audit(now=1)[0]["stale"] is False
        assert witness(first)["requirement_ids"] == ["P92"]


def test_stale_recovery_and_path_escape():
    with tempfile.TemporaryDirectory() as td:
        store = WorktreeLeaseStore(td)
        store.acquire(owner="a", task="t", worktree="one", branch="main", tree_hash="h", expiry=1)
        assert store.audit(now=2, recover=True)[0]["recovered"]
        with pytest.raises(ValueError):
            store.path("../escape")
        outside = Path(td).parent / "outside-leases"
        outside.mkdir(exist_ok=True)
        (Path(td) / ".worktree-leases").rmdir()
        (Path(td) / ".worktree-leases").symlink_to(outside, target_is_directory=True)
        with pytest.raises(ValueError):
            WorktreeLeaseStore(td)


def test_two_real_processes_race_and_different_worktrees_succeed():
    with tempfile.TemporaryDirectory() as td:
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        racers = [context.Process(target=_race_acquire, args=(td, "same", queue)) for _ in range(2)]
        for process in racers:
            process.start()
        for process in racers:
            process.join(15)
            assert process.exitcode == 0
        assert sorted(queue.get(timeout=2) for _ in racers) == ["acquired", "collision"]

        queue = context.Queue()
        separate = [context.Process(target=_race_acquire, args=(td, name, queue)) for name in ("left", "right")]
        for process in separate:
            process.start()
        for process in separate:
            process.join(15)
            assert process.exitcode == 0
        assert sorted(queue.get(timeout=2) for _ in separate) == ["acquired", "acquired"]


def test_crashed_process_stale_lease_recovers_with_audit_record():
    with tempfile.TemporaryDirectory() as td:
        process = multiprocessing.get_context("spawn").Process(target=_crash_after_acquire, args=(td,))
        process.start()
        process.join(15)
        assert process.exitcode == 0
        audit = WorktreeLeaseStore(td).audit(now=2, recover=True)
        assert audit == [{"worktree": "crashed", "owner": "crashed", "expiry": 1.0,
                          "stale": True, "recovered": True}]


def test_git_porcelain_nul_interfaces():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.email=a@b", "-c", "user.name=a", "commit", "--allow-empty", "-qm", "init"], check=True)
        assert Path(git_worktrees(root)[0]["worktree"]).resolve() == root.resolve()
        assert git_status(root) == []
