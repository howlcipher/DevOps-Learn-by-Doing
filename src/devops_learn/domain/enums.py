"""Shared enumerations for the platform's domain model.

ExplanationDepth is an IntEnum so depth-gated rendering can express threshold
comparisons instead of duplicating branch logic per value. RiskLevel for tool
operations lives in tools/approval.py, not here, so approval gating has no
dependency on the rest of the domain model; recommendation/plan risk reuses
that same enum rather than introducing a second, near-duplicate taxonomy.
"""

from __future__ import annotations

from enum import Enum, IntEnum


class CloudProviderKind(Enum):
    AZURE = "azure"
    AWS = "aws"
    GCP = "gcp"


class LanguageKind(Enum):
    PYTHON = "python"
    GO = "go"
    UNKNOWN = "unknown"


class OperatingMode(Enum):
    """How much the human is asked to decide versus have explained to them.

    See docs/adr/0003-human-approval-gates.md. This is orthogonal to
    ExplanationDepth: a mode controls how much interaction happens, a depth
    controls how deeply any given explanation goes.
    """

    LEARN = "learn"
    COLLABORATE = "collaborate"
    AUTOPILOT = "autopilot"
    REVIEW = "review"


class ExplanationDepth(IntEnum):
    """Ordered from least elaboration to most."""

    BRIEF = 1
    NORMAL = 2
    LEARNING = 3
    DEEP = 4


class MaturityStatus(Enum):
    """A category's current state, used throughout ProjectAssessment and Review Mode."""

    MISSING = "missing"
    PARTIAL = "partial"
    GOOD = "good"
    HIGH_RISK = "high_risk"
    UNKNOWN = "unknown"


class KubernetesNeed(Enum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"
    LEARNING_ONLY = "learning_only"
    NOT_RECOMMENDED = "not_recommended"


class RecommendationCategory(Enum):
    ARCHITECTURE = "architecture"
    CLOUD = "cloud"
    NETWORKING = "networking"
    COMPUTE = "compute"
    KUBERNETES = "kubernetes"
    TERRAFORM = "terraform"
    CI_CD = "ci_cd"
    SECURITY = "security"
    SECRETS = "secrets"
    IDENTITY = "identity"
    DATABASE = "database"
    OBSERVABILITY = "observability"
    RELIABILITY = "reliability"
    COST = "cost"
    DEPLOYMENT = "deployment"
    ROLLBACK = "rollback"
    LEARNING = "learning"


class ChangeAction(Enum):
    """How a Terraform plan affects one resource, so CREATE/UPDATE/REPLACE/DESTROY are
    never conflated when assessing plan risk."""

    CREATE = "create"
    UPDATE = "update"
    REPLACE = "replace"
    DESTROY = "destroy"


class EnvironmentKind(Enum):
    LOCAL = "local"
    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class CostPriority(Enum):
    LOWEST_COST = "lowest_cost"
    BALANCED = "balanced"
    HIGHEST_AVAILABILITY = "highest_availability"


class DecisionOutcome(Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    DEFERRED = "deferred"


class ExperienceState(Enum):
    """An evidence log, not a certification: see docs/adr/0008 (renumbered) ->
    experience is what the user was actually exposed to or did, nothing more."""

    NOT_SEEN = "not_seen"
    EXPLAINED = "explained"
    OBSERVED = "observed"
    PARTICIPATED = "participated"
    DEMONSTRATED = "demonstrated"


class AuditEventType(Enum):
    """Names for entries in the append-only audit log. See docs/safety.md."""

    SESSION_STARTED = "session_started"
    PROJECT_ANALYZED = "project_analyzed"
    REQUIREMENT_DETECTED = "requirement_detected"
    QUESTION_ASKED = "question_asked"
    USER_DECISION = "user_decision"
    RECOMMENDATION_CREATED = "recommendation_created"
    USER_APPROVED = "user_approved"
    USER_REJECTED = "user_rejected"
    ARCHITECTURE_PROPOSED = "architecture_proposed"
    PLAN_CREATED = "plan_created"
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    TERRAFORM_PLAN_STARTED = "terraform_plan_started"
    TERRAFORM_PLAN_COMPLETED = "terraform_plan_completed"
    USER_APPROVED_PLAN = "user_approved_plan"
    TOOL_INVOKED = "tool_invoked"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_SUCCEEDED = "deployment_succeeded"
    DEPLOYMENT_FAILED = "deployment_failed"
    TROUBLESHOOTING_STARTED = "troubleshooting_started"
    DIAGNOSIS_PRODUCED = "diagnosis_produced"
    ROLLBACK_PERFORMED = "rollback_performed"
    SESSION_COMPLETED = "session_completed"
