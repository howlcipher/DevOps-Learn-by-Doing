from pathlib import Path

from devops_learn.analysis.project_analyzer import ProjectAnalyzer
from devops_learn.domain.enums import LanguageKind, MaturityStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
API_PLATFORM = REPO_ROOT / "projects" / "api_platform"


def test_analyzes_the_bundled_example_project() -> None:
    assessment = ProjectAnalyzer().analyze(API_PLATFORM)
    assert assessment.language is LanguageKind.PYTHON
    assert assessment.framework == "FastAPI"
    assert assessment.containerization_status is MaturityStatus.GOOD
    assert assessment.healthcheck_status is MaturityStatus.GOOD
    assert assessment.ci_cd_status is MaturityStatus.MISSING
    # projects/api_platform/infra/terraform/ is real Terraform config as of Milestone 2
    # (docs/roadmap.md) -- ProjectAnalyzer correctly detects it.
    assert assessment.iac_status is MaturityStatus.GOOD


def test_detects_missing_everything_for_an_empty_project(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")
    assessment = ProjectAnalyzer().analyze(tmp_path)
    assert assessment.containerization_status is MaturityStatus.MISSING
    assert assessment.ci_cd_status is MaturityStatus.MISSING
    assert assessment.test_status is MaturityStatus.MISSING


def test_flags_a_hardcoded_secret(tmp_path: Path) -> None:
    (tmp_path / "config.py").write_text('API_KEY = "sk-abcdef123456"\n')
    assessment = ProjectAnalyzer().analyze(tmp_path)
    assert assessment.security_findings
