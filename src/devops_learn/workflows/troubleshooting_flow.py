"""Troubleshooting workflow: fault injection -> observation -> progressive assistance
-> remediation -> deterministic recovery verification -> cleanup.

Per the product spec, scenarios follow an explicit lifecycle:
SETUP -> INJECT -> OBSERVE -> EXPLAIN -> REMEDIATE -> VERIFY -> CLEANUP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

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
from devops_learn.domain.question_models import ClarifyingQuestion
from devops_learn.domain.troubleshooting_models import (
    Observation,
    RemediationAttempt,
    TroubleshootingEvidence,
    VerificationResult,
)
from devops_learn.workflows.ui import Ui


@dataclass(frozen=True)
class TroubleshootingOptions:
    scenario_id: str
    hint_level: int | None = None
    remediation_action: str | None = None
    remediation_params: Mapping[str, Any] = field(default_factory=dict)
    project_root: str = "."
    simulate: bool | None = None
    interactive: bool = False


def list_troubleshooting_scenarios(platform: Platform, ui: Ui) -> None:
    scenarios = platform.troubleshooting_service.list_scenarios()
    lines = [
        "============================================================",
        "AVAILABLE TROUBLESHOOTING SCENARIOS",
        "============================================================",
        "",
    ]
    for s in scenarios:
        lines.extend(
            (
                f"[{s.scenario_id}] {s.title}",
                f"  Category:  {s.category.value}",
                f"  Objective: {s.learning_objective}",
                f"  Fault:     {s.fault_description}",
                "",
            )
        )
    lines.append("Run a scenario with: devops-learn troubleshoot run <scenario_id>")
    ui.present("\n".join(lines))


def run_troubleshooting_flow(
    platform: Platform,
    ui: Ui,
    options: TroubleshootingOptions,
) -> TroubleshootingEvidence:
    # 1. Determine execution capability (real vs simulated)
    is_live = False
    if options.simulate is False or options.simulate is None:
        docker_available = False
        try:
            doc_res = platform.tool_service.invoke(
                "docker", "logs", {"container": "nonexistent_test"}
            )
            docker_available = not doc_res.summary.endswith("(simulated)")
        except Exception:
            docker_available = False

        if options.simulate is False and not docker_available:
            ui.present(
                "[!] Real Docker environment requested but unavailable. "
                "Falling back safely to simulated mode."
            )
            is_live = False
        else:
            is_live = docker_available

    mode_label = "LIVE VERIFIED" if is_live else "SIMULATED / TESTED"

    # 2. Start engagement session for tracking and persistence
    session = platform.session_service.start(
        project_root=options.project_root,
        mode=ExecutionMode.COLLABORATIVE,
        explanation_depth=ExplanationDepth.LEARNING,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.LOCAL,
        cost_priority=CostPriority.BALANCED,
        simulation_mode=not is_live,
    )
    assert session.id is not None
    session_id = session.id

    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.TROUBLESHOOTING_STARTED,
        occurred_at=datetime.now(timezone.utc),
        summary=f"Started troubleshooting scenario: {options.scenario_id} ({mode_label})",
        payload={"scenario_id": options.scenario_id, "is_live": is_live},
    )

    # 3. Setup and Inject Fault
    tb_session, context, before_obs = platform.troubleshooting_service.start_session(
        options.scenario_id,
        project_root=options.project_root,
        is_live=is_live,
    )
    scenario = tb_session.scenario

    ui.present(
        f"============================================================\n"
        f"TROUBLESHOOTING: {scenario.title}\n"
        f"Execution Mode: {mode_label}\n"
        f"Category:       {scenario.category.value}\n"
        f"Objective:      {scenario.learning_objective}\n"
        f"============================================================\n"
    )

    ui.present("--- LEVEL 0: RAW OBSERVATIONS (EVIDENCE ONLY) ---")
    for obs in before_obs:
        status_tag = "[ERROR]" if obs.is_error else "[INFO]"
        ui.present(f"{status_tag} ({obs.source}) {obs.content}")
    ui.present("")

    # 4. Progressive Assistance / Hints
    requested_hint_level = options.hint_level
    if options.interactive and requested_hint_level is None:
        choice = ui.ask_choice(
            ClarifyingQuestion(
                id="hint_request",
                category="troubleshooting",
                prompt="Would you like a progressive hint before attempting remediation?",
                options=(
                    "Level 0: Proceed with evidence only",
                    "Level 1: Inspection guide (where to look)",
                    "Level 2: Subsystem explanation",
                    "Level 3: Root cause explanation",
                    "Level 4: Suggested remediation",
                ),
            )
        )
        if "Level 1" in choice:
            requested_hint_level = 1
        elif "Level 2" in choice:
            requested_hint_level = 2
        elif "Level 3" in choice:
            requested_hint_level = 3
        elif "Level 4" in choice:
            requested_hint_level = 4
        else:
            requested_hint_level = 0

    if requested_hint_level is not None and requested_hint_level > 0:
        ui.present(f"--- PROGRESSIVE ASSISTANCE (LEVEL 1 TO {requested_hint_level}) ---")
        for lvl in range(1, requested_hint_level + 1):
            hint_text = platform.troubleshooting_service.get_hint(scenario.scenario_id, lvl)
            ui.present(f"[HINT LEVEL {lvl}] {hint_text}")
        ui.present("")

    # 5. Remediation & Verification
    remediation_action = options.remediation_action
    remediation_params = dict(options.remediation_params)

    if options.interactive and not remediation_action and not remediation_params:
        rem_input = ui.ask_choice(
            ClarifyingQuestion(
                id="remediation_input",
                category="troubleshooting",
                prompt=(
                    "Enter remediation parameter (e.g. port=8081, "
                    "REQUIRED_CONFIG_KEY=value, dependency_status=healthy, memory_limit=64m):"
                ),
                options=(),
            )
        )
        remediation_action = rem_input
        for token in rem_input.split():
            if "=" in token:
                k, v = token.split("=", 1)
                remediation_params[k.strip()] = v.strip()

    attempt = RemediationAttempt(
        scenario_id=scenario.scenario_id,
        action=remediation_action or "",
        parameters=remediation_params,
    )

    after_obs: tuple[Observation, ...] = ()
    verification: VerificationResult | None = None
    resolved = False

    try:
        if attempt.action or attempt.parameters:
            platform.audit_service.record(
                session_id=session_id,
                event_type=AuditEventType.TROUBLESHOOTING_REMEDIATION_ATTEMPTED,
                occurred_at=datetime.now(timezone.utc),
                summary=f"Remediation attempted: {attempt.action or attempt.parameters}",
                payload={"action": attempt.action, "params": dict(attempt.parameters)},
            )
            ui.present("--- APPLYING REMEDIATION ---")
            after_obs = platform.troubleshooting_service.remediate(tb_session, context, attempt)
            for obs in after_obs:
                status_tag = "[ERROR]" if obs.is_error else "[OK]"
                ui.present(f"{status_tag} ({obs.source}) {obs.content}")
            ui.present("")

            ui.present("--- DETERMINISTIC RECOVERY VERIFICATION ---")
            verification = platform.troubleshooting_service.verify(tb_session, context, attempt)
            resolved = verification.success

            if resolved:
                ui.present(f"[PASS] {verification.summary}")
                platform.audit_service.record(
                    session_id=session_id,
                    event_type=AuditEventType.TROUBLESHOOTING_VERIFIED,
                    occurred_at=datetime.now(timezone.utc),
                    summary=f"Recovery verified: {verification.summary}",
                    payload={"success": True, "mode": mode_label},
                )
                platform.experience_tracker.record(
                    session_id,
                    scenario.category.value.title(),
                    f"Resolved incident: {scenario.title}",
                    ExperienceState.DEMONSTRATED,
                )
            else:
                ui.present(f"[FAIL] {verification.summary}")
                platform.audit_service.record(
                    session_id=session_id,
                    event_type=AuditEventType.TROUBLESHOOTING_FAILED,
                    occurred_at=datetime.now(timezone.utc),
                    summary=f"Verification failed: {verification.summary}",
                    payload={"success": False, "mode": mode_label},
                )
        else:
            ui.present("--- NO REMEDIATION SUPPLIED ---")
            verification = VerificationResult(
                success=False,
                summary="No remediation attempt was supplied; failure condition persists.",
                is_live=is_live,
            )
    finally:
        # 6. Guaranteed Cleanup
        platform.troubleshooting_service.cleanup(tb_session, context)
        ui.present("\n[✓] Teardown & cleanup completed successfully.\n")

    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.TROUBLESHOOTING_COMPLETED,
        occurred_at=datetime.now(timezone.utc),
        summary=(
            f"Troubleshooting session completed for {options.scenario_id} (Resolved: {resolved})"
        ),
        payload={"resolved": resolved},
    )
    platform.session_service.complete(session)

    evidence = TroubleshootingEvidence(
        scenario_id=scenario.scenario_id,
        before_state=before_obs,
        remediation=attempt,
        after_state=after_obs,
        verification=verification,
        resolved=resolved,
        mode_label=mode_label,
    )
    return evidence
