"""Stable base-versus-proposed finding classification."""

from __future__ import annotations

from collections import Counter
from dataclasses import replace

from devops_learn.domain.enums import FindingChangeStatus
from devops_learn.domain.security_models import SecurityFinding


def classify_changes(
    base: tuple[SecurityFinding, ...], proposed: tuple[SecurityFinding, ...]
) -> tuple[SecurityFinding, ...]:
    """Classify comparable reports without claiming certainty for collisions.

    A duplicated fingerprint within either report means a stable identity is not
    specific enough to compare those occurrences; affected findings are marked
    UNCERTAIN rather than arbitrarily paired.
    """
    base_counts = Counter(finding.fingerprint for finding in base)
    proposed_counts = Counter(finding.fingerprint for finding in proposed)
    findings: list[SecurityFinding] = []
    for finding in proposed:
        fingerprint = finding.fingerprint
        if base_counts[fingerprint] > 1 or proposed_counts[fingerprint] > 1:
            status = FindingChangeStatus.UNCERTAIN
        elif fingerprint in base_counts:
            status = FindingChangeStatus.UNCHANGED
        else:
            status = FindingChangeStatus.INTRODUCED
        findings.append(replace(finding, change_status=status))
    for finding in base:
        fingerprint = finding.fingerprint
        if fingerprint not in proposed_counts:
            status = (
                FindingChangeStatus.UNCERTAIN
                if base_counts[fingerprint] > 1
                else FindingChangeStatus.RESOLVED
            )
            findings.append(replace(finding, change_status=status))
    return tuple(findings)
