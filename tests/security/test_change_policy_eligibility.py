from devops_learn.domain.enums import (
    DeploymentEligibility,
    FindingCategory,
    FindingChangeStatus,
    FindingSeverity,
    SecurityGateDecision,
)
from devops_learn.domain.security_models import SecurityFinding
from devops_learn.security.change_analysis import classify_changes
from devops_learn.security.eligibility import evaluate_deployment_eligibility
from devops_learn.security.normalization import stable_fingerprint
from devops_learn.security.policy import parse_conftest_output


def _finding(
    fingerprint: str = "same",
    severity: FindingSeverity = FindingSeverity.HIGH,
    category: FindingCategory = FindingCategory.DEPENDENCY,
) -> SecurityFinding:
    return SecurityFinding(fingerprint, "trivy", "RULE", "Finding", category, severity, "target")


def test_change_classification_and_fingerprint_stability() -> None:
    unchanged = _finding("unchanged")
    introduced = _finding("introduced")
    resolved = _finding("resolved")
    result = classify_changes((unchanged, resolved), (unchanged, introduced))
    statuses = {finding.fingerprint: finding.change_status for finding in result}
    assert statuses == {
        "unchanged": FindingChangeStatus.UNCHANGED,
        "introduced": FindingChangeStatus.INTRODUCED,
        "resolved": FindingChangeStatus.RESOLVED,
    }
    first = stable_fingerprint(
        category=FindingCategory.DEPENDENCY,
        rule_id="CVE",
        target="a",
        file="a",
        resource="pkg",
        installed_version="1",
    )
    second = stable_fingerprint(
        category=FindingCategory.DEPENDENCY,
        rule_id="CVE",
        target="a",
        file="a",
        resource="pkg",
        installed_version="1",
    )
    assert first == second


def test_duplicate_fingerprint_is_uncertain() -> None:
    result = classify_changes((_finding(),), (_finding(), _finding()))
    assert all(finding.change_status is FindingChangeStatus.UNCERTAIN for finding in result)


def test_conftest_policy_output_maps_to_most_restrictive_gate() -> None:
    output = (
        '[{"failures":[{"msg":"BLOCK: introduced secret"}],'
        '"warnings":[{"msg":"WARN: introduced medium"}]}]'
    )
    result = parse_conftest_output(output)
    assert result.decision is SecurityGateDecision.BLOCK
    assert (
        parse_conftest_output(
            '[{"warnings":[{"msg":"REQUIRE_APPROVAL: high dependency"}]}]'
        ).decision
        is SecurityGateDecision.REQUIRE_APPROVAL
    )
    assert (
        parse_conftest_output('[{"warnings":[{"msg":"WARN: uncertain high"}]}]').decision
        is SecurityGateDecision.WARN
    )


def test_deployment_eligibility_obeys_validation_security_and_approval() -> None:
    assert (
        evaluate_deployment_eligibility(
            validation_passed=False, gate=SecurityGateDecision.ALLOW
        ).eligibility
        is DeploymentEligibility.INELIGIBLE
    )
    assert (
        evaluate_deployment_eligibility(
            validation_passed=True, gate=SecurityGateDecision.BLOCK
        ).eligibility
        is DeploymentEligibility.INELIGIBLE
    )
    assert (
        evaluate_deployment_eligibility(
            validation_passed=True, gate=SecurityGateDecision.REQUIRE_APPROVAL
        ).eligibility
        is DeploymentEligibility.PENDING_APPROVAL
    )
    assert (
        evaluate_deployment_eligibility(
            validation_passed=True,
            gate=SecurityGateDecision.REQUIRE_APPROVAL,
            approval_granted=True,
        ).eligibility
        is DeploymentEligibility.ELIGIBLE
    )
    assert (
        evaluate_deployment_eligibility(
            validation_passed=True, gate=SecurityGateDecision.ALLOW
        ).eligibility
        is DeploymentEligibility.ELIGIBLE
    )
