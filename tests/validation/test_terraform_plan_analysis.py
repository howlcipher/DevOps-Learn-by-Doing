from devops_learn.domain.enums import ChangeAction
from devops_learn.tools.approval import RiskLevel
from devops_learn.validation.terraform_plan_analysis import analyze


def test_create_only_plan_is_safe() -> None:
    summary = analyze({"create": 8, "change": 0, "replace": 0, "destroy": 0})
    assert summary.risk_level is RiskLevel.SAFE
    assert summary.count(ChangeAction.CREATE) == 8


def test_replace_triggers_high_risk() -> None:
    summary = analyze({"create": 7, "change": 0, "replace": 1, "destroy": 0})
    assert summary.risk_level is RiskLevel.HIGH
    assert summary.count(ChangeAction.REPLACE) == 1


def test_destroy_triggers_destructive_risk() -> None:
    summary = analyze({"create": 0, "change": 0, "replace": 0, "destroy": 2})
    assert summary.risk_level is RiskLevel.DESTRUCTIVE
