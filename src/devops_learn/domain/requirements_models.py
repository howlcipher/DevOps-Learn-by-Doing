"""Likely DevOps requirements inferred from a ProjectAssessment.

Kept distinct from Recommendation (recommendations/service.py): a
DetectedRequirement says "this project probably needs X"; a Recommendation
says "here is the specific way to satisfy that, and the tradeoffs."
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedRequirement:
    id: str
    title: str
    rationale: str
    confidence: float  # 0.0-1.0
    is_assumption: bool = False
