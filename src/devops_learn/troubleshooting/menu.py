"""Pure functions building letter-labeled menus for a troubleshooting scenario.

Kept separate from TroubleshootingService so menu presentation logic (which
letter maps to which source/diagnosis) is independently testable and reusable
by the CLI presenter without duplicating the mapping.
"""

from __future__ import annotations

from devops_learn.domain.content import MenuOption
from devops_learn.domain.troubleshooting_models import (
    Diagnosis,
    EvidenceSource,
    FailureScenario,
    TroubleshootingStep,
)

_LETTERS = "ABCDEFGH"


class MenuKeyError(KeyError):
    pass


def build_inspection_menu(step: TroubleshootingStep) -> tuple[MenuOption, ...]:
    return tuple(
        MenuOption(key=_LETTERS[i], label=source.label) for i, source in enumerate(step.sources)
    )


def resolve_source(step: TroubleshootingStep, key: str) -> EvidenceSource:
    for letter, source in zip(_LETTERS, step.sources):
        if letter == key.strip().upper():
            return source
    raise MenuKeyError(f"No evidence source for menu key '{key}'")


def build_diagnosis_menu(scenario: FailureScenario) -> tuple[MenuOption, ...]:
    return tuple(
        MenuOption(key=_LETTERS[i], label=d.label)
        for i, d in enumerate(scenario.candidate_diagnoses)
    )


def resolve_diagnosis(scenario: FailureScenario, key: str) -> Diagnosis:
    for letter, diagnosis in zip(_LETTERS, scenario.candidate_diagnoses):
        if letter == key.strip().upper():
            return diagnosis
    raise MenuKeyError(f"No diagnosis for menu key '{key}'")
