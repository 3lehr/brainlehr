import pytest

from kern.ai_comment_policy import (
    PolicyViolation,
    preserve_human_comment,
    validate_ai_result,
)
from kern.anchor_registry import Anchor, AnchorRegistry


def registry():
    revision = "a" * 40
    return (AnchorRegistry.empty(revision).register(
        Anchor.create("src:main", revision, "P100", ())), revision)


def test_none_and_registered_link_are_the_only_ai_results():
    anchors, revision = registry()
    assert validate_ai_result("NONE", anchors) == {"kind": "NONE"}
    assert validate_ai_result(
        {"kind": "brainlehr:link", "anchor_id": "src:main", "revision": revision},
        anchors,
    ) == {"kind": "brainlehr:link", "anchor_id": "src:main", "revision": revision}


@pytest.mark.parametrize("payload", [
    "freeform explanation",
    {"kind": "brainlehr:link", "anchor_id": "invented", "revision": "a" * 40},
    {"kind": "brainlehr:link", "anchor_id": "src:main", "revision": "b" * 40},
    {"kind": "NONE", "comment": "secret"},
    {"kind": "brainlehr:link", "anchor_id": "src:main", "revision": "a" * 40,
     "prompt": "leak"},
    {"kind": "brainlehr:link", "anchor_id": "src:main", "revision": "a" * 40,
     "self_proof": True},
])
def test_untrusted_or_freeform_ai_output_is_rejected(payload):
    anchors, _ = registry()
    with pytest.raises(PolicyViolation):
        validate_ai_result(payload, anchors)


def test_human_comment_is_byte_preserved_and_not_reinterpreted():
    value = b"# human: brainlehr:link NONE\n"
    assert preserve_human_comment(value) == value
    with pytest.raises(TypeError):
        preserve_human_comment("not bytes")
