"""Portable rewrite candidates for historical absolute paths.

This module is deliberately pure: it does not open a database and never
persists a replacement.  The migration CLI owns the read-only scan and sends
approved writes through the MCP ``tools/call`` boundary.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


_PATH = re.compile(
    r"/(?:Volumes/daten/Begod2026|Volumes/daten/videoki studio|Volumes/daten/videoki|Users/lehrmacbook)(?:/[^\s`'\")\]}>,;:]*)?"
)


@dataclass(frozen=True)
class Rewrite:
    old: str
    new: str
    category: str


def _portable(match: re.Match[str]) -> str:
    value = match.group(0)
    if value.startswith("/Volumes/daten/Begod2026"):
        rest = value.removeprefix("/Volumes/daten/Begod2026").lstrip("/")
        return "project://" + rest
    if value.startswith("/Volumes/daten/videoki studio"):
        rest = value.removeprefix("/Volumes/daten/videoki studio").lstrip("/")
        return "project://videoki%20studio" + ("/" + rest if rest else "")
    if value.startswith("/Volumes/daten/videoki"):
        rest = value.removeprefix("/Volumes/daten/videoki").lstrip("/")
        return "project://videoki" + ("/" + rest if rest else "")
    rest = value.removeprefix("/Users/lehrmacbook").lstrip("/")
    return "workspace://" + rest


def rewrite(text: str) -> tuple[str, tuple[Rewrite, ...]]:
    """Replace only the two historical operator-machine prefixes."""
    changes: list[Rewrite] = []

    def replace(match: re.Match[str]) -> str:
        old = match.group(0)
        new = _portable(match)
        category = "project-path" if old.startswith("/Volumes/") else "workspace-path"
        changes.append(Rewrite(old, new, category))
        return new

    return _PATH.sub(replace, text), tuple(changes)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = ["Rewrite", "digest", "rewrite"]
