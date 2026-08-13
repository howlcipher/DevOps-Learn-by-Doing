"""Safe human and machine-readable reporting for normalized evidence."""

from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from devops_learn.domain.security_models import SecurityReport
from devops_learn.security.redaction import redact_data


def render_summary(report: SecurityReport) -> str:
    counts = {status: 0 for status in ("introduced", "resolved", "unchanged", "uncertain")}
    severities = {severity: 0 for severity in ("critical", "high", "medium", "low")}
    for finding in report.findings:
        counts[finding.change_status.value] += 1
        if finding.severity.value in severities:
            severities[finding.severity.value] += 1
    lines = [
        "DEVSECOPS GATE",
        "",
        f"Introduced: {counts['introduced']}",
        f"Resolved:   {counts['resolved']}",
        f"Unchanged:  {counts['unchanged']}",
        f"Uncertain:  {counts['uncertain']}",
        "",
        f"Critical: {severities['critical']}",
        f"High:     {severities['high']}",
        f"Medium:   {severities['medium']}",
        f"Low:      {severities['low']}",
        "",
        f"GATE: {report.policy.decision.name}",
    ]
    for finding in report.findings:
        if finding.change_status.value == "introduced" and report.policy.decision.value in (
            "block",
            "require_approval",
        ):
            location = f" {finding.file}:{finding.line}" if finding.file and finding.line else ""
            lines.append(
                f"- {finding.severity.value.upper()} {finding.title} ({finding.rule_id}){location}"
            )
    return "\n".join(lines)


def write_report(report: SecurityReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "metadata": dict(report.metadata),
        "scanner_versions": dict(report.scanner_versions),
        "base_ref": report.base_ref,
        "proposed_target": report.proposed_target,
        "findings": [asdict(finding) for finding in report.findings],
        "policy": asdict(report.policy),
    }
    path.write_text(
        json.dumps(
            redact_data(document),
            indent=2,
            sort_keys=True,
            default=lambda value: value.value if isinstance(value, Enum) else str(value),
        )
        + "\n"
    )
