from devops_learn.domain.enums import CompetencyCode
from devops_learn.domain.troubleshooting_models import (
    Diagnosis,
    EvidenceSource,
    FailureScenario,
    Resolution,
    TroubleshootingStep,
)


def test_failure_scenario_tracks_exactly_one_correct_diagnosis() -> None:
    scenario = FailureScenario(
        id="container_wont_start",
        title="The API container will not start",
        narrative="The API container will not start.",
        steps=(
            TroubleshootingStep(
                prompt="What should you inspect?",
                sources=(
                    EvidenceSource(
                        id="container_logs",
                        label="Container logs",
                        evidence_text="Error: PORT environment variable is not set.",
                        is_relevant=True,
                    ),
                    EvidenceSource(
                        id="dns",
                        label="DNS",
                        evidence_text="DNS resolution looks normal.",
                        is_relevant=False,
                    ),
                ),
            ),
        ),
        candidate_diagnoses=(
            Diagnosis(key="missing_port_env_var", label="Missing PORT env var", is_correct=True),
            Diagnosis(key="bad_image", label="Corrupted image", is_correct=False),
        ),
        resolution=Resolution(
            diagnosis_key="missing_port_env_var",
            explanation="The application is missing the required PORT environment variable.",
            fix_summary="Set PORT in the container's environment.",
        ),
        competency_codes=(CompetencyCode.TROUBLESHOOTING, CompetencyCode.DOCKER),
    )
    correct = [d for d in scenario.candidate_diagnoses if d.is_correct]
    assert len(correct) == 1
    assert correct[0].key == scenario.resolution.diagnosis_key
