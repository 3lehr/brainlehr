from dataclasses import FrozenInstanceError

import pytest

from kern.anchor_registry import Anchor, AnchorRegistry


def test_anchor_binding_is_deterministic_and_immutable():
    a = Anchor.create("src:main", "a" * 40, "P100", ("src", "main"))
    assert a.digest == Anchor.binding_digest(a.anchor_id, a.revision, a.contract, a.edges)
    with pytest.raises(FrozenInstanceError):
        a.anchor_id = "other"


def test_registry_is_copy_on_write_and_resolves_selected_only():
    base = AnchorRegistry.empty("a" * 40)
    first = Anchor.create("src:one", "a" * 40, "P100", ())
    second = Anchor.create("src:two", "a" * 40, "P100", ("two", "missing"))
    newer = base.register(first).register(second)
    assert base.resolve(["src:one"]).anchors == ()
    result = newer.resolve(["src:one"])
    assert [a.anchor_id for a in result.anchors] == ["src:one"]
    assert result.gaps == ()
    assert newer.resolve(["src:two"]).gaps == ("unknown_edge",)


def test_registry_surfaces_unknown_stale_and_budget_gaps():
    registry = AnchorRegistry.empty("a" * 40)
    registry = registry.register(Anchor.create("a", "a" * 40, "P100", ()))
    registry = registry.register(Anchor.create("b", "a" * 40, "P100", ()))
    registry = registry.register(Anchor.create("c", "b" * 40, "P100", ()))
    result = registry.resolve(["missing", "b", "c", "a"], budget=2)
    assert result.gaps == ("unknown_registry_id", "budget_exhausted")
    assert [a.anchor_id for a in result.anchors] == ["b"]
    assert registry.resolve(["c"], budget=3).gaps == ("stale_anchor",)


def test_validation_rejects_unbounded_or_invalid_bindings():
    with pytest.raises(ValueError):
        Anchor.create("bad id", "a" * 40, "P100", ())
    with pytest.raises(ValueError):
        Anchor.create("a", "not-a-revision", "P100", ())
    with pytest.raises(ValueError):
        AnchorRegistry.empty("a" * 40).resolve(["a"], budget=4)
    with pytest.raises(ValueError):
        Anchor("a", "a" * 40, "P100", (), "0" * 64).validate()
