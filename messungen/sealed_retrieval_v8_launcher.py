"""Canonical resource-bound command for the sealed V8 scorer."""
from __future__ import annotations

from messungen.sealed_retrieval_v7_launcher import RESOURCE_ENV


def score_command(python: str) -> list[str]:
    return [python, "-m", "messungen.sealed_retrieval_v8_score"]
