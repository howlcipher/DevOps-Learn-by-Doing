"""Learner skill profile and knowledge-gap model.

A profile captures uneven expertise: a learner may be strong in Docker and
weak in Terraform. The platform uses this to spend explanation time where
gaps exist, rather than explaining everything equally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CompetencyArea(Enum):
    DOCKER = "docker"
    GIT = "git"
    CI_CD = "ci_cd"
    AZURE = "azure"
    TERRAFORM = "terraform"
    KUBERNETES = "kubernetes"
    NETWORKING = "networking"
    PYTHON = "python"
    GO = "go"
    CLOUD_ARCHITECTURE = "cloud_architecture"
    SECURITY = "security"
    SECRETS = "secrets"
    OBSERVABILITY = "observability"


class ProficiencyLevel(Enum):
    """Ordered from least to most proficient."""

    BEGINNER = "beginner"
    DEVELOPING = "developing"
    WORKING = "working"
    STRONG = "strong"
    EXPERT = "expert"


@dataclass(frozen=True)
class LearnerProfile:
    """A sparse map of declared proficiencies. Missing areas are BEGINNER."""

    proficiencies: dict[CompetencyArea, ProficiencyLevel] = field(default_factory=dict)
    learning_focus: tuple[CompetencyArea, ...] = field(default_factory=tuple)

    def level(self, area: CompetencyArea) -> ProficiencyLevel:
        return self.proficiencies.get(area, ProficiencyLevel.BEGINNER)

    def is_strong(self, area: CompetencyArea) -> bool:
        return self.level(area) in (ProficiencyLevel.STRONG, ProficiencyLevel.EXPERT)

    def is_beginner(self, area: CompetencyArea) -> bool:
        return self.level(area) is ProficiencyLevel.BEGINNER
