from kern.architecture_health import architecture_envelope, as_evidence_witness
from kern.evidence_adapters import normalize_record
from kern.project_context import witness_envelope


META = {"revision": "r1", "config_hash": "c1", "artifact_hash": "a1"}


def semgrep(revision="r1", results=()):
    return normalize_record("semgrep", {"source": "semgrep", "revision": revision,
                                         "tool_version": "1.0", "results": list(results)})


def test_layer_rule_uses_bound_semgrep_and_no_finding_is_not_absence():
    result = architecture_envelope(**META, language="python", scope=["src/a.py"], semgrep_fragment=semgrep(),
                                   import_edges=[{"from": "ui/view.py", "to": "db/store.py"}],
                                   layer_policy=[{"from_prefix": "ui", "to_prefix": "db"}])
    assert result["status"] == "observed"
    assert result["layer_violations"] == [{"from": "ui/view.py", "to": "db/store.py",
                                            "policy": result["layer_violations"][0]["policy"]}]
    assert "no_finding_is_not_architecture_absence" in result["coverage_gaps"]


def test_clones_are_advisory_and_dead_code_is_only_candidate_with_bound_runtime():
    result = architecture_envelope(**META, language="python", scope=["src/a.py"], semgrep_fragment=semgrep(),
                                   clone_candidates=[{"left": "src/a.py", "right": "src/b.py"}],
                                   reachability=[{"path": "src/old.py", "importers": 0, "route_refs": 0,
                                                  "config_refs": 0, "test_refs": 0}],
                                   runtime_evidence={**META, "status": "observed"})
    assert result["clone_candidates"][0]["status"] == "advisory"
    assert result["reachability"][0]["status"] == "candidate"
    assert result["reachability"][0]["runtime_absence_bound"] is True


def test_missing_runtime_or_wrong_analyzer_stays_unknown_and_p98_can_load_witness():
    result = architecture_envelope(**META, language="python", scope=["src/a.py"],
                                   semgrep_fragment=semgrep("old"),
                                   reachability=[{"path": "src/old.py", "importers": 0, "route_refs": 0,
                                                  "config_refs": 0, "test_refs": 0}])
    assert result["status"] == "UNKNOWN"
    assert result["reachability"][0]["status"] == "UNKNOWN"
    witness = as_evidence_witness(result, witness_id="w-p91", requirement_ids=["P91"],
                                  independence_group="semgrep", lineage_id="semgrep-r1")
    assert witness_envelope(witnesses=[witness])["requirement_summaries"][0]["verdict_counts"] == {"unknown": 1}
