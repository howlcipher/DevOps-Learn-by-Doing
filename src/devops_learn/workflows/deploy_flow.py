"""One real, security-gated Azure Container Apps deployment lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping
import urllib.error
import urllib.request

from devops_learn.bootstrap import Platform
from devops_learn.deployment.candidate import DeploymentCandidate, sha256_file
from devops_learn.deployment.evidence import write_evidence_report
from devops_learn.domain.enums import (
    AuditEventType,
    CloudProviderKind,
    CostPriority,
    DeploymentEligibility,
    EnvironmentKind,
    ExecutionMode,
    ExperienceState,
    ExplanationDepth,
    LanguageKind,
    SecurityGateDecision,
)
from devops_learn.security.eligibility import evaluate_deployment_eligibility
from devops_learn.tools import _subprocess_safety
from devops_learn.tools.terraform_tool import terraform_config_digest
from devops_learn.validation import terraform_plan_analysis
from devops_learn.workflows.security_flow import SecurityOptions, run_security_scan
from devops_learn.workflows.doctor_flow import collect_doctor_report, render_doctor_report
from devops_learn.workflows.ui import Ui


@dataclass(frozen=True)
class DeployOptions:
    project_root: str
    cloud: str = "azure"
    depth: ExplanationDepth = ExplanationDepth.LEARNING
    location: str = "eastus"
    environment: str = "learning"
    base_ref: str = "origin/main"


def run_deploy_flow(platform: Platform, ui: Ui, options: DeployOptions) -> None:
    """Run bootstrap then application deployment, stopping at every failed gate."""
    project = Path(options.project_root).resolve()
    infra = project / "infra" / "terraform"
    report_path = project / "artifacts" / "deployment" / "azure-deployment-evidence.json"
    stages: dict[str, str] = {}
    observed: dict[str, Any] | None = None
    if options.cloud != "azure" or not infra.is_dir():
        ui.present(
            "This real lifecycle currently supports the bundled Azure Terraform project only."
        )
        return
    session = platform.session_service.start(
        project_root=str(project),
        mode=ExecutionMode.COLLABORATIVE,
        explanation_depth=options.depth,
        cloud=CloudProviderKind.AZURE,
        environment=EnvironmentKind.DEV,
        cost_priority=CostPriority.LOWEST_COST,
        simulation_mode=False,
    )
    assert session.id is not None
    session_id = session.id
    _audit(
        platform,
        session_id,
        AuditEventType.SESSION_STARTED,
        "Real Azure deployment lifecycle started",
    )
    try:
        preflight = _preflight(platform, ui, options)
        if not preflight:
            stages["preflight"] = "NOT EXECUTED: prerequisites or Azure authentication unavailable"
            return
        stages["preflight"] = "REAL PASS"
        if not ui.confirm(
            "Azure resources will be created in the displayed subscription. Continue?",
            default=False,
        ):
            stages["cloud_confirmation"] = "NOT EXECUTED: learner declined"
            return
        stages["cloud_confirmation"] = "APPROVED"

        if not _validation(platform, project):
            stages["application_validation"] = "REAL FAIL"
            return
        stages["application_validation"] = "REAL PASS"
        local_tag = "api-platform:deployment-candidate"
        if not platform.tool_service.invoke(
            "docker",
            "build",
            {
                "context": str(project),
                "dockerfile": str(project / "Dockerfile"),
                "tag": local_tag,
            },
        ).success:
            stages["docker_build"] = "REAL FAIL"
            return
        stages["docker_build"] = "REAL PASS"

        source = _source_identity(project)
        config_digest = terraform_config_digest(infra)
        bootstrap_security = _security(
            platform, ui, project, options, local_tag, "bootstrap", session_id
        )
        if bootstrap_security is None:
            stages["bootstrap_security"] = "REAL FAIL"
            return
        stages["bootstrap_security"] = bootstrap_security[1].value.upper()
        bootstrap = DeploymentCandidate(
            source_revision=source,
            project_path=str(project),
            cloud="azure",
            environment=options.environment,
            terraform_config_digest=config_digest,
            security_report_path=str(bootstrap_security[0]),
            security_report_digest=sha256_file(bootstrap_security[0]),
            security_decision=bootstrap_security[1].value,
            created_at=datetime.now(timezone.utc),
        )
        bootstrap_candidate = _plan_and_gate(
            platform,
            ui,
            infra,
            bootstrap,
            {
                "deploy_application": False,
                "environment": options.environment,
                "location": options.location,
            },
            session_id,
        )
        if bootstrap_candidate is None:
            stages["bootstrap_plan_or_eligibility"] = "REAL FAIL OR NOT APPROVED"
            return
        stages["bootstrap_plan_or_eligibility"] = "REAL APPROVED"
        if not _apply(platform, project, infra, bootstrap_candidate, session_id):
            stages["bootstrap_apply"] = "REAL FAIL OR APPROVAL DENIED"
            return
        stages["bootstrap_apply"] = "REAL PASS"

        outputs = platform.tool_service.invoke("terraform", "output", {"path": str(infra)})
        if not outputs.success:
            stages["bootstrap_outputs"] = "REAL FAIL"
            return
        registry_server = str(outputs.details.get("container_registry_login_server", ""))
        if not registry_server:
            stages["bootstrap_outputs"] = "REAL FAIL: ACR output missing"
            return
        stages["bootstrap_outputs"] = "REAL PASS"
        registry_name = registry_server.split(".", maxsplit=1)[0]
        image_tag = f"{registry_server}/api:{source.split(':', maxsplit=1)[0][:12]}"
        if not platform.tool_service.invoke(
            "azure", "acr_login", {"registry_name": registry_name}
        ).success:
            stages["acr_login"] = "REAL FAIL"
            return
        if (
            not platform.tool_service.invoke(
                "docker",
                "build",
                {
                    "context": str(project),
                    "dockerfile": str(project / "Dockerfile"),
                    "tag": image_tag,
                },
            ).success
            or not platform.tool_service.invoke("docker", "push", {"image": image_tag}).success
        ):
            stages["acr_image_push"] = "REAL FAIL"
            return
        digest_result = platform.tool_service.invoke(
            "docker", "inspect_digest", {"image": image_tag}
        )
        if not digest_result.success:
            stages["image_digest"] = "REAL FAIL"
            return
        image_digest_ref = str(digest_result.details["digest"])
        stages["acr_image_push"] = "REAL PASS"
        stages["image_digest"] = "REAL PASS"

        application_security = _security(
            platform, ui, project, options, image_digest_ref, "application", session_id
        )
        if application_security is None:
            stages["application_security"] = "REAL FAIL"
            return
        stages["application_security"] = application_security[1].value.upper()
        application = DeploymentCandidate(
            source_revision=source,
            project_path=str(project),
            cloud="azure",
            environment=options.environment,
            terraform_config_digest=config_digest,
            image_reference=image_digest_ref,
            image_digest=image_digest_ref.rsplit("@", maxsplit=1)[-1],
            security_report_path=str(application_security[0]),
            security_report_digest=sha256_file(application_security[0]),
            security_decision=application_security[1].value,
            created_at=datetime.now(timezone.utc),
        )
        application_candidate = _plan_and_gate(
            platform,
            ui,
            infra,
            application,
            {
                "deploy_application": True,
                "app_image": image_digest_ref,
                "environment": options.environment,
                "location": options.location,
            },
            session_id,
        )
        if application_candidate is None:
            stages["application_plan_or_eligibility"] = "REAL FAIL OR NOT APPROVED"
            return
        stages["application_plan_or_eligibility"] = "REAL APPROVED"
        if not _apply(platform, project, infra, application_candidate, session_id):
            stages["application_apply"] = "REAL FAIL OR APPROVAL DENIED"
            return
        stages["application_apply"] = "REAL PASS"
        application_outputs = platform.tool_service.invoke(
            "terraform", "output", {"path": str(infra)}
        )
        if not application_outputs.success:
            stages["application_outputs"] = "REAL FAIL"
            return
        stages["application_outputs"] = "REAL PASS"
        observed = _verify_azure(
            platform, application_outputs.details, options, image_digest_ref
        )
        if observed is None:
            stages["azure_verification"] = "REAL FAIL"
            return
        stages["azure_verification"] = "REAL PASS"
        endpoint = str(observed.get("container_app", {}).get("endpoint", ""))
        if not _health_check(endpoint):
            stages["health_verification"] = "REAL FAIL: gather Container App evidence"
            platform.tool_service.invoke(
                "azure",
                "container_app_evidence",
                {
                    "resource_group": application_outputs.details["resource_group_name"],
                    "container_app_name": application_outputs.details["container_app_name"],
                },
            )
            _audit(
                platform,
                session_id,
                AuditEventType.TROUBLESHOOTING_STARTED,
                "Health verification failed; collected Container App revision and log evidence",
                {"candidate_identity": application_candidate.identity},
            )
            return
        stages["health_verification"] = "REAL PASS"
        _audit(
            platform,
            session_id,
            AuditEventType.DEPLOYMENT_SUCCEEDED,
            "Azure Container App health verified",
        )
        for concept in (
            "Azure subscription",
            "ACR",
            "image digest",
            "managed identity",
            "AcrPull",
            "Container Apps",
            "Terraform state",
            "security gate",
            "health checks",
        ):
            platform.experience_tracker.record(
                session_id, concept, "Practiced in real deployment", ExperienceState.PRACTICED
            )
    finally:
        candidate = locals().get("application_candidate", locals().get("bootstrap_candidate", None))
        if isinstance(candidate, DeploymentCandidate):
            write_evidence_report(
                report_path,
                candidate,
                status="completed"
                if stages.get("health_verification") == "REAL PASS"
                else "stopped",
                stages=stages,
                observed_azure=observed,
            )
        platform.session_service.complete(session)
        if report_path.is_file():
            ui.present(f"Sanitized lifecycle evidence: {report_path}")
        else:
            ui.present("No deployment candidate was created; no lifecycle evidence was written.")


def _preflight(platform: Platform, ui: Ui, options: DeployOptions) -> bool:
    doctor = collect_doctor_report(platform)
    if not doctor.azure_deployment_ready:
        ui.present(render_doctor_report(doctor))
        ui.present("AZURE PREFLIGHT FAILED: Azure deployment is not ready.")
        return False
    result = platform.tool_service.invoke(
        "azure", "preflight", {"region": options.location, "environment": options.environment}
    )
    if result.success:
        ui.present(
            (
                "AZURE TARGET\n\nSubscription: {subscription}\nTenant: {tenant}\n"
                "Region: {region}\nEnvironment: {environment}"
            ).format(**result.details)
        )
    else:
        ui.present(result.summary)
    return result.success


def _validation(platform: Platform, project: Path) -> bool:
    assessment = platform.analyzer.analyze(project)
    if assessment.language is LanguageKind.GO:
        return all(
            platform.tool_service.invoke("go", operation, params).success
            for operation, params in (
                ("run_tests", {"path": str(project)}),
                ("run_vet", {"path": str(project)}),
            )
        )
    return all(
        platform.tool_service.invoke("python", operation, params).success
        for operation, params in (
            ("run_tests", {"path": str(project)}),
            ("run_lint", {"path": str(project), "paths": ["."]}),
        )
    )


def _security(
    platform: Platform,
    ui: Ui,
    project: Path,
    options: DeployOptions,
    image: str,
    stage: str,
    session_id: int,
) -> tuple[Path, SecurityGateDecision] | None:
    path = project / "artifacts" / "deployment" / f"security-{stage}.json"
    report = run_security_scan(
        platform, ui, SecurityOptions(str(project), options.base_ref, image, str(path))
    )
    if report is None:
        return None
    _audit(
        platform,
        session_id,
        AuditEventType.SECURITY_GATE_EVALUATED,
        f"{stage.title()} security evidence bound to deployment candidate",
        {
            "report_digest": sha256_file(path),
            "decision": report.policy.decision.value,
            "image": image,
        },
    )
    return path, report.policy.decision


def _plan_and_gate(
    platform: Platform,
    ui: Ui,
    infra: Path,
    candidate: DeploymentCandidate,
    variables: dict[str, object],
    session_id: int,
) -> DeploymentCandidate | None:
    if not platform.tool_service.invoke("terraform", "fmt", {"path": str(infra)}).success:
        return None
    if not platform.tool_service.invoke("terraform", "init", {"path": str(infra)}).success:
        return None
    if not platform.tool_service.invoke("terraform", "validate", {"path": str(infra)}).success:
        return None
    planned = platform.tool_service.invoke(
        "terraform",
        "plan",
        {
            "path": str(infra),
            "source_revision": candidate.source_revision,
            "candidate_context": candidate.context_identity,
            "variables": variables,
        },
    )
    if not planned.success:
        return None
    risk = terraform_plan_analysis.analyze(planned.details).risk_level
    completed = replace(
        candidate,
        terraform_plan_path=str(planned.details["plan_path"]),
        terraform_plan_digest=str(planned.details["plan_digest"]),
        terraform_plan_risk=risk.name,
    )
    security_approval = True
    if candidate.security_decision == SecurityGateDecision.BLOCK.value:
        ui.present("SECURITY BLOCK: deployment stopped.")
        return None
    if candidate.security_decision == SecurityGateDecision.REQUIRE_APPROVAL.value:
        prompt = f"Security approval for candidate {completed.identity[:12]} required. Approve?"
        security_approval = ui.confirm(prompt, default=False)
        if not security_approval:
            eligibility = evaluate_deployment_eligibility(
                validation_passed=True,
                gate=SecurityGateDecision.REQUIRE_APPROVAL,
                approval_granted=False,
            )
            ui.present(
                f"DEPLOYMENT ELIGIBILITY: {eligibility.eligibility.value} ({eligibility.reason})"
            )
            return None
    risk_prompt = (
        f"Terraform plan risk is {risk.name}. "
        f"Approve this exact candidate {completed.identity[:12]}?"
    )
    risk_approval = risk.name not in {"HIGH", "DESTRUCTIVE"} or ui.confirm(
        risk_prompt, default=False
    )
    if not risk_approval:
        ui.present("DEPLOYMENT ELIGIBILITY: ineligible (Terraform plan risk was not approved.)")
        return None
    cloud_action_approval = ui.confirm(
        "Cloud action approval: apply this exact candidate "
        f"{completed.identity[:12]} to Azure?",
        default=False,
    )
    eligibility = evaluate_deployment_eligibility(
        validation_passed=True,
        gate=SecurityGateDecision(candidate.security_decision or "block"),
        approval_granted=security_approval and risk_approval and cloud_action_approval,
    )
    ui.present(
        f"DEPLOYMENT ELIGIBILITY: {eligibility.eligibility.value} ({eligibility.reason})"
    )
    if eligibility.eligibility is DeploymentEligibility.ELIGIBLE:
        approvals: list[str] = []
        if candidate.security_decision == SecurityGateDecision.REQUIRE_APPROVAL.value:
            approvals.append("security")
        if risk.name in {"HIGH", "DESTRUCTIVE"}:
            approvals.append("terraform_plan_risk")
        approvals.append("cloud_action")
        _audit(
            platform,
            session_id,
            AuditEventType.USER_APPROVED_PLAN,
            "Human approved exact deployment candidate",
            {
                "candidate_identity": completed.identity,
                "plan_digest": completed.terraform_plan_digest,
                "security_report_digest": completed.security_report_digest,
                "image_digest": completed.image_digest,
                "approvals": approvals,
            },
        )
        return replace(
            completed,
            deployment_eligibility=eligibility.eligibility.value,
            human_approvals=tuple(approvals),
        )
    return None


def _apply(
    platform: Platform,
    project: Path,
    infra: Path,
    candidate: DeploymentCandidate,
    session_id: int,
) -> bool:
    if (
        not candidate.is_current()
        or candidate.terraform_config_digest != terraform_config_digest(infra)
        or candidate.source_revision != _source_identity(project)
    ):
        _audit(
            platform,
            session_id,
            AuditEventType.DEPLOYMENT_FAILED,
            "Deployment candidate became stale before apply",
            {"candidate_identity": candidate.identity},
        )
        return False
    result = platform.tool_service.invoke(
        "terraform",
        "apply_approved_plan",
        {
            "path": str(infra),
            "plan_path": candidate.terraform_plan_path,
            "candidate_identity": candidate.identity,
            "candidate_context": candidate.context_identity,
            "source_revision": candidate.source_revision,
        },
    )
    _audit(
        platform,
        session_id,
        AuditEventType.TOOL_INVOKED,
        (
            "Approved Terraform apply completed"
            if result.success
            else "Approved Terraform apply failed"
        ),
        {
            "candidate_identity": candidate.identity,
            "plan_digest": candidate.terraform_plan_digest,
            "returncode": result.details.get("returncode"),
            "approved_by": result.approval.approved_by if result.approval else None,
        },
    )
    return result.success


def _verify_azure(
    platform: Platform,
    outputs: Mapping[str, Any],
    options: DeployOptions,
    expected_image: str,
) -> dict[str, Any] | None:
    result = platform.tool_service.invoke(
        "azure",
        "verify_environment",
        {
            "resource_group": outputs["resource_group_name"],
            "acr_name": str(outputs["container_registry_login_server"]).split(".")[0],
            "container_environment_name": outputs["container_app_environment_name"],
            "container_app_name": outputs["container_app_name"],
            "expected_region": options.location,
            "expected_tags": {"environment": options.environment, "managed-by": "terraform"},
            "expected_image": expected_image,
        },
    )
    return dict(result.details) if result.success else None


def _health_check(endpoint: str) -> bool:
    if not endpoint:
        return False
    try:
        with urllib.request.urlopen(f"{endpoint.rstrip('/')}/health", timeout=20) as response:
            return response.status == 200 and "healthy" in response.read().decode("utf-8").lower()
    except (urllib.error.URLError, TimeoutError):
        return False


def _source_identity(project: Path) -> str:
    digest = sha256()
    for path in sorted(
        [
            project / "Dockerfile",
            project / "requirements.txt",
            *project.glob("app/**/*.py"),
            *project.glob("infra/terraform/*.tf"),
            project / "infra/terraform/.terraform.lock.hcl",
        ]
    ):
        if path.is_file():
            digest.update(str(path.relative_to(project)).encode())
            digest.update(path.read_bytes())
    revision = _subprocess_safety.run_safely(
        ["git", "-C", str(project), "rev-parse", "HEAD"], cwd=None, timeout=15
    )
    git_sha = revision.stdout.strip() if revision.returncode == 0 else "no-git-sha"
    return f"{git_sha}:workspace-{digest.hexdigest()}"


def _audit(
    platform: Platform,
    session_id: int,
    event_type: AuditEventType,
    summary: str,
    payload: Mapping[str, Any] | None = None,
) -> None:
    platform.audit_service.record(
        session_id=session_id,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        summary=summary,
        payload=payload,
    )


def run_cleanup_flow(platform: Platform, ui: Ui, options: DeployOptions) -> bool:
    """Destroy the named learning environment only after two human checkpoints."""
    project = Path(options.project_root).resolve()
    infra = project / "infra" / "terraform"
    if not infra.is_dir() or not _preflight(platform, ui, options):
        return False
    outputs = platform.tool_service.invoke("terraform", "output", {"path": str(infra)})
    resource_group = str(outputs.details.get("resource_group_name", ""))
    if not outputs.success or not resource_group:
        ui.present(
            "DESTROY REFUSED: Terraform state does not identify a deployed learning resource group."
        )
        return False
    ui.present(
        "DESTROY TARGET\n\n"
        f"Resource group: {resource_group}\nEnvironment: {options.environment}\n"
        f"State path: {infra / 'terraform.tfstate'}\n"
        "Expected deletion: Container App, Container Apps Environment, managed identity, "
        "AcrPull assignment, ACR, Log Analytics Workspace, Resource Group."
    )
    if not ui.confirm("Destroy this learning environment?", default=False):
        return False
    result = platform.tool_service.invoke(
        "terraform",
        "destroy_approved_environment",
        {
            "path": str(infra),
            "resource_group": resource_group,
            "environment": options.environment,
        },
    )
    if not result.success:
        ui.present(result.summary)
        return False
    verified = platform.tool_service.invoke(
        "azure", "verify_cleanup", {"resource_group": resource_group}
    )
    ui.present(verified.summary)
    return verified.success
