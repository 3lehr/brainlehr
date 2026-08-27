"""Canonical detached command for the sealed V6 scorer."""
from __future__ import annotations


def score_command(python: str) -> list[str]:
    return [python, "-m", "messungen.sealed_retrieval_v6_score"]
