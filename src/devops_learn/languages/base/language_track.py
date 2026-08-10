"""LanguageTrack: the interface a project's application-language content implements.

Not implemented tracks (Go in V1) declare is_available=False and raise
ComingSoonError from every other method, rather than faking parity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from devops_learn.domain.enums import LanguageTrackKind


class LanguageTrack(ABC):
    @property
    @abstractmethod
    def kind(self) -> LanguageTrackKind: ...

    @property
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def demo_app_summary(self) -> str:
        """A short description of the demo application this track teaches against."""

    @abstractmethod
    def demo_app_endpoints(self) -> tuple[str, ...]:
        """E.g. ('GET /health', 'GET /info')."""
