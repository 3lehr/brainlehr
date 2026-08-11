"""Synthetic crypto-shredding falsification spike; no production storage involved."""
from __future__ import annotations

import hashlib
import json
import secrets

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _seal(key: bytes, subject: str, fragment: str) -> bytes:
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, fragment.encode(), subject.encode())


def _open(key: bytes, subject: str, blob: bytes) -> str:
    return AESGCM(key).decrypt(blob[:12], blob[12:], subject.encode()).decode()


def _derive(master: bytes, key_ref: tuple[str, ...]) -> bytes:
    return hashlib.sha256(master + repr(key_ref).encode()).digest()


def _deletion_gate(case) -> tuple[bool, str | None]:
    if case["a_ref"] in case["vault"]:
        return False, "KEY_NOT_DESTROYED"
    for key, blob in [(key, case["a_blob"]) for key in case["copies"]] + case["shared_holds"]:
        try:
            _open(key, "A", blob)
        except InvalidTag:
            continue
        return False, "KEY_COPY" if blob is case["a_blob"] and key in case["copies"] else "SHARED_BLOB"
    if case["master"] is not None and _open(_derive(case["master"], case["a_ref"]), "A", case["a_blob"]) == case["a_canary"]:
        return False, "DETERMINISTIC_MASTER_DERIVATION"
    if any(value in str(case["consumers"][surface]) for surface in ("cache", "log", "vector")
           for value in (case["a_canary"], case["a_semantic"])):
        return False, "PLAINTEXT_CACHE_LOG_EMBEDDING"
    return True, None


def _restore_gate(snapshot: dict, anchor: dict | None) -> tuple[bool, str | None]:
    if not anchor or not anchor.get("reachable") or not anchor.get("authentic"):
        return False, "RESTORE_WITHOUT_CURRENT_ANCHOR"
    return True, None


def _fixture():
    scope = ("identity", "care", "care-team", "epoch-1")
    a_ref, b_ref = ("A",) + scope, ("B",) + scope
    vault = {a_ref: secrets.token_bytes(32), b_ref: secrets.token_bytes(32)}
    assert len(vault[a_ref]) == len(vault[b_ref]) == 32 and vault[a_ref] != vault[b_ref]
    a_canary, b_canary = "SYNTHETIC-A-CANARY", "SYNTHETIC-B-CANARY"
    return {
        "a_ref": a_ref, "b_ref": b_ref, "vault": vault, "original_a_key": vault[a_ref],
        "a_blob": _seal(vault[a_ref], "A", a_canary), "b_blob": _seal(vault[b_ref], "B", b_canary),
        "a_canary": a_canary, "a_semantic": "SYNTHETIC-A-SEMANTIC", "b_canary": b_canary,
        "consumers": {"cache": "", "log": "", "fts": "", "vector": "", "export": ""},
        "kernel": json.dumps({"group_count": 2, "purpose": "synthetic"}),
        "snapshot": {"epoch": 1}, "anchor": {"reachable": True, "authentic": True, "epoch": 2},
        "copies": [], "master": None, "shared_holds": [],
    }


def _delete_a(case):
    assert _open(case["vault"][case["a_ref"]], "A", case["a_blob"]) == case["a_canary"]
    del case["vault"][case["a_ref"]]
    assert case["a_ref"] not in case["vault"]


def _assert_mutant_rejected(mutate, expected):
    case = _fixture()
    _delete_a(case)
    assert _deletion_gate(case) == (True, None)
    mutate(case)
    assert _deletion_gate(case) == (False, expected)


def test_crypto_shredding_baseline():
    case = _fixture()
    _delete_a(case)
    assert all(case["a_canary"] not in str(value) for value in (case["a_blob"], *case["consumers"].values()))
    assert _open(case["vault"][case["b_ref"]], "B", case["b_blob"]) == case["b_canary"]
    assert json.loads(case["kernel"])["group_count"] == 2
    assert case["snapshot"]["epoch"] < case["anchor"]["epoch"]
    assert _restore_gate(case["snapshot"], case["anchor"]) == (True, None)
    assert _deletion_gate(case) == (True, None)


def test_key_copy_mutation_is_rejected():
    _assert_mutant_rejected(lambda case: case["copies"].append(case["original_a_key"]), "KEY_COPY")


def test_deterministic_master_derivation_is_rejected():
    def mutate(case):
        case["master"] = secrets.token_bytes(32)
        derived = _derive(case["master"], case["a_ref"])
        case["a_blob"] = _seal(derived, "A", case["a_canary"])
    _assert_mutant_rejected(mutate, "DETERMINISTIC_MASTER_DERIVATION")


@pytest.mark.parametrize("surface", ["cache", "log", "vector"])
def test_plaintext_cache_log_embedding_is_rejected(surface):
    _assert_mutant_rejected(
        lambda case: case["consumers"].__setitem__(surface, case["a_semantic"]),
        "PLAINTEXT_CACHE_LOG_EMBEDDING",
    )


def test_shared_blob_is_rejected():
    _assert_mutant_rejected(
        lambda case: case["shared_holds"].append((case["original_a_key"], case["a_blob"])),
        "SHARED_BLOB",
    )


def test_restore_without_current_anchor_is_rejected():
    case = _fixture()
    _delete_a(case)
    assert _restore_gate(case["snapshot"], case["anchor"]) == (True, None)
    assert _restore_gate(case["snapshot"], None) == (False, "RESTORE_WITHOUT_CURRENT_ANCHOR")
