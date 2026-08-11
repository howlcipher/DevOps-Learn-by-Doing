"""The composition root: the only place all concrete implementations are wired
together via constructor injection. See docs/adr/0002-modular-monolith.md.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from devops_learn.ai.mock_provider import MockLLMProvider
from devops_learn.ai.provider import LLMProvider
from devops_learn.analysis.project_analyzer import ProjectAnalyzer
from devops_learn.approvals.decision_service import DecisionService
from devops_learn.architecture.service import ArchitectureService
from devops_learn.audit.service import AuditService
from devops_learn.cloud.azure.provider import AzureProvider
from devops_learn.cloud.base.provider import CloudProvider
from devops_learn.experience.tracker import ExperienceTracker
from devops_learn.explanations.service import ExplanationService
from devops_learn.learning.persistence.migrations import ensure_schema
from devops_learn.learning.persistence.repositories.artifact_repository import (
    ArtifactRepository,
)
from devops_learn.learning.persistence.repositories.audit_repository import AuditRepository
from devops_learn.learning.persistence.repositories.decision_repository import (
    DecisionRepository,
)
from devops_learn.learning.persistence.repositories.experience_repository import (
    ExperienceRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository
from devops_learn.learning.session_service import SessionService
from devops_learn.planning.service import PlanningService
from devops_learn.recommendations.service import RecommendationService
from devops_learn.requirements.service import RequirementsService
from devops_learn.questions.service import QuestionService
from devops_learn.tools.approval import ApprovalGate, CliApprovalGate
from devops_learn.tools.cloud_tool import SimulatedCloudTool
from devops_learn.tools.docker_tool import SimulatedDockerTool
from devops_learn.tools.git_tool import SimulatedGitTool
from devops_learn.tools.kubernetes_tool import SimulatedKubernetesTool
from devops_learn.tools.python_tool import SimulatedPythonTool
from devops_learn.tools.service import ToolService
from devops_learn.tools.terraform_tool import SimulatedTerraformTool
from devops_learn.tools.validation_tool import SimulatedValidationTool
from devops_learn.troubleshooting.service import TroubleshootingService


@dataclass
class Platform:
    analyzer: ProjectAnalyzer
    requirements_service: RequirementsService
    question_service: QuestionService
    recommendation_service: RecommendationService
    architecture_service: ArchitectureService
    planning_service: PlanningService
    explanation_service: ExplanationService
    troubleshooting_service: TroubleshootingService
    tool_service: ToolService
    session_service: SessionService
    audit_service: AuditService
    decision_service: DecisionService
    experience_tracker: ExperienceTracker
    artifact_repository: ArtifactRepository
    llm: LLMProvider


def build_platform(
    conn: sqlite3.Connection,
    *,
    llm_provider: LLMProvider | None = None,
    approval_gate: ApprovalGate | None = None,
    cloud_provider: CloudProvider | None = None,
) -> Platform:
    ensure_schema(conn)

    audit_repository = AuditRepository(conn)
    audit_service = AuditService(audit_repository)
    session_service = SessionService(SessionRepository(conn), audit_service)
    decision_service = DecisionService(DecisionRepository(conn))
    experience_tracker = ExperienceTracker(ExperienceRepository(conn))
    artifact_repository = ArtifactRepository(conn)

    llm = llm_provider or MockLLMProvider()
    cloud = cloud_provider or AzureProvider()

    tool_service = ToolService(
        {
            "python": SimulatedPythonTool(),
            "git": SimulatedGitTool(),
            "docker": SimulatedDockerTool(),
            "terraform": SimulatedTerraformTool(),
            "kubernetes": SimulatedKubernetesTool(),
            "cloud": SimulatedCloudTool(),
            "validation": SimulatedValidationTool(),
        },
        approval_gate or CliApprovalGate(),
    )

    return Platform(
        analyzer=ProjectAnalyzer(),
        requirements_service=RequirementsService(),
        question_service=QuestionService(),
        recommendation_service=RecommendationService(),
        architecture_service=ArchitectureService(cloud),
        planning_service=PlanningService(),
        explanation_service=ExplanationService(),
        troubleshooting_service=TroubleshootingService(tool_service),
        tool_service=tool_service,
        session_service=session_service,
        audit_service=audit_service,
        decision_service=decision_service,
        experience_tracker=experience_tracker,
        artifact_repository=artifact_repository,
        llm=llm,
    )
