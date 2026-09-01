from kern.evidence_projections import _hash, otel_trace_projection


def _graph():
    graph = {"schema": 2, "source_revision": "r1", "nodes": [{"id": "kern/a.py"}], "edges": []}
    graph["content_hash"] = _hash(graph)
    return graph


def _trace(**extra):
    trace = {"revision": "r1", "tree_hash": "t1", "captured_at_ns": 100,
             "spans": [{"span_id": "stable", "name": "test", "code_file": "kern/a.py",
                        "revision": "r1", "tree_hash": "t1", "duration_ns": 4,
                        "start_time_unix_nano": 10, "end_time_unix_nano": 14}]}
    trace.update(extra)
    return trace


def test_trace_sampling_clock_retention_and_erasure_are_explicit():
    current = otel_trace_projection(_trace(), source_revision="r1", tree_hash="t1", graph=_graph(),
                                    sample_rate=1.0, now_ns=105, retention_ns=10)
    assert current["status"] == "current" and current["sampling"] == {"rate": 1.0, "kept": 1, "seen": 1}
    expired = otel_trace_projection(_trace(), source_revision="r1", tree_hash="t1", graph=_graph(),
                                    now_ns=111, retention_ns=10)
    assert expired == {"status": "expired", "erased": True, "bindings": [],
                       "coverage_gaps": ["trace_retention_expired"]}
    skew = _trace(spans=[{**_trace()["spans"][0], "end_time_unix_nano": 9}])
    assert otel_trace_projection(skew, source_revision="r1", tree_hash="t1", graph=_graph())["coverage_gaps"] == ["clock_skew_or_invalid_span_time"]
