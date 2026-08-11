"""LearnerProfile lifecycle: load, save, and map between CLI strings and enums."""

from __future__ import annotations

from devops_learn.domain.learner_profile_models import (
    CompetencyArea,
    LearnerProfile,
    ProficiencyLevel,
)
from devops_learn.learning.persistence.repositories.learner_profile_repository import (
    LearnerProfileRepository,
)


class LearnerProfileService:
    def __init__(self, repository: LearnerProfileRepository) -> None:
        self._repository = repository

    def load(self) -> LearnerProfile:
        return self._repository.load() or LearnerProfile()

    def save(self, profile: LearnerProfile) -> LearnerProfile:
        return self._repository.save(profile)

    @staticmethod
    def parse_area(text: str) -> CompetencyArea:
        normalized = text.strip().lower().replace("-", "_")
        mapping = {
            "docker": CompetencyArea.DOCKER,
            "git": CompetencyArea.GIT,
            "cicd": CompetencyArea.CI_CD,
            "ci_cd": CompetencyArea.CI_CD,
            "ci/cd": CompetencyArea.CI_CD,
            "azure": CompetencyArea.AZURE,
            "terraform": CompetencyArea.TERRAFORM,
            "kubernetes": CompetencyArea.KUBERNETES,
            "k8s": CompetencyArea.KUBERNETES,
            "networking": CompetencyArea.NETWORKING,
            "python": CompetencyArea.PYTHON,
            "go": CompetencyArea.GO,
            "golang": CompetencyArea.GO,
            "cloud_architecture": CompetencyArea.CLOUD_ARCHITECTURE,
            "architecture": CompetencyArea.CLOUD_ARCHITECTURE,
            "security": CompetencyArea.SECURITY,
            "secrets": CompetencyArea.SECRETS,
            "observability": CompetencyArea.OBSERVABILITY,
        }
        if normalized not in mapping:
            raise ValueError(f"Unknown competency area: {text}")
        return mapping[normalized]

    @staticmethod
    def parse_level(text: str) -> ProficiencyLevel:
        normalized = text.strip().lower()
        mapping = {
            "beginner": ProficiencyLevel.BEGINNER,
            "developing": ProficiencyLevel.DEVELOPING,
            "working": ProficiencyLevel.WORKING,
            "strong": ProficiencyLevel.STRONG,
            "expert": ProficiencyLevel.EXPERT,
        }
        if normalized not in mapping:
            raise ValueError(f"Unknown proficiency level: {text}")
        return mapping[normalized]
