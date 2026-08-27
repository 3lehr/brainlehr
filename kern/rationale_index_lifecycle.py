"""Immutable rationale references with explicit binding and lifecycle gaps."""

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping

from .anchor_registry import AnchorRegistry


@dataclass(frozen=True, slots=True)
class Binding:
    anchor_id: str
    revision: str
    symbol: str
    code_hash: str


@dataclass(frozen=True, slots=True)
class Entry:
    entry_id: str
    binding: Binding
    rationale_ref: str
    responsibility_ref: str
    prerequisites: tuple[str, ...] = ()
    status: str = "current"


@dataclass(frozen=True, slots=True)
class Resolution:
    entry: Entry | None
    gaps: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RationaleIndex:
    revision: str
    registry: AnchorRegistry
    _entries: Mapping[str, Entry]
    _prerequisites: frozenset[str]

    @classmethod
    def empty(cls, revision: str, registry: AnchorRegistry) -> "RationaleIndex":
        if registry.revision != revision:
            raise ValueError("registry revision mismatch")
        return cls(revision, registry, MappingProxyType({}), frozenset())

    def with_prerequisite(self, prerequisite: str) -> "RationaleIndex":
        return replace(self, _prerequisites=self._prerequisites | {prerequisite})

    def add(self, entry: Entry) -> "RationaleIndex":
        if not entry.rationale_ref or not entry.responsibility_ref:
            raise ValueError("rationale and responsibility references required")
        old = self._entries.get(entry.entry_id)
        if old and old.binding != entry.binding:
            raise ValueError("conflicting binding")
        updated = dict(self._entries)
        updated[entry.entry_id] = entry
        return replace(self, _entries=MappingProxyType(updated))

    def mark_stale(self, entry_id: str) -> "RationaleIndex":
        return self._set_status(entry_id, "stale")

    def tombstone(self, entry_id: str) -> "RationaleIndex":
        return self._set_status(entry_id, "tombstone")

    def _set_status(self, entry_id: str, status: str) -> "RationaleIndex":
        entry = self._entries[entry_id]
        updated = dict(self._entries)
        updated[entry_id] = replace(entry, status=status)
        return replace(self, _entries=MappingProxyType(updated))

    def resolve(self, entry_id: str) -> Resolution:
        entry = self._entries.get(entry_id)
        if entry is None:
            return Resolution(None, ("unknown_entry",))
        if entry.status == "tombstone":
            return Resolution(entry, ("tombstone_entry",))
        if entry.status == "stale":
            return Resolution(entry, ("stale_entry",))
        missing = [p for p in entry.prerequisites if p not in self._prerequisites]
        if missing:
            return Resolution(entry, ("missing_prerequisite",))
        binding = entry.binding
        anchor = self.registry._anchors.get(binding.anchor_id)
        if anchor is None:
            return Resolution(entry, ("unknown_anchor",))
        if anchor.revision != binding.revision or anchor.revision != self.revision:
            return Resolution(entry, ("revision_mismatch",))
        if anchor.contract != binding.symbol:
            return Resolution(entry, ("symbol_mismatch",))
        if anchor.digest != binding.code_hash:
            return Resolution(entry, ("code_hash_mismatch",))
        return Resolution(entry)
