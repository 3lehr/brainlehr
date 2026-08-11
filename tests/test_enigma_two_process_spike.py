"""Synthetic logical-two-store test; it deliberately makes no P2 claim."""
from __future__ import annotations

import hashlib
import multiprocessing as mp
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _seal(key, subject, text):
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, text.encode(), subject.encode())


def _open(key, subject, blob):
    return AESGCM(key).decrypt(blob[:12], blob[12:], subject.encode()).decode()


def _derive(master, ref):
    return hashlib.sha256(master + repr(ref).encode()).digest()


def _keyholder(conn, vault_path):
    ref = ("A", "identity", "care", "team", "epoch-1")
    a_key, b_key = secrets.token_bytes(32), secrets.token_bytes(32)
    a_blob, b_blob = _seal(a_key, "A", "SYNTHETIC-A"), _seal(b_key, "B", "SYNTHETIC-B")
    open(vault_path, "wb").write(a_key)  # synthetic Same-UID root mutation target
    copy = master = None
    run = secrets.token_hex(6)
    while True:
        op = conn.recv()
        if op == "public": conn.send({"pid": os.getpid(), "a_blob": a_blob, "b_blob": b_blob, "run": run})
        elif op == "a": conn.send(_open(a_key, "A", a_blob) if a_key else None)
        elif op == "b": conn.send(_open(b_key, "B", b_blob))
        elif op == "copy": copy = a_key; conn.send(True)
        elif op == "master":
            master = secrets.token_bytes(32); a_key = _derive(master, ref); a_blob = _seal(a_key, "A", "SYNTHETIC-A"); conn.send(True)
        elif op == "shared": conn.send({"key": a_key, "blob": a_blob})
        elif op == "delete": a_key = None; os.unlink(vault_path); conn.send(True)
        elif op == "mutant": conn.send("KEY_COPY" if copy and _open(copy, "A", a_blob) else "DETERMINISTIC_MASTER_DERIVATION" if master and _open(_derive(master, ref), "A", a_blob) else None)
        elif op == "restart": run = secrets.token_hex(6); conn.send({"run": run, "pid": os.getpid()})
        elif op == "stop": conn.send(True); conn.close(); return


def _workstore(conn):
    state = {"cache": "", "log": "", "vector": "", "key_mutant": None, "shared": None, "run": secrets.token_hex(6)}
    while True:
        msg = conn.recv()
        if msg[0] == "init": state["projection"] = {"groups": 2}; state["cipher"] = msg[1]; conn.send(os.getpid())
        elif msg[0] == "inject": state[msg[1]] = msg[2]; conn.send(True)
        elif msg[0] == "shared": state["shared"] = msg[1]; conn.send(True)
        elif msg[0] == "gate":
            if state["key_mutant"]: conn.send((False, state["key_mutant"]))
            elif any("SYNTHETIC-A" in state[x] for x in ("cache", "log", "vector")): conn.send((False, "PLAINTEXT_CACHE_LOG_EMBEDDING"))
            elif state["shared"] and _open(state["shared"]["key"], "A", state["shared"]["blob"]) == "SYNTHETIC-A": conn.send((False, "SHARED_BLOB"))
            else: conn.send((True, None))
        elif msg[0] == "restore":
            snapshot, anchor = msg[1:]
            conn.send((False, "RESTORE_WITHOUT_CURRENT_ANCHOR") if not anchor else (False, "STALE_SNAPSHOT") if snapshot["epoch"] < anchor["epoch"] else (True, None))
        elif msg[0] == "serve": conn.send((False, "CACHE_FD_SESSION") if msg[1] != state["run"] else (True, None))
        elif msg[0] == "state": conn.send({k: v for k, v in state.items() if k not in {"cipher"}})
        elif msg[0] == "stop": conn.send(True); conn.close(); return


def _ask(conn, message):
    conn.send(message)
    assert conn.poll(2), "IPC timeout"
    return conn.recv()


def _p2_gate(vault_path):
    return (False, "P2_SHARED_ROOT_SAME_UID") if os.access(vault_path, os.R_OK) else (True, None)


def test_logical_two_store_ipc_oracles_and_same_uid_root(tmp_path):
    ctx = mp.get_context("fork")
    kp_parent, kp_child = ctx.Pipe(); ws_parent, ws_child = ctx.Pipe(); vault = tmp_path / "synthetic-vault"
    kp = ctx.Process(target=_keyholder, args=(kp_child, str(vault))); ws = ctx.Process(target=_workstore, args=(ws_child,))
    kp.start(); ws.start()
    try:
        public = _ask(kp_parent, "public"); ws_pid = _ask(ws_parent, ("init", public["a_blob"]))
        assert len({os.getpid(), public["pid"], ws_pid}) == 3
        assert set(_ask(ws_parent, ("state",))).isdisjoint({"a_key", "b_key", "dek"})
        assert _ask(kp_parent, "a") == "SYNTHETIC-A"; assert _ask(kp_parent, "b") == "SYNTHETIC-B"
        _ask(kp_parent, "delete"); assert not vault.exists(); assert _ask(kp_parent, "a") is None; assert _ask(ws_parent, ("gate",)) == (True, None)
        # New isolated runs make pre-delete mutation observable without preserving test state.
        for command, expected in [("copy", "KEY_COPY"), ("master", "DETERMINISTIC_MASTER_DERIVATION")]:
            _ask(kp_parent, "stop"); kp.join(2); kp = ctx.Process(target=_keyholder, args=(kp_child, str(vault))); kp.start()
            assert _ask(kp_parent, "a") == "SYNTHETIC-A" and _ask(kp_parent, "b") == "SYNTHETIC-B"
            _ask(kp_parent, command); _ask(kp_parent, "delete"); assert _ask(kp_parent, "a") is None
            _ask(ws_parent, ("inject", "key_mutant", _ask(kp_parent, "mutant"))); assert _ask(ws_parent, ("gate",)) == (False, expected)
            _ask(ws_parent, ("inject", "key_mutant", None))
        for surface in ("cache", "log", "vector"):
            _ask(ws_parent, ("inject", surface, "")); assert _ask(ws_parent, ("gate",)) == (True, None)
            _ask(ws_parent, ("inject", surface, "SYNTHETIC-A")); assert _ask(ws_parent, ("gate",)) == (False, "PLAINTEXT_CACHE_LOG_EMBEDDING")
            _ask(ws_parent, ("inject", surface, ""))
        assert _ask(ws_parent, ("restore", {"epoch": 1}, {"epoch": 2})) == (False, "STALE_SNAPSHOT")
        assert _ask(ws_parent, ("restore", {"epoch": 2}, None)) == (False, "RESTORE_WITHOUT_CURRENT_ANCHOR")
        assert _ask(ws_parent, ("restore", {"epoch": 2}, {"epoch": 2})) == (True, None)
        # A real mutation passes a retained A key/blob through the public test protocol.
        _ask(kp_parent, "stop"); kp.join(2); kp = ctx.Process(target=_keyholder, args=(kp_child, str(vault))); kp.start()
        _ask(ws_parent, ("shared", _ask(kp_parent, "shared"))); _ask(kp_parent, "delete")
        assert _ask(ws_parent, ("gate",)) == (False, "SHARED_BLOB")
        old_session = _ask(ws_parent, ("state",))["run"]
        assert _ask(ws_parent, ("serve", old_session)) == (True, None)
        _ask(ws_parent, ("stop",)); ws.join(2); ws_parent.close()
        ws_parent, ws_child = ctx.Pipe(); ws = ctx.Process(target=_workstore, args=(ws_child,)); ws.start()
        _ask(ws_parent, ("init", b"ciphertext-only")); new_session = _ask(ws_parent, ("state",))["run"]
        assert new_session != old_session and _ask(ws_parent, ("serve", old_session)) == (False, "CACHE_FD_SESSION")
        assert _ask(ws_parent, ("serve", new_session)) == (True, None) and _ask(ws_parent, ("state",))["cache"] == ""
        # Expected fatal: parent under the same UID can read the synthetic vault directly.
        _ask(kp_parent, "stop"); kp.join(2); kp = ctx.Process(target=_keyholder, args=(kp_child, str(vault))); kp.start()
        again = _ask(kp_parent, "public")
        assert again["run"] != public["run"] and again["pid"] != public["pid"]
        assert vault.read_bytes()
        assert _p2_gate(vault) == (False, "P2_SHARED_ROOT_SAME_UID")
    finally:
        for conn, proc in ((kp_parent, kp), (ws_parent, ws)):
            if proc.is_alive():
                try: _ask(conn, "stop" if conn is kp_parent else ("stop",))
                except (EOFError, BrokenPipeError, AssertionError): pass
                proc.join(2)
            if proc.is_alive(): proc.terminate(); proc.join(2)
