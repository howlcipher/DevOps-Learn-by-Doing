from devops_learn.tools.approval import (
    AutoApproveApprovalGate,
    AutoDenyApprovalGate,
    ThresholdApprovalGate,
)
from devops_learn.tools.base import RiskLevel


def test_threshold_gate_auto_approves_below_threshold() -> None:
    inner = AutoDenyApprovalGate()
    gate = ThresholdApprovalGate(inner, RiskLevel.HIGH)
    record = gate.request("safe-op", RiskLevel.SAFE, {})
    assert record.granted
    assert record.approved_by == "auto-below-threshold"


def test_threshold_gate_delegates_at_or_above_threshold() -> None:
    inner = AutoApproveApprovalGate()
    gate = ThresholdApprovalGate(inner, RiskLevel.LOW)
    record = gate.request("low-op", RiskLevel.LOW, {})
    assert record.granted
    assert record.approved_by == "test-auto-approve"


def test_threshold_gate_can_deny_when_inner_denies() -> None:
    inner = AutoDenyApprovalGate()
    gate = ThresholdApprovalGate(inner, RiskLevel.LOW)
    record = gate.request("high-op", RiskLevel.HIGH, {})
    assert not record.granted
