"""Content authored once per lesson/task, rendered differently per learner settings.

See docs/learning-model.md for how ContentBlock lists are filtered by
ExplanationDepth and arranged by AssistanceLevel in curriculum/renderer.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from devops_learn.domain.enums import ContentBlockKind, ExplanationDepth


@dataclass(frozen=True)
class ChoiceOption:
    key: str
    text: str


@dataclass(frozen=True)
class ComprehensionQuestion:
    """A multiple choice check-for-understanding question."""

    prompt: str
    options: tuple[ChoiceOption, ...]
    correct_key: str
    explanation_correct: str
    explanation_incorrect: str


@dataclass(frozen=True)
class MenuOption:
    """A human control offered to the learner (e.g. 'Give me a hint')."""

    key: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class PredictionPrompt:
    """Asks the learner to predict an outcome before an action is taken.

    See docs/learning-model.md 'prediction system'. The learner's free-text
    answer is recorded as a LearningEvent; it is not graded right or wrong,
    only compared against the recorded outcome_summary for reflection.
    """

    prompt: str
    outcome_summary: str


@dataclass(frozen=True)
class ContentBlock:
    """One tagged unit of authored content.

    ``question`` is populated only when kind is CHECK_QUESTION; ``menu_options``
    only when kind is NEXT_STEP_MENU. Optional payloads are used instead of
    per-kind subclasses because there are only two kinds that carry structured
    data beyond text.
    """

    kind: ContentBlockKind
    text: str
    min_depth: ExplanationDepth = ExplanationDepth.BRIEF
    always_include: bool = False
    question: ComprehensionQuestion | None = None
    menu_options: tuple[MenuOption, ...] = field(default_factory=tuple)
