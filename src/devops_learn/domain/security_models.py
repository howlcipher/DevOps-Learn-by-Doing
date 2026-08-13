"""Scanner-independent DevSecOps evidence and deterministic decisions.

Raw scanner output is intentionally not represented here.  In particular, a
secret match is never a field that downstream code can accidentally render.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from devops_learn.domain.enums import (
    DeploymentEligibility,
    FindingCategory,
    FindingChangeStatus,
    FindingSeverity,
    RemediationRisk,
    SecurityGateDecision,
)


@dataclass(frozen=True)
class SecurityFinding:
    fingerprint: str
    scanner: str
    rule_id: str
    title: str
    category: FindingCategory
    severity: FindingSeverity
    target: str
    file: str | None = None
    line: int | None = None
    resource: str | None = None
    installed_version: str | None = None
    fixed_version: str | None = None
    description: str | None = None
    references: tuple[str, ...] = ()
    change_status: FindingChangeStatus = FindingChangeStatus.UNCERTAIN
    evidence: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RemediationAction:
    finding_fingerprint: str
    recommended_change: str
    why: str
    risk: RemediationRisk
    required_information: str | None
    automation_available: bool


@dataclass(frozen=True)
class PolicyResult:
    decision: SecurityGateDecision
    reasons: tuple[str, ...]
    policy_available: bool = True


@dataclass(frozen=True)
class SecurityReport:
    findings: tuple[SecurityFinding, ...]
    policy: PolicyResult
    scanner_versions: Mapping[str, str]
    base_ref: str | None
    proposed_target: str
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DeploymentEligibilityResult:
    validation_passed: bool
    security_gate: SecurityGateDecision
    approval_granted: bool
    eligibility: DeploymentEligibility
    reason: str
