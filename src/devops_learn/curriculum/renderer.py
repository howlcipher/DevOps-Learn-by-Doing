"""Assistance level x explanation depth composition.

Content is authored once as a list of tagged ContentBlocks (see domain/content.py)
and rendered N ways by composing two independent, pure functions:

- select_by_depth: a monotonic threshold filter controlling HOW MUCH is said.
- arrange_by_assistance: controls WHAT is revealed proactively versus withheld
  until the learner asks for it or escalates through hints.

Explicit rule table (write once, keep in sync with tests in
tests/curriculum/test_renderer.py):

| Level        | WHY | WHAT | HOW proactive | CHECK_QUESTION timing        |
|--------------|-----|------|----------------|-------------------------------|
| GUIDED       | yes | yes  | yes            | after WHY/WHAT/HOW            |
| ASSISTED     | yes | yes  | withheld       | after WHY/WHAT                |
| CHALLENGE    | yes | yes  | withheld       | before WHAT (predict first)   |
| INDEPENDENT  | yes | withheld | withheld   | before any content (cold)     |

DETAIL/ANALOGY/PITFALL/elaborated HOW text are additionally gated by
ExplanationDepth via ``min_depth`` regardless of assistance level.

full_explanation_allowed encodes the separate hint-escalation gate: GUIDED
offers it after 1 hint, ASSISTED after 2, CHALLENGE only once every hint is
exhausted, INDEPENDENT never proactively (only on explicit request, or when
continuing is otherwise impossible).
"""

from __future__ import annotations

from dataclasses import dataclass

from devops_learn.domain.content import ContentBlock
from devops_learn.domain.enums import AssistanceLevel, ContentBlockKind, ExplanationDepth

_NEVER_WITHHELD_KINDS = frozenset(
    {ContentBlockKind.CHECK_QUESTION, ContentBlockKind.NEXT_STEP_MENU}
)

_WITHHELD_KINDS_BY_LEVEL: dict[AssistanceLevel, frozenset[ContentBlockKind]] = {
    AssistanceLevel.GUIDED: frozenset(),
    AssistanceLevel.ASSISTED: frozenset({ContentBlockKind.HOW}),
    AssistanceLevel.CHALLENGE: frozenset({ContentBlockKind.HOW}),
    AssistanceLevel.INDEPENDENT: frozenset({ContentBlockKind.HOW, ContentBlockKind.WHAT}),
}

_PREDICT_FIRST_LEVELS = frozenset({AssistanceLevel.CHALLENGE, AssistanceLevel.INDEPENDENT})


@dataclass(frozen=True)
class ArrangedContent:
    """proactive is shown immediately; on_demand is available via a menu/hint request."""

    proactive: tuple[ContentBlock, ...]
    on_demand: tuple[ContentBlock, ...]


def select_by_depth(
    blocks: tuple[ContentBlock, ...], depth: ExplanationDepth
) -> tuple[ContentBlock, ...]:
    """Monotonic threshold filter: a block is included once depth >= its min_depth."""

    return tuple(b for b in blocks if b.always_include or b.min_depth <= depth)


def arrange_by_assistance(
    blocks: tuple[ContentBlock, ...], level: AssistanceLevel
) -> ArrangedContent:
    withheld_kinds = _WITHHELD_KINDS_BY_LEVEL[level]
    proactive: list[ContentBlock] = []
    on_demand: list[ContentBlock] = []
    for block in blocks:
        never_withheld = block.always_include or block.kind in _NEVER_WITHHELD_KINDS
        if not never_withheld and block.kind in withheld_kinds:
            on_demand.append(block)
        else:
            proactive.append(block)

    if level in _PREDICT_FIRST_LEVELS:
        proactive = _move_check_question_first(proactive)

    return ArrangedContent(proactive=tuple(proactive), on_demand=tuple(on_demand))


def _move_check_question_first(blocks: list[ContentBlock]) -> list[ContentBlock]:
    questions = [b for b in blocks if b.kind == ContentBlockKind.CHECK_QUESTION]
    others = [b for b in blocks if b.kind != ContentBlockKind.CHECK_QUESTION]
    return questions + others


def render_content(
    blocks: tuple[ContentBlock, ...], level: AssistanceLevel, depth: ExplanationDepth
) -> ArrangedContent:
    """render_lesson/task content = arrange_by_assistance(select_by_depth(blocks, depth), level)."""

    return arrange_by_assistance(select_by_depth(blocks, depth), level)


_FULL_EXPLANATION_HINT_THRESHOLD: dict[AssistanceLevel, int | None] = {
    AssistanceLevel.GUIDED: 1,
    AssistanceLevel.ASSISTED: 2,
    AssistanceLevel.CHALLENGE: None,  # only once every hint is exhausted
    AssistanceLevel.INDEPENDENT: None,  # never proactively
}


def full_explanation_allowed(
    level: AssistanceLevel,
    hints_used: int,
    total_hints: int,
    *,
    explicitly_requested: bool,
) -> bool:
    if explicitly_requested:
        return True
    if total_hints > 0 and hints_used >= total_hints:
        return True  # otherwise impossible to continue
    threshold = _FULL_EXPLANATION_HINT_THRESHOLD[level]
    if threshold is None:
        return False
    return hints_used >= threshold
