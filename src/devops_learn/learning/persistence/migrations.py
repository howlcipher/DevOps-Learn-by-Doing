"""Applies schema.sql idempotently. One schema version for V1; no framework needed."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from importlib import resources

SCHEMA_VERSION = 1


def ensure_schema(conn: sqlite3.Connection) -> None:
    schema_sql = (
        resources.files("devops_learn.learning.persistence").joinpath("schema.sql").read_text()
    )
    with conn:
        conn.executescript(schema_sql)
        applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = ?", (SCHEMA_VERSION,)
        ).fetchone()
        if applied is None:
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now(timezone.utc).isoformat()),
            )
