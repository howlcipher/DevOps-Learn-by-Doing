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


class ExecutionMode(Enum):
    """Who performs the work: a separate axis from ExplanationDepth.

    See docs/adr/0003-human-approval-gates.md and docs/learning-model.md.
    Mode controls how much the human is asked to decide or perform; depth
    controls how detailed any explanation is.
    """

    OBSERVE = "observe"
    GUIDED = "guided"
    COLLABORATIVE = "collaborative"
    AI_EXECUTED = "ai_executed"
    AUTONOMOUS = "autonomous"


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
    """Competency evidence, not certification.

    Progress reflects understanding and judgment, not how many characters the
    learner manually typed. See docs/adr/0008 (renumbered) and
    docs/learning-model.md.
    """

    NOT_STARTED = "not_started"
    INTRODUCED = "introduced"
    GUIDED = "guided"
    PRACTICED = "practiced"
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
    SECURITY_SCAN_STARTED = "security_scan_started"
    SECURITY_SCAN_COMPLETED = "security_scan_completed"
    SECURITY_GATE_EVALUATED = "security_gate_evaluated"
    SECURITY_OVERRIDE_APPROVED = "security_override_approved"
    REMEDIATION_PROPOSED = "remediation_proposed"
    REMEDIATION_APPLIED = "remediation_applied"
    USER_APPROVED_PLAN = "user_approved_plan"
    TOOL_INVOKED = "tool_invoked"
    DEPLOYMENT_STARTED = "deployment_started"
    DEPLOYMENT_SUCCEEDED = "deployment_succeeded"
    DEPLOYMENT_FAILED = "deployment_failed"
    TROUBLESHOOTING_STARTED = "troubleshooting_started"
    DIAGNOSIS_PRODUCED = "diagnosis_produced"
    TROUBLESHOOTING_REMEDIATION_ATTEMPTED = "troubleshooting_remediation_attempted"
    TROUBLESHOOTING_VERIFIED = "troubleshooting_verified"
    TROUBLESHOOTING_FAILED = "troubleshooting_failed"
    TROUBLESHOOTING_COMPLETED = "troubleshooting_completed"
    ROLLBACK_PERFORMED = "rollback_performed"
    SESSION_COMPLETED = "session_completed"


class FindingSeverity(Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingCategory(Enum):
    VULNERABILITY = "vulnerability"
    SECRET = "secret"
    IAC_MISCONFIGURATION = "iac_misconfiguration"
    CONTAINER = "container"
    DEPENDENCY = "dependency"
    IDENTITY = "identity"
    NETWORK = "network"
    KUBERNETES = "kubernetes"
    POLICY = "policy"
    UNKNOWN = "unknown"


class FindingChangeStatus(Enum):
    INTRODUCED = "introduced"
    RESOLVED = "resolved"
    UNCHANGED = "unchanged"
    UNCERTAIN = "uncertain"


class SecurityGateDecision(Enum):
    ALLOW = "allow"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"
    BLOCK = "block"


class RemediationRisk(Enum):
    SAFE_TO_AUTO_FIX = "safe_to_auto_fix"
    REQUIRES_REVIEW = "requires_review"
    REQUIRES_HUMAN_INPUT = "requires_human_input"
    HIGH_RISK = "high_risk"


class DeploymentEligibility(Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    PENDING_APPROVAL = "pending_approval"
