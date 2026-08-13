"""Trivy-to-domain normalization with no raw-secret retention."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from devops_learn.domain.enums import FindingCategory, FindingSeverity
from devops_learn.domain.security_models import SecurityFinding
from devops_learn.security.redaction import REDACTED_SECRET, redact_text


def _severity(value: object) -> FindingSeverity:
    try:
        return FindingSeverity(str(value).lower())
    except ValueError:
        return FindingSeverity.UNKNOWN


def _category(result: Mapping[str, Any], item: Mapping[str, Any], kind: str) -> FindingCategory:
    if kind == "secret":
        return FindingCategory.SECRET
    if kind == "misconfiguration":
        text = " ".join(str(item.get(key, "")) for key in ("Type", "ID", "Title"))
        lowered = text.lower()
        if "kubernetes" in lowered or "k8s" in lowered:
            return FindingCategory.KUBERNETES
        if "docker" in lowered or "container" in lowered:
            return FindingCategory.CONTAINER
        if "network" in lowered or "port" in lowered or "ingress" in lowered:
            return FindingCategory.NETWORK
        if "identity" in lowered or "rbac" in lowered:
            return FindingCategory.IDENTITY
        return FindingCategory.IAC_MISCONFIGURATION
    if kind == "vulnerability":
        return FindingCategory.DEPENDENCY
    return FindingCategory.UNKNOWN


def stable_fingerprint(
    *,
    category: FindingCategory,
    rule_id: str,
    target: str,
    file: str | None,
    resource: str | None,
    installed_version: str | None,
) -> str:
    """Hash stable identity fields, never scanner prose, ordering, or timestamps."""
    parts = (category.value, rule_id, target, file or "", resource or "", installed_version or "")
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:24]


def _line(item: Mapping[str, Any]) -> int | None:
    cause = item.get("CauseMetadata")
    if isinstance(cause, Mapping) and isinstance(cause.get("StartLine"), int):
        return int(cause["StartLine"])
    value = item.get("StartLine")
    return value if isinstance(value, int) else None


def _finding(result: Mapping[str, Any], item: Mapping[str, Any], kind: str) -> SecurityFinding:
    target = str(result.get("Target", "unknown"))
    rule_id = str(item.get("VulnerabilityID") or item.get("ID") or item.get("RuleID") or "unknown")
    resource = item.get("PkgName") or item.get("Resource")
    resource_text = str(resource) if resource is not None else None
    installed = item.get("InstalledVersion")
    installed_text = str(installed) if installed is not None else None
    file_value = item.get("File") or target
    file = str(file_value) if file_value else None
    category = _category(result, item, kind)
    title = str(item.get("Title") or item.get("Message") or rule_id)
    description = item.get("Description")
    description_text = redact_text(str(description)) if description else None
    references_raw = item.get("References", [])
    references = tuple(str(item) for item in references_raw if isinstance(item, str))
    evidence = None
    if kind == "secret":
        evidence = f"Secret pattern detected; value {REDACTED_SECRET}"
    elif file:
        evidence = f"Trivy rule {rule_id} at {file}" + (f":{_line(item)}" if _line(item) else "")
    return SecurityFinding(
        fingerprint=stable_fingerprint(
            category=category,
            rule_id=rule_id,
            target=target,
            file=file,
            resource=resource_text,
            installed_version=installed_text,
        ),
        scanner="trivy",
        rule_id=rule_id,
        title=title,
        category=category,
        severity=_severity(item.get("Severity")),
        target=target,
        file=file,
        line=_line(item),
        resource=resource_text,
        installed_version=installed_text,
        fixed_version=str(item["FixedVersion"]) if item.get("FixedVersion") else None,
        description=description_text,
        references=references,
        evidence=evidence,
        metadata={"trivy_type": str(result.get("Type", "unknown")), "finding_kind": kind},
    )


def normalize_trivy(document: Mapping[str, Any]) -> tuple[SecurityFinding, ...]:
    """Normalize a complete Trivy JSON document; tolerate partial output."""
    results = document.get("Results", [])
    if not isinstance(results, list):
        return ()
    findings: list[SecurityFinding] = []
    for result in results:
        if not isinstance(result, Mapping):
            continue
        for field, kind in (
            ("Vulnerabilities", "vulnerability"),
            ("Misconfigurations", "misconfiguration"),
            ("Secrets", "secret"),
        ):
            items = result.get(field, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, Mapping):
                    findings.append(_finding(result, item, kind))
    return tuple(findings)
