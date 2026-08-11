"""Ui: the only interaction seam workflows use, so the same workflow function
can run against a terminal today and a future web UI later without change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from devops_learn.domain.question_models import ClarifyingQuestion


class Ui(ABC):
    @abstractmethod
    def present(self, text: str) -> None: ...

    @abstractmethod
    def ask_choice(self, question: ClarifyingQuestion) -> str:
        """Returns the chosen option text (or free text if the question has none)."""

    @abstractmethod
    def confirm(self, prompt: str, *, default: bool = False) -> bool: ...
