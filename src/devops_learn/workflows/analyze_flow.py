"""The end-to-end workflow: analyze -> requirements -> questions -> recommend ->
architecture -> plan -> validate -> approve -> build -> verify -> troubleshoot.

This is the single place that sequences the platform's services (see
docs/architecture.md). It depends only on the Ui abstraction for interaction,
so the same function drives the CLI today and could drive a web UI later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from devops_learn.bootstrap import Platform
from devops_learn.domain.enums import (
    AuditEventType,
    CloudProviderKind,
    CostPriority,
    EnvironmentKind,
    ExperienceState,
    ExplanationDepth,
    OperatingMode,
)
from devops_learn.domain.explanation_models import Explanation
from devops_learn.domain.plan_models import ImplementationPlan, PlanStep
from devops_learn.domain.recommendation_models import Recommendation
from devops_learn.domain.requirements_models import DetectedRequirement
from devops_learn.domain.analysis_models import ProjectAssessment
from devops_learn.domain.session_models import EngagementSession
from devops_learn.validation.terraform_plan_analysis import analyze as analyze_terraform_plan
from devops_learn.workflows import presenters
from devops_learn.workflows.ui import Ui


@dataclass(frozen=True)
class AnalyzeOptions:
    project_root: str
    mode: OperatingMode
    explanation_depth: ExplanationDepth
    cloud: CloudProviderKind
    environment: EnvironmentKind | None
    cost_priority: CostPriority | None
    public_access: bool | None
    wants_kubernetes_experience: bool
    simulation_mode: bool = True


def run_analysis(platform: Platform, ui: Ui, options: AnalyzeOptions) -> EngagementSession:
    session = platform.session_service.start(
        project_root=options.project_root,
        mode=options.mode,
        explanation_depth=options.explanation_depth,
        cloud=options.cloud,
        environment=options.environment or EnvironmentKind.DEV,
        cost_priority=options.cost_priority or CostPriority.BALANCED,
        simulation_mode=options.simulation_mode,
    )
    assert session.id is not None
    session_id = session.id

    assessment = platform.analyzer.analyze(options.project_root)
    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.PROJECT_ANALYZED,
        occurred_at=_now(),
        summary=f"Analyzed {options.project_root}",
    )
    ui.present(presenters.render_assessment(assessment))

    requirements = platform.requirements_service.detect(assessment)
    for requirement in requirements:
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.REQUIREMENT_DETECTED,
            occurred_at=_now(),
            summary=requirement.title,
        )
    ui.present(presenters.render_requirements(requirements))

    if options.mode is OperatingMode.REVIEW:
        _run_review_only(platform, ui, session_id, assessment, requirements, options)
        platform.session_service.complete(session)
        return session

    environment, public_access, cost_priority = _resolve_decisions(
        platform, ui, session_id, options
    )

    recommendations = platform.recommendation_service.build_recommendations(
        assessment,
        requirements,
        cost_priority=cost_priority,
        wants_kubernetes_experience=options.wants_kubernetes_experience,
    )
    accepted = _walk_recommendations(platform, ui, session_id, recommendations, options)

    architecture = platform.architecture_service.propose(accepted)
    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.ARCHITECTURE_PROPOSED,
        occurred_at=_now(),
        summary=architecture.summary,
    )
    ui.present(presenters.render_architecture(architecture))
    if options.mode in (OperatingMode.LEARN, OperatingMode.COLLABORATE):
        if not ui.confirm("Proceed with this architecture?", default=True):
            ui.present("Stopping before any implementation. Nothing was changed.")
            platform.session_service.complete(session)
            return session

    plan = platform.planning_service.build_plan(architecture)
    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.PLAN_CREATED,
        occurred_at=_now(),
        summary=f"Implementation plan with {len(plan.steps)} step(s)",
    )

    _run_validation_and_build(platform, ui, session_id, plan, environment, options)
    _run_health_check_and_troubleshoot(platform, ui, session_id, options)

    platform.session_service.complete(session)
    _print_history_and_experience(platform, ui, session_id)
    return session


def _resolve_decisions(
    platform: Platform, ui: Ui, session_id: int, options: AnalyzeOptions
) -> tuple[EnvironmentKind, bool, CostPriority]:
    questions = platform.question_service.material_questions(
        environment_known=options.environment is not None,
        public_access_known=options.public_access is not None,
        cost_priority_known=options.cost_priority is not None,
        wants_kubernetes_experience=options.wants_kubernetes_experience,
    )
    environment = options.environment
    public_access = options.public_access
    cost_priority = options.cost_priority

    for question in questions:
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.QUESTION_ASKED,
            occurred_at=_now(),
            summary=question.prompt,
        )
        answer = ui.ask_choice(question)
        platform.decision_service.record(
            session_id, subject_kind="question", subject_id=question.id, outcome=answer
        )
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.USER_DECISION,
            occurred_at=_now(),
            summary=f"{question.id} -> {answer}",
        )
        if question.id == "environment":
            environment = _parse_environment(answer)
        elif question.id == "public_access":
            public_access = answer.lower().startswith("yes")
        elif question.id == "cost_priority":
            cost_priority = _parse_cost_priority(answer)

    return (
        environment or EnvironmentKind.DEV,
        public_access if public_access is not None else True,
        cost_priority or CostPriority.BALANCED,
    )


def _walk_recommendations(
    platform: Platform,
    ui: Ui,
    session_id: int,
    recommendations: tuple[Recommendation, ...],
    options: AnalyzeOptions,
) -> tuple[Recommendation, ...]:
    accepted: list[Recommendation] = []
    for rec in recommendations:
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.RECOMMENDATION_CREATED,
            occurred_at=_now(),
            summary=rec.title,
        )
        ui.present(presenters.render_recommendation(rec))

        should_ask = rec.requires_user_decision and options.mode in (
            OperatingMode.LEARN,
            OperatingMode.COLLABORATE,
        )
        if should_ask:
            proceed = ui.confirm(f"Accept recommendation '{rec.title}'?", default=True)
        else:
            proceed = True

        outcome = "accepted" if proceed else "rejected"
        platform.decision_service.record(
            session_id, subject_kind="recommendation", subject_id=rec.id, outcome=outcome
        )
        platform.audit_service.record(
            session_id=session_id,
            event_type=(AuditEventType.USER_APPROVED if proceed else AuditEventType.USER_REJECTED),
            occurred_at=_now(),
            summary=rec.title,
        )
        if proceed:
            accepted.append(rec)
    return tuple(accepted)


def _run_review_only(
    platform: Platform,
    ui: Ui,
    session_id: int,
    assessment: ProjectAssessment,
    requirements: tuple[DetectedRequirement, ...],
    options: AnalyzeOptions,
) -> None:
    roadmap = sorted(requirements, key=lambda r: r.confidence, reverse=True)
    lines = ["RECOMMENDED ROADMAP", ""]
    for i, requirement in enumerate(roadmap, start=1):
        lines.append(f"{i}. {requirement.title}")
    lines.append("")
    lines.append("KUBERNETES RECOMMENDATION:")
    lines.append(
        "Required."
        if False
        else (
            "Not currently required for this workload."
            if not options.wants_kubernetes_experience
            else "Not required by the workload; only a learning objective justifies it here."
        )
    )
    ui.present("\n".join(lines))
    for i, requirement in enumerate(roadmap, start=1):
        platform.experience_tracker.record(
            session_id, "Review", f"Prioritized: {requirement.title}", ExperienceState.OBSERVED
        )


def _run_validation_and_build(
    platform: Platform,
    ui: Ui,
    session_id: int,
    plan: ImplementationPlan,
    environment: EnvironmentKind,
    options: AnalyzeOptions,
) -> None:
    for step in plan.steps:
        if step.tool_name == "terraform" and step.operation == "plan":
            params = dict(step.params)
            params["simulate_replace"] = 1 if environment.value == "production" else 0
            step = PlanStep(
                id=step.id,
                title=step.title,
                tool_name=step.tool_name,
                operation=step.operation,
                risk_level=step.risk_level,
                requires_approval=step.requires_approval,
                params=params,
            )
        _run_step(platform, ui, session_id, step, options)


def _run_step(
    platform: Platform, ui: Ui, session_id: int, step: PlanStep, options: AnalyzeOptions
) -> None:
    explanation = _explain_step(step)
    rendered = platform.explanation_service.render(
        explanation, mode=options.mode, depth=options.explanation_depth
    )
    ui.present(rendered)

    if step.tool_name == "terraform" and step.operation == "apply_approved_plan":
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.DEPLOYMENT_STARTED,
            occurred_at=_now(),
            summary="Applying Terraform plan",
        )

    result = platform.tool_service.invoke(step.tool_name, step.operation, step.params)
    ui.present(result.summary)

    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.TOOL_INVOKED,
        occurred_at=_now(),
        summary=f"{step.tool_name}.{step.operation}",
        payload={"success": result.success},
    )

    if step.tool_name == "terraform" and step.operation == "plan":
        summary = analyze_terraform_plan(result.details)
        ui.present(presenters.render_terraform_plan(summary))
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.TERRAFORM_PLAN_COMPLETED,
            occurred_at=_now(),
            summary=summary.reason,
        )
        platform.experience_tracker.record(
            session_id, "Terraform", "Interpreted Terraform plan", ExperienceState.PARTICIPATED
        )

    if step.tool_name == "terraform" and step.operation == "apply_approved_plan":
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.DEPLOYMENT_SUCCEEDED,
            occurred_at=_now(),
            summary="Terraform apply complete",
        )
        platform.experience_tracker.record(
            session_id,
            "Terraform",
            "Approved infrastructure deployment",
            ExperienceState.PARTICIPATED,
        )

    _record_experience_for_step(platform, session_id, step)


def _record_experience_for_step(platform: Platform, session_id: int, step: PlanStep) -> None:
    mapping: dict[tuple[str, str], tuple[str, str]] = {
        ("docker", "build"): ("Docker", "Built image"),
        ("docker", "run"): ("Docker", "Ran container"),
        ("validation", "check_dockerfile_best_practices"): ("Docker", "Reviewed Dockerfile"),
        ("terraform", "fmt"): ("Terraform", "Reviewed generated Terraform"),
        ("terraform", "validate"): ("Terraform", "Validated Terraform configuration"),
        ("kubernetes", "rollout_status"): ("Kubernetes", "Reviewed Deployment rollout"),
        ("kubernetes", "get_pods"): ("Kubernetes", "Reviewed pod status"),
        ("python", "run_tests"): ("Testing", "Ran automated tests"),
        ("python", "run_lint"): ("Testing", "Ran lint checks"),
        ("cloud", "list_resources"): ("Cloud", "Reviewed provisioned resources"),
    }
    entry = mapping.get((step.tool_name, step.operation))
    if entry is not None:
        concept, item = entry
        platform.experience_tracker.record(session_id, concept, item, ExperienceState.PARTICIPATED)


def _explain_step(step: PlanStep) -> Explanation:
    if step.tool_name == "terraform" and step.operation == "apply_approved_plan":
        return Explanation(
            action="Applying the approved Terraform plan.",
            why="This is the step that actually creates or changes cloud infrastructure.",
            decision="Only apply a plan that has already been reviewed above.",
            what_to_understand=(
                "Terraform reconciles the difference between desired state (your .tf files) and "
                "real state (what actually exists); `apply` is what performs that reconciliation."
            ),
        )
    return Explanation(action=step.title)


def _run_health_check_and_troubleshoot(
    platform: Platform, ui: Ui, session_id: int, options: AnalyzeOptions
) -> None:
    failure = platform.troubleshooting_service.gather_evidence()
    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.DEPLOYMENT_FAILED,
        occurred_at=_now(),
        summary=failure.title,
    )
    ui.present(presenters.render_failure(failure))

    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.TROUBLESHOOTING_STARTED,
        occurred_at=_now(),
        summary="Gathering evidence before diagnosing",
    )
    diagnosis = platform.troubleshooting_service.diagnose(failure)
    platform.audit_service.record(
        session_id=session_id,
        event_type=AuditEventType.DIAGNOSIS_PRODUCED,
        occurred_at=_now(),
        summary=diagnosis.likely_cause,
    )
    ui.present(presenters.render_diagnosis(diagnosis))
    platform.experience_tracker.record(
        session_id, "Kubernetes", "Investigated readiness failure", ExperienceState.PARTICIPATED
    )

    if ui.confirm("Apply the recommended fix and roll back the bad rollout?", default=True):
        result = platform.tool_service.invoke("kubernetes", "rollback")
        ui.present(result.summary)
        platform.audit_service.record(
            session_id=session_id,
            event_type=AuditEventType.ROLLBACK_PERFORMED,
            occurred_at=_now(),
            summary=result.summary,
        )
        platform.experience_tracker.record(
            session_id, "Kubernetes", "Performed rollback", ExperienceState.PARTICIPATED
        )


def _print_history_and_experience(platform: Platform, ui: Ui, session_id: int) -> None:
    events = platform.audit_service.history(session_id)
    lines = ["AUDIT HISTORY", ""]
    for event in events:
        lines.append(f"{event.sequence_no:>3}. {event.event_type.value}: {event.summary}")
    ui.present("\n".join(lines))

    grouped = platform.experience_tracker.summary(session_id)
    lines = ["EXPERIENCE SUMMARY", ""]
    for concept, entries in grouped.items():
        lines.append(concept)
        for entry in entries:
            lines.append(f"  \u2713 {entry.item}")
        lines.append("")
    ui.present("\n".join(lines).rstrip())


def _parse_environment(answer: str) -> EnvironmentKind:
    lowered = answer.lower()
    if "production-like" in lowered:
        return EnvironmentKind.STAGING
    if "production" in lowered:
        return EnvironmentKind.PRODUCTION
    return EnvironmentKind.DEV


def _parse_cost_priority(answer: str) -> CostPriority:
    lowered = answer.lower()
    if "cost" in lowered:
        return CostPriority.LOWEST_COST
    if "availability" in lowered:
        return CostPriority.HIGHEST_AVAILABILITY
    return CostPriority.BALANCED


def _now() -> datetime:
    return datetime.now(timezone.utc)
