"""Explicit eligibility gate for optional CodeQL SARIF evidence."""
from __future__ import annotations

from datetime import datetime, timezone


TERMS_URL = "https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md"


def eligibility(*, source_is_public_osi: bool, github_code_security_entitled: bool,
                accepted_by_user: bool, version: str = "") -> dict:
    """No network, download or scan: only decide whether a caller may request one."""
    if not accepted_by_user:
        return {"status": "coverage_gap", "coverage_gaps": ["explicit CodeQL request/acceptance required"]}
    if not (source_is_public_osi or github_code_security_entitled):
        return {"status": "coverage_gap", "coverage_gaps": ["CodeQL CLI license eligibility not evidenced for private source"],
                "terms_url": TERMS_URL}
    basis = "public_osi" if source_is_public_osi else "github_code_security_entitlement"
    return {"status": "eligible", "basis": basis, "version": version,
            "terms_url": TERMS_URL, "evaluated_at": datetime.now(timezone.utc).isoformat()}
