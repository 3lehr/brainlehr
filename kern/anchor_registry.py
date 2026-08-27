"""Small, immutable registry for validated, lazy lineage anchors."""

from dataclasses import dataclass
import hashlib
import json
import re
from types import MappingProxyType
from typing import Mapping, Sequence


_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_REVISION = re.compile(r"^[0-9a-f]{7,64}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_BUDGET = 3


def _safe(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SAFE.fullmatch(value):
        raise ValueError(f"invalid {name}")
    return value


def _revision(value: str) -> str:
    if not isinstance(value, str) or not _REVISION.fullmatch(value):
        raise ValueError("invalid revision")
    return value


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Anchor:
    anchor_id: str
    revision: str
    contract: str
    edges: tuple[str, ...]
    digest: str

    @staticmethod
    def binding_digest(anchor_id: str, revision: str, contract: str,
                       edges: Sequence[str] = ()) -> str:
        payload = json.dumps(
            {"anchor_id": anchor_id, "contract": contract,
             "edges": list(edges), "revision": revision},
            ensure_ascii=False, separators=(",", ":"), sort_keys=True,
        )
        return _digest(payload)

    @classmethod
    def create(cls, anchor_id: str, revision: str, contract: str,
               edges: Sequence[str] = ()) -> "Anchor":
        _safe(anchor_id, "anchor id")
        _revision(revision)
        if not isinstance(contract, str) or not contract or len(contract) > 256:
            raise ValueError("invalid contract")
        normalized = tuple(_safe(edge, "edge id") for edge in edges)
        return cls(anchor_id, revision, contract, normalized,
                   cls.binding_digest(anchor_id, revision, contract, normalized))

    def validate(self) -> None:
        expected = self.binding_digest(self.anchor_id, self.revision,
                                       self.contract, self.edges)
        _safe(self.anchor_id, "anchor id")
        _revision(self.revision)
        if not isinstance(self.contract, str) or not self.contract or len(self.contract) > 256:
            raise ValueError("invalid contract")
        if not _HEX64.fullmatch(self.digest) or self.digest != expected:
            raise ValueError("invalid binding digest")


@dataclass(frozen=True, slots=True)
class ResolveResult:
    anchors: tuple[Anchor, ...]
    gaps: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AnchorRegistry:
    revision: str
    _anchors: Mapping[str, Anchor]

    @classmethod
    def empty(cls, revision: str) -> "AnchorRegistry":
        _revision(revision)
        return cls(revision, MappingProxyType({}))

    def register(self, anchor: Anchor) -> "AnchorRegistry":
        anchor.validate()
        updated = dict(self._anchors)
        updated[anchor.anchor_id] = anchor
        return AnchorRegistry(self.revision, MappingProxyType(updated))

    def resolve(self, selected: Sequence[str], budget: int = _MAX_BUDGET) -> ResolveResult:
        if not isinstance(budget, int) or not 0 < budget <= _MAX_BUDGET:
            raise ValueError("budget must be between 1 and 3")
        found: list[Anchor] = []
        gaps: list[str] = []
        for index, anchor_id in enumerate(selected):
            if index >= budget:
                if "budget_exhausted" not in gaps:
                    gaps.append("budget_exhausted")
                break
            if anchor_id not in self._anchors:
                gaps.append("unknown_registry_id")
                continue
            anchor = self._anchors[anchor_id]
            if anchor.revision != self.revision:
                gaps.append("stale_anchor")
                continue
            found.append(anchor)
            for edge in anchor.edges:
                if edge not in self._anchors and "unknown_edge" not in gaps:
                    gaps.append("unknown_edge")
        return ResolveResult(tuple(found), tuple(gaps))
