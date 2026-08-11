"""Synthetic logical-two-store and C1 grant-boundary tests; no P2 claim."""
from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import re
import secrets
import subprocess
from multiprocessing.connection import wait

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

DENIAL = {"content": None, "metadata": None, "protected_edge_reads": 0}
ALLOWED_FIELDS = ("availability", "area", "window", "status")
RECORD_A = {"availability": "available", "area": "A1", "window": "W1", "status": "active"}
REQUIRED_GRANT_FIELDS = {
    "subject", "fields", "purpose", "recipient", "expiry",
    "audience_policy", "grant_id", "nonce",
}
POLICY = {"subject": "A", "purpose": "care", "recipient": "team", "audience_policy": "internal"}
SERVER_NOW = 1_000


def _seal(key: bytes, subject: str, text: str) -> bytes:
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, text.encode(), subject.encode())


def _open(key: bytes, subject: str, blob: bytes) -> str:
    return AESGCM(key).decrypt(blob[:12], blob[12:], subject.encode()).decode()


def _derive(master: bytes, ref: tuple[str, ...]) -> bytes:
    return hashlib.sha256(master + repr(ref).encode()).digest()


def _valid_grant(grant, issued_grants, consumed_nonces, revoked_grants) -> bool:
    if not isinstance(grant, dict) or set(grant) != REQUIRED_GRANT_FIELDS:
        return False
    registered = issued_grants.get(grant.get("grant_id"))
    if registered != grant or grant["grant_id"] in revoked_grants:
        return False
    if any(grant[name] != value for name, value in POLICY.items()):
        return False
    fields = grant["fields"]
    if not isinstance(fields, list) or not fields or len(fields) != len(set(fields)):
        return False
    if not set(fields).issubset(ALLOWED_FIELDS):
        return False
    if not isinstance(grant["expiry"], int) or grant["expiry"] <= SERVER_NOW:
        return False
    return isinstance(grant["nonce"], str) and bool(grant["nonce"]) and grant["nonce"] not in consumed_nonces


def _keyholder(serving_conn, control_conn, vault_path: str) -> None:
    ref = ("A", "identity", "care", "team", "epoch-1")
    a_key, b_key = secrets.token_bytes(32), secrets.token_bytes(32)
    a_blob = _seal(a_key, "A", json.dumps(RECORD_A, sort_keys=True))
    b_blob = _seal(b_key, "B", "SYNTHETIC-B")
    with open(vault_path, "wb") as vault:
        vault.write(a_key)
    copied_key = master = shared = None
    deleted = False
    run_id = secrets.token_hex(6)
    issued_grants: dict[str, dict] = {}
    consumed_nonces: set[str] = set()
    revoked_grants: set[str] = set()
    audit: list[dict] = []
    protected_edge_reads = 0

    while True:
        for ready in wait((serving_conn, control_conn)):
            request = ready.recv()
            if ready is serving_conn:
                correlation_id = secrets.token_hex(8)
                response = dict(DENIAL)
                grant = request.get("grant") if isinstance(request, dict) and request.get("op") == "read" else None
                if not deleted and a_key is not None and _valid_grant(
                    grant, issued_grants, consumed_nonces, revoked_grants,
                ):
                    consumed_nonces.add(grant["nonce"])
                    protected = json.loads(_open(a_key, "A", a_blob))
                    protected_edge_reads += 1
                    response = {
                        "content": {name: protected[name] for name in grant["fields"]},
                        "metadata": {"correlation_id": correlation_id},
                        "protected_edge_reads": 1,
                    }
                audit.append({
                    "correlation_id": correlation_id,
                    "decision": "allow" if response["protected_edge_reads"] else "deny",
                    "protected_edge_reads": response["protected_edge_reads"],
                })
                serving_conn.send(response)
                continue

            op = request.get("op") if isinstance(request, dict) else None
            if op == "public":
                control_conn.send({"pid": os.getpid(), "a_blob": a_blob, "b_blob": b_blob, "run_id": run_id})
            elif op == "read_fixture":
                if request.get("subject") == "A":
                    control_conn.send(json.loads(_open(a_key, "A", a_blob)) if a_key else None)
                elif request.get("subject") == "B":
                    control_conn.send(_open(b_key, "B", b_blob))
                else:
                    control_conn.send(None)
            elif op == "issue_grant":
                grant = request["grant"]
                issued_grants[grant["grant_id"]] = dict(grant)
                control_conn.send(True)
            elif op == "revoke":
                revoked_grants.add(request["grant_id"])
                control_conn.send(True)
            elif op == "copy":
                copied_key = a_key
                control_conn.send(True)
            elif op == "master":
                master = secrets.token_bytes(32)
                a_key = _derive(master, ref)
                a_blob = _seal(a_key, "A", json.dumps(RECORD_A, sort_keys=True))
                control_conn.send(True)
            elif op == "shared":
                shared = {"key": a_key, "blob": a_blob}
                control_conn.send(shared)
            elif op == "delete":
                a_key = None
                deleted = True
                os.unlink(vault_path)
                control_conn.send(True)
            elif op == "mutant":
                if copied_key and json.loads(_open(copied_key, "A", a_blob)) == RECORD_A:
                    control_conn.send("KEY_COPY")
                elif master and json.loads(_open(_derive(master, ref), "A", a_blob)) == RECORD_A:
                    control_conn.send("DETERMINISTIC_MASTER_DERIVATION")
                else:
                    control_conn.send(None)
            elif op == "metrics":
                control_conn.send({"protected_edge_reads": protected_edge_reads, "audit": list(audit)})
            elif op == "introspect":
                control_conn.send({
                    "pid": os.getpid(), "run_id": run_id, "deleted": deleted,
                    "copied": copied_key is not None, "master": master is not None,
                    "shared": shared is not None, "issued_count": len(issued_grants),
                    "revoked_grants": sorted(revoked_grants),
                })
            elif op == "stop":
                control_conn.send(True)
                serving_conn.close()
                control_conn.close()
                return
            else:
                control_conn.send(False)


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
            elif state["shared"] and json.loads(
                _open(state["shared"]["key"], "A", state["shared"]["blob"]),
            ) == RECORD_A:
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


def _start_keyholder(ctx, vault_path):
    serving_parent, serving_child = ctx.Pipe()
    control_parent, control_child = ctx.Pipe()
    process = ctx.Process(target=_keyholder, args=(serving_child, control_child, str(vault_path)))
    process.start()
    serving_child.close()
    control_child.close()
    return serving_parent, control_parent, process


def _ask(conn, message):
    conn.send(message)
    assert conn.poll(2), "IPC timeout"
    return conn.recv()


def _assert_closed(conn, message) -> None:
    closed = False
    try:
        conn.send(message)
        if conn.poll(0.5):
            conn.recv()
    except (EOFError, BrokenPipeError, OSError):
        closed = True
    finally:
        conn.close()
    assert closed, "old parent IPC handle remained usable"


def _stop_process(conn, process, stop_message):
    if process.is_alive():
        assert _ask(conn, stop_message) is True
        process.join(2)
    if process.is_alive():
        process.terminate()
        process.join(2)
        raise AssertionError("process did not stop cleanly")
    _assert_closed(conn, stop_message)


def _stop_keyholder(serving_conn, control_conn, process):
    if process.is_alive():
        assert _ask(control_conn, {"op": "stop"}) is True
        process.join(2)
    if process.is_alive():
        process.terminate()
        process.join(2)
        raise AssertionError("keyholder did not stop cleanly")
    _assert_closed(serving_conn, {"op": "read"})
    _assert_closed(control_conn, {"op": "stop"})


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


def _safe_stop_keyholder(serving_conn, control_conn, process):
    if serving_conn is None or control_conn is None or process is None:
        return
    try:
        _stop_keyholder(serving_conn, control_conn, process)
    except (AssertionError, EOFError, BrokenPipeError, OSError):
        if process.is_alive():
            process.terminate()
            process.join(2)
        serving_conn.close()
        control_conn.close()


def _grant(token: str, fields=("availability",)) -> dict:
    return {
        "subject": "A", "fields": list(fields), "purpose": "care", "recipient": "team",
        "expiry": 2_000, "audience_policy": "internal",
        "grant_id": f"grant-{token}", "nonce": f"nonce-{token}",
    }


def _issue(control_conn, grant: dict) -> None:
    assert _ask(control_conn, {"op": "issue_grant", "grant": grant}) is True


def _serving_call(serving_conn, control_conn, request):
    before = _ask(control_conn, {"op": "metrics"})
    response = _ask(serving_conn, request)
    after = _ask(control_conn, {"op": "metrics"})
    assert len(after["audit"]) == len(before["audit"]) + 1
    evidence = after["audit"][-1]
    assert evidence["correlation_id"]
    assert evidence["correlation_id"] not in {item["correlation_id"] for item in before["audit"]}
    return response, before, after, evidence


def _assert_denied(serving_conn, control_conn, request) -> None:
    response, before, after, evidence = _serving_call(serving_conn, control_conn, request)
    assert response == DENIAL
    assert after["protected_edge_reads"] == before["protected_edge_reads"]
    assert evidence["decision"] == "deny" and evidence["protected_edge_reads"] == 0


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


def test_c1_positive_projection_matrix(tmp_path):
    ctx = mp.get_context("spawn")
    serving = control = process = None
    try:
        serving, control, process = _start_keyholder(ctx, tmp_path / "synthetic-vault")
        for index, fields in enumerate((ALLOWED_FIELDS[:1], ALLOWED_FIELDS[:2], ALLOWED_FIELDS), 1):
            grant = _grant(f"positive-{index}", fields)
            _issue(control, grant)
            response, before, after, evidence = _serving_call(serving, control, {"op": "read", "grant": grant})
            assert response["content"] == {name: RECORD_A[name] for name in fields}
            assert set(response["content"]) == set(fields)
            assert response["metadata"] == {"correlation_id": evidence["correlation_id"]}
            assert response["protected_edge_reads"] == 1
            assert after["protected_edge_reads"] == before["protected_edge_reads"] + 1
            assert evidence["decision"] == "allow" and evidence["protected_edge_reads"] == 1
    finally:
        _safe_stop_keyholder(serving, control, process)


def test_c1_one_factor_denial_replay_revocation_and_deleted(tmp_path):
    ctx = mp.get_context("spawn")
    serving = control = process = None
    try:
        serving, control, process = _start_keyholder(ctx, tmp_path / "synthetic-vault")
        _assert_denied(serving, control, {"op": "read"})

        mutations = (
            ("missing-subject", "subject", None), ("wrong-subject", "subject", "B"),
            ("missing-fields", "fields", None), ("wrong-field", "fields", ["secret"]),
            ("extra-field", "fields", ["availability", "secret"]),
            ("missing-purpose", "purpose", None), ("wrong-purpose", "purpose", "wrong"),
            ("missing-recipient", "recipient", None), ("wrong-recipient", "recipient", "wrong"),
            ("missing-expiry", "expiry", None), ("expired", "expiry", SERVER_NOW),
            ("missing-audience", "audience_policy", None), ("wrong-audience", "audience_policy", "public"),
            ("missing-grant-id", "grant_id", None), ("wrong-grant-id", "grant_id", "unknown"),
            ("missing-nonce", "nonce", None),
        )
        for token, field, replacement in mutations:
            registered = _grant(token)
            _issue(control, registered)
            request_grant = dict(registered)
            if replacement is None:
                request_grant.pop(field)
            else:
                request_grant[field] = replacement
            _assert_denied(serving, control, {"op": "read", "grant": request_grant})

        replay = _grant("replay")
        _issue(control, replay)
        first, _, _, _ = _serving_call(serving, control, {"op": "read", "grant": replay})
        assert first["protected_edge_reads"] == 1
        _assert_denied(serving, control, {"op": "read", "grant": replay})

        revoked = _grant("revoked")
        _issue(control, revoked)
        assert _ask(control, {"op": "revoke", "grant_id": revoked["grant_id"]}) is True
        _assert_denied(serving, control, {"op": "read", "grant": revoked})
        _assert_denied(serving, control, {"op": "read", "grant": revoked})

        fresh = _grant("fresh")
        _issue(control, fresh)
        success, _, _, _ = _serving_call(serving, control, {"op": "read", "grant": fresh})
        assert success["content"] == {"availability": RECORD_A["availability"]}

        deleted = _grant("deleted")
        _issue(control, deleted)
        assert _ask(control, {"op": "delete"}) is True
        _assert_denied(serving, control, {"op": "read", "grant": deleted})
    finally:
        _safe_stop_keyholder(serving, control, process)


def test_c1_serving_control_separation_and_audit(tmp_path):
    ctx = mp.get_context("spawn")
    serving = control = process = None
    try:
        serving, control, process = _start_keyholder(ctx, tmp_path / "synthetic-vault")
        initial = _ask(control, {"op": "introspect"})
        for raw in ("a", "b"):
            _assert_denied(serving, control, raw)
        for op in ("copy", "master", "delete", "shared", "mutant", "stop", "revoke", "issue_grant", "metrics", "introspect", "read_fixture", "public"):
            _assert_denied(serving, control, {"op": op, "actor": "operator", "purpose": "care"})
        assert _ask(control, {"op": "introspect"}) == initial

        grant = _grant("separation")
        _issue(control, grant)
        success, _, _, evidence = _serving_call(serving, control, {"op": "read", "grant": grant})
        assert success["metadata"]["correlation_id"] == evidence["correlation_id"]
        metrics = _ask(control, {"op": "metrics"})
        serialized = json.dumps(metrics, sort_keys=True)
        assert "SYNTHETIC-A" not in serialized
        assert not re.search(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", serialized.lower())
    finally:
        _safe_stop_keyholder(serving, control, process)


def test_baseline_and_crypto_mutants_use_fresh_keyholders(tmp_path):
    ctx = mp.get_context("spawn")
    vault = tmp_path / "synthetic-vault"
    ws_conn = ws_process = serving = control = kh_process = None
    try:
        ws_conn, ws_process = _start_process(ctx, _workstore)
        serving, control, kh_process = _start_keyholder(ctx, vault)
        public = _ask(control, {"op": "public"})
        work = _ask(ws_conn, ("init", public["a_blob"]))
        assert len({os.getpid(), public["pid"], work["pid"]}) == 3
        _assert_clean_introspection(_ask(ws_conn, ("introspect",)))
        assert _ask(control, {"op": "read_fixture", "subject": "A"}) == RECORD_A
        assert _ask(control, {"op": "read_fixture", "subject": "B"}) == "SYNTHETIC-B"
        _ask(control, {"op": "delete"})
        assert _ask(control, {"op": "read_fixture", "subject": "A"}) is None
        assert _ask(control, {"op": "read_fixture", "subject": "B"}) == "SYNTHETIC-B"
        assert _lsof_matches(vault) == []
        assert _ask(ws_conn, ("gate",)) == (True, None)
        previous_identity = (public["pid"], public["run_id"])
        _stop_keyholder(serving, control, kh_process)
        serving = control = kh_process = None

        for mutation, expected in (("copy", "KEY_COPY"), ("master", "DETERMINISTIC_MASTER_DERIVATION")):
            serving, control, kh_process = _start_keyholder(ctx, vault)
            current = _ask(control, {"op": "public"})
            assert (current["pid"], current["run_id"]) != previous_identity
            previous_identity = (current["pid"], current["run_id"])
            assert _ask(control, {"op": "read_fixture", "subject": "A"}) == RECORD_A
            assert _ask(control, {"op": mutation}) is True
            assert _ask(control, {"op": "delete"}) is True
            assert _ask(control, {"op": "read_fixture", "subject": "A"}) is None
            assert _ask(control, {"op": "read_fixture", "subject": "B"}) == "SYNTHETIC-B"
            _ask(ws_conn, ("inject", "key_mutant", _ask(control, {"op": "mutant"})))
            assert _ask(ws_conn, ("gate",)) == (False, expected)
            _ask(ws_conn, ("inject", "key_mutant", None))
            assert _ask(ws_conn, ("gate",)) == (True, None)
            _stop_keyholder(serving, control, kh_process)
            serving = control = kh_process = None

        serving, control, kh_process = _start_keyholder(ctx, vault)
        current = _ask(control, {"op": "public"})
        assert (current["pid"], current["run_id"]) != previous_identity
        assert _ask(ws_conn, ("gate",)) == (True, None)
        shared = _ask(control, {"op": "shared"})
        _ask(control, {"op": "delete"})
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
        _safe_stop_keyholder(serving, control, kh_process)
        _safe_stop(ws_conn, ws_process, ("stop",))


def test_fd_and_same_uid_mutants_are_separate_from_baseline(tmp_path):
    ctx = mp.get_context("spawn")
    vault = tmp_path / "synthetic-vault"
    ws_conn = ws_process = serving = control = kh_process = None
    old_fd = None
    try:
        ws_conn, ws_process = _start_process(ctx, _workstore)
        _ask(ws_conn, ("init", b"ciphertext-only"))
        assert _ask(ws_conn, ("gate",)) == (True, None)

        serving, control, kh_process = _start_keyholder(ctx, vault)
        fd_run = _ask(control, {"op": "public"})
        old_fd = os.open(vault, os.O_RDONLY)
        _ask(control, {"op": "delete"})
        assert len(os.read(old_fd, 32)) == 32
        assert _lsof_matches(vault), "lsof did not observe the live unlinked vault FD"
        _ask(ws_conn, ("inject", "old_handles", [f"lsof:fd:{old_fd}"]))
        assert _ask(ws_conn, ("gate",)) == (False, "CACHE_FD_SESSION")
        os.close(old_fd)
        old_fd = None
        assert _lsof_matches(vault) == []
        _ask(ws_conn, ("inject", "old_handles", []))
        assert _ask(ws_conn, ("gate",)) == (True, None)
        _stop_keyholder(serving, control, kh_process)
        serving = control = kh_process = None

        serving, control, kh_process = _start_keyholder(ctx, vault)
        direct_run = _ask(control, {"op": "public"})
        assert (direct_run["pid"], direct_run["run_id"]) != (fd_run["pid"], fd_run["run_id"])
        assert len(vault.read_bytes()) == 32
        assert _p2_gate(vault) == (False, "P2_SHARED_ROOT_SAME_UID")
    finally:
        if old_fd is not None:
            os.close(old_fd)
        _safe_stop_keyholder(serving, control, kh_process)
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
