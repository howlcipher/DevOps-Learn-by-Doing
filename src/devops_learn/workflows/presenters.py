"""Pure text rendering for ProjectAssessment/Recommendation/ArchitectureProposal.

Kept separate from workflows/analyze_flow.py's control flow so a future web UI
can reuse these renderers (or ignore them and render the same domain objects
its own way) without depending on the workflow's I/O.
"""

from __future__ import annotations

from devops_learn.domain.analysis_models import ProjectAssessment
from devops_learn.domain.architecture_models import ArchitectureProposal
from devops_learn.domain.plan_models import TerraformPlanSummary
from devops_learn.domain.recommendation_models import Recommendation
from devops_learn.domain.requirements_models import DetectedRequirement
from devops_learn.domain.troubleshooting_models import Diagnosis, FailureEvent


def render_assessment(assessment: ProjectAssessment) -> str:
    lines = [
        "PROJECT ASSESSMENT",
        "",
        "Application:",
        assessment.application_type,
        "",
        "Detected:",
        f"- Language: {assessment.language.value}",
        f"- Docker support: {_status(assessment.containerization_status)}",
        f"- CI/CD: {_status(assessment.ci_cd_status)}",
        f"- Infrastructure as Code: {_status(assessment.iac_status)}",
        f"- Cloud deployment: {_status(assessment.cloud_status)}",
        f"- Health endpoint: {_status(assessment.healthcheck_status)}",
        f"- Tests: {_status(assessment.test_status)}",
        f"- Observability: {_status(assessment.observability_status)}",
    ]
    if assessment.database_dependencies:
        lines.append(f"- Database dependency: {', '.join(assessment.database_dependencies)}")
    lines.append(
        f"- Configuration: {assessment.env_var_count} environment variable(s), "
        f"{len(assessment.secret_indicators)} likely secret(s)"
    )
    if assessment.security_findings:
        lines.append("")
        lines.append("SECURITY FINDINGS")
        for finding in assessment.security_findings:
            lines.append(f"- {finding}")
    if assessment.assumptions:
        lines.append("")
        lines.append("ASSUMPTIONS")
        for assumption in assessment.assumptions:
            lines.append(f"- {assumption.text} (confidence: {assumption.confidence:.0%})")
    return "\n".join(lines)


def render_requirements(requirements: tuple[DetectedRequirement, ...]) -> str:
    if not requirements:
        return "No additional DevOps requirements were detected."
    lines = ["DEVOPS ASSESSMENT", "", "Likely production requirements:"]
    for r in requirements:
        tag = " (assumption)" if r.is_assumption else ""
        lines.append(f"- {r.title}{tag}: {r.rationale}")
    return "\n".join(lines)


def render_recommendation(rec: Recommendation) -> str:
    lines = [
        f"RECOMMENDATION: {rec.title}",
        "",
        rec.recommendation,
        "",
        f"WHY: {rec.reason}",
    ]
    if rec.engineering_need:
        lines.append(f"ENGINEERING NEED: {rec.engineering_need}")
    if rec.learning_value:
        lines.append(f"LEARNING VALUE: {rec.learning_value}")
    if rec.alternatives:
        lines.append("")
        lines.append("ALTERNATIVES")
        for alt in rec.alternatives:
            lines.append(f"- {alt.option}: {alt.why_not_preferred}")
    for label, value in (
        ("COST IMPACT", rec.cost_impact),
        ("SECURITY IMPACT", rec.security_impact),
        ("RELIABILITY IMPACT", rec.reliability_impact),
        ("COMPLEXITY IMPACT", rec.complexity_impact),
    ):
        if value:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def render_architecture(proposal: ArchitectureProposal) -> str:
    lines = [
        "ARCHITECTURE RECOMMENDATION",
        "",
        " -> ".join(proposal.pipeline),
        "",
    ]
    if proposal.terraform_resources:
        lines.append("Terraform provisions:")
        for resource in proposal.terraform_resources:
            lines.append(f"- {resource}")
        lines.append("")
    lines.append(f"Kubernetes: {proposal.kubernetes_need.value}")
    if proposal.simpler_alternative:
        lines.append("")
        lines.append("IMPORTANT")
        lines.append(proposal.simpler_alternative)
    if proposal.learning_rationale:
        lines.append("")
        lines.append(f"LEARNING OBJECTIVE: {proposal.learning_rationale}")
    return "\n".join(lines)


def render_terraform_plan(summary: TerraformPlanSummary) -> str:
    from devops_learn.domain.enums import ChangeAction

    lines = [
        "TERRAFORM PLAN",
        "",
        f"Create: {summary.count(ChangeAction.CREATE)}",
        f"Modify: {summary.count(ChangeAction.UPDATE)}",
        f"Replace: {summary.count(ChangeAction.REPLACE)}",
        f"Destroy: {summary.count(ChangeAction.DESTROY)}",
        "",
        f"Risk: {summary.risk_level.name}",
        "",
        f"Reason: {summary.reason}",
    ]
    return "\n".join(lines)


def render_failure(failure: FailureEvent) -> str:
    lines = [f"DEPLOYMENT ISSUE: {failure.title}", "", failure.narrative, "", "EVIDENCE GATHERED:"]
    for item in failure.evidence:
        lines.append(f"- [{item.source}] {item.content}")
    return "\n".join(lines)


def render_diagnosis(diagnosis: Diagnosis) -> str:
    lines = [
        f"DIAGNOSIS: {diagnosis.likely_cause}",
        "",
        diagnosis.explanation,
        "",
        f"RECOMMENDED FIX: {diagnosis.recommended_fix}",
    ]
    if diagnosis.learning_moment:
        lines.append("")
        lines.append(f"LEARNING MOMENT: {diagnosis.learning_moment}")
    return "\n".join(lines)


def _status(status: object) -> str:
    return str(getattr(status, "value", status)).replace("_", " ")
