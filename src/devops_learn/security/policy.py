"""Conftest result parsing and policy input generation."""

from __future__ import annotations

import json
from typing import Any, Mapping

from devops_learn.domain.enums import SecurityGateDecision
from devops_learn.domain.security_models import PolicyResult, SecurityFinding

_RANK = {
    SecurityGateDecision.ALLOW: 0,
    SecurityGateDecision.WARN: 1,
    SecurityGateDecision.REQUIRE_APPROVAL: 2,
    SecurityGateDecision.BLOCK: 3,
}


def policy_input(findings: tuple[SecurityFinding, ...]) -> dict[str, Any]:
    return {
        "findings": [
            {
                "fingerprint": finding.fingerprint,
                "rule_id": finding.rule_id,
                "category": finding.category.value,
                "severity": finding.severity.value,
                "change_status": finding.change_status.value,
                "title": finding.title,
                "target": finding.target,
                "file": finding.file,
                "resource": finding.resource,
                "fixed_version": finding.fixed_version,
            }
            for finding in findings
        ]
    }


def parse_conftest_output(output: str) -> PolicyResult:
    """Map policy-owned message prefixes to a single conservative decision."""
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return PolicyResult(
            SecurityGateDecision.BLOCK, ("Policy engine returned malformed JSON.",), False
        )
    messages: list[str] = []
    if isinstance(data, list):
        for result in data:
            if not isinstance(result, Mapping):
                continue
            for failure in result.get("failures", []):
                if isinstance(failure, Mapping) and isinstance(failure.get("msg"), str):
                    messages.append(failure["msg"])
            for warning in result.get("warnings", []):
                if isinstance(warning, Mapping) and isinstance(warning.get("msg"), str):
                    messages.append(warning["msg"])
    decision = SecurityGateDecision.ALLOW
    reasons: list[str] = []
    for message in messages:
        prefix, _, reason = message.partition(":")
        candidate = {
            "BLOCK": SecurityGateDecision.BLOCK,
            "WARN": SecurityGateDecision.WARN,
            "REQUIRE_APPROVAL": SecurityGateDecision.REQUIRE_APPROVAL,
        }.get(prefix.strip().upper(), SecurityGateDecision.WARN)
        if _RANK[candidate] > _RANK[decision]:
            decision = candidate
        reasons.append(reason.strip() or message)
    return PolicyResult(decision, tuple(reasons))
