"""Revision-bound routing and metadata for the optional CodeRank code channel.

This module intentionally neither writes the canonical evidence graph nor
touches normal knowledge embeddings.  A caller supplies only semantic code
chunks and keeps their vectors in its separate index.
"""
from __future__ import annotations

import hashlib
import json
from typing import Mapping

CODE_MODALITIES = frozenset({"signature_to_implementation", "code_to_consumer"})
REQUIRED_VECTOR_FIELDS = frozenset({"project_id", "revision", "tree_hash", "graph_node_ref",
                                    "modality", "language", "content_hash", "model_id",
                                    "model_version", "dimensions", "created_at", "status"})


def route(query_modality: str, *, explicit: str | None = None) -> str:
    """Use the fixed, benchmarked router; ambiguous input stays on BGE-M3."""
    if explicit in {"bge_m3", "coderankembed"}:
        return explicit
    return "coderankembed" if query_modality in CODE_MODALITIES else "bge_m3"


def vector_metadata(*, project_id: str, revision: str, tree_hash: str, graph_node_ref: str,
                    modality: str, language: str, content: str, model_id: str,
                    model_version: str, dimensions: int, created_at: str) -> dict:
    """Make a semantic-code vector auditable without storing its raw source here."""
    if modality not in {"code", "signature"}:
        raise ValueError("CodeRank vectors only accept code or signature modality")
    return {"project_id": project_id, "revision": revision, "tree_hash": tree_hash,
            "graph_node_ref": graph_node_ref, "modality": modality, "language": language,
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "model_id": model_id, "model_version": model_version, "dimensions": dimensions,
            "created_at": created_at, "status": "current"}


def accept_vector(record: Mapping[str, object], *, project_id: str, revision: str,
                  tree_hash: str, model_id: str, model_version: str) -> dict:
    """Reject stale/malformed hints before they can affect a code ranking."""
    missing = sorted(REQUIRED_VECTOR_FIELDS - set(record))
    current = (not missing and record.get("status") == "current"
               and record.get("project_id") == project_id and record.get("revision") == revision
               and record.get("tree_hash") == tree_hash and record.get("model_id") == model_id
               and record.get("model_version") == model_version)
    return {"accepted": current,
            "coverage_gaps": ([] if current else ["stale or incomplete CodeRank vector metadata"]),
            "record_hash": hashlib.sha256(json.dumps(dict(record), sort_keys=True,
                                                        separators=(",", ":")).encode()).hexdigest()}
