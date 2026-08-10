"""sqlite3 connection helpers. All SQL for the platform is confined to persistence/."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def default_db_path() -> Path:
    return Path.home() / ".devops_learn" / "learning.db"


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_in_memory() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
