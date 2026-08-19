"""ProjectAnalyzer: inspects a real repository on disk and produces a
ProjectAssessment.

Detection here is heuristic and deliberately conservative: it is confined to
cheap, explainable filesystem/text checks (file presence, a handful of regex
patterns) rather than executing anything or invoking an LLM. Findings that
cannot be observed directly are recorded as Assumption, not asserted as fact.
This keeps analysis fast, deterministic, and safe to run against a project
the platform has never seen, per docs/architecture.md#project-analysis.
"""

from __future__ import annotations

import re
from pathlib import Path

from devops_learn.domain.analysis_models import Assumption, ProjectAssessment
from devops_learn.domain.enums import LanguageKind, MaturityStatus

_IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}

_FRAMEWORK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bfrom\s+fastapi\b|\bimport\s+fastapi\b", "FastAPI"),
    (r"\bfrom\s+flask\b|\bimport\s+flask\b", "Flask"),
    (r"\bfrom\s+django\b|\bimport\s+django\b", "Django"),
    (r"\bgin-gonic/gin\b", "Gin"),
    (r'"net/http"', "net/http"),
)

_DATABASE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"psycopg2|sqlalchemy|asyncpg", "PostgreSQL"),
    (r"pymysql|mysqlclient", "MySQL"),
    (r"pymongo|mongoengine", "MongoDB"),
    (r"redis", "Redis"),
)

_SECRET_NAME_PATTERN = re.compile(
    r"(?:os\.(?:environ(?:\.get)?|getenv|Getenv|LookupEnv))\("
    r"\s*['\"]([A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*)"
)
_ENV_VAR_PATTERN = re.compile(
    r"(?:os\.(?:environ(?:\.get)?|getenv|Getenv|LookupEnv))\(\s*['\"]([A-Z0-9_]+)"
)
_HARDCODED_SECRET_PATTERN = re.compile(
    r"(?:API_KEY|SECRET|PASSWORD|TOKEN)\s*=\s*['\"][^'\"$]{6,}['\"]"
)


def _iter_source_files(root: Path, *, suffixes: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if any(part in _IGNORED_DIRS for part in path.parts):
            continue
        files.append(path)
    return files


def _read_text(path: Path) -> str:
    try:
        return path.read_text(errors="ignore")
    except OSError:
        return ""


class ProjectAnalyzer:
    """Stateless: analyze() takes the repository path each call."""

    def analyze(self, root: str | Path) -> ProjectAssessment:
        root = Path(root).resolve()

        language, source_files = self._detect_language(root)
        source_text = "\n".join(_read_text(f) for f in source_files)

        framework = self._detect_framework(source_text)
        containerization = self._status(
            any(root.glob("Dockerfile*")) or (root / "Dockerfile").exists()
        )
        ci_cd = self._status(self._has_ci_workflows(root))
        iac = self._status(bool(list(root.rglob("*.tf"))))
        k8s_present = bool(list(root.rglob("*.yaml"))) and self._has_k8s_manifest(root)
        cloud = self._status(iac is MaturityStatus.GOOD or k8s_present)
        healthcheck = self._status(bool(re.search(r"/health\b", source_text)))
        test_status = self._detect_test_status(root)
        observability = self._detect_observability(source_text)

        database_dependencies = tuple(
            sorted(
                {
                    name
                    for pattern, name in _DATABASE_PATTERNS
                    if re.search(pattern, source_text, re.I)
                }
            )
        )
        secret_names = sorted(set(_SECRET_NAME_PATTERN.findall(source_text)))
        env_var_names = sorted(set(_ENV_VAR_PATTERN.findall(source_text)))

        security_findings = []
        if _HARDCODED_SECRET_PATTERN.search(source_text):
            security_findings.append(
                "A credential-shaped value appears to be assigned directly in source rather "
                "than read from the environment or a secret store."
            )

        operational_risks = []
        if ci_cd is MaturityStatus.GOOD and containerization is MaturityStatus.MISSING:
            operational_risks.append("CI/CD exists but there is no container build step.")
        if cloud is MaturityStatus.GOOD and observability is MaturityStatus.MISSING:
            operational_risks.append(
                "Cloud deployment is configured but no logging/monitoring was found."
            )

        assumptions = []
        if framework is not None:
            assumptions.append(
                Assumption(
                    text="The application is intended to be reachable over HTTP.",
                    confidence=0.7,
                )
            )
        if secret_names and cloud is not MaturityStatus.GOOD:
            assumptions.append(
                Assumption(
                    text=(
                        "Secrets referenced from the environment need managed storage once "
                        "deployed."
                    ),
                    confidence=0.8,
                )
            )

        application_type = f"{framework} HTTP API" if framework else "Unclassified application"

        notes = [f"Analyzed {len(source_files)} source file(s) under {root}."]

        return ProjectAssessment(
            root_path=str(root),
            application_type=application_type,
            language=language,
            framework=framework,
            containerization_status=containerization,
            ci_cd_status=ci_cd,
            iac_status=iac,
            cloud_status=cloud,
            healthcheck_status=healthcheck,
            test_status=test_status,
            observability_status=observability,
            database_dependencies=database_dependencies,
            secret_indicators=tuple(secret_names),
            env_var_count=len(env_var_names),
            security_findings=tuple(security_findings),
            operational_risks=tuple(operational_risks),
            assumptions=tuple(assumptions),
            notes=tuple(notes),
        )

    def _detect_language(self, root: Path) -> tuple[LanguageKind, list[Path]]:
        go_files = _iter_source_files(root, suffixes=(".go",))
        if (root / "go.mod").exists() or go_files:
            return LanguageKind.GO, go_files
        py_files = _iter_source_files(root, suffixes=(".py",))
        if (root / "pyproject.toml").exists() or (root / "requirements.txt").exists() or py_files:
            return LanguageKind.PYTHON, py_files
        return LanguageKind.UNKNOWN, []

    def _detect_framework(self, source_text: str) -> str | None:
        for pattern, name in _FRAMEWORK_PATTERNS:
            if re.search(pattern, source_text):
                return name
        return None

    def _has_ci_workflows(self, root: Path) -> bool:
        workflows_dir = root / ".github" / "workflows"
        if not workflows_dir.is_dir():
            return False
        return any(workflows_dir.glob("*.yml")) or any(workflows_dir.glob("*.yaml"))

    def _has_k8s_manifest(self, root: Path) -> bool:
        for path in root.rglob("*.y*ml"):
            if any(part in _IGNORED_DIRS for part in path.parts):
                continue
            text = _read_text(path)
            if re.search(r"^kind:\s*(Deployment|Service|Pod)", text, re.MULTILINE):
                return True
        return False

    def _detect_test_status(self, root: Path) -> MaturityStatus:
        test_files = [
            p for p in root.rglob("test_*.py") if not any(part in _IGNORED_DIRS for part in p.parts)
        ] + [
            p for p in root.rglob("*_test.go") if not any(part in _IGNORED_DIRS for part in p.parts)
        ]
        if len(test_files) >= 2:
            return MaturityStatus.GOOD
        if test_files:
            return MaturityStatus.PARTIAL
        return MaturityStatus.MISSING

    def _detect_observability(self, source_text: str) -> MaturityStatus:
        if re.search(
            r"prometheus|opentelemetry|application insights|log analytics", source_text, re.I
        ):
            return MaturityStatus.GOOD
        observability_pattern = (
            r"\blogging\.(getLogger|basicConfig)\b|structlog|"
            r"\b(?:log|slog)\.(?:New|Info|Debug|Warn|Error|Printf|Print|Println)\b|"
            r"\b(?:zap|logrus)\b"
        )
        if re.search(observability_pattern, source_text):
            return MaturityStatus.PARTIAL
        return MaturityStatus.MISSING

    def _status(self, present: bool) -> MaturityStatus:
        return MaturityStatus.GOOD if present else MaturityStatus.MISSING
