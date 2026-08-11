"""Synthetic logical-two-store tests; they deliberately make no P2 claim."""
from __future__ import annotations

import hashlib
import multiprocessing as mp
import os
import re
import secrets
import subprocess

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _seal(key: bytes, subject: str, text: str) -> bytes:
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, text.encode(), subject.encode())


def _open(key: bytes, subject: str, blob: bytes) -> str:
    return AESGCM(key).decrypt(blob[:12], blob[12:], subject.encode()).decode()


def _derive(master: bytes, ref: tuple[str, ...]) -> bytes:
    return hashlib.sha256(master + repr(ref).encode()).digest()


def _keyholder(conn, vault_path: str) -> None:
    ref = ("A", "identity", "care", "team", "epoch-1")
    a_key, b_key = secrets.token_bytes(32), secrets.token_bytes(32)
    a_blob = _seal(a_key, "A", "SYNTHETIC-A")
    b_blob = _seal(b_key, "B", "SYNTHETIC-B")
    with open(vault_path, "wb") as vault:
        vault.write(a_key)
    copied_key = master = None
    run_id = secrets.token_hex(6)
    while True:
        op = conn.recv()
        if op == "public":
            conn.send({"pid": os.getpid(), "a_blob": a_blob, "b_blob": b_blob, "run_id": run_id})
        elif op == "a":
            conn.send(_open(a_key, "A", a_blob) if a_key else None)
        elif op == "b":
            conn.send(_open(b_key, "B", b_blob))
        elif op == "copy":
            copied_key = a_key
            conn.send(True)
        elif op == "master":
            master = secrets.token_bytes(32)
            a_key = _derive(master, ref)
            a_blob = _seal(a_key, "A", "SYNTHETIC-A")
            conn.send(True)
        elif op == "shared":
            conn.send({"key": a_key, "blob": a_blob})
        elif op == "delete":
            a_key = None
            os.unlink(vault_path)
            conn.send(True)
        elif op == "mutant":
            if copied_key and _open(copied_key, "A", a_blob) == "SYNTHETIC-A":
                conn.send("KEY_COPY")
            elif master and _open(_derive(master, ref), "A", a_blob) == "SYNTHETIC-A":
                conn.send("DETERMINISTIC_MASTER_DERIVATION")
            else:
                conn.send(None)
        elif op == "stop":
            conn.send(True)
            conn.close()
            return


def _workstore(conn) -> None:
    state = {
        "cache": "", "log": "", "fts": "", "vector": "", "export": "",
        "key_mutant": None, "shared": None, "old_handles": [],
        "run_id": secrets.token_hex(6), "projection": {"groups": 2}, "cipher": b"",
    }
    while True:
        msg = conn.recv()
        if msg[0] == "init":
            state["cipher"] = msg[1]
            conn.send({"pid": os.getpid(), "run_id": state["run_id"]})
        elif msg[0] == "inject":
            state[msg[1]] = msg[2]
            conn.send(True)
        elif msg[0] == "shared":
            state["shared"] = msg[1]
            conn.send(True)
        elif msg[0] == "gate":
            if state["key_mutant"]:
                conn.send((False, state["key_mutant"]))
            elif any("SYNTHETIC-A" in state[name] for name in ("cache", "log", "vector")):
                conn.send((False, "PLAINTEXT_CACHE_LOG_EMBEDDING"))
            elif state["shared"] and _open(state["shared"]["key"], "A", state["shared"]["blob"]) == "SYNTHETIC-A":
                conn.send((False, "SHARED_BLOB"))
            elif state["old_handles"]:
                conn.send((False, "CACHE_FD_SESSION"))
            else:
                conn.send((True, None))
        elif msg[0] == "restore":
            snapshot, anchor = msg[1:]
            if not anchor or not anchor.get("reachable") or not anchor.get("authentic"):
                conn.send((False, "RESTORE_WITHOUT_CURRENT_ANCHOR"))
            elif snapshot["epoch"] < anchor["epoch"]:
                conn.send((False, "STALE_SNAPSHOT"))
            else:
                conn.send((True, None))
        elif msg[0] == "serve":
            conn.send((True, None) if msg[1] == state["run_id"] else (False, "CACHE_FD_SESSION"))
        elif msg[0] == "introspect":
            conn.send({
                "pid": os.getpid(), "run_id": state["run_id"],
                "projection": state["projection"], "cache": state["cache"],
                "log": state["log"], "fts": state["fts"], "vector": state["vector"],
                "export": state["export"], "old_handles": list(state["old_handles"]),
            })
        elif msg[0] == "stop":
            conn.send(True)
            conn.close()
            return


def _start_process(ctx, target, *args):
    parent, child = ctx.Pipe()
    process = ctx.Process(target=target, args=(child, *args))
    process.start()
    child.close()
    return parent, process


def _ask(conn, message):
    conn.send(message)
    assert conn.poll(2), "IPC timeout"
    return conn.recv()


def _stop_process(conn, process, stop_message):
    if process.is_alive():
        assert _ask(conn, stop_message) is True
        process.join(2)
    if process.is_alive():
        process.terminate()
        process.join(2)
        raise AssertionError("process did not stop cleanly")
    closed = False
    try:
        conn.send(stop_message)
        if conn.poll(0.5):
            conn.recv()
    except (EOFError, BrokenPipeError, OSError):
        closed = True
    finally:
        conn.close()
    assert closed, "old parent IPC handle remained usable"


def _safe_stop(conn, process, stop_message):
    if conn is None or process is None:
        return
    try:
        _stop_process(conn, process, stop_message)
    except (AssertionError, EOFError, BrokenPipeError, OSError):
        if process.is_alive():
            process.terminate()
            process.join(2)
        conn.close()


def _lsof_matches(path) -> list[str]:
    output = subprocess.run(
        ["/usr/sbin/lsof", "-Fn", "-p", str(os.getpid())],
        text=True, capture_output=True, check=True,
    ).stdout
    return [line for line in output.splitlines() if str(path) in line]


def _p2_gate(vault_path) -> tuple[bool, str | None]:
    return (False, "P2_SHARED_ROOT_SAME_UID") if os.access(vault_path, os.R_OK) else (True, None)


def _assert_clean_introspection(info: dict) -> None:
    serialized = repr(info).lower()
    assert "key" not in serialized and "dek" not in serialized
    assert not re.search(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", serialized)
    assert info["old_handles"] == []


def test_baseline_and_crypto_mutants_use_fresh_keyholders(tmp_path):
    ctx = mp.get_context("spawn")
    vault = tmp_path / "synthetic-vault"
    ws_conn = ws_process = kh_conn = kh_process = None
    try:
        ws_conn, ws_process = _start_process(ctx, _workstore)
        kh_conn, kh_process = _start_process(ctx, _keyholder, str(vault))
        public = _ask(kh_conn, "public")
        work = _ask(ws_conn, ("init", public["a_blob"]))
        assert len({os.getpid(), public["pid"], work["pid"]}) == 3
        _assert_clean_introspection(_ask(ws_conn, ("introspect",)))
        assert _ask(kh_conn, "a") == "SYNTHETIC-A" and _ask(kh_conn, "b") == "SYNTHETIC-B"
        _ask(kh_conn, "delete")
        assert _ask(kh_conn, "a") is None and _ask(kh_conn, "b") == "SYNTHETIC-B"
        assert _lsof_matches(vault) == []
        assert _ask(ws_conn, ("gate",)) == (True, None)
        previous_identity = (public["pid"], public["run_id"])
        _stop_process(kh_conn, kh_process, "stop")
        kh_conn = kh_process = None

        for mutation, expected in (("copy", "KEY_COPY"), ("master", "DETERMINISTIC_MASTER_DERIVATION")):
            kh_conn, kh_process = _start_process(ctx, _keyholder, str(vault))
            current = _ask(kh_conn, "public")
            assert (current["pid"], current["run_id"]) != previous_identity
            previous_identity = (current["pid"], current["run_id"])
            assert _ask(kh_conn, "a") == "SYNTHETIC-A" and _ask(kh_conn, "b") == "SYNTHETIC-B"
            _ask(kh_conn, mutation)
            _ask(kh_conn, "delete")
            assert _ask(kh_conn, "a") is None and _ask(kh_conn, "b") == "SYNTHETIC-B"
            _ask(ws_conn, ("inject", "key_mutant", _ask(kh_conn, "mutant")))
            assert _ask(ws_conn, ("gate",)) == (False, expected)
            _ask(ws_conn, ("inject", "key_mutant", None))
            assert _ask(ws_conn, ("gate",)) == (True, None)
            _stop_process(kh_conn, kh_process, "stop")
            kh_conn = kh_process = None

        kh_conn, kh_process = _start_process(ctx, _keyholder, str(vault))
        current = _ask(kh_conn, "public")
        assert (current["pid"], current["run_id"]) != previous_identity
        assert _ask(ws_conn, ("gate",)) == (True, None)
        shared = _ask(kh_conn, "shared")
        _ask(kh_conn, "delete")
        _ask(ws_conn, ("shared", shared))
        assert _ask(ws_conn, ("gate",)) == (False, "SHARED_BLOB")
        _ask(ws_conn, ("shared", None))
        assert _ask(ws_conn, ("gate",)) == (True, None)

        for surface in ("cache", "log", "vector"):
            assert _ask(ws_conn, ("gate",)) == (True, None)
            _ask(ws_conn, ("inject", surface, "SYNTHETIC-A"))
            assert _ask(ws_conn, ("gate",)) == (False, "PLAINTEXT_CACHE_LOG_EMBEDDING")
            _ask(ws_conn, ("inject", surface, ""))
    finally:
        _safe_stop(kh_conn, kh_process, "stop")
        _safe_stop(ws_conn, ws_process, ("stop",))


def test_fd_and_same_uid_mutants_are_separate_from_baseline(tmp_path):
    ctx = mp.get_context("spawn")
    vault = tmp_path / "synthetic-vault"
    ws_conn = ws_process = kh_conn = kh_process = None
    old_fd = None
    try:
        ws_conn, ws_process = _start_process(ctx, _workstore)
        _ask(ws_conn, ("init", b"ciphertext-only"))
        assert _ask(ws_conn, ("gate",)) == (True, None)

        kh_conn, kh_process = _start_process(ctx, _keyholder, str(vault))
        fd_run = _ask(kh_conn, "public")
        old_fd = os.open(vault, os.O_RDONLY)
        _ask(kh_conn, "delete")
        key_bytes = os.read(old_fd, 32)
        assert len(key_bytes) == 32
        hits = _lsof_matches(vault)
        assert hits, "lsof did not observe the live unlinked vault FD"
        _ask(ws_conn, ("inject", "old_handles", [f"lsof:fd:{old_fd}"]))
        assert _ask(ws_conn, ("gate",)) == (False, "CACHE_FD_SESSION")
        os.close(old_fd)
        old_fd = None
        assert _lsof_matches(vault) == []
        _ask(ws_conn, ("inject", "old_handles", []))
        assert _ask(ws_conn, ("gate",)) == (True, None)
        _stop_process(kh_conn, kh_process, "stop")
        kh_conn = kh_process = None

        kh_conn, kh_process = _start_process(ctx, _keyholder, str(vault))
        direct_run = _ask(kh_conn, "public")
        assert (direct_run["pid"], direct_run["run_id"]) != (fd_run["pid"], fd_run["run_id"])
        assert len(vault.read_bytes()) == 32
        assert _p2_gate(vault) == (False, "P2_SHARED_ROOT_SAME_UID")
    finally:
        if old_fd is not None:
            os.close(old_fd)
        _safe_stop(kh_conn, kh_process, "stop")
        _safe_stop(ws_conn, ws_process, ("stop",))


def test_workstore_restart_and_restore_use_fresh_pipes():
    ctx = mp.get_context("spawn")
    ws_conn = ws_process = None
    try:
        ws_conn, ws_process = _start_process(ctx, _workstore)
        old = _ask(ws_conn, ("init", b"ciphertext-only"))
        old_info = _ask(ws_conn, ("introspect",))
        _assert_clean_introspection(old_info)
        assert _ask(ws_conn, ("serve", old["run_id"])) == (True, None)
        valid_anchor = {"epoch": 2, "reachable": True, "authentic": True}
        assert _ask(ws_conn, ("restore", {"epoch": 1}, valid_anchor)) == (False, "STALE_SNAPSHOT")
        assert _ask(ws_conn, ("restore", {"epoch": 2}, valid_anchor)) == (True, None)
        for anchor in (None, {"epoch": 2, "reachable": False, "authentic": True}, {"epoch": 2, "reachable": True, "authentic": False}):
            assert _ask(ws_conn, ("restore", {"epoch": 2}, anchor)) == (False, "RESTORE_WITHOUT_CURRENT_ANCHOR")
        _stop_process(ws_conn, ws_process, ("stop",))
        ws_conn = ws_process = None

        ws_conn, ws_process = _start_process(ctx, _workstore)
        new = _ask(ws_conn, ("init", b"ciphertext-only"))
        assert new["pid"] != old["pid"] and new["run_id"] != old["run_id"]
        assert _ask(ws_conn, ("serve", old["run_id"])) == (False, "CACHE_FD_SESSION")
        assert _ask(ws_conn, ("serve", new["run_id"])) == (True, None)
        new_info = _ask(ws_conn, ("introspect",))
        _assert_clean_introspection(new_info)
        assert [new_info[name] for name in ("cache", "log", "fts", "vector", "export")] == [""] * 5
    finally:
        _safe_stop(ws_conn, ws_process, ("stop",))
