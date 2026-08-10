import pytest

from devops_learn.troubleshooting.menu import (
    MenuKeyError,
    build_diagnosis_menu,
    build_inspection_menu,
    resolve_diagnosis,
    resolve_source,
)
from devops_learn.troubleshooting.scenarios import build_container_wont_start_scenario


def test_inspection_menu_has_one_letter_per_source() -> None:
    scenario = build_container_wont_start_scenario()
    step = scenario.steps[0]
    menu = build_inspection_menu(step)
    assert [o.key for o in menu] == ["A", "B", "C", "D"]


def test_resolve_source_by_letter() -> None:
    scenario = build_container_wont_start_scenario()
    step = scenario.steps[0]
    source = resolve_source(step, "b")
    assert source.id == "container_logs"


def test_resolve_source_with_unknown_letter_raises() -> None:
    scenario = build_container_wont_start_scenario()
    step = scenario.steps[0]
    with pytest.raises(MenuKeyError):
        resolve_source(step, "Z")


def test_diagnosis_menu_and_resolve_round_trip() -> None:
    scenario = build_container_wont_start_scenario()
    menu = build_diagnosis_menu(scenario)
    first_key = menu[0].key
    diagnosis = resolve_diagnosis(scenario, first_key)
    assert diagnosis.key == scenario.candidate_diagnoses[0].key
