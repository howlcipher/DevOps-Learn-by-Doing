from dataclasses import replace

import pytest

from devops_learn.deployment.candidate import DeploymentCandidate


def _candidate() -> DeploymentCandidate:
    return DeploymentCandidate(
        source_revision="source-a",
        project_path="projects/api_platform",
        cloud="azure",
        environment="learning",
        terraform_config_digest="terraform-a",
        image_reference="acr/api@sha256:abc",
        image_digest="sha256:abc",
        security_report_path="report.json",
        security_report_digest="security-a",
        security_decision="allow",
    )


def test_candidate_identity_is_deterministic_and_change_aware() -> None:
    candidate = _candidate()
    assert candidate.identity == _candidate().identity
    assert candidate.identity != replace(candidate, source_revision="source-b").identity
    assert candidate.identity != replace(candidate, security_report_digest="security-b").identity
    assert candidate.identity != replace(candidate, image_digest="sha256:def").identity
    assert (
        candidate.context_identity
        != replace(candidate, terraform_config_digest="terraform-b").context_identity
    )


def test_candidate_requires_evidence_paths_for_digests() -> None:
    with pytest.raises(ValueError, match="saved plan path"):
        replace(_candidate(), terraform_plan_digest="plan")
    with pytest.raises(ValueError, match="report path"):
        replace(_candidate(), security_report_path=None)
