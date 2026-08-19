from pathlib import Path

from devops_learn.analysis.project_analyzer import ProjectAnalyzer
from devops_learn.domain.enums import LanguageKind, MaturityStatus

REPO_ROOT = Path(__file__).resolve().parents[2]
API_PLATFORM = REPO_ROOT / "projects" / "api_platform"
GO_SERVICE = REPO_ROOT / "projects" / "go_service"


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


def test_analyzes_the_bundled_go_service() -> None:
    assessment = ProjectAnalyzer().analyze(GO_SERVICE)
    assert assessment.language is LanguageKind.GO
    assert assessment.framework == "net/http"
    assert assessment.containerization_status is MaturityStatus.GOOD
    assert assessment.healthcheck_status is MaturityStatus.GOOD
    assert assessment.test_status is MaturityStatus.GOOD
    assert assessment.observability_status is MaturityStatus.PARTIAL
    assert "WEATHER_API_KEY" in assessment.secret_indicators


def test_generic_go_detection_without_special_cased_folder_name(tmp_path: Path) -> None:
    custom_dir = tmp_path / "arbitrary_random_backend_name"
    custom_dir.mkdir()
    (custom_dir / "server.go").write_text(
        'package main\n\nimport "net/http"\n\nfunc main() {}\n'
    )
    assessment = ProjectAnalyzer().analyze(custom_dir)
    assert assessment.language is LanguageKind.GO
    assert assessment.framework == "net/http"


def test_generic_go_detection_with_gomod(tmp_path: Path) -> None:
    custom_dir = tmp_path / "microservice_xyz"
    custom_dir.mkdir()
    (custom_dir / "go.mod").write_text("module example.com/xyz\n\ngo 1.22\n")
    (custom_dir / "app.go").write_text("package main\n\nfunc main() {}\n")
    assessment = ProjectAnalyzer().analyze(custom_dir)
    assert assessment.language is LanguageKind.GO


def test_detects_missing_everything_for_an_empty_project(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')\n")
    assessment = ProjectAnalyzer().analyze(tmp_path)
    assert assessment.containerization_status is MaturityStatus.MISSING
    assert assessment.ci_cd_status is MaturityStatus.MISSING
    assert assessment.test_status is MaturityStatus.MISSING


def test_unsupported_project_not_falsely_classified_as_go(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("just some text\n")
    (tmp_path / "README.md").write_text("# Readme\n")
    assessment = ProjectAnalyzer().analyze(tmp_path)
    assert assessment.language is LanguageKind.UNKNOWN
    assert assessment.containerization_status is MaturityStatus.MISSING


def test_flags_a_hardcoded_secret(tmp_path: Path) -> None:
    (tmp_path / "config.py").write_text('API_KEY = "sk-abcdef123456"\n')
    assessment = ProjectAnalyzer().analyze(tmp_path)
    assert assessment.security_findings
