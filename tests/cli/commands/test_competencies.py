import argparse

import pytest

from devops_learn.cli.commands import competencies
from devops_learn.domain.competency_models import LearnerCompetency
from devops_learn.domain.enums import CompetencyCode, CompetencyState
from devops_learn.tutor.bootstrap import Platform

from tests.conftest import FIXED_NOW


def test_prompts_to_start_when_no_profile_exists(
    platform: Platform, capsys: pytest.CaptureFixture[str]
) -> None:
    competencies.run(argparse.Namespace(), platform)
    assert "devops-learn start" in capsys.readouterr().out


def test_reports_when_a_profile_has_no_tracked_competencies(
    platform: Platform, learner_id: int, capsys: pytest.CaptureFixture[str]
) -> None:
    competencies.run(argparse.Namespace(), platform)
    assert "No competencies tracked yet." in capsys.readouterr().out


def test_lists_each_persisted_competency_state(
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

    competencies.run(argparse.Namespace(), platform)
    output = capsys.readouterr().out

    assert f"{CompetencyCode.DOCKER.value}: Practiced" in output
