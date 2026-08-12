"""Real Terraform vertical slice: fmt -> init -> validate -> plan -> risk analysis.

Runs RealTerraformTool against a real, committed Terraform working directory
(projects/api_platform/infra/terraform/ by default). Never applies or
destroys -- see docs/roadmap.md (Milestone 3) and docs/safety.md. A plan
failure due to missing Azure credentials is treated as an expected, honest
outcome to teach from, not something to hide.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
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
from devops_learn.domain.explanation_models import Explanation, LearningMoment
from devops_learn.domain.learner_profile_models import CompetencyArea
from devops_learn.domain.plan_models import TerraformPlanSummary
from devops_learn.domain.session_models import EngagementSession
from devops_learn.tools.approval import RiskLevel
from devops_learn.tools.base import ToolResult
from devops_learn.validation import terraform_plan_analysis
from devops_learn.workflows import presenters
from devops_learn.workflows.ui import Ui


@dataclass(frozen=True)
class TerraformOptions:
    project_root: str
    infra_root: str


def run_terraform_flow(
    platform: Platform, ui: Ui, options: TerraformOptions
) -> EngagementSession:
    session = platform.session_service.start(
        project_root=options.project_root,
        mode=ExecutionMode.COLLABORATIVE,
        explanation_depth=ExplanationDepth.LEARNING,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.DEV,
        cost_priority=CostPriority.BALANCED,
        simulation_mode=False,
    )
    assert session.id is not None
    session_id = session.id

    _audit(platform, session_id, AuditEventType.SESSION_STARTED, "Terraform workflow started")

    fmt_result = _run_terraform_step(
        platform, ui, session_id, "fmt", options.infra_root, "Terraform fmt"
    )
    if not fmt_result.success:
        ui.present(
            f"Configuration is not formatted. Run `terraform fmt` in {options.infra_root} "
            "to fix this before continuing."
        )

    _teach_provider_concept(platform, ui, session_id)
    init_result = _run_terraform_step(
        platform, ui, session_id, "init", options.infra_root, "Terraform init"
    )
    if not init_result.success:
        _diagnose_and_stop(platform, ui, session_id, "terraform init failed")
        platform.session_service.complete(session)
        return session

    validate_result = _run_terraform_step(
        platform, ui, session_id, "validate", options.infra_root, "Terraform validate"
    )
    if not validate_result.success:
        _diagnose_and_stop(platform, ui, session_id, "terraform validate failed")
        platform.session_service.complete(session)
        return session

    _teach_state_concepts(platform, ui, session_id)
    _audit(platform, session_id, AuditEventType.TERRAFORM_PLAN_STARTED, "Terraform plan started")
    plan_result = _run_terraform_step(
        platform, ui, session_id, "plan", options.infra_root, "Terraform plan"
    )
    if not plan_result.success:
        _diagnose_plan_failure(platform, ui, session_id, plan_result)
        platform.session_service.complete(session)
        return session

    summary = terraform_plan_analysis.analyze(plan_result.details)
    ui.present(presenters.render_terraform_plan(summary))
    _audit(platform, session_id, AuditEventType.TERRAFORM_PLAN_COMPLETED, summary.reason)
    _explain(platform, ui, "What to check", _what_to_check_explanation(summary))

    platform.experience_tracker.record(
        session_id, "Terraform", "Ran real fmt/init/validate/plan", ExperienceState.PRACTICED
    )
    platform.experience_tracker.record(
        session_id, "Azure", "Reviewed a real Azure resource plan", ExperienceState.INTRODUCED
    )

    _print_history_and_experience(platform, ui, session_id)
    platform.session_service.complete(session)
    return session


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


def _run_terraform_step(
    platform: Platform,
    ui: Ui,
    session_id: int,
    operation: str,
    infra_root: str,
    label: str,
) -> ToolResult:
    _explain(platform, ui, label, _terraform_explanation(operation))
    result = platform.tool_service.invoke("terraform", operation, {"path": infra_root})
    ui.present(result.summary)
    _audit(
        platform,
        session_id,
        AuditEventType.TOOL_INVOKED,
        f"terraform.{operation}",
        {"success": result.success},
    )
    return result


def _diagnose_and_stop(
    platform: Platform, ui: Ui, session_id: int, context: str
) -> None:
    ui.present(f"{context}. Diagnosis starts from the output above.")
    _audit(platform, session_id, AuditEventType.DEPLOYMENT_FAILED, context)
    platform.experience_tracker.record(
        session_id, "Troubleshooting", f"Investigated {context}", ExperienceState.INTRODUCED
    )


def _diagnose_plan_failure(
    platform: Platform, ui: Ui, session_id: int, result: ToolResult
) -> None:
    stderr = str(result.details.get("stderr", "")).lower()
    is_auth_failure = "az login" in stderr or "authoriz" in stderr or "authent" in stderr
    if is_auth_failure:
        ui.present(
            "DIAGNOSIS: terraform plan failed because Terraform could not authenticate to "
            "Azure. The azurerm provider needs credentials to build API requests, even for a "
            "read-only plan.\n\n"
            "Fix by doing ONE of:\n"
            "  - `az login` (uses your interactive Azure CLI session), or\n"
            "  - setting ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, and "
            "ARM_SUBSCRIPTION_ID for a service principal.\n\n"
            "This is an expected, honest failure on a machine with no Azure credentials -- "
            "not a bug. See docs/safety.md."
        )
    else:
        ui.present("terraform plan failed. Diagnosis starts from the output above.")
    _audit(platform, session_id, AuditEventType.DEPLOYMENT_FAILED, "terraform plan failed")
    platform.experience_tracker.record(
        session_id,
        "Troubleshooting",
        "Diagnosed a terraform plan authentication failure"
        if is_auth_failure
        else "Diagnosed a terraform plan failure",
        ExperienceState.PRACTICED,
    )


def _should_teach(platform: Platform) -> bool:
    profile = platform.learner_profile_service.load()
    return not profile.is_strong(CompetencyArea.TERRAFORM)


def _teach_state_concepts(platform: Platform, ui: Ui, session_id: int) -> None:
    if not _should_teach(platform):
        return
    moment = LearningMoment(
        concept="Terraform state",
        trigger="before running terraform plan",
        summary=(
            "Terraform tracks the infrastructure it manages in a state file. State is "
            "Terraform's record of what it believes exists; the real Azure resources are the "
            "ground truth, and the two can drift apart."
        ),
        deep_explanation=(
            "Every managed resource gets an address (e.g. azurerm_resource_group.main) "
            "recorded in state alongside the real Azure resource ID it maps to. Terraform "
            "diffs your configuration against state, then confirms that against Azure during "
            "plan/apply. State can contain resource attribute values, including sensitive "
            "ones, which is why it is never committed to git (see .gitignore) -- and why "
            "deleting a state file does NOT delete the real Azure resources; it only makes "
            "Terraform forget about them."
        ),
        why_it_matters=(
            "Understanding state is the difference between reading a `terraform plan` and "
            "actually knowing what it will do."
        ),
        related_artifact="docs/terraform-state.md",
    )
    _render_learning_moment(platform, ui, moment)
    platform.experience_tracker.record(
        session_id,
        "Terraform state",
        "Explained desired vs. actual state",
        ExperienceState.INTRODUCED,
    )


def _teach_provider_concept(platform: Platform, ui: Ui, session_id: int) -> None:
    if not _should_teach(platform):
        return
    moment = LearningMoment(
        concept="Terraform provider",
        trigger="before running terraform init",
        summary=(
            "A provider is the plugin Terraform uses to talk to a specific platform -- here, "
            "the azurerm provider talks to Azure's Resource Manager API. `terraform init` "
            "downloads it."
        ),
        deep_explanation=(
            "A resource block's type prefix (azurerm_) tells Terraform which provider owns it "
            "and which real API calls to make. A resource address like "
            "azurerm_resource_group.main combines the resource type and a local name; "
            "Terraform uses addresses to track dependencies between resources, such as the "
            "container registry needing the resource group to exist first."
        ),
        why_it_matters=(
            "init failing almost always means a provider or network problem, not a mistake in "
            "your .tf files -- a different failure mode than validate or plan."
        ),
        related_artifact="docs/terraform-state.md",
    )
    _render_learning_moment(platform, ui, moment)
    platform.experience_tracker.record(
        session_id,
        "Terraform",
        "Explained provider and resource address",
        ExperienceState.INTRODUCED,
    )


def _render_learning_moment(platform: Platform, ui: Ui, moment: LearningMoment) -> None:
    rendered = platform.explanation_service.render_learning_moment(
        moment, mode=ExecutionMode.COLLABORATIVE, depth=ExplanationDepth.LEARNING
    )
    if rendered:
        ui.present(rendered)


def _explain(platform: Platform, ui: Ui, label: str, explanation: Explanation) -> None:
    rendered = platform.explanation_service.render(
        explanation, mode=ExecutionMode.COLLABORATIVE, depth=ExplanationDepth.LEARNING
    )
    ui.present(rendered)


def _terraform_explanation(operation: str) -> Explanation:
    if operation == "fmt":
        return Explanation(
            action="Checking Terraform formatting.",
            why="Consistent formatting makes configuration easy to review and diff.",
        )
    if operation == "init":
        return Explanation(
            action="Initializing the Terraform working directory.",
            why=(
                "Terraform must download the azurerm provider before it can validate, plan, "
                "or apply anything."
            ),
            what_to_understand=(
                "init also creates a local .terraform/ plugin cache, which is never committed "
                "to git -- it is regenerated by running init again."
            ),
        )
    if operation == "validate":
        return Explanation(
            action="Validating the configuration.",
            why="Validate catches syntax and type errors locally, before Terraform talks to Azure.",
        )
    return Explanation(
        action="Running terraform plan.",
        why="Plan shows exactly what Terraform would change, without changing anything yet.",
        what_to_understand=(
            "Plan compares your configuration against Terraform's state file, then confirms "
            "that against Azure. It requires Azure authentication even though it makes no "
            "changes."
        ),
    )


def _what_to_check_explanation(summary: TerraformPlanSummary) -> Explanation:
    if summary.risk_level is RiskLevel.DESTRUCTIVE:
        result = (
            "This plan would destroy real resources. Never approve an apply from a plan like "
            "this without independently confirming that destruction is intended."
        )
    elif summary.risk_level is RiskLevel.HIGH:
        result = (
            "Terraform must destroy and recreate at least one resource. Confirm you "
            "understand *why* before ever approving an apply: is the resource stateful, "
            "would its address or endpoint change, and would that cause downtime?"
        )
    elif summary.risk_level is RiskLevel.LOW:
        result = "Confirm the in-place changes match what you intended to modify."
    else:
        result = (
            "Confirm the resource names in this plan won't collide with anything already in "
            "the target subscription."
        )
    return Explanation(
        action="Reviewing what this plan means before any apply.",
        what_to_understand=(
            "Terraform state can drift from real infrastructure if something changes "
            "resources outside Terraform. A plan is only trustworthy if state and Azure "
            "haven't drifted apart."
        ),
        result=result,
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
            lines.append(f"  ✓ {entry.item}")
        lines.append("")
    ui.present("\n".join(lines).rstrip())


def _now() -> datetime:
    return datetime.now(timezone.utc)
