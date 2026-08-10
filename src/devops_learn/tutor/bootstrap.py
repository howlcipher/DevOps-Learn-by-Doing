"""The composition root: the only place all concrete implementations are wired
together via constructor injection. See docs/adr/0002-modular-monolith.md.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from devops_learn.ai.provider import LLMProvider
from devops_learn.ai.mock_provider import MockLLMProvider
from devops_learn.assessments.service import AssessmentService
from devops_learn.competencies.service import CompetencyService
from devops_learn.curriculum.service import CurriculumService
from devops_learn.learning.journal import LearningJournal
from devops_learn.learning.persistence.migrations import ensure_schema
from devops_learn.learning.persistence.repositories.artifact_repository import (
    ArtifactRepository,
)
from devops_learn.learning.persistence.repositories.competency_repository import (
    CompetencyRepository,
)
from devops_learn.learning.persistence.repositories.event_repository import EventRepository
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)
from devops_learn.learning.persistence.repositories.session_repository import SessionRepository
from devops_learn.learning.persistence.repositories.task_attempt_repository import (
    TaskAttemptRepository,
)
from devops_learn.learning.session_service import SessionService
from devops_learn.learning.summary_service import SummaryService
from devops_learn.projects.service import ProjectService
from devops_learn.recommendations.service import RecommendationService
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
from devops_learn.tutor.orchestrator import TutorOrchestrator


@dataclass
class Platform:
    orchestrator: TutorOrchestrator
    curriculum_service: CurriculumService
    session_service: SessionService
    profile_repository: LearnerProfileRepository
    competency_repository: CompetencyRepository
    summary_service: SummaryService
    llm: LLMProvider


def build_platform(
    conn: sqlite3.Connection,
    *,
    llm_provider: LLMProvider | None = None,
    approval_gate: ApprovalGate | None = None,
) -> Platform:
    ensure_schema(conn)

    event_repository = EventRepository(conn)
    journal = LearningJournal(event_repository)
    session_repository = SessionRepository(conn)
    competency_repository = CompetencyRepository(conn)
    task_attempt_repository = TaskAttemptRepository(conn)
    artifact_repository = ArtifactRepository(conn)

    curriculum_service = CurriculumService()
    session_service = SessionService(session_repository, journal)
    competency_service = CompetencyService(competency_repository, journal)

    llm = llm_provider or MockLLMProvider()
    assessment_service = AssessmentService(llm, competency_service)
    recommendation_service = RecommendationService(llm, curriculum_service, competency_service)
    troubleshooting_service = TroubleshootingService(
        task_attempt_repository, journal, competency_service
    )

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
    project_service = ProjectService(tool_service, artifact_repository, journal)

    orchestrator = TutorOrchestrator(
        curriculum=curriculum_service,
        assessment=assessment_service,
        recommendation=recommendation_service,
        competency=competency_service,
        troubleshooting=troubleshooting_service,
        project=project_service,
        tool=tool_service,
        llm=llm,
        session=session_service,
        journal=journal,
        task_attempt_repository=task_attempt_repository,
    )

    return Platform(
        orchestrator=orchestrator,
        curriculum_service=curriculum_service,
        session_service=session_service,
        profile_repository=LearnerProfileRepository(conn),
        competency_repository=competency_repository,
        summary_service=SummaryService(competency_repository, event_repository),
        llm=llm,
    )
