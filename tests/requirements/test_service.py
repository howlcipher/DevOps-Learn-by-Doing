from devops_learn.domain.analysis_models import ProjectAssessment
from devops_learn.domain.enums import LanguageKind, MaturityStatus
from devops_learn.requirements.service import RequirementsService


def _assessment(**overrides: object) -> ProjectAssessment:
    defaults: dict[str, object] = dict(
        root_path="/tmp/x",
        application_type="FastAPI HTTP API",
        language=LanguageKind.PYTHON,
        framework="FastAPI",
        containerization_status=MaturityStatus.MISSING,
        ci_cd_status=MaturityStatus.MISSING,
        iac_status=MaturityStatus.MISSING,
        cloud_status=MaturityStatus.MISSING,
        healthcheck_status=MaturityStatus.GOOD,
        test_status=MaturityStatus.PARTIAL,
        observability_status=MaturityStatus.MISSING,
    )
    defaults.update(overrides)
    return ProjectAssessment(**defaults)  # type: ignore[arg-type]


def test_detects_containerization_and_ci_cd_gaps() -> None:
    requirements = RequirementsService().detect(_assessment())
    ids = {r.id for r in requirements}
    assert "containerization" in ids
    assert "ci_cd" in ids
    assert "iac" in ids


def test_present_capabilities_are_not_flagged_as_requirements() -> None:
    requirements = RequirementsService().detect(
        _assessment(
            containerization_status=MaturityStatus.GOOD,
            ci_cd_status=MaturityStatus.GOOD,
            iac_status=MaturityStatus.GOOD,
        )
    )
    ids = {r.id for r in requirements}
    assert "containerization" not in ids
    assert "ci_cd" not in ids
    assert "iac" not in ids


def test_secret_indicators_produce_a_secret_management_requirement() -> None:
    requirements = RequirementsService().detect(_assessment(secret_indicators=("WEATHER_API_KEY",)))
    assert any(r.id == "secret_management" for r in requirements)
