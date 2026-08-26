from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "kern")]

import code_retrieval  # noqa: E402


def test_router_is_fixed_by_modality_with_safe_ambiguous_fallback():
    assert code_retrieval.route("signature_to_implementation") == "coderankembed"
    assert code_retrieval.route("code_to_consumer") == "coderankembed"
    assert code_retrieval.route("en_prose_to_code") == "bge_m3"
    assert code_retrieval.route("unknown") == "bge_m3"
    assert code_retrieval.route("unknown", explicit="coderankembed") == "coderankembed"


def test_code_vector_metadata_is_revision_bound_and_stale_vectors_are_rejected():
    record = code_retrieval.vector_metadata(
        project_id="brainlehr", revision="a" * 40, tree_hash="b" * 64,
        graph_node_ref="src:main", modality="code", language="python", content="def x(): pass",
        model_id="nomic-ai/CodeRankEmbed", model_version="3c4b608", dimensions=768,
        created_at="2026-08-26T00:00:00Z")
    accepted = code_retrieval.accept_vector(record, project_id="brainlehr", revision="a" * 40,
                                             tree_hash="b" * 64, model_id="nomic-ai/CodeRankEmbed",
                                             model_version="3c4b608")
    assert accepted["accepted"] is True
    assert code_retrieval.accept_vector(record, project_id="brainlehr", revision="a" * 40,
                                        tree_hash="c" * 64, model_id="nomic-ai/CodeRankEmbed",
                                        model_version="3c4b608")["accepted"] is False
