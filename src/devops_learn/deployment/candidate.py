"""Immutable, deterministic evidence binding for a deployment.

The candidate's identity deliberately excludes its creation timestamp.  The
same source, image, plan, and security evidence therefore produce the same
identity, while the timestamp remains useful audit context.  Approval records
must name this identity; changing any material evidence creates a new one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return a stable digest without ever rendering the file's content."""
    digest = sha256()
    with path.open("rb") as artifact:
        for block in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class DeploymentCandidate:
    """Exactly the deployable evidence a human is authorizing."""

    source_revision: str
    project_path: str
    cloud: str
    environment: str
    terraform_config_digest: str
    terraform_plan_path: str | None = None
    terraform_plan_digest: str | None = None
    terraform_plan_risk: str | None = None
    security_report_path: str | None = None
    security_report_digest: str | None = None
    security_decision: str | None = None
    image_reference: str | None = None
    image_digest: str | None = None
    deployment_eligibility: str | None = None
    human_approvals: tuple[str, ...] = ()
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.terraform_plan_digest and not self.terraform_plan_path:
            raise ValueError("A Terraform plan digest requires a saved plan path.")
        if self.security_report_digest and not self.security_report_path:
            raise ValueError("A security report digest requires its report path.")
        if self.image_digest and not self.image_reference:
            raise ValueError("An image digest requires an image reference.")

    @property
    def identity(self) -> str:
        """Stable SHA-256 identity of the material, approval-relevant state."""
        encoded = json.dumps(self.material(), sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

    @property
    def context_identity(self) -> str:
        """Pre-plan binding for a saved plan; excludes only its own digest."""
        material = self.material()
        material["terraform_plan_digest"] = None
        material["terraform_plan_risk"] = None
        encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        return sha256(encoded).hexdigest()

    def material(self) -> dict[str, str | None]:
        return {
            "source_revision": self.source_revision,
            "project_path": self.project_path,
            "cloud": self.cloud,
            "environment": self.environment,
            "terraform_config_digest": self.terraform_config_digest,
            "terraform_plan_digest": self.terraform_plan_digest,
            "terraform_plan_risk": self.terraform_plan_risk,
            "security_report_digest": self.security_report_digest,
            "security_decision": self.security_decision,
            "image_reference": self.image_reference,
            "image_digest": self.image_digest,
        }

    def is_current(self) -> bool:
        """Check that persisted evidence still matches the candidate."""
        return all(
            (
                not self.terraform_plan_path
                or self.terraform_plan_digest == sha256_file(Path(self.terraform_plan_path)),
                not self.security_report_path
                or self.security_report_digest == sha256_file(Path(self.security_report_path)),
            )
        )
