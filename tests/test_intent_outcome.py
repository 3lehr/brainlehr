import pytest

from kern.intent_outcome import build_trace


def req(**extra):
    base = {"id": "BDW-P86", "claim": "at least 1 observed journey", "type": "boolean",
            "unit": "boolean", "data_source": "test fixture", "falsifier": "no event",
            "threshold": True}
    return {**base, **extra}


def parts(status="success", **extra):
    return dict(intent={"id": "i1", "requirement": req(**extra)},
                journey={"id": "j1", "steps": ["run"]},
                evidence={"id": "e1", "source": "fixture:event", "measurement": "seen", "value": 1},
                outcome={"status": status, "observed": status == "success"},
                source_revision="abc123", tree_hash="sha256:def456")


def test_success_and_observed_failure_are_distinct():
    assert build_trace(**parts())["status"] == "success"
    assert build_trace(**parts("failure"))["status"] == "failure"


def test_infeasible_requirement_is_unmeasurable_gap():
    assert build_trace(**parts(claim="works well"))["status"] == "unmeasurable"


@pytest.mark.parametrize("field", ["source_revision", "tree_hash"])
def test_source_binding_is_required(field):
    data = parts()
    data[field] = ""
    with pytest.raises(ValueError, match="missing_"):
        build_trace(**data)


def test_raw_input_and_llm_label_are_rejected():
    data = parts()
    data["evidence"]["raw_content"] = "secret"
    with pytest.raises(ValueError, match="invalid_evidence_fields"):
        build_trace(**data)
    data = parts()
    data["outcome"]["label"] = "likely success"
    with pytest.raises(ValueError, match="invalid_outcome_fields"):
        build_trace(**data)
    data = parts()
    data["evidence"]["source"] = "/host/raw-trace"
    with pytest.raises(ValueError, match="missing_evidence_source"):
        build_trace(**data)
