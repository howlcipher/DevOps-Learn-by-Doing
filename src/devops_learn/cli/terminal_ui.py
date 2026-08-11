"""TerminalUi: the only Ui implementation wired into the real CLI."""

from __future__ import annotations

from devops_learn.domain.question_models import ClarifyingQuestion
from devops_learn.workflows.ui import Ui


class TerminalUi(Ui):
    def present(self, text: str) -> None:
        print()
        print(text)

    def ask_choice(self, question: ClarifyingQuestion) -> str:
        print()
        print(question.prompt)
        if not question.options:
            return input("> ").strip()
        for i, option in enumerate(question.options, start=1):
            print(f"  {i}. {option}")
        while True:
            raw = input("> ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(question.options):
                return question.options[int(raw) - 1]
            print(f"Enter a number from 1 to {len(question.options)}.")

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        answer = input(f"{prompt} {suffix} ").strip().lower()
        if not answer:
            return default
        return answer in ("y", "yes")
