"""Extension point only. Not implemented in V1: see docs/roadmap.md."""

from __future__ import annotations

from devops_learn.domain.enums import LanguageTrackKind
from devops_learn.errors import ComingSoonError
from devops_learn.languages.base.language_track import LanguageTrack


class GoTrack(LanguageTrack):
    @property
    def kind(self) -> LanguageTrackKind:
        return LanguageTrackKind.GO

    @property
    def is_available(self) -> bool:
        return False

    def demo_app_summary(self) -> str:
        raise ComingSoonError("Go is not implemented yet. Python is the V1 language path.")

    def demo_app_endpoints(self) -> tuple[str, ...]:
        raise ComingSoonError("Go is not implemented yet. Python is the V1 language path.")
