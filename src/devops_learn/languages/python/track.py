"""The only fully implemented LanguageTrack in V1.

Describes projects/api_platform/, the learner-facing FastAPI demo app; this
module contains no application code itself, only the track description.
"""

from __future__ import annotations

from devops_learn.domain.enums import LanguageTrackKind
from devops_learn.languages.base.language_track import LanguageTrack


class PythonTrack(LanguageTrack):
    @property
    def kind(self) -> LanguageTrackKind:
        return LanguageTrackKind.PYTHON

    @property
    def is_available(self) -> bool:
        return True

    def demo_app_summary(self) -> str:
        return (
            "A small FastAPI application with environment-variable configuration and "
            "structured logging, deliberately kept minimal: it exists to teach DevOps, "
            "not to be a large application-development project."
        )

    def demo_app_endpoints(self) -> tuple[str, ...]:
        return ("GET /health", "GET /info")
