"""Environment-based configuration for the platform's own CLI (not the demo app)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from devops_learn.learning.persistence.connection import default_db_path


@dataclass(frozen=True)
class Settings:
    db_path: Path
    anthropic_api_key: str | None


def load_settings() -> Settings:
    db_path_value = os.environ.get("DEVOPS_LEARN_DB_PATH")
    db_path = Path(db_path_value) if db_path_value else default_db_path()
    return Settings(
        db_path=db_path,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
