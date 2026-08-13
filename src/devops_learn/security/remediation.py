"""Deterministic, conservative remediation guidance."""

from __future__ import annotations

from devops_learn.domain.enums import FindingCategory, RemediationRisk
from devops_learn.domain.security_models import RemediationAction, SecurityFinding


def plan_remediation(finding: SecurityFinding) -> RemediationAction:
    if finding.category is FindingCategory.SECRET:
        return RemediationAction(
            finding.fingerprint,
            (
                "Remove the fixture or credential from source and replace any real "
                "credential outside this tool."
            ),
            "A committed secret can be copied from source history and logs.",
            RemediationRisk.HIGH_RISK,
            "Credential owner and rotation procedure, if this is not a synthetic fixture.",
            False,
        )
    if finding.category in (FindingCategory.NETWORK, FindingCategory.IDENTITY):
        return RemediationAction(
            finding.fingerprint,
            "Restrict the exposure to an approved source range or managed access mechanism.",
            "Network and identity changes can remove legitimate access or expand attack surface.",
            RemediationRisk.REQUIRES_HUMAN_INPUT,
            "Approved administrative source range or access strategy.",
            False,
        )
    if finding.category in (FindingCategory.IAC_MISCONFIGURATION, FindingCategory.KUBERNETES):
        return RemediationAction(
            finding.fingerprint,
            "Apply the scanner's least-privilege recommendation and review the resulting plan.",
            "Infrastructure configuration changes can affect availability and access.",
            RemediationRisk.REQUIRES_REVIEW,
            None,
            False,
        )
    if finding.category in (FindingCategory.DEPENDENCY, FindingCategory.VULNERABILITY):
        return RemediationAction(
            finding.fingerprint,
            (
                f"Upgrade {finding.resource or 'the affected dependency'} to "
                f"{finding.fixed_version or 'a supported fixed version'}."
            ),
            "A fixed version may require application compatibility testing.",
            RemediationRisk.REQUIRES_REVIEW,
            None,
            False,
        )
    return RemediationAction(
        finding.fingerprint,
        "Review the scanner evidence and make the smallest safe correction.",
        "The finding has insufficient normalized context for safe automation.",
        RemediationRisk.REQUIRES_REVIEW,
        None,
        False,
    )
