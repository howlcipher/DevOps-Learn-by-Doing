from devops_learn.ai.mock_provider import MockLLMProvider
from devops_learn.curriculum.content_library import build_api_platform_project
from devops_learn.domain.enums import AssistanceLevel, ExplanationDepth
from devops_learn.domain.troubleshooting_models import EvidenceSource, FailureScenario, Resolution


def _task():
    project = build_api_platform_project()
    return project.modules[1].lessons[0].tasks[0]  # task_write_dockerfile


def test_explain_topic_is_deterministic() -> None:
    provider = MockLLMProvider()
    first = provider.explain_topic(
        "Dockerfiles", level=AssistanceLevel.GUIDED, depth=ExplanationDepth.NORMAL
    )
    second = provider.explain_topic(
        "Dockerfiles", level=AssistanceLevel.GUIDED, depth=ExplanationDepth.NORMAL
    )
    assert first == second
    assert first.title == "Dockerfiles"


def test_assess_open_response_never_grades_predictions_right_or_wrong() -> None:
    provider = MockLLMProvider()
    assessment = provider.assess_open_response(_task(), "It will use the cache.")
    assert assessment.is_correct is None
    assert assessment.task_id == _task().id


def test_assess_open_response_handles_empty_answer() -> None:
    provider = MockLLMProvider()
    assessment = provider.assess_open_response(_task(), "   ")
    assert "guess" in assessment.feedback.lower()


def test_troubleshooting_feedback_reflects_source_relevance() -> None:
    provider = MockLLMProvider()
    scenario = FailureScenario(
        id="s",
        title="t",
        narrative="n",
        steps=(),
        candidate_diagnoses=(),
        resolution=Resolution(diagnosis_key="k", explanation="e", fix_summary="f"),
        competency_codes=(),
    )
    relevant = EvidenceSource(
        id="logs", label="Container logs", evidence_text="x", is_relevant=True
    )
    irrelevant = EvidenceSource(id="dns", label="DNS", evidence_text="y", is_relevant=False)

    assert provider.give_troubleshooting_feedback(scenario, relevant).is_on_track is True
    assert provider.give_troubleshooting_feedback(scenario, irrelevant).is_on_track is False


def test_narrate_summary_does_not_invent_facts() -> None:
    provider = MockLLMProvider()
    lines = ("Docker: Practiced.", "Terraform: Introduced.")
    narrative = provider.narrate_summary(lines)
    assert "Docker: Practiced." in narrative
    assert "Terraform: Introduced." in narrative
