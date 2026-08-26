from kern.codeql_policy import eligibility
from kern.evidence_adapters import normalize_record


def test_private_codeql_is_denied_without_entitlement_or_network():
    denied = eligibility(source_is_public_osi=False, github_code_security_entitled=False,
                         accepted_by_user=True)
    assert denied["status"] == "coverage_gap"
    assert "private" in denied["coverage_gaps"][0]


def test_explicit_public_or_entitled_basis_is_eligible():
    assert eligibility(source_is_public_osi=True, github_code_security_entitled=False,
                       accepted_by_user=True, version="2")["basis"] == "public_osi"
    assert eligibility(source_is_public_osi=False, github_code_security_entitled=True,
                       accepted_by_user=True)["status"] == "eligible"


def test_codeql_sarif_normalizes_as_rule_evidence():
    graph = normalize_record("codeql", {"source": "codeql", "revision": "r1", "runs": [{"results": [
        {"ruleId": "py/example", "locations": [{"physicalLocation": {"artifactLocation": {"uri": "x.py"}}}]}
    ]}]})
    assert graph["provenance"]["strength"] == "rule"
    assert graph["edges"][0]["type"] == "rule_finding"
