"""Human approval gating. Lower-tier module: base.py depends on this, not the reverse.

RiskLevel lives here (not in base.py) so ApprovalGate has no dependency on
Tool/ToolOperationSpec; it only needs to know an operation's name and risk.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Mapping


class RiskLevel(Enum):
    SAFE = auto()
    LOW = auto()
    HIGH = auto()
    DESTRUCTIVE = auto()


@dataclass(frozen=True)
class ApprovalRecord:
    granted: bool
    approved_by: str
    reason: str | None = None
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalGate(ABC):
    @abstractmethod
    def request(
        self, operation_name: str, risk_level: RiskLevel, params: Mapping[str, Any]
    ) -> ApprovalRecord:
        """Returns a decision. Must never be skipped for an operation that requires it."""


class CliApprovalGate(ApprovalGate):
    """Prompts the human in the terminal. The only gate wired into the real CLI."""

    def request(
        self, operation_name: str, risk_level: RiskLevel, params: Mapping[str, Any]
    ) -> ApprovalRecord:
        print()
        print("APPROVAL REQUIRED")
        print(f"Operation: {operation_name}  (risk: {risk_level.name})")
        if params:
            print(f"Parameters: {dict(params)}")
        answer = input("Approve this action? [y/N] ").strip().lower()
        granted = answer in ("y", "yes")
        return ApprovalRecord(granted=granted, approved_by="learner")


class AutoApproveApprovalGate(ApprovalGate):
    """For tests and scripted demos only; never wired into the real CLI."""

    def request(
        self, operation_name: str, risk_level: RiskLevel, params: Mapping[str, Any]
    ) -> ApprovalRecord:
        return ApprovalRecord(granted=True, approved_by="test-auto-approve")


class AutoDenyApprovalGate(ApprovalGate):
    """For tests that must prove a denial is respected."""

    def request(
        self, operation_name: str, risk_level: RiskLevel, params: Mapping[str, Any]
    ) -> ApprovalRecord:
        return ApprovalRecord(granted=False, approved_by="test-auto-deny")


class ThresholdApprovalGate(ApprovalGate):
    """Wraps another gate and only prompts when risk is at least a threshold.

    Useful for GUIDED mode, where even LOW-risk operations should be confirmed.
    """

    def __init__(self, inner: ApprovalGate, threshold: RiskLevel) -> None:
        self._inner = inner
        self._order = (RiskLevel.SAFE, RiskLevel.LOW, RiskLevel.HIGH, RiskLevel.DESTRUCTIVE)
        self._threshold_index = self._order.index(threshold)

    def request(
        self, operation_name: str, risk_level: RiskLevel, params: Mapping[str, Any]
    ) -> ApprovalRecord:
        if self._order.index(risk_level) < self._threshold_index:
            return ApprovalRecord(granted=True, approved_by="auto-below-threshold")
        return self._inner.request(operation_name, risk_level, params)
