"""Structured output of inspecting a real repository: see analysis/project_analyzer.py.

ProjectAssessment is deliberately flat and serializable so it can be printed,
journaled, and handed to RequirementsService/RecommendationService without
re-walking the filesystem. Findings that are inferred rather than observed are
carried as Assumption, never presented as fact.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.domain.enums import LanguageKind, MaturityStatus


@dataclass(frozen=True)
class Assumption:
    text: str
    confidence: float  # 0.0-1.0; see docs/architecture.md#confidence


@dataclass(frozen=True)
class ProjectAssessment:
    root_path: str
    application_type: str
    language: LanguageKind
    framework: str | None
    containerization_status: MaturityStatus
    ci_cd_status: MaturityStatus
    iac_status: MaturityStatus
    cloud_status: MaturityStatus
    healthcheck_status: MaturityStatus
    test_status: MaturityStatus
    observability_status: MaturityStatus
    database_dependencies: tuple[str, ...] = field(default_factory=tuple)
    secret_indicators: tuple[str, ...] = field(default_factory=tuple)
    env_var_count: int = 0
    security_findings: tuple[str, ...] = field(default_factory=tuple)
    operational_risks: tuple[str, ...] = field(default_factory=tuple)
    assumptions: tuple[Assumption, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)
