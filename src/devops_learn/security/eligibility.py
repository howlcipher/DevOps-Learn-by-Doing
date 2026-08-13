"""Security gate to deployment eligibility conversion."""

from __future__ import annotations

from devops_learn.domain.enums import DeploymentEligibility, SecurityGateDecision
from devops_learn.domain.security_models import DeploymentEligibilityResult


def evaluate_deployment_eligibility(
    *, validation_passed: bool, gate: SecurityGateDecision, approval_granted: bool = False
) -> DeploymentEligibilityResult:
    if not validation_passed:
        return DeploymentEligibilityResult(
            False, gate, approval_granted, DeploymentEligibility.INELIGIBLE, "Validation failed."
        )
    if gate is SecurityGateDecision.BLOCK:
        return DeploymentEligibilityResult(
            True,
            gate,
            approval_granted,
            DeploymentEligibility.INELIGIBLE,
            "Security policy blocked this change.",
        )
    if gate is SecurityGateDecision.REQUIRE_APPROVAL and not approval_granted:
        return DeploymentEligibilityResult(
            True,
            gate,
            False,
            DeploymentEligibility.PENDING_APPROVAL,
            "Security policy requires human approval.",
        )
    return DeploymentEligibilityResult(
        True,
        gate,
        approval_granted,
        DeploymentEligibility.ELIGIBLE,
        "Validation and security requirements are satisfied.",
    )
