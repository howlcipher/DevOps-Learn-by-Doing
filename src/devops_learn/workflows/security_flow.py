"""The DevSecOps stage: scanner evidence -> policy -> eligibility evidence."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from devops_learn.bootstrap import Platform
from devops_learn.domain.enums import (
    AuditEventType,
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExecutionMode,
    ExperienceState,
    ExplanationDepth,
)
from devops_learn.domain.explanation_models import Explanation
from devops_learn.domain.project_models import Artifact
from devops_learn.domain.security_models import SecurityFinding, SecurityReport
from devops_learn.security.change_analysis import classify_changes
from devops_learn.security.normalization import normalize_trivy
from devops_learn.security.policy import parse_conftest_output, policy_input
from devops_learn.security.remediation import plan_remediation
from devops_learn.security.reporting import render_summary, write_report
from devops_learn.workflows.ui import Ui


@dataclass(frozen=True)
class SecurityOptions:
    target: str
    base_ref: str | None = None
    image: str | None = None
    artifact_path: str | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    platform: Platform,
    session_id: int,
    event_type: AuditEventType,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> None:
    platform.audit_service.record(
        session_id=session_id,
        event_type=event_type,
        occurred_at=_now(),
        summary=summary,
        payload=payload or {},
    )


def _scan(
    platform: Platform, operation: str, target: str, base_ref: str | None
) -> tuple[bool, tuple[SecurityFinding, ...]]:
    params: dict[str, Any] = {"target": target}
    if base_ref:
        params["base_ref"] = base_ref
    result = platform.tool_service.invoke("security_scanner", operation, params)
    if not result.success:
        return False, ()
    scan = result.details.get("scan", {})
    return True, normalize_trivy(scan) if isinstance(scan, dict) else ()


def run_security_scan(
    platform: Platform, ui: Ui, options: SecurityOptions
) -> SecurityReport | None:
    target = str(Path(options.target).resolve())
    session = platform.session_service.start(
        project_root=target,
        mode=ExecutionMode.COLLABORATIVE,
        explanation_depth=ExplanationDepth.LEARNING,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.DEV,
        cost_priority=CostPriority.BALANCED,
        simulation_mode=False,
    )
    assert session.id is not None
    session_id = session.id
    _audit(
        platform,
        session_id,
        AuditEventType.SECURITY_SCAN_STARTED,
        "Security scan started",
        {"base_ref": options.base_ref} if options.base_ref else {},
    )
    ui.present(
        platform.explanation_service.render(
            Explanation(
                action="Scanning the proposed change with Trivy.",
                why=(
                    "Scanner evidence is collected before policy or AI explanation "
                    "can describe security risk."
                ),
                what_to_understand=(
                    "A scanner is evidence, not a deployment decision. Policy decides "
                    "eligibility from normalized findings."
                ),
            ),
            mode=ExecutionMode.COLLABORATIVE,
            depth=ExplanationDepth.LEARNING,
        )
    )
    operations = ["scan_filesystem", "scan_config"]
    proposed: list[SecurityFinding] = []
    base: list[SecurityFinding] = []
    for operation in operations:
        ok, findings = _scan(platform, operation, target, None)
        if not ok:
            ui.present(
                "SECURITY SCAN FAILED: Trivy could not produce usable evidence. "
                "Run `devops-learn security doctor` for prerequisites."
            )
            _audit(
                platform,
                session_id,
                AuditEventType.SECURITY_SCAN_COMPLETED,
                "Security scan failed",
                {"success": False},
            )
            platform.session_service.complete(session)
            return None
        proposed.extend(findings)
        if options.base_ref:
            ok, findings = _scan(platform, operation, target, options.base_ref)
            if not ok:
                ui.present(
                    "SECURITY SCAN FAILED: the requested base ref could not be scanned safely."
                )
                _audit(
                    platform,
                    session_id,
                    AuditEventType.SECURITY_SCAN_COMPLETED,
                    "Base security scan failed",
                    {"success": False},
                )
                platform.session_service.complete(session)
                return None
            base.extend(findings)
    if options.image:
        ok, findings = _scan(platform, "scan_image", options.image, None)
        if ok:
            proposed.extend(findings)
        else:
            ui.present(
                "IMAGE SECURITY SCAN FAILED: filesystem/config evidence is retained, "
                "but no image gate was evaluated."
            )
            platform.session_service.complete(session)
            return None
    findings = (
        classify_changes(tuple(base), tuple(proposed)) if options.base_ref else tuple(proposed)
    )
    if not options.base_ref:
        # A single-state scan cannot assert historical novelty.
        from dataclasses import replace
        from devops_learn.domain.enums import FindingChangeStatus

        findings = tuple(
            replace(finding, change_status=FindingChangeStatus.UNCERTAIN) for finding in findings
        )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="devops-learn-policy-", delete=False
    ) as temporary:
        json.dump(policy_input(findings), temporary)
        policy_input_path = Path(temporary.name)
    import importlib.resources
    try:
        policy_files = importlib.resources.files("devops_learn.policy").joinpath("security")
        with importlib.resources.as_file(policy_files) as policy_dir:
            policy_result = platform.tool_service.invoke(
                "security_policy",
                "evaluate",
                {"input_path": str(policy_input_path), "policy_path": str(policy_dir)},
            )
    finally:
        policy_input_path.unlink(missing_ok=True)
    if not policy_result.success:
        ui.present(
            "SECURITY POLICY FAILED: Conftest could not evaluate normalized evidence. "
            "Run `devops-learn security doctor` for prerequisites."
        )
        _audit(
            platform,
            session_id,
            AuditEventType.SECURITY_GATE_EVALUATED,
            "Security policy failed",
            {"success": False},
        )
        platform.session_service.complete(session)
        return None
    policy = parse_conftest_output(str(policy_result.details.get("output", "")))
    report = SecurityReport(
        findings=findings,
        policy=policy,
        scanner_versions={"trivy": "detected at runtime", "conftest": "detected at runtime"},
        base_ref=options.base_ref,
        proposed_target=target,
        metadata={"scanner": "real", "policy": "conftest", "raw_scanner_output_persisted": "false"},
    )
    artifact_path = (
        Path(options.artifact_path)
        if options.artifact_path
        else Path(target) / "artifacts" / "security" / "security-report.json"
    )
    write_report(report, artifact_path)
    platform.artifact_repository.create(
        Artifact(session_id, "security_report", str(artifact_path), _now())
    )
    _audit(
        platform,
        session_id,
        AuditEventType.SECURITY_SCAN_COMPLETED,
        "Security scan completed",
        {"finding_count": len(findings), "secret_values_logged": False},
    )
    _audit(
        platform,
        session_id,
        AuditEventType.SECURITY_GATE_EVALUATED,
        f"Security gate: {policy.decision.value}",
        {"decision": policy.decision.value, "reason_count": len(policy.reasons)},
    )
    platform.experience_tracker.record(
        session_id, "DevSecOps", "Reviewed normalized scanner evidence", ExperienceState.PRACTICED
    )
    platform.experience_tracker.record(
        session_id,
        "Policy as code",
        f"Observed {policy.decision.value} gate",
        ExperienceState.INTRODUCED,
    )
    ui.present(render_summary(report))
    for finding in findings:
        if finding.change_status.value == "introduced" and policy.decision.value in (
            "block",
            "require_approval",
        ):
            remediation = plan_remediation(finding)
            ui.present(
                platform.explanation_service.render(
                    Explanation(
                        action=f"Security finding: {finding.title}",
                        why=finding.description
                        or "The scanner reported this finding in the proposed state.",
                        decision=f"Policy gate is {policy.decision.value.upper()}.",
                        what_to_understand=(
                            "Least privilege and reduced attack surface reduce the impact "
                            "of a compromise."
                        ),
                        result=(
                            "Recommended remediation: "
                            f"{remediation.recommended_change} Risk: {remediation.risk.value}."
                        ),
                    ),
                    mode=ExecutionMode.COLLABORATIVE,
                    depth=ExplanationDepth.LEARNING,
                )
            )
            _audit(
                platform,
                session_id,
                AuditEventType.REMEDIATION_PROPOSED,
                "Security remediation proposed",
                {"finding": finding.fingerprint, "risk": remediation.risk.value},
            )
    ui.present(f"Security report: {artifact_path}")
    platform.session_service.complete(session)
    return report


def run_security_doctor(platform: Platform, ui: Ui) -> bool:
    checks = (
        ("Git", ["git", "--version"]),
        ("Docker", ["docker", "--version"]),
        ("Terraform", ["terraform", "--version"]),
    )
    import shutil

    for label, command in checks:
        ui.present(f"{label:<10} {'available' if shutil.which(command[0]) else 'unavailable'}")
    trivy = platform.tool_service.invoke("security_scanner", "version")
    conftest = platform.tool_service.invoke("security_policy", "version")
    ui.present(f"Trivy      {'available' if trivy.success else 'unavailable'}")
    ui.present(f"Conftest   {'available' if conftest.success else 'unavailable'}")
    if not trivy.success:
        ui.present("Install Trivy: https://trivy.dev/latest/getting-started/installation/")
    if not conftest.success:
        ui.present("Install Conftest: https://www.conftest.dev/install/")
    return trivy.success and conftest.success
