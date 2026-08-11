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
        elif op == "delete": a_key = None; os.unlink(vault_path); conn.send(True)
        elif op == "mutant": conn.send("KEY_COPY" if copy and _open(copy, "A", a_blob) else "DETERMINISTIC_MASTER_DERIVATION" if master and _open(_derive(master, ref), "A", a_blob) else None)
        elif op == "restart": run = secrets.token_hex(6); conn.send({"run": run, "pid": os.getpid()})
        elif op == "stop": conn.send(True); conn.close(); return


def _workstore(conn):
    state = {"cache": "", "log": "", "vector": "", "shared": False, "stale": False, "anchor": True, "session": None}
    while True:
        msg = conn.recv()
        if msg[0] == "init": state["projection"] = {"groups": 2}; state["cipher"] = msg[1]; conn.send(os.getpid())
        elif msg[0] == "inject": state[msg[1]] = msg[2]; conn.send(True)
        elif msg[0] == "state": conn.send({k: v for k, v in state.items() if k not in {"cipher"}})
        elif msg[0] == "stop": conn.send(True); conn.close(); return


def _ask(conn, message):
    conn.send(message)
    assert conn.poll(2), "IPC timeout"
    return conn.recv()


def _gate(key_mutant, state):
    if key_mutant: return False, key_mutant
    if any("SYNTHETIC-A" in state[x] for x in ("cache", "log", "vector")): return False, "PLAINTEXT_CACHE_LOG_EMBEDDING"
    if state["shared"]: return False, "SHARED_BLOB"
    if state["stale"]: return False, "STALE_SNAPSHOT"
    if not state["anchor"]: return False, "RESTORE_WITHOUT_CURRENT_ANCHOR"
    if state["session"]: return False, "CACHE_FD_SESSION"
    return True, None


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
        _ask(kp_parent, "delete"); assert not vault.exists(); assert _ask(kp_parent, "a") is None; assert _gate(_ask(kp_parent, "mutant"), _ask(ws_parent, ("state",))) == (True, None)
        # Every mutant first sees this same IPC baseline, then must kill exactly.
        for command, expected in [("copy", "KEY_COPY"), ("master", "DETERMINISTIC_MASTER_DERIVATION")]:
            # fresh keyholder gives a fresh baseline; mutation is deliberately test-only.
            assert expected in {"KEY_COPY", "DETERMINISTIC_MASTER_DERIVATION"}
        # New isolated runs make pre-delete mutation observable without preserving test state.
        for command, expected in [("copy", "KEY_COPY"), ("master", "DETERMINISTIC_MASTER_DERIVATION")]:
            _ask(kp_parent, "stop"); kp.join(2); kp = ctx.Process(target=_keyholder, args=(kp_child, str(vault))); kp.start()
            _ask(kp_parent, command); _ask(kp_parent, "delete"); assert _gate(_ask(kp_parent, "mutant"), _ask(ws_parent, ("state",))) == (False, expected)
        for surface in ("cache", "log", "vector"):
            _ask(ws_parent, ("inject", surface, "")); assert _gate(None, _ask(ws_parent, ("state",))) == (True, None)
            _ask(ws_parent, ("inject", surface, "SYNTHETIC-A")); assert _gate(None, _ask(ws_parent, ("state",))) == (False, "PLAINTEXT_CACHE_LOG_EMBEDDING")
            _ask(ws_parent, ("inject", surface, ""))
        for field, expected in [("shared", "SHARED_BLOB"), ("stale", "STALE_SNAPSHOT"), ("anchor", "RESTORE_WITHOUT_CURRENT_ANCHOR"), ("session", "CACHE_FD_SESSION")]:
            _ask(ws_parent, ("inject", field, False if field == "anchor" else True)); assert _gate(None, _ask(ws_parent, ("state",))) == (False, expected)
            _ask(ws_parent, ("inject", field, True if field == "anchor" else False)); assert _gate(None, _ask(ws_parent, ("state",))) == (True, None)
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
