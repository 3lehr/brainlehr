import pytest

from kern.lineage_dag import LineageConflict, LineageDAG, LineageNode


def test_node_digest_is_canonical_and_node_is_frozen():
    left = LineageNode("a", "r1", "source text", parents=("root",))
    right = LineageNode("a", "r1", "source text", parents=("root",))
    assert left.binding_digest == right.binding_digest
    with pytest.raises((AttributeError, TypeError)):
        left.node_id = "changed"


def test_append_is_copy_on_write_and_join_preserves_branches():
    root = LineageNode("root", "r1", "r")
    left = LineageNode("left", "r1", "l", parents=("root",))
    right = LineageNode("right", "r1", "q", parents=("root",))
    base = LineageDAG().append(root)
    left_dag = base.append(left)
    joined = left_dag.join(LineageDAG().append(root).append(right))
    assert tuple(base.ids) == ("root",)
    assert set(joined.ids) == {"root", "left", "right"}
    assert joined.node("left") == left
    assert joined.node("right") == right


def test_same_id_different_digest_is_explicit_conflict_without_overwrite():
    dag = LineageDAG().append(LineageNode("a", "r1", "one"))
    with pytest.raises(LineageConflict):
        dag.append(LineageNode("a", "r1", "two"))
    assert dag.node("a").local_binding == "one"


def test_missing_parent_is_visible_gap_and_never_invented():
    dag = LineageDAG().append(LineageNode("child", "r1", "c", parents=("missing",)))
    assert dag.node("child").parents == ("missing",)
    assert dag.gaps == ("missing_parent:child:missing",)
    assert "missing" not in dag.ids
