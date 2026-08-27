import pytest

from kern.anchor_registry import Anchor, AnchorRegistry
from kern.rationale_index_lifecycle import Binding, Entry, RationaleIndex


def _registry(revision="a" * 40):
    return AnchorRegistry.empty(revision).register(
        Anchor.create("src:rule", revision, "symbol:rule", ())
    )


def test_lifecycle_classifies_binding_and_keeps_old_entries_visible():
    revision = "a" * 40
    index = RationaleIndex.empty(revision, _registry(revision))
    binding = Binding("src:rule", revision, "symbol:rule", Anchor.create(
        "src:rule", revision, "symbol:rule", ()
    ).digest)
    entry = Entry("e1", binding, "rat:1", "resp:1", ("pre:1",))
    ready = index.with_prerequisite("pre:1").add(entry)
    assert ready.resolve("e1").entry == entry
    stale = ready.mark_stale("e1")
    assert stale.resolve("e1").gaps == ("stale_entry",)
    tombstone = stale.tombstone("e1")
    assert tombstone.resolve("e1").gaps == ("tombstone_entry",)
    assert tombstone.resolve("e1").entry.status == "tombstone"


@pytest.mark.parametrize("binding, gap", [
    (Binding("missing", "a" * 40, "symbol:rule", "0" * 64), "unknown_anchor"),
    (Binding("src:rule", "b" * 40, "symbol:rule", "0" * 64), "revision_mismatch"),
    (Binding("src:rule", "a" * 40, "other", "0" * 64), "symbol_mismatch"),
    (Binding("src:rule", "a" * 40, "symbol:rule", "0" * 64), "code_hash_mismatch"),
])
def test_binding_gaps_are_distinct(binding, gap):
    index = RationaleIndex.empty("a" * 40, _registry())
    result = index.add(Entry("e", binding, "rat", "resp")).resolve("e")
    assert result.gaps == (gap,)


def test_missing_prerequisite_and_conflicting_binding_are_explicit():
    revision = "a" * 40
    binding = Binding("src:rule", revision, "symbol:rule", "0" * 64)
    index = RationaleIndex.empty(revision, _registry(revision))
    entry = Entry("e", binding, "rat", "resp", ("pre:missing",))
    assert index.add(entry).resolve("e").gaps == ("missing_prerequisite",)
    other = Entry("e", Binding("src:rule", revision, "symbol:rule", "1" * 64), "rat", "resp")
    with pytest.raises(ValueError, match="conflicting binding"):
        index.add(entry).add(other)
