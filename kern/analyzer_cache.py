"""Signed, revision-bound analyzer-cache envelope; no raw tool output."""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any


def _bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def create(*, revision: str, tool_sha256: str, config_sha256: str,
           input_sha256: str, output_sha256: str, tool_version: str,
           actor: str, private_key: Any) -> dict[str, Any]:
    body = {"schema": 1, "revision": revision, "tool_sha256": tool_sha256,
            "config_sha256": config_sha256, "input_sha256": input_sha256,
            "output_sha256": output_sha256, "tool_version": tool_version, "actor": actor}
    signature = base64.b64encode(private_key.sign(_bytes(body))).decode()
    return {**body, "signature": signature,
            "content_hash": hashlib.sha256(_bytes({**body, "signature": signature})).hexdigest()}


def verify(envelope: dict[str, Any], *, revision: str, tool_version: str, public_key: Any) -> bool:
    required = {"schema", "revision", "tool_sha256", "config_sha256", "input_sha256", "output_sha256",
                "tool_version", "actor", "signature", "content_hash"}
    if not required <= set(envelope) or envelope.get("revision") != revision or envelope.get("tool_version") != tool_version:
        return False
    body = {key: envelope[key] for key in required - {"signature", "content_hash"}}
    signed = {**body, "signature": envelope["signature"]}
    if hashlib.sha256(_bytes(signed)).hexdigest() != envelope["content_hash"]:
        return False
    try:
        public_key.verify(base64.b64decode(envelope["signature"], validate=True), _bytes(body))
    except Exception:
        return False
    return True
