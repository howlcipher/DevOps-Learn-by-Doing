"""Shared enumerations for the learning domain model.

AssistanceLevel and ExplanationDepth are IntEnum so curriculum rendering rules
(see curriculum/renderer.py) can express threshold comparisons instead of
duplicating branch logic per value.
"""

from __future__ import annotations

from enum import Enum, IntEnum, auto


class CloudProviderKind(Enum):
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"


class LanguageTrackKind(Enum):
    PYTHON = "python"
    GO = "go"


class AssistanceLevel(IntEnum):
    """Ordered from most AI support to least."""

    GUIDED = 1
    ASSISTED = 2
    CHALLENGE = 3
    INDEPENDENT = 4


class ExplanationDepth(IntEnum):
    """Ordered from least elaboration to most."""

    BRIEF = 1
    NORMAL = 2
    LEARNING = 3
    DEEP = 4


class CompetencyCode(Enum):
    PYTHON_BASICS = "python_basics"
    HTTP_API = "http_api"
    GIT = "git"
    TESTING = "testing"
    DOCKER = "docker"
    CI_CD = "ci_cd"
    TERRAFORM = "terraform"
    TERRAFORM_STATE = "terraform_state"
    CLOUD_NETWORKING = "cloud_networking"
    IAM = "iam"
    SECRETS = "secrets"
    KUBERNETES_PODS = "kubernetes_pods"
    KUBERNETES_DEPLOYMENTS = "kubernetes_deployments"
    KUBERNETES_SERVICES = "kubernetes_services"
    KUBERNETES_PROBES = "kubernetes_probes"
    OBSERVABILITY = "observability"
    TROUBLESHOOTING = "troubleshooting"
    ROLLBACK = "rollback"


class CompetencyState(IntEnum):
    """Ordered progression. DEMONSTRATED requires learner success, never mere viewing."""

    NOT_STARTED = 0
    INTRODUCED = 1
    GUIDED = 2
    PRACTICED = 3
    DEMONSTRATED = 4


class LearningEventType(Enum):
    SESSION_STARTED = "session_started"
    SESSION_RESUMED = "session_resumed"
    LESSON_STARTED = "lesson_started"
    CONCEPT_INTRODUCED = "concept_introduced"
    QUESTION_ANSWERED = "question_answered"
    TASK_ATTEMPTED = "task_attempted"
    TASK_COMPLETED = "task_completed"
    HINT_REQUESTED = "hint_requested"
    ERROR_MADE = "error_made"
    DIAGNOSIS_ATTEMPTED = "diagnosis_attempted"
    COMPETENCY_ADVANCED = "competency_advanced"
    PROJECT_ARTIFACT_CREATED = "project_artifact_created"
    MODULE_COMPLETED = "module_completed"


class SessionStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class TaskOutcome(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ContentBlockKind(Enum):
    WHY = auto()
    WHAT = auto()
    HOW = auto()
    DETAIL = auto()
    ANALOGY = auto()
    PITFALL = auto()
    CHECK_QUESTION = auto()
    NEXT_STEP_MENU = auto()


class HumanControl(Enum):
    """Shared vocabulary for learner-facing controls.

    A single dispatch table (see cli/session_loop.py) maps each member to one
    TutorOrchestrator method, so menu handling is not re-implemented per screen.
    """

    EXPLAIN = "explain"
    WHY = "why"
    GO_DEEPER = "go_deeper"
    SHOW_ALTERNATIVES = "show_alternatives"
    GIVE_HINT = "give_hint"
    LET_ME_TRY = "let_me_try"
    REVIEW_MY_ANSWER = "review_my_answer"
    SHOW_EXPECTED_RESULT = "show_expected_result"
    DO_IT_FOR_ME = "do_it_for_me"
    UNDO = "undo"
    SKIP = "skip"
    CONTINUE = "continue"
