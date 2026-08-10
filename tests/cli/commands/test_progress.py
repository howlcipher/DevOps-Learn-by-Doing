import argparse

import pytest

from devops_learn.cli.commands import progress
from devops_learn.domain.competency_models import LearnerCompetency
from devops_learn.domain.enums import CompetencyCode, CompetencyState
from devops_learn.tutor.bootstrap import Platform

from tests.conftest import FIXED_NOW


def test_prompts_to_start_when_no_profile_exists(
    platform: Platform, capsys: pytest.CaptureFixture[str]
) -> None:
    progress.run(argparse.Namespace(), platform)
    assert "devops-learn start" in capsys.readouterr().out


def test_prints_summary_sections_for_an_existing_profile(
    platform: Platform, learner_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    platform.competency_repository.upsert_state(
        LearnerCompetency(
            learner_id=learner_id,
            code=CompetencyCode.DOCKER,
            state=CompetencyState.PRACTICED,
            updated_at=FIXED_NOW,
        )
    )

    progress.run(argparse.Namespace(), platform)
    output = capsys.readouterr().out

    summary = platform.summary_service.build_summary(learner_id)
    assert "TODAY'S PROGRESS" in output
    assert "Recommended next step:" in output
    assert summary.recommended_next_step in output
    for line in summary.competency_lines + summary.narrative_lines:
        assert line in output
