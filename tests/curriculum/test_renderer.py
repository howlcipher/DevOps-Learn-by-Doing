import pytest

from devops_learn.curriculum.renderer import (
    arrange_by_assistance,
    full_explanation_allowed,
    select_by_depth,
)
from devops_learn.domain.content import ContentBlock
from devops_learn.domain.enums import AssistanceLevel, ContentBlockKind, ExplanationDepth


def _blocks() -> tuple[ContentBlock, ...]:
    return (
        ContentBlock(kind=ContentBlockKind.WHY, text="why", always_include=True),
        ContentBlock(kind=ContentBlockKind.WHAT, text="what"),
        ContentBlock(kind=ContentBlockKind.HOW, text="how", min_depth=ExplanationDepth.NORMAL),
        ContentBlock(
            kind=ContentBlockKind.ANALOGY, text="analogy", min_depth=ExplanationDepth.LEARNING
        ),
        ContentBlock(kind=ContentBlockKind.DETAIL, text="detail", min_depth=ExplanationDepth.DEEP),
    )


class TestSelectByDepth:
    def test_brief_only_shows_always_include_blocks(self) -> None:
        result = select_by_depth(_blocks(), ExplanationDepth.BRIEF)
        assert [b.kind for b in result] == [ContentBlockKind.WHY, ContentBlockKind.WHAT]

    def test_normal_adds_how(self) -> None:
        result = select_by_depth(_blocks(), ExplanationDepth.NORMAL)
        assert ContentBlockKind.HOW in [b.kind for b in result]
        assert ContentBlockKind.ANALOGY not in [b.kind for b in result]

    def test_deep_includes_everything(self) -> None:
        result = select_by_depth(_blocks(), ExplanationDepth.DEEP)
        assert len(result) == len(_blocks())


class TestArrangeByAssistance:
    def _blocks_with_question(self) -> tuple[ContentBlock, ...]:
        return _blocks() + (
            ContentBlock(kind=ContentBlockKind.CHECK_QUESTION, text="q"),
        )

    def test_guided_withholds_nothing(self) -> None:
        arranged = arrange_by_assistance(self._blocks_with_question(), AssistanceLevel.GUIDED)
        assert arranged.on_demand == ()
        assert ContentBlockKind.HOW in [b.kind for b in arranged.proactive]

    def test_assisted_withholds_how(self) -> None:
        arranged = arrange_by_assistance(self._blocks_with_question(), AssistanceLevel.ASSISTED)
        assert [b.kind for b in arranged.on_demand] == [ContentBlockKind.HOW]
        assert ContentBlockKind.HOW not in [b.kind for b in arranged.proactive]

    def test_challenge_withholds_how_and_asks_question_first(self) -> None:
        arranged = arrange_by_assistance(self._blocks_with_question(), AssistanceLevel.CHALLENGE)
        assert arranged.proactive[0].kind == ContentBlockKind.CHECK_QUESTION
        assert ContentBlockKind.HOW not in [b.kind for b in arranged.proactive]

    def test_independent_withholds_what_and_how(self) -> None:
        arranged = arrange_by_assistance(self._blocks_with_question(), AssistanceLevel.INDEPENDENT)
        withheld_kinds = {b.kind for b in arranged.on_demand}
        assert withheld_kinds == {ContentBlockKind.WHAT, ContentBlockKind.HOW}
        assert arranged.proactive[0].kind == ContentBlockKind.CHECK_QUESTION

    def test_next_step_menu_is_never_withheld(self) -> None:
        blocks = self._blocks_with_question() + (
            ContentBlock(kind=ContentBlockKind.NEXT_STEP_MENU, text="menu"),
        )
        arranged = arrange_by_assistance(blocks, AssistanceLevel.INDEPENDENT)
        assert ContentBlockKind.NEXT_STEP_MENU in [b.kind for b in arranged.proactive]


class TestFullExplanationAllowed:
    @pytest.mark.parametrize(
        "level,hints_used,expected",
        [
            (AssistanceLevel.GUIDED, 1, True),
            (AssistanceLevel.GUIDED, 0, False),
            (AssistanceLevel.ASSISTED, 1, False),
            (AssistanceLevel.ASSISTED, 2, True),
            (AssistanceLevel.CHALLENGE, 2, False),
            (AssistanceLevel.INDEPENDENT, 2, False),
        ],
    )
    def test_threshold_by_level(
        self, level: AssistanceLevel, hints_used: int, expected: bool
    ) -> None:
        allowed = full_explanation_allowed(
            level, hints_used=hints_used, total_hints=3, explicitly_requested=False
        )
        assert allowed is expected

    def test_exhausting_all_hints_always_unlocks_it(self) -> None:
        allowed = full_explanation_allowed(
            AssistanceLevel.INDEPENDENT, hints_used=3, total_hints=3, explicitly_requested=False
        )
        assert allowed is True

    def test_explicit_request_always_unlocks_it(self) -> None:
        allowed = full_explanation_allowed(
            AssistanceLevel.INDEPENDENT, hints_used=0, total_hints=3, explicitly_requested=True
        )
        assert allowed is True
