"""Fail-closed policy for AI-authored comments (P99/P104)."""

from collections.abc import Mapping


class PolicyViolation(ValueError):
    """Untrusted AI output did not match the narrow comment contract."""


_LINK_KEYS = frozenset(("kind", "anchor_id", "revision"))
_MACHINE_DIRECTIVES = frozenset(("shebang", "encoding", "license", "linter",
                                 "type_pragma", "framework", "docgen", "generated"))
_FORBIDDEN = frozenset(("comment", "text", "content", "prompt", "transcript",
                        "secret", "credential", "token", "password", "self_proof",
                        "proof", "verified", "evidence"))


def _reject_fields(value: object) -> None:
    if isinstance(value, Mapping):
        if any(str(key).casefold() in _FORBIDDEN for key in value):
            raise PolicyViolation("forbidden AI field")
        for child in value.values():
            _reject_fields(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _reject_fields(child)


def validate_ai_result(result: object, registry: object, *, budget: int = 3) -> dict[str, str]:
    """Return only a safe normalized result; never echo untrusted content."""
    _reject_fields(result)
    if result == "NONE" or result == {"kind": "NONE"}:
        return {"kind": "NONE"}
    if not isinstance(result, Mapping) or set(result) != _LINK_KEYS:
        raise PolicyViolation("AI result must be NONE or a registered link")
    if result.get("kind") != "brainlehr:link":
        raise PolicyViolation("unsupported AI result")
    anchor_id, revision = result.get("anchor_id"), result.get("revision")
    if not isinstance(anchor_id, str) or not isinstance(revision, str):
        raise PolicyViolation("invalid link")
    resolved = registry.resolve([anchor_id], budget=budget)
    if resolved.gaps or len(resolved.anchors) != 1:
        raise PolicyViolation("unresolved link")
    anchor = resolved.anchors[0]
    if anchor.revision != revision:
        raise PolicyViolation("stale link")
    return {"kind": "brainlehr:link", "anchor_id": anchor_id, "revision": revision}


def validate_machine_directive(directive: object) -> str:
    """Allow only finite, non-content machine/legal markers."""
    if not isinstance(directive, str) or directive not in _MACHINE_DIRECTIVES:
        raise PolicyViolation("unsupported machine directive")
    return directive


def preserve_human_comment(comment: bytes) -> bytes:
    """Keep human-authored bytes opaque and byte-identical."""
    if not isinstance(comment, bytes):
        raise TypeError("human comment must be bytes")
    return comment
