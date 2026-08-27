"""Small immutable, append-only lineage DAG (P101)."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json


class LineageConflict(ValueError):
    """A stable node ID was already bound to different local content."""


@dataclass(frozen=True)
class LineageNode:
    node_id: str
    revision: str
    local_binding: object
    parents: tuple[str, ...] = ()
    binding_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.node_id or not self.revision:
            raise ValueError("node_id and revision must not be empty")
        object.__setattr__(self, "parents", tuple(self.parents))
        encoded = json.dumps(
            {"local_binding": self.local_binding, "revision": self.revision},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        object.__setattr__(self, "binding_digest", hashlib.sha256(encoded).hexdigest())


@dataclass(frozen=True)
class LineageDAG:
    _nodes: tuple[LineageNode, ...] = ()
    gaps: tuple[str, ...] = ()

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self._nodes)

    def node(self, node_id: str) -> LineageNode:
        for node in self._nodes:
            if node.node_id == node_id:
                return node
        raise KeyError(node_id)

    def append(self, node: LineageNode) -> "LineageDAG":
        try:
            current = self.node(node.node_id)
        except KeyError:
            current = None
        if current is not None:
            if current.binding_digest != node.binding_digest:
                raise LineageConflict(f"node_id conflict: {node.node_id}")
            return self
        missing = tuple(
            f"missing_parent:{node.node_id}:{parent}"
            for parent in node.parents
            if parent not in self.ids
        )
        return LineageDAG(self._nodes + (node,), self.gaps + missing)

    def join(self, *others: "LineageDAG") -> "LineageDAG":
        result = self
        for other in others:
            for node in other._nodes:
                result = result.append(node)
            result = LineageDAG(result._nodes, result.gaps + tuple(
                gap for gap in other.gaps if gap not in result.gaps
            ))
        return result
