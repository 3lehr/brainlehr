"""Canonical resource-bound command for the sealed V7 scorer."""
from __future__ import annotations


RESOURCE_ENV = {
    "TOKENIZERS_PARALLELISM": "false",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
}


def score_command(python: str) -> list[str]:
    return [python, "-m", "messungen.sealed_retrieval_v7_score"]
