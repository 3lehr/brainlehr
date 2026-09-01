from kern.requirement_feasibility import validate_requirement


def req(kind, unit, threshold):
    return {"id": "BDW-P96", "claim": "at least 95% within threshold",
            "type": kind, "unit": unit, "threshold": threshold,
            "data_source": "pytest measurement", "falsifier": "one failed observation"}


def test_valid_ratio_duration_and_boolean_requirements():
    assert validate_requirement(req("ratio", "fraction", .95))["status"] == "feasible"
    assert validate_requirement(req("duration", "seconds", 2))["status"] == "feasible"
    assert validate_requirement(req("boolean", "", True))["status"] == "feasible"


def test_missing_measurement_contract_is_reported_as_typed_gaps():
    result = validate_requirement({"id": "BDW-P96", "claim": "works well", "type": "ratio",
                                   "threshold": .5})
    assert result["status"] == "invalid"
    assert {"unmeasurable_claim", "missing_unit", "missing_data_source", "missing_falsifier"} <= set(result["coverage_gaps"])


def test_invalid_type_and_threshold_are_rejected():
    assert "invalid_type" in validate_requirement(req("guess", "x", 1))["coverage_gaps"]
    assert "invalid_threshold" in validate_requirement(req("ratio", "fraction", 2))["coverage_gaps"]
    assert "invalid_threshold" in validate_requirement(req("duration", "seconds", -1))["coverage_gaps"]
    assert "invalid_threshold" in validate_requirement(req("boolean", "", 1))["coverage_gaps"]

