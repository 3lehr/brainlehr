from kern.coverage_provenance import classify_coverage


def test_unsupported_provenance_is_an_explicit_gap_and_never_complete():
    result = classify_coverage(files=["src/loader.py", "terraform/main.tf"],
                               signals=["dynamic import"],
                               evidence={"ci": False, "local": True, "flaky": True})
    assert result["status"] == "coverage_gap"
    assert result["complete"] is False
    assert {"dynamic", "iac", "ci evidence unavailable", "flaky evidence is non-reproducible"} <= set(result["coverage_gaps"])


def test_clean_input_is_bounded_not_complete():
    result = classify_coverage(files=["kern/example.py"], evidence={"ci": True, "local": True})
    assert result == {"status": "bounded", "coverage_gaps": [], "complete": False,
                      "provenance": {"files": 1, "signals": 0}}


def test_mixed_project_widens_impact_conservatively_for_unmodelled_inputs():
    result = classify_coverage(files=["src/plugin/loader.py", "vendor/sdk.py", "generated/api.py",
                                      "infra/main.tf", "app/ios/Runner.swift"],
                               signals=["getattr(", "importlib"],
                               evidence={"ci": False, "local": True, "flaky": True})
    assert result["status"] == "coverage_gap" and result["complete"] is False
    assert {"dynamic", "reflection", "plugin", "vendor", "generated", "iac", "mobile",
            "ci evidence unavailable", "flaky evidence is non-reproducible"} <= set(result["coverage_gaps"])
