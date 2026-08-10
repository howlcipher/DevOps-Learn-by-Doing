import pytest

from devops_learn.tools.approval import (
    AutoApproveApprovalGate,
    AutoDenyApprovalGate,
    CliApprovalGate,
    RiskLevel,
)


def _answer(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    monkeypatch.setattr("builtins.input", lambda *_: text)


@pytest.mark.parametrize("answer", ["y", "Y", "yes", " YES "])
def test_cli_gate_grants_on_an_affirmative_answer(
    monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    _answer(monkeypatch, answer)

    record = CliApprovalGate().request("delete_namespace", RiskLevel.DESTRUCTIVE, {})

    assert record.granted is True
    assert record.approved_by == "learner"


@pytest.mark.parametrize("answer", ["", "n", "no", "maybe"])
def test_cli_gate_denies_anything_else_including_an_empty_answer(
    monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    _answer(monkeypatch, answer)

    record = CliApprovalGate().request("delete_namespace", RiskLevel.DESTRUCTIVE, {})

    assert record.granted is False


def test_cli_gate_shows_the_operation_risk_and_parameters(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _answer(monkeypatch, "n")

    CliApprovalGate().request(
        "delete_resource_group", RiskLevel.DESTRUCTIVE, {"resource_group": "rg-test"}
    )
    output = capsys.readouterr().out

    assert "APPROVAL REQUIRED" in output
    assert "delete_resource_group" in output
    assert "DESTRUCTIVE" in output
    assert "rg-test" in output


def test_scripted_gates_identify_themselves_as_non_human() -> None:
    approved = AutoApproveApprovalGate().request("plan", RiskLevel.SAFE, {})
    denied = AutoDenyApprovalGate().request("plan", RiskLevel.SAFE, {})

    assert (approved.granted, approved.approved_by) == (True, "test-auto-approve")
    assert (denied.granted, denied.approved_by) == (False, "test-auto-deny")
