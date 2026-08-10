"""Renders a TurnResult as the structured WHY/WHAT/HOW... text the spec describes.

Kept separate from TutorOrchestrator so presentation formatting can change
without touching business logic, and so it's testable by capturing stdout.
"""

from __future__ import annotations

from devops_learn.domain.content import ContentBlock
from devops_learn.domain.enums import ContentBlockKind
from devops_learn.tutor.orchestrator import TurnResult

_HEADER_BY_KIND = {
    ContentBlockKind.WHY: "WHY",
    ContentBlockKind.WHAT: "WHAT",
    ContentBlockKind.HOW: "HOW",
    ContentBlockKind.DETAIL: "MORE DETAIL",
    ContentBlockKind.ANALOGY: "ANALOGY",
    ContentBlockKind.PITFALL: "WATCH OUT FOR",
}


def render_turn(turn: TurnResult) -> None:
    print()
    print(turn.heading.upper())
    print()
    for block in turn.blocks:
        _render_block(block)
    if turn.prediction is not None:
        print("PREDICTION")
        print(turn.prediction.prompt)
        print("(type your prediction and press enter)")
        print()
    if turn.status_message:
        print(turn.status_message)
        print()
    if turn.menu:
        print("OPTIONS")
        for option in turn.menu:
            print(f"{option.key}. {option.label}")
        print()
    if turn.is_terminal:
        print("(session complete)")
        print()


def _render_block(block: ContentBlock) -> None:
    if block.kind == ContentBlockKind.CHECK_QUESTION:
        assert block.question is not None
        print("QUESTION")
        print(block.question.prompt)
        for option in block.question.options:
            print(f"{option.key}. {option.text}")
        print()
        return
    if block.kind == ContentBlockKind.NEXT_STEP_MENU:
        return  # already surfaced via turn.menu
    header = _HEADER_BY_KIND.get(block.kind)
    if header is None:
        return
    print(header)
    print(block.text)
    print()
