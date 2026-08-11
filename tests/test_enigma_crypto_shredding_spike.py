"""Synthetic crypto-shredding falsification spike; no production storage involved."""
from __future__ import annotations

import json
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _seal(key: bytes, subject: str, fragment: str) -> bytes:
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, fragment.encode(), subject.encode())


def _open(key: bytes, subject: str, blob: bytes) -> str:
    return AESGCM(key).decrypt(blob[:12], blob[12:], subject.encode()).decode()


def _deletion_gate(key_ref, vault, copies, subject, blob):
    if key_ref in vault:
        return False, "KEY_NOT_DESTROYED"
    for copied_key in copies:
        try:
            _open(copied_key, subject, blob)
        except InvalidTag:
            continue
        return False, "KEY_COPY"
    return True, None


def _fixture():
    scope = ("identity", "care", "care-team", "epoch-1")
    a_ref, b_ref = ("A",) + scope, ("B",) + scope
    vault = {a_ref: secrets.token_bytes(32), b_ref: secrets.token_bytes(32)}
    assert len(vault[a_ref]) == len(vault[b_ref]) == 32 and vault[a_ref] != vault[b_ref]
    a_canary, b_canary = "SYNTHETIC-A-CANARY", "SYNTHETIC-B-CANARY"
    return {
        "a_ref": a_ref, "b_ref": b_ref, "vault": vault,
        "a_blob": _seal(vault[a_ref], "A", a_canary),
        "b_blob": _seal(vault[b_ref], "B", b_canary),
        "a_canary": a_canary, "b_canary": b_canary,
        "consumers": {"cache": b"", "log": "", "fts": "", "vector": "", "export": b""},
        "kernel": json.dumps({"group_count": 2, "purpose": "synthetic"}),
        "snapshot": {"epoch": 1}, "external_tombstone": 2,
    }


def test_crypto_shredding_baseline():
    case = _fixture()
    assert _open(case["vault"][case["a_ref"]], "A", case["a_blob"]) == case["a_canary"]
    del case["vault"][case["a_ref"]]
    assert case["a_ref"] not in case["vault"]
    assert all(case["a_canary"].encode() not in value.encode() if isinstance(value, str)
               else case["a_canary"].encode() not in value
               for value in (case["a_blob"], *case["consumers"].values()))
    assert _open(case["vault"][case["b_ref"]], "B", case["b_blob"]) == case["b_canary"]
    assert json.loads(case["kernel"])["group_count"] == 2
    assert not case["snapshot"]["epoch"] >= case["external_tombstone"]
    assert _deletion_gate(case["a_ref"], case["vault"], [], "A", case["a_blob"]) == (True, None)


def test_key_copy_mutation_is_rejected():
    case = _fixture()
    copied_a_key = case["vault"][case["a_ref"]]
    del case["vault"][case["a_ref"]]
    ok, reason = _deletion_gate(case["a_ref"], case["vault"], [copied_a_key], "A", case["a_blob"])
    assert ok is False
    assert reason == "KEY_COPY"
